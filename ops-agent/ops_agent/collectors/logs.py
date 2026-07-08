from __future__ import annotations

import re
from datetime import datetime, timezone
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
    "llm_failure": re.compile(
        r"(?:llm|groq).{0,40}\bfailed\b(?!\s*=\s*0\b)|"
        r"\bfailed\b(?!\s*=\s*0\b).{0,40}(?:llm|groq)|"
        r"llm.{0,40}rate[ _]limit|rate[ _]limit.{0,40}llm|"
        r"schema validation|invalid JSON|rate limit",
        re.IGNORECASE,
    ),
    "report_failure": re.compile(r"report.*failed|market_report_failed", re.IGNORECASE),
    "heartbeat_failure": re.compile(
        r"heartbeat.{0,40}\bfailed\b\s*:|"
        r"ops_event=heartbeat_(?:generation|delivery)_failed|"
        r"heartbeat.{0,40}\bfailed=[1-9]\d*\b",
        re.IGNORECASE,
    ),
    "payment_rejection": re.compile(r"payment.*rejected|invalid payload", re.IGNORECASE),
}
OPS_EVENT_RE = re.compile(r"\bops_event=([a-z0-9_]+)")
SUPPRESSION_REASON_RE = re.compile(r"\bsuppression_reason=([a-z0-9_]+)")
LOG_TIMESTAMP_RE = re.compile(
    r"^(?P<stamp>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}"
    r"(?:,\d{1,6}|\.\d{1,6})?(?:Z|[+-]\d{2}:?\d{2})?)"
)


def _tail_bytes(path: Path, limit: int) -> str:
    with path.open("rb") as file:
        file.seek(0, 2)
        size = file.tell()
        file.seek(max(size - limit, 0))
        return file.read().decode("utf-8", errors="replace")


def parse_log_timestamp(line: str) -> datetime | None:
    match = LOG_TIMESTAMP_RE.match(line)
    if not match:
        return None
    raw = match.group("stamp").replace(" ", "T", 1).replace(",", ".")
    if raw.endswith("Z"):
        raw = f"{raw[:-1]}+00:00"
    if re.search(r"[+-]\d{4}$", raw):
        raw = f"{raw[:-2]}:{raw[-2:]}"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _empty_counts() -> dict[str, int]:
    counts: dict[str, int] = {name: 0 for name in LOG_PATTERNS}
    counts["ops_event"] = 0
    return counts


def _line_patterns(line: str) -> list[str]:
    matches = [name for name, pattern in LOG_PATTERNS.items() if pattern.search(line)]
    if OPS_EVENT_RE.search(line):
        matches.append("ops_event")
    return matches


