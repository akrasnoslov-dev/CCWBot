from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ops_agent.schemas import DetectorResult, Period, isoformat_utc

ATTENTION_STATUSES = {"triggered", "unknown"}
MAX_ALERT_QUALITY_ISSUES = 8
MAX_EVIDENCE_REFS = 24


def render_report_context(
    *,
    period: Period,
    evidence: dict[str, Any],
    detector_results: list[DetectorResult],
    collection_status: str,
    collector_status: list[dict[str, Any]] | None = None,
    bundle_id: str,
    generated_at: datetime | None = None,
) -> str:
    """Render the compact, deterministic decision packet consumed by the report LLM.

    The bundle keeps the full sanitized evidence for audit/forensics. This context intentionally
    contains only report-driving aggregates, anomalies, gaps, and exact evidence paths so the LLM
    can avoid loading healthy evidence streams.
    """
    generated_at = generated_at or datetime.now(timezone.utc)
    collectors = collector_status or []
    attention = [result for result in detector_results if result.status in ATTENTION_STATUSES]
    quality = _alert_quality_summary(evidence)
    regression = _event_regression_summary(evidence)
    report_status = _report_status(collection_status, attention, quality, regression)
    evidence_refs = _targeted_evidence_refs(attention, quality, regression)
    read_plan = [f"- `{path}`" for path in evidence_refs] or [
        "- No extra evidence read is required by current findings."
    ]

    lines = [
        "# Ops-Agent Compact Report Context",
        "",
        "Read `manifest.json` and this file first. Do not preload other bundle files. "
        "Open only evidence paths listed under a finding/gap or needed to answer "
        "an explicit investigation question.",
        "",
        "## Metadata",
        "",
        f"- Bundle: `{bundle_id}`",
        f"- Collection status: `{collection_status}`",
        f"- Report status: `{report_status}`",
        f"- Window: {period.as_dict()['start']} to {period.as_dict()['end']}",
        f"- Generated at: {isoformat_utc(generated_at)}",
        f"- Period source: `{period.source}`",
        "",
        "## Collection Gaps",
        "",
        *_collection_gaps(collectors),
        "",
        "## Current Status",
        "",
        *_current_status(evidence),
        "",
        "## Key Metrics",
        "",
        *_key_metrics(evidence),
        "",
        "## Alert Quality Signals",
        "",
        *quality["lines"],
        "",
        "## Event Alert Regression Signals",
        "",
        *regression["lines"],
        "",
        "## Findings Requiring Attention",
        "",
        *_attention_findings(attention),
        "",
        "## Targeted Evidence Read Plan",
        "",
        *read_plan,
        "",
        "## Report Writing Contract",
        "",
        "- Verify material triggered findings against their referenced evidence before "
        "calling a root cause confirmed.",
        "- Treat detector `unknown` and non-ok collectors as evidence gaps, not healthy states.",
        "- Keep confirmed, likely, and unknown conclusions distinct.",
        "- Do not repeat the same finding across multiple report sections.",
        "- Omit healthy/default detail unless it changes the operator decision.",
    ]
    return "\n".join(lines)


def _payload(evidence: dict[str, Any], path: str) -> dict[str, Any]:
    value = evidence.get(path)
    return value if isinstance(value, dict) else {}


