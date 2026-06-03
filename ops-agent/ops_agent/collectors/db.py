from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from ops_agent.alert_similarity import build_alert_evidence_payloads
from ops_agent.config import OpsAgentConfig, database_role_warning
from ops_agent.db_queries import QUERIES, validate_read_only_queries
from ops_agent.redaction import RedactionReport, ReferenceMapper, redact_error_message, redact_value
from ops_agent.schemas import Period

ALERT_EVIDENCE_SQL = """
WITH recent_analyses AS (
    SELECT
        eai.id AS event_ai_analysis_id,
        eai.market_event_id,
        eai.analysis_id,
        eai.symbol AS analysis_symbol,
        eai.analysis_type,
        eai.provider,
        eai.model,
        eai.input_hash,
        eai.status AS analysis_status,
        eai.should_alert,
        eai.event_key AS analysis_event_key,
        eai.title AS analysis_title,
        eai.message_body AS analysis_message_body,
        eai.possible_action AS analysis_possible_action,
        eai.urgency,
        eai.confidence,
        eai.reason_for_no_alert AS analysis_reason_for_no_alert,
        eai.related_news_ids,
        eai.plain_text AS analysis_plain_text,
        eai.created_at AS analysis_created_at
    FROM event_ai_analyses eai
    WHERE eai.created_at >= :since
      AND eai.created_at < :until
      AND coalesce(eai.analysis_type, 'event_analysis') = 'event_analysis'
    ORDER BY eai.created_at DESC, eai.id DESC
    LIMIT :alert_evidence_limit
),
delivery_rollup AS (
    SELECT
        a.market_event_id,
        a.event_ai_analysis_id,
        count(*) AS delivery_count,
        count(*) FILTER (WHERE a.status = 'sent') AS sent_delivery_count,
        count(*) FILTER (
            WHERE a.status IN ('failed', 'retry_pending') OR a.final_failed_at IS NOT NULL
        ) AS failed_delivery_count,
        count(DISTINCT a.user_id) AS distinct_recipient_count,
        min(a.created_at) AS first_delivery_at,
        max(a.created_at) AS last_delivery_at,
        (array_agg(a.alert_type ORDER BY a.created_at DESC, a.id DESC))[1] AS alert_type,
        (array_agg(a.trigger_source ORDER BY a.created_at DESC, a.id DESC))[1] AS trigger_source,
        (array_agg(a.status ORDER BY a.created_at DESC, a.id DESC))[1] AS status,
        (array_agg(a.message ORDER BY a.created_at DESC, a.id DESC))[1] AS alert_message
    FROM alerts a
    WHERE a.created_at >= :since
      AND a.created_at < :until
      AND (a.alert_type = 'event_alert' OR a.event_ai_analysis_id IS NOT NULL)
    GROUP BY a.market_event_id, a.event_ai_analysis_id
)
SELECT
    coalesce(me.symbol, ra.analysis_symbol, 'UNKNOWN') AS symbol,
    me.id AS market_event_id,
    me.event_type,
    me.event_key,
    me.event_instance_key,
    me.price_change_percent,
    me.last_24h_change,
    me.last_7d_change,
    me.detected_at,
    ra.event_ai_analysis_id,
    ra.analysis_id,
    ra.analysis_symbol,
    ra.analysis_type,
    ra.provider,
    ra.model,
    ra.input_hash,
    ra.analysis_status,
    ra.should_alert,
    ra.analysis_event_key,
    ra.analysis_title,
    ra.analysis_message_body,
    ra.analysis_possible_action,
    ra.urgency,
    ra.confidence,
    ra.analysis_reason_for_no_alert,
    ra.related_news_ids,
    ra.analysis_plain_text,
    ra.analysis_created_at,
    coalesce(dr.delivery_count, 0) AS delivery_count,
    coalesce(dr.sent_delivery_count, 0) AS sent_delivery_count,
    coalesce(dr.failed_delivery_count, 0) AS failed_delivery_count,
    coalesce(dr.distinct_recipient_count, 0) AS distinct_recipient_count,
    dr.first_delivery_at,
    dr.last_delivery_at,
    dr.alert_type,
    dr.trigger_source,
    dr.status,
    dr.alert_message
FROM recent_analyses ra
LEFT JOIN market_events me ON me.id = ra.market_event_id
LEFT JOIN delivery_rollup dr
  ON (dr.event_ai_analysis_id = ra.event_ai_analysis_id)
  OR (dr.event_ai_analysis_id IS NULL AND dr.market_event_id = ra.market_event_id)
ORDER BY ra.analysis_created_at DESC, ra.event_ai_analysis_id DESC
"""


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, Decimal):
        return float(value)
    return value


