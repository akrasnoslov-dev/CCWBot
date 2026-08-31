from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ops_agent.config import OpsAgentConfig
from ops_agent.redaction import RedactionReport, ReferenceMapper, looks_like_secret_value
from ops_agent.schemas import Period

LOG_PATTERNS = {
    "error": re.compile(r"\bERROR\b|Traceback|Exception|uncaught", re.IGNORECASE),
    "warning": re.compile(r"\bWARNING\b", re.IGNORECASE),
    "coingecko_rate_limit": re.compile(
        r"\bops_event=coingecko_rate_limit\b|"
        r"\bcoingecko\b.{0,80}\b(?:429|rate[ _-]?limit(?:ed|ing)?)\b|"
        r"\b(?:429|rate[ _-]?limit(?:ed|ing)?)\b.{0,80}\bcoingecko\b",
        re.IGNORECASE,
    ),
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
    # Per-delivery failures already log one ops_event=heartbeat_delivery_failed line each;
    # the heartbeat_delivery_summary line repeats them as failed=N and previously double-
    # counted every failure (pattern count 2x the DB truth). Summary lines are therefore
    # excluded; genuine failure lines (per-delivery, generation, schema-validation) match.
    "heartbeat_failure": re.compile(
        r"heartbeat.{0,40}\bfailed\b\s*:|"
        r"ops_event=heartbeat_(?:generation|delivery)_failed\b",
        re.IGNORECASE,
    ),
    "payment_rejection": re.compile(r"payment.*rejected|invalid payload", re.IGNORECASE),
}
OPS_EVENT_RE = re.compile(r"\bops_event=([a-z0-9_]+)")
SUPPRESSION_REASON_RE = re.compile(r"\bsuppression_reason=([a-z0-9_]+)")
_SAFE_FIELD_RE = re.compile(
    r"\b(?P<key>call_type|symbol|provider|model|status|reason|operation_id)="
    r"(?P<value>[^\s]+)"
)
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-"
    r"[0-9a-f]{12}$",
    re.IGNORECASE,
)
_SAFE_TOKEN_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_SAFE_MODEL_RE = re.compile(r"^[A-Za-z0-9._:/-]{1,128}$")
_SAFE_SYMBOLS = frozenset({"BTC", "ETH", "GRAM", "SOL"})
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


def _structured_match_record(
    line: str,
    *,
    parsed_at: datetime | None,
    patterns: list[str],
    mapper: ReferenceMapper,
) -> dict[str, Any]:
    """Export a strict allowlist, never a redacted copy of a raw log line."""
    fields = {match.group("key"): match.group("value") for match in _SAFE_FIELD_RE.finditer(line)}
    record: dict[str, Any] = {
        "timestamp": parsed_at.isoformat().replace("+00:00", "Z") if parsed_at else None,
        "patterns": sorted(pattern for pattern in patterns if pattern != "ops_event"),
        "event": (OPS_EVENT_RE.search(line).group(1) if OPS_EVENT_RE.search(line) else None),
    }
    for key in ("call_type", "provider", "status", "reason"):
        value = fields.get(key, "")
        if _SAFE_TOKEN_RE.fullmatch(value):
            record[key] = value
    symbol = fields.get("symbol", "").upper()
    if symbol in _SAFE_SYMBOLS:
        record["symbol"] = symbol
    model = fields.get("model", "")
    if _SAFE_MODEL_RE.fullmatch(model) and not looks_like_secret_value(model):
        record["model"] = model
    operation_id = fields.get("operation_id", "")
    if _UUID_RE.fullmatch(operation_id):
        record["operation_ref"] = mapper.ref("operation", operation_id)
    return record


def _safe_collector_error(error: Exception) -> str:
    if isinstance(error, PermissionError):
        category = "permission_error"
    elif isinstance(error, OSError):
        category = "io_error"
    else:
        category = "collector_error"
    return f"{type(error).__name__}: {category}"


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
    period_match_records: list[dict[str, Any]] = []
    tail_match_records: list[dict[str, Any]] = []
    statuses = []
    for path in log_files:
        try:
            period_records_before = len(period_match_records)
            tail_records_before = len(tail_match_records)
            text = _tail_bytes(path, config.limits.max_log_tail_bytes)
            lines = text.splitlines()
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
                        if matches and len(period_match_records) < 500:
                            period_match_records.append(
                                _structured_match_record(
                                    line, parsed_at=parsed_at, patterns=matches, mapper=mapper
                                )
                            )
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
                    if matches and len(tail_match_records) < 500:
                        tail_match_records.append(
                            _structured_match_record(
                                line, parsed_at=None, patterns=matches, mapper=mapper
                            )
                        )
                match = OPS_EVENT_RE.search(line)
                if match:
                    ops_events[match.group(1)] = ops_events.get(match.group(1), 0) + 1

            if parseable_timestamps == 0:
                index["warnings"].append(
                    f"{path.name}: no parseable timestamps; excerpts are tail context only"
                )
            index["files"].append(
                {
                    "name": path.name,
                    "bytes_read": len(text.encode("utf-8")),
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
                            "matching_records": len(period_match_records) - period_records_before,
                            "description": (
                                "allowlisted records from timestamped lines within requested period"
                            ),
                        },
                        "tail_context": {
                            "matching_records": len(tail_match_records) - tail_records_before,
                            "description": (
                                "allowlisted records from lines without parseable timestamps"
                            ),
                        },
                    },
                    "ops_events": ops_events,
                    "suppression_reasons": {
                        "period_matched": period_suppression_reasons,
                        "tail_context": tail_suppression_reasons,
                    },
                }
            )
            statuses.append({"name": f"logs.{path.name}", "status": "ok", "error": None})
        except Exception as error:
            message = _safe_collector_error(error)
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
        "period_matched_records": period_match_records,
        "tail_context_records": tail_match_records,
        "notes": [
            "period_matched_pattern_counts are timestamped lines within the requested period",
            "tail_context_pattern_counts are unscoped lines without parseable timestamps",
            "match records are strict allowlisted fields, never raw or redacted log lines",
        ],
    }, excerpts, statuses