def _query_row(evidence: dict[str, Any], name: str) -> dict[str, Any]:
    aggregate = _payload(evidence, "evidence/db/aggregate_metrics.json")
    query = (aggregate.get("queries") or {}).get(name)
    if not isinstance(query, dict):
        return {}
    rows = [row for row in (query.get("rows") or []) if isinstance(row, dict)]
    return rows[0] if rows else {}


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _pct(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "not available"
    return f"{(numerator / denominator) * 100:.1f}%"


def _report_status(
    collection_status: str,
    attention: list[DetectorResult],
    quality: dict[str, Any],
    regression: dict[str, Any],
) -> str:
    if collection_status != "complete":
        return "degraded"
    severities = {result.severity for result in attention if result.status == "triggered"}
    if (
        "critical" in severities
        or quality["severe_count"] > 0
        or regression["status"] == "critical"
    ):
        return "degraded"
    if attention or quality["issue_count"] > 0 or regression["status"] in {"warning", "unknown"}:
        return "needs attention"
    return "healthy"


def _collection_gaps(collectors: list[dict[str, Any]]) -> list[str]:
    non_ok = [item for item in collectors if str(item.get("status") or "unknown") != "ok"]
    if not non_ok:
        return ["- None."]
    lines = []
    for item in non_ok:
        name = str(item.get("name") or "unknown")
        status = str(item.get("status") or "unknown")
        error = str(item.get("error") or "no sanitized reason")
        lines.append(f"- `{name}`: `{status}` ({error})")
    return lines


def _current_status(evidence: dict[str, Any]) -> list[str]:
    health = _payload(evidence, "evidence/health/health.json")
    docker = _payload(evidence, "evidence/docker/container_state.json")
    health_status = str(health.get("status") or "unknown")
    docker_status = str(docker.get("status") or "unknown")
    services = [item for item in (docker.get("services") or []) if isinstance(item, dict)]
    service_summary = "not available"
    if services:
        # Docker evidence uses sanitized is_running / running_state / health, not
        # the raw Compose Status/State keys (nor a per-service "status" field).
        unhealthy = sum(
            1
            for item in services
            if (
                item.get("is_running") is False
                or (item.get("is_running") is None
                    and str(item.get("running_state") or "").lower() != "running")
                or str(item.get("health") or "").lower() in {"unhealthy", "starting"}
            )
        )
        service_summary = f"{len(services)} services, {unhealthy} non-healthy"
    return [
        f"- Health probe: `{health_status}`",
        f"- Docker summary: `{docker_status}` ({service_summary})",
    ]


def _key_metrics(evidence: dict[str, Any]) -> list[str]:
    impact = _query_row(evidence, "user_impact_summary")
    funnel = _query_row(evidence, "delivery_funnel")
    if not impact and not funnel:
        return ["- No aggregate key metrics available."]

    metrics: list[tuple[str, Any]] = []
    if impact:
        metrics.extend(
            [
                ("Active users", _int(impact.get("active_users_current"))),
                ("Users receiving Event Alerts", _int(impact.get("users_received_event_alerts"))),
                (
                    "Users affected by delivery failures",
                    _int(impact.get("users_affected_by_delivery_failures")),
                ),
                (
                    "Users affected by noisy/duplicate alerts",
                    _int(impact.get("users_affected_by_duplicate_alerts")),
                ),
                (
                    "Users affected by content quality",
                    _int(impact.get("users_affected_by_content_quality_issues")),
                ),
            ]
        )
    if funnel:
        attempts = _int(funnel.get("telegram_delivery_attempts"))
        failed = _int(funnel.get("telegram_failed"))
        metrics.extend(
            [
                ("Market events", _int(funnel.get("market_events"))),
                ("AI analyses", _int(funnel.get("ai_analyses"))),
                ("should_alert=true", _int(funnel.get("should_alert_true"))),
                ("Telegram delivered", _int(funnel.get("telegram_delivered"))),
                ("Telegram failed", f"{failed} / {attempts} ({_pct(failed, attempts)})"),
            ]
        )
    metric_rows = [f"| {name} | {value} |" for name, value in metrics]
    return ["| Metric | Value |", "|---|---:|", *metric_rows]


def _alert_quality_summary(evidence: dict[str, Any]) -> dict[str, Any]:
    quality = _payload(evidence, "evidence/db/alert_quality.json")
    if not quality:
        return {
            "lines": ["- Alert-quality evidence unavailable."],
            "issue_count": 0,
            "severe_count": 0,
            "needs_evidence": True,
        }
    issues = [item for item in (quality.get("issues") or []) if isinstance(item, dict)]
    total = _int(quality.get("total_event_alert_deliveries"))
    sampled_attempts = _int(quality.get("sampled_event_alert_attempts"))
    non_sent = _int(quality.get("sampled_non_sent_event_alerts"))
    funnel = _query_row(evidence, "delivery_funnel")
    full_sent = _int(funnel.get("telegram_delivered")) if funnel else None
    grouped: dict[str, int] = {}
    severe_count = 0
    severe_names = {"contains_n_a", "contains_unknown", "contains_unavailable", "contains_null"}
    for item in issues:
        name = str(item.get("issue") or "unknown")
        count = _int(item.get("delivery_count"))
        grouped[name] = grouped.get(name, 0) + count
        if name in severe_names:
            severe_count += count
    if not issues:
        lines = ["- No alert-quality issue groups in collected evidence."]
    else:
        lines = ["- Issue groups (sampled sent deliveries only):"]
        ordered = sorted(grouped.items(), key=lambda pair: (-pair[1], pair[0]))
        for name, count in ordered[:MAX_ALERT_QUALITY_ISSUES]:
            lines.append(f"  - `{name}`: {count} ({_pct(count, total)})")
    if full_sent is not None:
        lines.insert(
            0,
            f"- Sampled sent Event Alert deliveries: {total} of {full_sent} "
            f"(full-period sent; {max(full_sent - total, 0)} outside sample)."
        )
    else:
        lines.insert(0, f"- Sampled sent Event Alert deliveries: {total} (full total unavailable).")
    if sampled_attempts or non_sent:
        lines.insert(
            1, f"- Sampled attempts: {sampled_attempts}; excluded non-sent: {non_sent}."
        )
    return {
        "lines": lines,
        "issue_count": sum(grouped.values()),
        "severe_count": severe_count,
        "needs_evidence": bool(issues),
    }


def _event_regression_summary(evidence: dict[str, Any]) -> dict[str, Any]:
    payload = _payload(evidence, "evidence/db/event_alert_regression_checks.json")
    if not payload:
        return {"lines": ["- Not available."], "status": "unknown", "needs_evidence": True}
    status = str(payload.get("status") or "unknown").lower()
    lines = [f"- Status: `{status}`"]
    signals: list[tuple[str, int]] = []
    for key, value in payload.items():
        if key in {"status", "schema_version", "period"}:
            continue
        if isinstance(value, (int, float)) and int(value) != 0:
            signals.append((key, int(value)))
        elif isinstance(value, dict):
            total = sum(_int(item) for item in value.values())
            if total:
                signals.append((key, total))
    for key, value in sorted(signals, key=lambda pair: (-pair[1], pair[0]))[:10]:
        lines.append(f"- `{key}`: {value}")
    if len(lines) == 1 and status in {"ok", "healthy"}:
        lines.append("- No regression counters triggered.")
    return {
        "lines": lines,
        "status": status,
        "needs_evidence": status not in {"ok", "healthy"} or len(lines) > 2,
    }


def _attention_findings(results: list[DetectorResult]) -> list[str]:
    if not results:
        return ["- No triggered or unknown detector findings."]
    lines = [
        "| Severity | State | Confidence | Finding | Evidence refs |",
        "|---|---|---|---|---|",
    ]
    for result in sorted(results, key=_detector_sort_key):
        confidence = "medium" if result.evidence_gap else "high"
        if result.status == "unknown":
            confidence = "low"
        refs = ", ".join(f"`{ref}`" for ref in result.evidence_refs) or "none"
        summary = result.summary.replace("|", "/").replace("\n", " ")
        if result.evidence_gap:
            summary = f"{summary} Gap: {result.evidence_gap}".replace("|", "/")
        lines.append(
            f"| {result.severity} | {result.status} | {confidence} | "
            f"`{result.id}`: {summary} | {refs} |"
        )
    return lines


def _detector_sort_key(result: DetectorResult) -> tuple[int, int, str]:
    severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    status_rank = {"triggered": 0, "unknown": 1}
    return (
        severity_rank.get(result.severity, 9),
        status_rank.get(result.status, 9),
        result.id,
    )


def _targeted_evidence_refs(
    attention: list[DetectorResult],
    quality: dict[str, Any],
    regression: dict[str, Any],
) -> list[str]:
    refs: list[str] = []
    for result in attention:
        refs.extend(str(ref) for ref in result.evidence_refs if ref)
    if quality["needs_evidence"]:
        refs.append("evidence/db/alert_quality.json")
    if regression["needs_evidence"]:
        refs.append("evidence/db/event_alert_regression_checks.json")

    unique: list[str] = []
    for ref in refs:
        if ref not in unique:
            unique.append(ref)
        if len(unique) >= MAX_EVIDENCE_REFS:
            break
    return unique