def _encode_excerpt(
    lines: list[str],
    *,
    mapper: ReferenceMapper,
    redaction_report: RedactionReport,
    max_bytes: int,
) -> bytes:
    redacted = redact_text("\n".join(lines), mapper, redaction_report)
    return redacted.encode("utf-8")[:max_bytes]


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
    period_counts = _empty_counts()
    tail_context_counts = _empty_counts()
    period_suppression_reason_counts: dict[str, int] = {}
    tail_suppression_reason_counts: dict[str, int] = {}
    excerpts: dict[str, dict[str, Any]] = {}
    total_exported = 0
    statuses = []
    for path in log_files:
        try:
            text = _tail_bytes(path, config.limits.max_log_tail_bytes)
            lines = text.splitlines()
            period_selected: list[str] = []
            tail_selected: list[str] = []
            ops_events: dict[str, int] = {}
            period_suppression_reasons: dict[str, int] = {}
            tail_suppression_reasons: dict[str, int] = {}
            parseable_timestamps = 0
            period_matched_lines = 0
            outside_period_lines = 0
            unparseable_timestamp_lines = 0
            for line in lines:
                parsed_at = parse_log_timestamp(line)
                matches = _line_patterns(line)
                if parsed_at is not None:
                    parseable_timestamps += 1
                    if period.start <= parsed_at < period.end:
                        period_matched_lines += 1
                        for name in matches:
                            period_counts[name] += 1
                        suppression_match = SUPPRESSION_REASON_RE.search(line)
                        if suppression_match:
                            reason = suppression_match.group(1)
                            period_suppression_reasons[reason] = (
                                period_suppression_reasons.get(reason, 0) + 1
                            )
                            period_suppression_reason_counts[reason] = (
                                period_suppression_reason_counts.get(reason, 0) + 1
                            )
                        if matches and len(period_selected) < 200:
                            period_selected.append(line)
                    else:
                        outside_period_lines += 1
                else:
                    unparseable_timestamp_lines += 1
                    for name in matches:
                        tail_context_counts[name] += 1
                    suppression_match = SUPPRESSION_REASON_RE.search(line)
                    if suppression_match:
                        reason = suppression_match.group(1)
                        tail_suppression_reasons[reason] = (
                            tail_suppression_reasons.get(reason, 0) + 1
                        )
                        tail_suppression_reason_counts[reason] = (
                            tail_suppression_reason_counts.get(reason, 0) + 1
                        )
                    if matches and len(tail_selected) < 200:
                        tail_selected.append(line)
                match = OPS_EVENT_RE.search(line)
                if match:
                    ops_events[match.group(1)] = ops_events.get(match.group(1), 0) + 1

            period_encoded = _encode_excerpt(
                period_selected,
                mapper=mapper,
                redaction_report=redaction_report,
                max_bytes=config.limits.max_log_export_bytes_per_file,
            )
            tail_encoded = _encode_excerpt(
                tail_selected,
                mapper=mapper,
                redaction_report=redaction_report,
                max_bytes=config.limits.max_log_export_bytes_per_file,
            )
            export_bytes = total_exported + len(period_encoded) + len(tail_encoded)
            if export_bytes > config.limits.max_log_export_bytes_total:
                index["warnings"].append(
                    "log export total limit reached; remaining excerpts omitted"
                )
                period_encoded = b""
                tail_encoded = b""
            total_exported += len(period_encoded) + len(tail_encoded)
            period_excerpt_name = f"{path.name}.period.redacted.log"
            tail_excerpt_name = f"{path.name}.tail-context.redacted.log"
            if parseable_timestamps == 0:
                index["warnings"].append(
                    f"{path.name}: no parseable timestamps; excerpts are tail context only"
                )
            index["files"].append(
                {
                    "name": path.name,
                    "bytes_read": len(text.encode("utf-8")),
                    "period_matched_excerpt": (
                        f"evidence/logs/excerpts/{period_excerpt_name}"
                    ),
                    "tail_context_excerpt": (
                        f"evidence/logs/excerpts/{tail_excerpt_name}"
                    ),
                    "timestamp_parse": {
                        "parseable_lines": parseable_timestamps,
                        "period_matched_lines": period_matched_lines,
                        "outside_period_lines": outside_period_lines,
                        "unparseable_timestamp_lines": unparseable_timestamp_lines,
                        "period_filter_applied": parseable_timestamps > 0,
                        "timezone_assumption": "naive log timestamps are treated as UTC",
                    },
                    "evidence_scopes": {
                        "period_matched": {
                            "matching_excerpt_lines": len(period_selected),
                            "description": "timestamped lines within requested period",
                        },
                        "tail_context": {
                            "matching_excerpt_lines": len(tail_selected),
                            "description": "matching lines without parseable timestamps",
                        },
                    },
                    "ops_events": ops_events,
                    "suppression_reasons": {
                        "period_matched": period_suppression_reasons,
                        "tail_context": tail_suppression_reasons,
                    },
                }
            )
            excerpts[f"evidence/logs/excerpts/{period_excerpt_name}"] = {
                "text": period_encoded.decode("utf-8", errors="replace")
            }
            excerpts[f"evidence/logs/excerpts/{tail_excerpt_name}"] = {
                "text": tail_encoded.decode("utf-8", errors="replace")
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
        "evidence_scope": "period_matched_and_tail_context",
        "period_matched_pattern_counts": period_counts,
        "tail_context_pattern_counts": tail_context_counts,
        "pattern_counts": {
            name: period_counts.get(name, 0) + tail_context_counts.get(name, 0)
            for name in period_counts
        },
        "period_matched_suppression_reason_counts": period_suppression_reason_counts,
        "tail_context_suppression_reason_counts": tail_suppression_reason_counts,
        "suppression_reason_counts": {
            reason: period_suppression_reason_counts.get(reason, 0)
            + tail_suppression_reason_counts.get(reason, 0)
            for reason in sorted(
                set(period_suppression_reason_counts) | set(tail_suppression_reason_counts)
            )
        },
        "notes": [
            "period_matched_pattern_counts are timestamped lines within the requested period",
            "tail_context_pattern_counts are unscoped lines without parseable timestamps",
        ],
    }, excerpts, statuses
