# ruff: noqa: E501
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ops_agent.schemas import DetectorResult, Period


def _query_payload(
    evidence: dict[str, Any], file_name: str, query_name: str
) -> dict[str, Any] | None:
    file_payload = evidence.get(file_name)
    if not isinstance(file_payload, dict):
        return None
    query = (file_payload.get("queries") or {}).get(query_name)
    return query if isinstance(query, dict) else None


def _has_query(evidence: dict[str, Any], file_name: str, query_name: str) -> bool:
    return _query_payload(evidence, file_name, query_name) is not None


def _query_rows(evidence: dict[str, Any], file_name: str, query_name: str) -> list[dict[str, Any]]:
    query = _query_payload(evidence, file_name, query_name) or {}
    return list(query.get("rows") or [])


def _missing_gap(evidence: dict[str, Any], required: list[tuple[str, str]]) -> str | None:
    missing = [
        f"{file_name}:{query_name}"
        for file_name, query_name in required
        if not _has_query(evidence, file_name, query_name)
    ]
    if not missing:
        return None
    return "Required evidence missing: " + ", ".join(missing)


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _event_ref(value: Any) -> str:
    return f"market_event:{value}"


def _log_counts(evidence: dict[str, Any]) -> tuple[bool, dict[str, Any], dict[str, Any], bool]:
    payload = evidence.get("evidence/logs/pattern_counts.json")
    if not isinstance(payload, dict):
        return False, {}, {}, False
    period_counts = payload.get("period_matched_pattern_counts")
    tail_counts = payload.get("tail_context_pattern_counts")
    if isinstance(period_counts, dict):
        log_index = evidence.get("evidence/logs/log_index.json") or {}
        files = log_index.get("files") if isinstance(log_index, dict) else []
        period_filter_applied = any(
            ((item.get("timestamp_parse") or {}).get("period_filter_applied"))
            for item in files or []
            if isinstance(item, dict)
        )
        return True, period_counts, tail_counts if isinstance(tail_counts, dict) else {}, period_filter_applied
    legacy_counts = payload.get("pattern_counts")
    return True, legacy_counts if isinstance(legacy_counts, dict) else {}, {}, False


def _no_delivery_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    classifications = {
        str(row.get("classification") or "unknown"): _int(row.get("events")) for row in rows
    }
    expected = sum(
        classifications.get(name, 0)
        for name in {
            "expected_should_alert_false",
            "expected_no_eligible_recipients",
            "expected_product_gating_possible",
            "expected_backend_cooldown_active",
        }
    )
    unknown = sum(
        classifications.get(name, 0)
        for name in {
            "unknown",
            "unknown_no_analysis",
            "unknown_should_alert_null",
        }
    )
    return {
        "classifications": classifications,
        "expected_no_delivery": expected,
        "llm_failure_or_rate_limit": classifications.get("llm_failure_or_rate_limit", 0),
        "expected_backend_cooldown_active": classifications.get(
            "expected_backend_cooldown_active", 0
        ),
        "delivery_gap_should_alert_true": classifications.get(
            "delivery_gap_should_alert_true", 0
        ),
        "unknown": unknown,
        "total_events_without_delivery": sum(classifications.values()),
        "sample_event_refs": [
            _event_ref(sample.get("market_event_id"))
            for row in rows
            for sample in (row.get("sample_events") or [])
            if isinstance(sample, dict) and sample.get("market_event_id") is not None
        ][:5],
    }


