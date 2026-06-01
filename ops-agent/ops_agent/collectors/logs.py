from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ops_agent.config import OpsAgentConfig
from ops_agent.redaction import RedactionReport, ReferenceMapper, redact_text
from ops_agent.schemas import Period

LOG_PATTERNS = {
    "error": re.compile(r"\bERROR\b|Traceback|Exception|uncaught", re.IGNORECASE),
    "warning": re.compile(r"\bWARNING\b", re.IGNORECASE),
    "coingecko_rate_limit": re.compile(r"CoinGecko|coingecko.*429|rate_limit", re.IGNORECASE),
    "telegram_delivery_failure": re.compile(
        r"telegram.*fail|delivery_failure|Forbidden",
        re.IGNORECASE,
    ),
    "llm_failure": re.compile(r"llm|groq|schema validation|invalid JSON|rate limit", re.IGNORECASE),
    "report_failure": re.compile(r"report.*failed|market_report_failed", re.IGNORECASE),
    "heartbeat_failure": re.compile(r"heartbeat.*failed|market_heartbeat", re.IGNORECASE),
    "payment_rejection": re.compile(r"payment.*rejected|invalid payload", re.IGNORECASE),
}
OPS_EVENT_RE = re.compile(r"\bops_event=([a-z0-9_]+)")


def _tail_bytes(path: Path, limit: int) -> str:
    with path.open("rb") as file:
        file.seek(0, 2)
        size = file.tell()
        file.seek(max(size - limit, 0))
        return file.read().decode("utf-8", errors="replace")


def collect_logs(
    *,
    config: OpsAgentConfig,
    period: Period,
    mapper: ReferenceMapper,
    redaction_report: RedactionReport,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], list[dict[str, str | None]]]:
    log_files = sorted(config.logs_dir.glob("ccwbot-operational.log*")) + sorted(
        config.logs_dir.glob("ccwbot-warnings-errors.log*")
    )
    index = {"schema_version": 1, "period": period.as_dict(), "files": [], "warnings": []}
    pattern_counts: dict[str, int] = {name: 0 for name in LOG_PATTERNS}
    pattern_counts["ops_event"] = 0
    excerpts: dict[str, dict[str, Any]] = {}
    total_exported = 0
    statuses = []
    for path in log_files:
        try:
            text = _tail_bytes(path, config.limits.max_log_tail_bytes)
            lines = text.splitlines()
            selected: list[str] = []
            ops_events: dict[str, int] = {}
            for line in lines:
                for name, pattern in LOG_PATTERNS.items():
                    if pattern.search(line):
                        pattern_counts[name] += 1
                        if len(selected) < 200:
                            selected.append(line)
                match = OPS_EVENT_RE.search(line)
                if match:
                    pattern_counts["ops_event"] += 1
                    ops_events[match.group(1)] = ops_events.get(match.group(1), 0) + 1
            redacted = redact_text("\n".join(selected), mapper, redaction_report)
            encoded = redacted.encode("utf-8")[: config.limits.max_log_export_bytes_per_file]
            if total_exported + len(encoded) > config.limits.max_log_export_bytes_total:
                index["warnings"].append(
                    "log export total limit reached; remaining excerpts omitted"
                )
                redacted = ""
                encoded = b""
            total_exported += len(encoded)
            excerpt_name = f"{path.name}.redacted.log"
            index["files"].append(
                {
                    "name": path.name,
                    "bytes_read": len(text.encode("utf-8")),
                    "excerpt": f"evidence/logs/excerpts/{excerpt_name}",
                    "ops_events": ops_events,
                }
            )
            excerpts[f"evidence/logs/excerpts/{excerpt_name}"] = {
                "text": encoded.decode("utf-8", errors="replace")
            }
            statuses.append({"name": f"logs.{path.name}", "status": "ok", "error": None})
        except Exception as error:
            message = f"{type(error).__name__}: {str(error)[:300]}"
            index["warnings"].append(f"{path.name}: {message}")
            statuses.append({"name": f"logs.{path.name}", "status": "partial", "error": message})
    if not log_files:
        statuses.append({"name": "logs", "status": "skipped", "error": "no log files found"})
    return index, {
        "schema_version": 1,
        "period": period.as_dict(),
        "pattern_counts": pattern_counts,
    }, excerpts, statuses
