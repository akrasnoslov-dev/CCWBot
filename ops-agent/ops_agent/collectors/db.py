from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from ops_agent.alert_similarity import build_alert_evidence_payloads
from ops_agent.config import OpsAgentConfig, database_role_warning
from ops_agent.db_queries import QUERIES, validate_read_only_queries
from ops_agent.redaction import RedactionReport, ReferenceMapper, redact_text, redact_value
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
      -- Failed attempts carry no alert content, so they contribute nothing to repetition
      -- evidence, yet they compete for the same per-bucket row cap. During the 2026-07 outage
      -- 3396 llm_error rows filled every bucket and pushed out the delivered analyses that the
      -- six alert-quality detectors read, leaving all of them unknown for the whole period.
      -- Excluding them here means a failure storm can no longer blind those detectors. The
      -- failures stay fully visible in llm_usage_logs and in the analysis summaries.
      AND coalesce(eai.status, '') NOT IN (
          'llm_error', 'invalid_json', 'schema_error', 'rate_limit', 'skipped_due_to_rate_limit'
      )
    ORDER BY eai.created_at DESC, eai.id DESC
    LIMIT :alert_evidence_limit
),
delivery_candidates AS (
    SELECT
        ra.event_ai_analysis_id AS rollup_event_ai_analysis_id,
        a.market_event_id,
        a.event_ai_analysis_id,
        a.user_id,
        a.id,
        a.alert_type,
        a.trigger_source,
        a.status,
        a.message,
        a.numeric_context,
        a.final_failed_at,
        a.created_at
    FROM recent_analyses ra
    JOIN alerts a ON a.event_ai_analysis_id = ra.event_ai_analysis_id
    WHERE a.created_at >= :since
      AND a.created_at < :until
      AND (a.alert_type = 'event_alert' OR a.event_ai_analysis_id IS NOT NULL)
    UNION ALL
    SELECT
        ra.event_ai_analysis_id AS rollup_event_ai_analysis_id,
        a.market_event_id,
        a.event_ai_analysis_id,
        a.user_id,
        a.id,
        a.alert_type,
        a.trigger_source,
        a.status,
        a.message,
        a.numeric_context,
        a.final_failed_at,
        a.created_at
    FROM recent_analyses ra
    JOIN alerts a ON a.event_ai_analysis_id IS NULL
                 AND a.market_event_id = ra.market_event_id
    WHERE a.created_at >= :since
      AND a.created_at < :until
      AND a.alert_type = 'event_alert'
      AND ra.market_event_id IS NOT NULL
),
delivery_rollup AS (
    SELECT
        a.rollup_event_ai_analysis_id,
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
        (array_agg(a.message ORDER BY a.created_at DESC, a.id DESC))[1] AS alert_message,
        (array_agg(a.numeric_context ORDER BY a.created_at DESC, a.id DESC))[1]
            AS alert_numeric_context,
        (array_agg(ado.semantic_family ORDER BY ado.created_at DESC, ado.id DESC)
            FILTER (WHERE ado.semantic_family IS NOT NULL))[1] AS semantic_family,
        (array_agg(ado.decision_reason ORDER BY ado.created_at DESC, ado.id DESC)
            FILTER (WHERE ado.decision_reason IS NOT NULL))[1] AS decision_reason
    FROM delivery_candidates a
    LEFT JOIN alert_delivery_outcomes ado ON ado.alert_id = a.id
    GROUP BY a.rollup_event_ai_analysis_id
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
    dr.alert_message,
    dr.alert_numeric_context,
    dr.semantic_family,
    dr.decision_reason
FROM recent_analyses ra
LEFT JOIN market_events me ON me.id = ra.market_event_id
LEFT JOIN delivery_rollup dr ON dr.rollup_event_ai_analysis_id = ra.event_ai_analysis_id
ORDER BY ra.analysis_created_at DESC, ra.event_ai_analysis_id DESC
"""


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, Decimal):
        return float(value)
    return value


def _collector_error(error: Exception, mapper: ReferenceMapper, report: RedactionReport) -> str:
    raw = f"{type(error).__name__}: {error}".lower()
    if "cancelled" in raw or "timeout" in raw:
        category = "timeout"
    elif "infailedsqltransaction" in raw or "current transaction is aborted" in raw:
        category = "transaction_state_error"
    elif any(
        token in raw
        for token in ("syntax", "programmingerror", "undefinedtable", "undefinedcolumn")
    ):
        category = "sql_syntax_or_schema_error"
    elif "permission" in raw or "insufficientprivilege" in raw:
        category = "permission_error"
    elif "connection" in raw or "connect" in raw:
        category = "connection_error"
    else:
        category = "collector_error"
    return redact_text(f"{type(error).__name__}: {category}", mapper, report)


def _alert_evidence_windows(
    period: Period, *, bucket_hours: int = 6
) -> list[tuple[datetime, datetime]]:
    windows: list[tuple[datetime, datetime]] = []
    cursor = period.start
    step = timedelta(hours=bucket_hours)
    while cursor < period.end:
        end = min(cursor + step, period.end)
        windows.append((cursor, end))
        cursor = end
    return windows or [(period.start, period.end)]


async def _collect_alert_repetition_rows(
    engine,
    *,
    params: dict[str, Any],
    period: Period,
    timeout_seconds: int,
    row_cap: int,
    mapper: ReferenceMapper,
    redaction_report: RedactionReport,
    bucket_hours: int = 6,
) -> tuple[list[dict[str, Any]], list[dict[str, str | None]], list[str]]:
    rows: list[dict[str, Any]] = []
    statuses: list[dict[str, str | None]] = []
    warnings: list[str] = []
    newest_first_windows = list(
        reversed(_alert_evidence_windows(period, bucket_hours=bucket_hours))
    )
    for index, (window_start, window_end) in enumerate(newest_first_windows, start=1):
        if len(rows) >= row_cap:
            warnings.append("alert repetition evidence row cap reached before older buckets ran")
            break
        bucket_name = f"db.alert_repetition_evidence.bucket_{index}"
        try:
            async with engine.connect() as connection:
                alert_result = await asyncio.wait_for(
                    connection.execute(
                        text(ALERT_EVIDENCE_SQL),
                        {
                            **params,
                            "since": window_start,
                            "until": window_end,
                            "alert_evidence_limit": max(row_cap - len(rows), 1),
                        },
                    ),
                    timeout=timeout_seconds,
                )
                rows.extend(
                    {key: _jsonable(value) for key, value in row._mapping.items()}
                    for row in alert_result
                )
                await connection.rollback()
            statuses.append({"name": bucket_name, "status": "ok", "error": None})
        except Exception as error:
            message = _collector_error(error, mapper, redaction_report)
            warnings.append(f"{bucket_name}: {message}")
            statuses.append({"name": bucket_name, "status": "failed", "error": message})
    return rows[:row_cap], statuses, warnings


def _successful_alert_repetition_buckets(statuses: list[dict[str, str | None]]) -> int:
    return sum(1 for status in statuses if status.get("status") == "ok")


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
    read_only_errors = validate_read_only_queries(
        extra={"alert_repetition_evidence": ALERT_EVIDENCE_SQL}
    )
    if read_only_errors:
        raise RuntimeError("; ".join(read_only_errors))
    warning = database_role_warning(config.database_url)
    if warning:
        for file_name in {
            "evidence/db/aggregate_metrics.json",
            "evidence/db/alert_quality.json",
            "evidence/db/anomalies.json",
            "evidence/db/recent_market_events.json",
            "evidence/db/recent_alert_failures.json",
            "evidence/db/recent_llm_failures.json",
            "evidence/db/recent_news_failures.json",
            "evidence/db/event_alert_regression_checks.json",
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
        for query in QUERIES:
            try:
                async with engine.connect() as connection:
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
                    await connection.rollback()
                grouped[query.evidence_file]["queries"][query.name] = {
                    "query_name": query.name,
                    "row_count": len(rows),
                    "rows": rows,
                    "warnings": [],
                }
                if query.name == "duplicate_market_event_buckets":
                    grouped[query.evidence_file]["queries"][query.name]["parameters"] = {
                        "bucket_minutes": config.limits.duplicate_market_event_bucket_minutes
                    }
                statuses.append({"name": f"db.{query.name}", "status": "ok", "error": None})
            except Exception as error:
                message = _collector_error(error, mapper, redaction_report)
                grouped[query.evidence_file]["warnings"].append(f"{query.name}: {message}")
                statuses.append(
                    {"name": f"db.{query.name}", "status": "failed", "error": message}
                )
        if include_raw_llm_samples:
            try:
                async with engine.connect() as connection:
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
                    await connection.rollback()
                grouped["evidence/db/raw_llm_samples.redacted.json"]["queries"][
                    "raw_llm_samples"
                ] = {
                    "query_name": "raw_llm_samples",
                    "row_count": len(rows),
                    "rows": rows,
                    "warnings": ["raw previews are opt-in, capped, and redacted"],
                }
                statuses.append({"name": "db.raw_llm_samples", "status": "ok", "error": None})
            except Exception as error:
                message = _collector_error(error, mapper, redaction_report)
                grouped["evidence/db/raw_llm_samples.redacted.json"]["warnings"].append(
                    f"raw_llm_samples: {message}"
                )
                statuses.append(
                    {
                        "name": "db.raw_llm_samples",
                        "status": "failed",
                        "error": message,
                    }
                )
        alert_rows, bucket_statuses, alert_warnings = await _collect_alert_repetition_rows(
            engine,
            params=params,
            period=period,
            timeout_seconds=config.limits.alert_evidence_query_timeout_seconds,
            row_cap=config.limits.alert_evidence_row_cap,
            mapper=mapper,
            redaction_report=redaction_report,
            bucket_hours=config.limits.alert_evidence_bucket_hours,
        )
        statuses.extend(bucket_statuses)
        successful_buckets = _successful_alert_repetition_buckets(bucket_statuses)
        if successful_buckets:
            alert_payloads = build_alert_evidence_payloads(
                alert_rows,
                period=period,
                row_cap=config.limits.alert_evidence_row_cap,
                semantic_cooldown_seconds=config.limits.event_alert_semantic_cooldown_seconds,
                warnings=alert_warnings,
            )
            grouped.update(alert_payloads)
            statuses.append(
                {
                    "name": "db.alert_repetition_evidence",
                    "status": "partial" if alert_warnings else "ok",
                    "error": "; ".join(alert_warnings) if alert_warnings else None,
                }
            )
        else:
            message = "; ".join(alert_warnings) or "all alert repetition evidence buckets failed"
            for file_name in {
                "evidence/db/alert_delivery_distribution.json",
                "evidence/db/alert_quality.json",
                "evidence/db/event_analysis_decision_timeline.json",
                "evidence/db/alert_content_fingerprints.json",
                "evidence/db/alert_similarity_groups.json",
                "evidence/db/backend_suppression_effectiveness.json",
                "evidence/db/event_identity_quality.json",
                "evidence/db/event_alert_regression_checks.json",
            }:
                grouped[file_name]["warnings"].append(f"alert_repetition_evidence: {message}")
            statuses.append(
                {
                    "name": "db.alert_repetition_evidence",
                    "status": "failed",
                    "error": message,
                }
            )
    finally:
        await engine.dispose()
    return grouped, statuses
