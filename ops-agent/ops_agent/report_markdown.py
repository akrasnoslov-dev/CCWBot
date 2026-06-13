# ruff: noqa: E501
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from ops_agent.schemas import DetectorResult, Period, isoformat_utc

SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


@dataclass(frozen=True)
class ReportFinding:
    title: str
    severity: str
    evidence: str
    user_impact: str
    recommended_action: str
    pr_mapping: str
    confidence: str
    status: str = "confirmed"


def render_decision_report_context(
    *,
    period: Period,
    evidence: dict[str, Any],
    detector_results: list[DetectorResult],
    collection_status: str,
    bundle_id: str,
    generated_at: datetime | None = None,
) -> str:
    generated_at = generated_at or datetime.now(timezone.utc)
    findings = _findings(evidence, detector_results)
    status = _report_status(collection_status, findings, detector_results)
    top_issue = findings[0] if findings else None
    affected_users = _affected_users(evidence, top_issue)

    lines = [
        "# Ops-Agent Decision Report Context",
        "",
        "This Markdown context is generated from sanitized bundle evidence. Use it to write the final Markdown operational report; do not add a JSON summary.",
        "",
        "## Executive Summary",
        "",
        f"Status: {status}",
        "",
        f"Top issue: {top_issue.title if top_issue else 'No triggered finding in available evidence.'}",
        f"Affected users: {affected_users}",
        f"Most severe finding: {top_issue.evidence if top_issue else 'No severe finding in available evidence.'}",
        f"Recommended next fix: {top_issue.recommended_action if top_issue else 'No fix required from available evidence.'}",
        f"PR mapping: {top_issue.pr_mapping if top_issue else 'not applicable'}",
        "",
        "## Report Metadata",
        "",
        f"- Report window start: {period.as_dict()['start']}",
        f"- Report window end: {period.as_dict()['end']}",
        f"- Generated at: {isoformat_utc(generated_at)}",
        f"- Environment/source: ops-agent sanitized bundle, period source `{period.source}`",
        f"- Generated from bundle: `{bundle_id}`",
        f"- Collection status: `{collection_status}`",
        f"- Data sources used: {_data_sources(evidence)}",
        "- Command/date input caveat: production wrapper accepts UTC ISO timestamps only, for example `2026-06-06T00:00:00Z`; ambiguous dates such as `06/06/2026` are rejected.",
        "",
        "## User Impact",
        "",
        *_user_impact_table(evidence),
        "",
        "## Delivery Funnel",
        "",
        *_delivery_funnel(evidence),
        "",
        "## Alert Quality",
        "",
        *_alert_quality(evidence),
        "",
        "## Event Alert Regression Checks",
        "",
        *_event_alert_regression_checks(evidence, detector_results),
        "",
        "## Suppression Reasons",
        "",
        *_suppression_reasons(evidence),
        "",
        "## Top Noisy Event Families",
        "",
        *_noisy_event_families(evidence),
        "",
        "## Severity Model",
        "",
        "- Critical: user-facing broken messages, high delivery failure rate, or issues that make alerts misleading/unusable.",
        "- High: duplicate/noisy alerts affecting many users or repeated failures with clear user impact.",
        "- Medium: internal inconsistency, degraded observability, or limited user impact.",
        "- Low: report-only issue, documentation gap, or minor formatting issue.",
        "",
        "## Confirmed Findings",
        "",
        *_finding_section(findings, "confirmed"),
        "",
        "## Likely Findings",
        "",
        *_finding_section(findings, "likely"),
        "",
        "## Unknown / Needs Investigation",
        "",
        *_unknown_section(detector_results),
        "",
        "## Data Completeness and Limitations",
        "",
        *_data_completeness(evidence),
        "",
    ]
    return "\n".join(lines)


def _query_rows(evidence: dict[str, Any], query_name: str) -> list[dict[str, Any]]:
    payload = evidence.get("evidence/db/aggregate_metrics.json")
    if not isinstance(payload, dict):
        return []
    query = (payload.get("queries") or {}).get(query_name)
    return list((query or {}).get("rows") or []) if isinstance(query, dict) else []