async def collect_db(
    *,
    config: OpsAgentConfig,
    period: Period,
    mapper: ReferenceMapper,
    redaction_report: RedactionReport,
    include_raw_llm_samples: bool = False,
) -> tuple[dict[str, Any], list[dict[str, str | None]]]:
    statuses: list[dict[str, str | None]] = []
    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "schema_version": 1,
            "period": period.as_dict(),
            "queries": {},
            "warnings": [],
        }
    )
    read_only_errors = validate_read_only_queries()
    if read_only_errors:
        raise RuntimeError("; ".join(read_only_errors))
    warning = database_role_warning(config.database_url)
    if warning:
        for file_name in {
            "evidence/db/aggregate_metrics.json",
            "evidence/db/anomalies.json",
            "evidence/db/recent_market_events.json",
            "evidence/db/recent_alert_failures.json",
            "evidence/db/recent_llm_failures.json",
            "evidence/db/recent_news_failures.json",
        }:
            grouped[file_name]["warnings"].append(warning)
        return grouped, [{"name": "db", "status": "skipped", "error": warning}]

    engine = create_async_engine(
        config.database_url,
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=0,
        connect_args={"server_settings": {"application_name": "ccwbot_ops_agent"}},
    )
    params = {
        "since": period.start,
        "until": period.end,
        "limit": config.limits.db_row_cap,
        "sample_limit": config.limits.recent_sample_row_cap,
        "anomaly_limit": config.limits.anomaly_row_cap,
        "duplicate_bucket_minutes": config.limits.duplicate_market_event_bucket_minutes,
        "alert_evidence_limit": config.limits.alert_evidence_row_cap,
    }
    try:
        async with engine.connect() as connection:
            for query in QUERIES:
                try:
                    result = await asyncio.wait_for(
                        connection.execute(text(query.sql), params),
                        timeout=config.limits.db_query_timeout_seconds,
                    )
                    rows = [
                        redact_value(
                            {key: _jsonable(value) for key, value in row._mapping.items()},
                            mapper,
                            redaction_report,
                        )
                        for row in result
                    ]
                    grouped[query.evidence_file]["queries"][query.name] = {
                        "query_name": query.name,
                        "row_count": len(rows),
                        "rows": rows,
                        "warnings": [],
                    }
                    if query.name == "duplicate_market_event_buckets":
                        grouped[query.evidence_file]["queries"][query.name]["parameters"] = {
                            "bucket_minutes": (
                                config.limits.duplicate_market_event_bucket_minutes
                            )
                        }
                    statuses.append({"name": f"db.{query.name}", "status": "ok", "error": None})
                except Exception as error:
                    message = redact_error_message(error, mapper, redaction_report)
                    grouped[query.evidence_file]["warnings"].append(f"{query.name}: {message}")
                    statuses.append(
                        {"name": f"db.{query.name}", "status": "partial", "error": message}
                    )
            if include_raw_llm_samples:
                try:
                    raw_result = await asyncio.wait_for(
                        connection.execute(
                            text(
                                "SELECT id, symbol, analysis_type, status, "
                                "left(raw_input_json, :preview_bytes) AS raw_input_preview, "
                                "left(raw_output_json, :preview_bytes) AS raw_output_preview, "
                                "created_at FROM event_ai_analyses "
                                "WHERE created_at >= :since AND created_at < :until "
                                "ORDER BY created_at DESC, id DESC LIMIT :raw_sample_limit"
                            ),
                            {
                                **params,
                                "preview_bytes": config.limits.raw_llm_preview_bytes,
                                "raw_sample_limit": config.limits.raw_llm_sample_cap,
                            },
                        ),
                        timeout=config.limits.db_query_timeout_seconds,
                    )
                    rows = [
                        redact_value(
                            {key: _jsonable(value) for key, value in row._mapping.items()},
                            mapper,
                            redaction_report,
                        )
                        for row in raw_result
                    ]
                    grouped["evidence/db/raw_llm_samples.redacted.json"]["queries"][
                        "raw_llm_samples"
                    ] = {
                        "query_name": "raw_llm_samples",
                        "row_count": len(rows),
                        "rows": rows,
                        "warnings": ["raw previews are opt-in, capped, and redacted"],
                    }
                    statuses.append(
                        {"name": "db.raw_llm_samples", "status": "ok", "error": None}
                    )
                except Exception as error:
                    message = redact_error_message(error, mapper, redaction_report)
                    grouped["evidence/db/raw_llm_samples.redacted.json"]["warnings"].append(
                        f"raw_llm_samples: {message}"
                    )
                    statuses.append(
                        {
                            "name": "db.raw_llm_samples",
                            "status": "partial",
                            "error": message,
                        }
                    )
            try:
                alert_result = await asyncio.wait_for(
                    connection.execute(text(ALERT_EVIDENCE_SQL), params),
                    timeout=config.limits.db_query_timeout_seconds,
                )
                alert_rows = [
                    {key: _jsonable(value) for key, value in row._mapping.items()}
                    for row in alert_result
                ]
                alert_payloads = build_alert_evidence_payloads(
                    alert_rows,
                    period=period,
                    row_cap=config.limits.alert_evidence_row_cap,
                    semantic_cooldown_seconds=(
                        config.limits.event_alert_semantic_cooldown_seconds
                    ),
                )
                grouped.update(alert_payloads)
                statuses.append(
                    {"name": "db.alert_repetition_evidence", "status": "ok", "error": None}
                )
            except Exception as error:
                message = redact_error_message(error, mapper, redaction_report)
                for file_name in {
                    "evidence/db/alert_delivery_distribution.json",
                    "evidence/db/event_analysis_decision_timeline.json",
                    "evidence/db/alert_content_fingerprints.json",
                    "evidence/db/alert_similarity_groups.json",
                    "evidence/db/backend_suppression_effectiveness.json",
                    "evidence/db/event_identity_quality.json",
                }:
                    grouped[file_name]["warnings"].append(f"alert_repetition_evidence: {message}")
                statuses.append(
                    {
                        "name": "db.alert_repetition_evidence",
                        "status": "partial",
                        "error": message,
                    }
                )
    finally:
        await engine.dispose()
    return grouped, statuses
