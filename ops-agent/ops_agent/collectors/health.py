from __future__ import annotations

from typing import Any

import httpx

from ops_agent.config import OpsAgentConfig
from ops_agent.redaction import RedactionReport, ReferenceMapper, redact_error_message, redact_value
from ops_agent.schemas import Period


async def collect_health(
    *,
    config: OpsAgentConfig,
    period: Period,
    mapper: ReferenceMapper,
    redaction_report: RedactionReport,
) -> tuple[dict[str, Any], dict[str, str | None]]:
    if not config.health_url:
        return (
            {
                "schema_version": 1,
                "period": period.as_dict(),
                "status": "unknown",
                "error": "OPS_AGENT_HEALTH_URL is not configured.",
            },
            {"name": "health", "status": "skipped", "error": "health URL is not configured"},
        )
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(config.health_url)
        content_type = response.headers.get("content-type", "")
        payload = response.json() if content_type.startswith("application/json") else {}
        return (
            {
                "schema_version": 1,
                "period": period.as_dict(),
                "http_status": response.status_code,
                "status": "ok" if response.status_code == 200 else "failed",
                "body": redact_value(payload, mapper, redaction_report),
                "warnings": [],
            },
            {
                "name": "health",
                "status": "ok" if response.status_code == 200 else "partial",
                "error": None,
            },
        )
    except Exception as error:
        message = redact_error_message(error, mapper, redaction_report)
        return (
            {
                "schema_version": 1,
                "period": period.as_dict(),
                "status": "failed",
                "error": message,
                "warnings": [message],
            },
            {"name": "health", "status": "partial", "error": message},
        )