def _query_rows_from(
    evidence: dict[str, Any], file_name: str, query_name: str
) -> list[dict[str, Any]]:
    payload = evidence.get(file_name)
    if not isinstance(payload, dict):
        return []
    query = (payload.get("queries") or {}).get(query_name)
    return list((query or {}).get("rows") or []) if isinstance(query, dict) else []


def _has_query(evidence: dict[str, Any], query_name: str) -> bool:
    payload = evidence.get("evidence/db/aggregate_metrics.json")
    if not isinstance(payload, dict):
        return False
    return isinstance((payload.get("queries") or {}).get(query_name), dict)


def _payload(evidence: dict[str, Any], path: str) -> dict[str, Any]:
    payload = evidence.get(path)
    return payload if isinstance(payload, dict) else {}


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _pct(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "not available"
    return f"{(numerator / denominator) * 100:.1f}%"


def _count_pct(numerator: int, denominator: int, label: str) -> str:
    return f"{numerator} / {denominator} {label}, {_pct(numerator, denominator)}"


def _findings(
    evidence: dict[str, Any], detector_results: list[DetectorResult]
) -> list[ReportFinding]:
    findings: list[ReportFinding] = []
    quality = _payload(evidence, "evidence/db/alert_quality.json")
    quality_issues = list(quality.get("issues") or [])
    severe_quality = [
        row
        for row in quality_issues
        if row.get("issue") in {
            "contains_n_a",
            "contains_unknown",
            "contains_unavailable",
            "contains_null",
        }
    ]
    if severe_quality:
        affected = sum(_int(row.get("affected_users_estimate")) for row in severe_quality)
        denominator = _int(quality.get("total_event_alert_deliveries"))
        affected_deliveries = _int(quality.get("severe_affected_event_alert_deliveries"))
        issue_occurrences = sum(_int(row.get("delivery_count")) for row in severe_quality)
        if not affected_deliveries and issue_occurrences and denominator:
            affected_deliveries = min(issue_occurrences, denominator)
        if denominator:
            affected_deliveries = min(affected_deliveries, denominator)
        findings.append(
            ReportFinding(
                title="Event Alerts with missing or placeholder market context",
                severity="critical",
                evidence=(
                    f"{_count_pct(affected_deliveries, denominator, 'unique affected Event Alert deliveries')} "
                    f"({issue_occurrences} grouped issue occurrences)"
                ),
                user_impact=(
                    f"{affected} affected-user estimate from grouped alert evidence; "
                    "exact distinct user count may be lower."
                ),
                recommended_action=(
                    "Fix Event Alert formatting so missing values are omitted instead of rendered."
                ),
                pr_mapping="Event Alert cleanup regression checks",
                confidence="high",
            )
        )
    old_label_quality = [
        row for row in quality_issues if str(row.get("issue") or "").startswith("old_")
    ]
    if old_label_quality:
        affected = sum(_int(row.get("affected_users_estimate")) for row in old_label_quality)
        issue_occurrences = sum(_int(row.get("delivery_count")) for row in old_label_quality)
        findings.append(
            ReportFinding(
                title="Event Alerts with old or confusing percentage labels",
                severity="high",
                evidence=f"{issue_occurrences} grouped old-label occurrences",
                user_impact=(
                    f"{affected} affected-user estimate from grouped alert evidence; "
                    "exact distinct user count may be lower."
                ),
                recommended_action=(
                    "Migrate Event Alert copy to `Since last alert/message` and "
                    "`<window> market move` labels."
                ),
                pr_mapping="Event Alert cleanup regression checks",
                confidence="high",
            )
        )
    for result in detector_results:
        if result.status != "triggered":
            continue
        findings.append(
            ReportFinding(
                title=result.id.replace("_", " ").title(),
                severity=result.severity,
                evidence=result.summary,
                user_impact=_detector_user_impact(result),
                recommended_action=_recommended_action(result.id),
                pr_mapping=_pr_mapping(result.id),
                confidence="medium" if result.evidence_gap else "high",
                status="likely" if result.evidence_gap else "confirmed",
            )
        )
    return sorted(findings, key=lambda item: (SEVERITY_RANK.get(item.severity, 9), item.title))


def _report_status(
    collection_status: str,
    findings: list[ReportFinding],
    detector_results: list[DetectorResult],
) -> str:
    if collection_status != "complete":
        return "degraded"
    if any(item.severity == "critical" for item in findings):
        return "degraded"
    if findings or any(item.status == "unknown" for item in detector_results):
        return "needs attention"
    return "healthy"


def _affected_users(evidence: dict[str, Any], top_issue: ReportFinding | None) -> str:
    impact = _query_rows(evidence, "user_impact_summary")
    if top_issue and "placeholder market context" in top_issue.title.lower() and impact:
        return str(_int(impact[0].get("users_affected_by_content_quality_issues")))
    if impact:
        return str(
            max(
                _int(impact[0].get("users_affected_by_delivery_failures")),
                _int(impact[0].get("users_affected_by_duplicate_alerts")),
                _int(impact[0].get("users_affected_by_content_quality_issues")),
            )
        )
    return "not available - user impact summary query is missing"


def _data_sources(evidence: dict[str, Any]) -> str:
    sources = []
    if "evidence/db/aggregate_metrics.json" in evidence:
        sources.append("database aggregate metrics")
    if "detectors/detector_results.json" in evidence:
        sources.append("detector results")
    if "evidence/logs/pattern_counts.json" in evidence:
        sources.append("log pattern counts")
    if "evidence/health/health.json" in evidence:
        sources.append("health probe")
    if "evidence/db/alert_quality.json" in evidence:
        sources.append("sanitized alert quality evidence")
    return ", ".join(sources) if sources else "not available"


def _user_impact_table(evidence: dict[str, Any]) -> list[str]:
    rows = _query_rows(evidence, "user_impact_summary")
    if not rows:
        return ["not available - `user_impact_summary` was not collected."]
    row = rows[0]
    return [
        "| Metric | Count | Notes |",
        "|---|---:|---|",
        f"| Current active users | {_int(row.get('active_users_current'))} | Current active-user count from DB. |",
        f"| Users who received Event Alerts | {_int(row.get('users_received_event_alerts'))} | Distinct recipients in `alerts`. |",
        f"| Users who received Heartbeats | {_int(row.get('users_received_heartbeats'))} | Distinct recipients with heartbeat-linked alerts. |",
        f"| Users affected by delivery failures | {_int(row.get('users_affected_by_delivery_failures'))} | Distinct users with failed or retry-pending delivery rows. |",
        f"| Users affected by duplicate or noisy alerts | {_int(row.get('users_affected_by_duplicate_alerts'))} | Duplicate delivery rows by user and market event. |",
        f"| Users affected by formatting/content quality issues | {_int(row.get('users_affected_by_content_quality_issues'))} | Event Alerts with placeholder text or missing numeric context. |",
    ]


def _delivery_funnel(evidence: dict[str, Any]) -> list[str]:
    rows = _query_rows(evidence, "delivery_funnel")
    if not rows:
        return ["not available - `delivery_funnel` was not collected."]
    row = rows[0]
    stages = [
        ("Market events", _int(row.get("market_events")), None),
        ("AI analyses", _int(row.get("ai_analyses")), _int(row.get("market_events"))),
        ("should_alert=true", _int(row.get("should_alert_true")), _int(row.get("ai_analyses"))),
        (
            "Alert records created",
            _int(row.get("alert_records_created")),
            _int(row.get("should_alert_true")),
        ),
        (
            "Telegram delivery attempts",
            _int(row.get("telegram_delivery_attempts")),
            _int(row.get("alert_records_created")),
        ),
        (
            "Telegram delivered",
            _int(row.get("telegram_delivered")),
            _int(row.get("telegram_delivery_attempts")),
        ),
        (
            "Telegram failed",
            _int(row.get("telegram_failed")),
            _int(row.get("telegram_delivery_attempts")),
        ),
    ]
    lines = ["| Stage | Count | Conversion |", "|---|---:|---:|"]
    for label, count, denominator in stages:
        conversion = "100.0%" if denominator is None and count else _pct(count, denominator or 0)
        lines.append(f"| {label} | {count} | {conversion} |")
    return lines


def _alert_quality(evidence: dict[str, Any]) -> list[str]:
    payload = _payload(evidence, "evidence/db/alert_quality.json")
    rows = list(payload.get("issues") or [])
    denominator = _int(payload.get("total_event_alert_deliveries"))
    if not rows:
        if payload:
            return ["No alert quality issues found in collected sanitized alert evidence."]
        return ["not available - sanitized alert quality evidence was not collected."]
    lines = [
        "| Issue | Symbol | Trigger Source | Alert Type | Count | Percent | Affected Users |",
        "|---|---|---|---|---:|---:|---:|",
    ]
    for row in rows[:20]:
        count = _int(row.get("delivery_count"))
        lines.append(
            "| {issue} | {symbol} | {trigger} | {alert_type} | {count} | {percent} | {users} |".format(
                issue=row.get("issue"),
                symbol=row.get("symbol"),
                trigger=row.get("trigger_source"),
                alert_type=row.get("alert_type"),
                count=count,
                percent=_pct(count, denominator),
                users=row.get("affected_users_estimate", "not available"),
            )
        )
    lines.append("")
    lines.append(
        "Limitations: raw Telegram text is not exported; affected-user estimates may double-count users across grouped rows."
    )
    return lines


def _event_alert_regression_checks(
    evidence: dict[str, Any], detector_results: list[DetectorResult]
) -> list[str]:
    regression_payload = _payload(evidence, "evidence/db/event_alert_regression_checks.json")
    duplicate_rows = _query_rows_from(
        evidence,
        "evidence/db/anomalies.json",
        "event_ai_analysis_invariant_checks",
    )
    gap_rows = _query_rows_from(
        evidence,
        "evidence/db/anomalies.json",
        "event_alert_delivery_explanation_gaps",
    )
    detector_by_id = {result.id: result for result in detector_results}
    cooldown = detector_by_id.get("cooldown_effectiveness_gap")
    delivery_gap = detector_by_id.get("event_alert_delivery_explanation_gaps")

    duplicate_count = len(duplicate_rows)
    duplicate_samples = [
        str(row.get("market_event_id"))
        for row in duplicate_rows[:5]
        if row.get("market_event_id") is not None
    ]
    duplicate_symbols = sorted(
        {
            str(row.get("symbol")).upper()
            for row in duplicate_rows
            if row.get("symbol") is not None
        }
    )
    placeholder_counts = regression_payload.get("placeholder_issue_counts") or {}
    old_label_counts = regression_payload.get("old_label_issue_counts") or {}
    repeat_noise_groups = _int(regression_payload.get("same_family_repeat_noise_groups"))
    allowed_repeat_groups = _int(
        regression_payload.get("same_family_allowed_escalation_groups")
    )
    gap_count = sum(_int(row.get("gap_count")) for row in gap_rows)

    status = "OK"
    if duplicate_count or gap_count or placeholder_counts or old_label_counts:
        status = "Critical"
    elif repeat_noise_groups:
        status = "Warning"

    lines = [f"Status: {status}"]
    if not any(
        [duplicate_count, gap_count, placeholder_counts, old_label_counts, repeat_noise_groups]
    ):
        return lines + [
            "OK - no duplicate attached analyses, same-family repeat noise, unexplained delivery gaps, placeholder text, or old percentage labels were found in collected evidence."
        ]

    lines.extend(
        [
            "| Check | Count | Interpretation | Recommended next action |",
            "|---|---:|---|---|",
            (
                f"| Duplicate attached successful event analyses | {duplicate_count} | "
                f"{'Critical invariant regression' if duplicate_count else 'OK'} | "
                "Keep one successful attached analysis per market event. |"
            ),
            (
                f"| Same-family repeats without escalation | {repeat_noise_groups} | "
                f"{'Likely alert noise' if repeat_noise_groups else 'OK'}; "
                f"{allowed_repeat_groups} escalation groups were counted separately. | "
                "Inspect semantic cooldown and escalation evidence. |"
            ),
            (
                f"| should_alert=true without delivery explanation | {gap_count} | "
                f"{'Observability gap' if gap_count else 'OK'} | "
                "Ensure delivery, suppression, failure, rate-limit, or no-recipient outcomes are persisted. |"
            ),
            (
                f"| Bad placeholder text | {sum(_int(value) for value in placeholder_counts.values())} | "
                f"{'User-facing copy regression' if placeholder_counts else 'OK'} | "
                "Omit missing numeric fields instead of rendering placeholders. |"
            ),
            (
                f"| Old/confusing percentage labels | {sum(_int(value) for value in old_label_counts.values())} | "
                f"{'User-facing copy regression' if old_label_counts else 'OK'} | "
                "Use `Since last alert/message` and `<window> market move`. |"
            ),
        ]
    )
    if duplicate_samples or duplicate_symbols:
        lines.append(
            "Samples: duplicate market_event_ids "
            f"{', '.join(duplicate_samples) or 'not available'}; symbols "
            f"{', '.join(duplicate_symbols) or 'not available'}."
        )
    if cooldown and cooldown.status == "unknown":
        lines.append(f"Cooldown repeat evidence gap: {cooldown.evidence_gap}")
    if delivery_gap and delivery_gap.status == "unknown":
        lines.append(f"Delivery explanation evidence gap: {delivery_gap.evidence_gap}")
    return lines


def _suppression_reasons(evidence: dict[str, Any]) -> list[str]:
    payload = _payload(evidence, "evidence/logs/pattern_counts.json")
    reasons = payload.get("period_matched_suppression_reason_counts")
    if not isinstance(reasons, dict) or not reasons:
        if payload:
            return [
                "not available - no period-matched suppression reason logs were present. If suppression observability is not deployed on this branch, treat this as a known limitation."
            ]
        return ["not available - log pattern counts were not collected."]
    total = sum(_int(value) for value in reasons.values())
    lines = ["| Reason | Count | Share |", "|---|---:|---:|"]
    for reason, count in sorted(reasons.items(), key=lambda item: (-_int(item[1]), item[0])):
        value = _int(count)
        lines.append(f"| {reason} | {value} | {_pct(value, total)} |")
    return lines


def _noisy_event_families(evidence: dict[str, Any]) -> list[str]:
    similarity = _payload(evidence, "evidence/db/alert_similarity_groups.json")
    groups = list(similarity.get("groups") or [])
    if not groups:
        if similarity:
            return [
                "No noisy semantic groups found in collected evidence. Durable `semantic_family` data may still be unavailable; use event keys and bundle-local semantic group ids."
            ]
        return ["not available - semantic similarity evidence was not collected."]
    lines = [
        "| Semantic Family | Event Keys | Symbol | Count | Affected Users | Evidence |",
        "|---|---|---|---:|---:|---|",
    ]
    for row in groups[:10]:
        symbols = ", ".join(str(item) for item in row.get("symbols") or ["unknown"])
        event_keys = ", ".join(str(item) for item in row.get("event_keys") or ["not available"])
        count = _int(row.get("sent_deliveries")) or _int(row.get("market_events"))
        lines.append(
            f"| {row.get('semantic_group_id', 'not available')} | {event_keys} | {symbols} | {count} | not available | {', '.join(row.get('safe_terms') or []) or 'safe summary unavailable'} |"
        )
    return lines


def _finding_section(findings: list[ReportFinding], status: str) -> list[str]:
    scoped = [item for item in findings if item.status == status]
    if not scoped:
        return ["No findings."]
    lines: list[str] = []
    for item in scoped:
        lines.extend(
            [
                f"### {item.title}",
                "",
                f"- Severity: {item.severity}",
                f"- Evidence: {item.evidence}",
                f"- User impact: {item.user_impact}",
                f"- Recommended action: {item.recommended_action}",
                f"- Confidence: {item.confidence}",
                "",
                "### PR Mapping",
                "",
                f"- Proposed fix: {item.recommended_action}",
                f"- Covered by: {item.pr_mapping}",
                f"- New work required: {'yes' if 'new work' in item.pr_mapping.lower() else 'no'}",
                "",
            ]
        )
    return lines


def _unknown_section(detector_results: list[DetectorResult]) -> list[str]:
    unknown = [item for item in detector_results if item.status == "unknown"]
    if not unknown:
        return ["No unknown findings."]
    return [
        f"- `{item.id}`: {item.evidence_gap or item.summary}"
        for item in sorted(unknown, key=lambda item: item.id)
    ]


def _data_completeness(evidence: dict[str, Any]) -> list[str]:
    checks = [
        ("Market events available", _has_query(evidence, "market_events_summary")),
        ("AI analyses available", _has_query(evidence, "event_ai_analysis_summary")),
        ("Alert delivery records available", _has_query(evidence, "alerts_summary")),
        ("Telegram failure details available", "evidence/db/recent_alert_failures.json" in evidence),
        ("Warning/error logs available", "evidence/logs/pattern_counts.json" in evidence),
        ("Suppression reason data available", bool(_suppression_reasons_available(evidence))),
        ("Semantic family data available", bool(_payload(evidence, "evidence/db/alert_similarity_groups.json"))),
    ]
    lines = [f"- {name}: {'yes' if available else 'no'}" for name, available in checks]
    lines.extend(
        [
            "",
            "Limitations:",
            "- Row caps and bundle size limits can omit lower-priority evidence.",
            "- Content hashes and semantic group ids are bundle-local and must not be compared across bundles.",
            "- Missing data should be reported as `not available`, not treated as healthy.",
        ]
    )
    return lines


def _suppression_reasons_available(evidence: dict[str, Any]) -> bool:
    payload = _payload(evidence, "evidence/logs/pattern_counts.json")
    reasons = payload.get("period_matched_suppression_reason_counts")
    return isinstance(reasons, dict) and bool(reasons)


def _detector_user_impact(result: DetectorResult) -> str:
    metrics = result.metrics
    if "failed" in metrics and "total" in metrics:
        return _count_pct(_int(metrics.get("failed")), _int(metrics.get("total")), "deliveries")
    if "duplicate_deliveries" in metrics:
        return f"{_int(metrics.get('duplicate_deliveries'))} duplicate delivery groups"
    if "blocked_active_users" in metrics:
        return f"{_int(metrics.get('blocked_active_users'))} blocked active users"
    return "not available from detector metrics"


def _recommended_action(detector_id: str) -> str:
    if detector_id in {"cooldown_effectiveness_gap", "repeated_alert_content", "similar_alert_groups"}:
        return "Implement or tune suppression observability and semantic cooldown behavior."
    if detector_id == "event_alert_delivery_explanation_gaps":
        return "Persist an explicit delivery, suppression, failure, rate-limit, or no-recipient outcome."
    if detector_id in {"weak_event_identity", "duplicate_market_events"}:
        return "Normalize semantic event identity and stable event keys."
    if detector_id == "failed_telegram_deliveries":
        return "Investigate delivery failures and blocked-user cleanup first."
    if detector_id == "market_event_analysis_invariant":
        return "Fix any path that creates more than one AI analysis for the same market event."
    return "Investigate the detector evidence and add the smallest targeted fix."


def _pr_mapping(detector_id: str) -> str:
    if detector_id in {"cooldown_effectiveness_gap", "repeated_alert_content", "similar_alert_groups"}:
        return "PR2 suppression observability"
    if detector_id in {"weak_event_identity", "duplicate_market_events"}:
        return "PR3 semantic identity"
    if detector_id == "failed_telegram_deliveries":
        return "new work"
    if detector_id == "event_alert_delivery_explanation_gaps":
        return "Event Alert cleanup regression checks"
    return "new work"
