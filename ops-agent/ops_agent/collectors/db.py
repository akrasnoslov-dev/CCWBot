from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from ops_agent.config import OpsAgentConfig, database_role_warning
from ops_agent.db_queries import QUERIES, validate_read_only_queries
from ops_agent.redaction import RedactionReport, ReferenceMapper, redact_value
from ops_agent.schemas import Period


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
                    statuses.append({"name": f"db.{query.name}", "status": "ok", "error": None})
                except Exception as error:
                    message = f"{type(error).__name__}: {str(error)[:300]}"
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
                    message = f"{type(error).__name__}: {str(error)[:300]}"
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
    finally:
        await engine.dispose()
    return grouped, statuses