def run_detectors(evidence: dict[str, Any], period: Period) -> list[DetectorResult]:
    aggregate = "evidence/db/aggregate_metrics.json"
    anomalies = "evidence/db/anomalies.json"
    alert_failures = _query_rows(evidence, "evidence/db/recent_alert_failures.json", "alerts_failures")
    alert_summary = _query_rows(evidence, aggregate, "alerts_summary")
    llm_summary = _query_rows(evidence, aggregate, "llm_usage_summary")
    reports = _query_rows(evidence, aggregate, "market_reports_summary")
    report_freshness = _query_rows(evidence, aggregate, "market_reports_freshness")
    heartbeats = _query_rows(evidence, aggregate, "market_heartbeats_summary")
    heartbeat_freshness = _query_rows(evidence, aggregate, "market_heartbeats_freshness")
    market_event_summary = _query_rows(evidence, aggregate, "market_events_summary")
    price_state = _query_rows(evidence, aggregate, "price_state_current")
    market_events = _query_rows(evidence, "evidence/db/recent_market_events.json", "market_events_recent")
    duplicate_event_payload = _query_payload(evidence, anomalies, "duplicate_market_event_buckets")
    duplicate_event_rows = _query_rows(evidence, anomalies, "duplicate_market_event_buckets")
    no_delivery_rows = _query_rows(
        evidence, anomalies, "market_events_without_delivery_classification"
    )
    invariant_rows = _query_rows(evidence, anomalies, "delivery_invariant_checks")
    analysis_invariant_rows = _query_rows(
        evidence, anomalies, "event_ai_analysis_invariant_checks"
    )
    blocked_users = _query_rows(evidence, anomalies, "blocked_users_still_active")
    payment_inconsistencies = _query_rows(evidence, anomalies, "premium_payment_inconsistencies")
    news_rows = _query_rows(evidence, "evidence/db/recent_news_failures.json", "news_items_recent_high_impact")
    logs_available, period_logs, tail_logs, period_logs_available = _log_counts(evidence)
    health = evidence.get("evidence/health/health.json") or {}

    failed_deliveries = sum(_int(row.get("failed")) for row in alert_summary)
    total_deliveries = sum(_int(row.get("deliveries")) for row in alert_summary)
    failed_rate = failed_deliveries / total_deliveries if total_deliveries else 0
    llm_failures = sum(
        _int(row.get("calls"))
        for row in llm_summary
        if str(row.get("status") or "") not in {"success", "completed"}
    )
    rate_limits = sum(_int(row.get("rate_limit_count")) for row in llm_summary)
    failed_reports = sum(
        _int(row.get("reports")) for row in reports if str(row.get("status")) != "completed"
    )
    stale_reports = [
        row
        for row in report_freshness
        if row.get("latest_generated_at") is None
        or str(row.get("latest_status") or "") != "completed"
        or _int(row.get("age_seconds")) > _int(row.get("max_age_seconds"))
        or (
            _parse_datetime(row.get("latest_expires_at")) is not None
            and _parse_datetime(row.get("latest_expires_at")) <= period.end
        )
    ]
    heartbeat_failures = sum(
        _int(row.get("heartbeats"))
        for row in heartbeats
        if str(row.get("status")) != "completed"
    )
    heartbeat_threshold_seconds = 7200
    stale_heartbeats = [
        row
        for row in heartbeat_freshness
        if row.get("latest_generated_at") is None
        or str(row.get("latest_status") or "") != "completed"
        or _int(row.get("age_seconds")) > heartbeat_threshold_seconds
    ]
    news_failures = sum(1 for row in news_rows if str(row.get("llm_status")) != "success")
    error_patterns = _int(period_logs.get("error"))
    tail_error_patterns = _int(tail_logs.get("error"))

    def result(
        detector_id: str,
        severity: str,
        status: str,
        summary: str,
        refs: list[str],
        metrics: dict[str, Any],
        evidence_gap: str | None = None,
    ) -> DetectorResult:
        return DetectorResult(detector_id, severity, status, summary, refs, metrics, evidence_gap)

    def db_result(
        detector_id: str,
        severity: str,
        required: list[tuple[str, str]],
        clear_status: str,
        summary: str,
        refs: list[str],
        metrics: dict[str, Any],
    ) -> DetectorResult:
        gap = _missing_gap(evidence, required)
        if gap:
            return result(detector_id, severity, "unknown", "Required evidence is missing", refs, metrics, gap)
        return result(detector_id, severity, clear_status, summary, refs, metrics)

    invariant_by_type: dict[str, int] = {}
    for row in invariant_rows:
        key = str(row.get("anomaly") or "unknown")
        invariant_by_type[key] = invariant_by_type.get(key, 0) + _int(row.get("count") or 1)
    for row in analysis_invariant_rows:
        key = str(row.get("anomaly") or "unknown")
        invariant_by_type[key] = invariant_by_type.get(key, 0) + _int(
            row.get("analysis_count") or 1
        )
    payment_by_type: dict[str, int] = {}
    for row in payment_inconsistencies:
        key = str(row.get("anomaly") or "unknown")
        payment_by_type[key] = payment_by_type.get(key, 0) + 1
    high_risk_payment_anomalies = sum(
        count
        for name, count in payment_by_type.items()
        if name
        in {
            "duplicate_provider_payment_ids",
            "duplicate_charge_ids",
            "paid_without_premium",
            "active_premium_without_trail",
            "payment_payload_user_mismatch",
            "charge_id_mismatch",
        }
    )

    duplicate_group_count = len(duplicate_event_rows)
    duplicate_max_group_size = max(
        (_int(row.get("group_size")) for row in duplicate_event_rows),
        default=0,
    )
    duplicate_symbols = sorted(
        {str(row.get("symbol")) for row in duplicate_event_rows if row.get("symbol")}
    )
    duplicate_samples = [
        {
            "symbol": row.get("symbol"),
            "event_type": row.get("event_type"),
            "event_key": row.get("event_key"),
            "group_size": _int(row.get("group_size")),
            "event_refs": [_event_ref(value) for value in (row.get("sample_market_event_ids") or [])],
        }
        for row in duplicate_event_rows[:5]
    ]
    duplicate_bucket_minutes = (
        ((duplicate_event_payload or {}).get("parameters") or {}).get("bucket_minutes") or 15
    )
    no_delivery = _no_delivery_metrics(no_delivery_rows)

    interval_seconds = max(
        (
            _int(row.get("automatic_check_interval_seconds"))
            for row in _query_rows(evidence, aggregate, "app_settings")
        ),
        default=0,
    )
    stale_price_rows = []
    freshness_threshold_seconds = max(interval_seconds * 2, 1800) if interval_seconds else None
    for row in price_state:
        checked_at = _parse_datetime(row.get("last_checked_at"))
        if checked_at and freshness_threshold_seconds is not None:
            age_seconds = (period.end - checked_at).total_seconds()
            if age_seconds > freshness_threshold_seconds:
                stale_price_rows.append(row)

    detectors = [
        db_result(
            "failed_telegram_deliveries",
            "high" if failed_deliveries >= 5 or failed_rate >= 0.2 else "info",
            [(aggregate, "alerts_summary"), ("evidence/db/recent_alert_failures.json", "alerts_failures")],
            "triggered" if failed_deliveries or alert_failures else "clear",
            f"{failed_deliveries} failed or retry-pending deliveries",
            ["evidence/db/recent_alert_failures.json", "evidence/db/aggregate_metrics.json"],
            {"failed": failed_deliveries, "total": total_deliveries, "failed_rate": failed_rate},
        ),
        db_result(
            "no_alert_deliveries_observed",
            "info",
            [(aggregate, "alerts_summary"), (aggregate, "price_state_current"), (aggregate, "market_events_summary")],
            "clear"
            if total_deliveries or not market_event_summary
            else "unknown",
            "Alert delivery rows are present or the active period has no market events",
            ["evidence/db/aggregate_metrics.json"],
            {
                "price_state_rows": len(price_state),
                "market_event_summary_rows": len(market_event_summary),
                "deliveries": total_deliveries,
                "interpretation": "zero deliveries alone is not a failure; inspect no-delivery classifications",
            },
        ),
        db_result(
            "market_events_without_alert_deliveries",
            "high"
            if no_delivery["delivery_gap_should_alert_true"]
            else "medium"
            if no_delivery["llm_failure_or_rate_limit"]
            else "info",
            [(anomalies, "market_events_without_delivery_classification")],
            "triggered"
            if no_delivery["delivery_gap_should_alert_true"]
            or no_delivery["llm_failure_or_rate_limit"]
            else "unknown"
            if no_delivery["unknown"]
            else "clear",
            "Market events without deliveries are classified before treating them as failures",
            ["evidence/db/anomalies.json"],
            no_delivery,
        ),
        db_result(
            "repeated_llm_failures_or_rate_limits",
            "high" if llm_failures >= 3 else "medium",
            [(aggregate, "llm_usage_summary")],
            "triggered" if llm_failures >= 3 or rate_limits else "clear",
            f"{llm_failures} LLM failures and {rate_limits} rate-limit signals",
            ["evidence/db/aggregate_metrics.json", "evidence/db/recent_llm_failures.json"],
            {"llm_failures": llm_failures, "rate_limits": rate_limits},
        ),
        db_result(
            "failed_daily_weekly_reports",
            "high" if stale_reports else "medium",
            [(aggregate, "market_reports_summary"), (aggregate, "market_reports_freshness")],
            "triggered" if failed_reports or stale_reports else "clear",
            f"{failed_reports} failed and {len(stale_reports)} stale/missing market reports",
            ["evidence/db/aggregate_metrics.json"],
            {
                "failed_reports": failed_reports,
                "stale_or_missing_reports": len(stale_reports),
                "affected_report_types": [row.get("report_type") for row in stale_reports],
            },
        ),
        db_result(
            "stale_or_failed_market_heartbeats",
            "medium",
            [(aggregate, "market_heartbeats_summary"), (aggregate, "market_heartbeats_freshness")],
            "triggered" if heartbeat_failures or stale_heartbeats else "clear",
            f"{heartbeat_failures} failed and {len(stale_heartbeats)} stale/missing heartbeat rows",
            ["evidence/db/aggregate_metrics.json"],
            {
                "failed_heartbeats": heartbeat_failures,
                "stale_or_missing_heartbeats": len(stale_heartbeats),
                "freshness_threshold_seconds": heartbeat_threshold_seconds,
                "affected_symbols": [row.get("symbol") for row in stale_heartbeats[:10]],
            },
        ),
        db_result(
            "duplicate_market_events",
            "medium",
            [(anomalies, "duplicate_market_event_buckets")],
            "triggered" if duplicate_group_count else "clear",
            f"{duplicate_group_count} duplicate-like market-event buckets",
            ["evidence/db/anomalies.json", "evidence/db/recent_market_events.json"],
            {
                "bucket_minutes": duplicate_bucket_minutes,
                "duplicate_like_group_count": duplicate_group_count,
                "max_group_size": duplicate_max_group_size,
                "affected_symbols": duplicate_symbols,
                "sample_groups": duplicate_samples,
                "recent_events": len(market_events),
            },
        ),
        db_result(
            "duplicate_alert_deliveries",
            "high",
            [(anomalies, "delivery_invariant_checks")],
            "triggered" if invariant_by_type.get("duplicate_alert_deliveries", 0) else "clear",
            f"{invariant_by_type.get('duplicate_alert_deliveries', 0)} duplicate delivery groups",
            ["evidence/db/anomalies.json"],
            {"duplicate_deliveries": invariant_by_type.get("duplicate_alert_deliveries", 0)},
        ),
        db_result(
            "market_event_analysis_invariant",
            "critical",
            [
                (anomalies, "delivery_invariant_checks"),
                (anomalies, "event_ai_analysis_invariant_checks"),
            ],
            "triggered"
            if invariant_by_type.get("multiple_analysis_ids_for_event", 0)
            or invariant_by_type.get("multiple_event_ai_analyses_for_event", 0)
            else "clear",
            "Core market event to AI analysis invariant check",
            ["evidence/db/anomalies.json"],
            {
                "multiple_analysis_ids_for_event": invariant_by_type.get(
                    "multiple_analysis_ids_for_event", 0
                ),
                "multiple_event_ai_analyses_for_event": invariant_by_type.get(
                    "multiple_event_ai_analyses_for_event", 0
                ),
            },
        ),
        db_result(
            "blocked_users_still_active",
            "high",
            [(anomalies, "blocked_users_still_active")],
            "triggered" if blocked_users else "clear",
            f"{len(blocked_users)} blocked users still active",
            ["evidence/db/anomalies.json"],
            {"blocked_active_users": len(blocked_users)},
        ),
        db_result(
            "payment_premium_inconsistencies",
            "high" if high_risk_payment_anomalies else "medium",
            [(anomalies, "premium_payment_inconsistencies")],
            "triggered" if payment_inconsistencies else "clear",
            f"{len(payment_inconsistencies)} premium/payment inconsistency rows",
            ["evidence/db/anomalies.json"],
            {
                "anomalies_by_type": payment_by_type,
                "high_risk_anomalies": high_risk_payment_anomalies,
            },
        ),
        db_result(
            "news_intelligence_failures",
            "medium",
            [("evidence/db/recent_news_failures.json", "news_items_recent_high_impact")],
            "triggered" if news_failures else "clear",
            f"{news_failures} failed or skipped high-impact news intelligence rows",
            ["evidence/db/recent_news_failures.json"],
            {"news_failures": news_failures},
        ),
        db_result(
            "stale_price_snapshots",
            "medium",
            [(aggregate, "price_state_current"), (aggregate, "app_settings")],
            "triggered" if stale_price_rows else "clear",
            f"{len(stale_price_rows)} price_state rows are stale against configured interval",
            ["evidence/db/aggregate_metrics.json"],
            {
                "price_state_rows": len(price_state),
                "stale_rows": len(stale_price_rows),
                "freshness_threshold_seconds": freshness_threshold_seconds,
                "sample_symbols": [row.get("symbol") for row in stale_price_rows[:5]],
            },
        ),
        result(
            "health_endpoint_unavailable",
            "critical",
            "unknown"
            if not health
            else "triggered"
            if health.get("status") != "ok"
            else "clear",
            f"Health collector status: {health.get('status', 'unknown')}",
            ["evidence/health/health.json"],
            {"http_status": health.get("http_status")},
            "Required evidence missing: evidence/health/health.json" if not health else None,
        ),
        result(
            "exception_patterns_in_logs",
            "medium",
            "unknown" if not logs_available else "triggered" if error_patterns else "clear",
            f"{error_patterns} period-matched error patterns and {tail_error_patterns} tail-context error patterns",
            ["evidence/logs/pattern_counts.json"],
            {
                "period_matched_error_patterns": error_patterns,
                "tail_context_error_patterns": tail_error_patterns,
                "period_logs_available": period_logs_available,
            },
            None if logs_available else "Required evidence missing: evidence/logs/pattern_counts.json",
        ),
    ]
    return detectors


def detector_payload(period: Period, results: list[DetectorResult]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "period": {"start": period.as_dict()["start"], "end": period.as_dict()["end"]},
        "results": [result.as_dict() for result in results],
    }


def detector_summary(results: list[DetectorResult]) -> str:
    lines = ["# Detector Summary", ""]
    unknown = [result for result in results if result.status == "unknown"]
    if unknown:
        lines.append("Unknown detector results require follow-up; do not treat them as healthy.")
        lines.append("")
    for result in results:
        lines.append(f"- `{result.id}`: {result.status} ({result.severity}) - {result.summary}")
        if result.evidence_gap:
            lines.append(f"  Evidence gap: {result.evidence_gap}")
    lines.append("")
    return "\n".join(lines)
