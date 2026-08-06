# ruff: noqa: E501
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ops_agent.expected_models import KNOWN_DECOMMISSIONED_MODELS, expected_model
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


def _file_payload(evidence: dict[str, Any], file_name: str) -> dict[str, Any]:
    payload = evidence.get(file_name)
    return payload if isinstance(payload, dict) else {}


def _missing_gap(evidence: dict[str, Any], required: list[tuple[str, str]]) -> str | None:
    missing = [
        f"{file_name}:{query_name}"
        for file_name, query_name in required
        if not _has_query(evidence, file_name, query_name)
    ]
    if not missing:
        return None
    return "Required evidence missing: " + ", ".join(missing)


def _missing_files_gap(evidence: dict[str, Any], required: list[str]) -> str | None:
    missing = [file_name for file_name in required if not isinstance(evidence.get(file_name), dict)]
    if not missing:
        return None
    return "Required evidence missing: " + ", ".join(missing)


def _incomplete_files_gap(evidence: dict[str, Any], required: list[str]) -> str | None:
    incomplete = []
    for file_name in required:
        payload = evidence.get(file_name)
        if not isinstance(payload, dict):
            continue
        warnings = payload.get("warnings")
        if payload.get("evidence_incomplete") or (isinstance(warnings, list) and warnings):
            incomplete.append(file_name)
    if not incomplete:
        return None
    return "Required evidence incomplete: " + ", ".join(incomplete)


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


def _list_payload_items(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    values = payload.get(key)
    return [item for item in values if isinstance(item, dict)] if isinstance(values, list) else []


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
            "expected_failed_or_rate_limited_outcome",
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
        "expected_failed_or_rate_limited_outcome": classifications.get(
            "expected_failed_or_rate_limited_outcome", 0
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
    llm_category_rows = _query_rows(evidence, aggregate, "llm_failure_category_summary")
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
    delivery_explanation_gap_rows = _query_rows(
        evidence, anomalies, "event_alert_delivery_explanation_gaps"
    )
    blocked_users = _query_rows(evidence, anomalies, "blocked_users_still_active")
    payment_inconsistencies = _query_rows(evidence, anomalies, "premium_payment_inconsistencies")
    news_rows = _query_rows(evidence, "evidence/db/recent_news_failures.json", "news_items_recent_high_impact")
    news_budget_rows = _query_rows(evidence, aggregate, "news_intelligence_budget_summary")
    delivery_distribution_payload = _file_payload(
        evidence, "evidence/db/alert_delivery_distribution.json"
    )
    content_fingerprint_payload = _file_payload(
        evidence, "evidence/db/alert_content_fingerprints.json"
    )
    similarity_payload = _file_payload(evidence, "evidence/db/alert_similarity_groups.json")
    suppression_payload = _file_payload(
        evidence, "evidence/db/backend_suppression_effectiveness.json"
    )
    identity_payload = _file_payload(evidence, "evidence/db/event_identity_quality.json")
    logs_available, period_logs, tail_logs, period_logs_available = _log_counts(evidence)
    health = evidence.get("evidence/health/health.json") or {}

    failure_summary_rows = _query_rows(evidence, aggregate, "telegram_delivery_failure_summary")
    failure_summary = failure_summary_rows[0] if failure_summary_rows else {}
    blocked_user_failures = _int(failure_summary.get("blocked_user"))
    retry_pending_actionable = _int(failure_summary.get("retry_pending_actionable"))
    unexplained_telegram_failures = _int(
        failure_summary.get("unexplained_telegram_failure")
    )
    failed_or_retry_pending_total = _int(failure_summary.get("failed_or_retry_pending_total"))
    failed_deliveries = retry_pending_actionable + unexplained_telegram_failures
    total_deliveries = sum(_int(row.get("deliveries")) for row in alert_summary)
    failed_rate = failed_deliveries / total_deliveries if total_deliveries else 0
    llm_category_counts: dict[str, int] = {}
    for row in llm_category_rows:
        category = str(row.get("failure_category") or "other")
        llm_category_counts[category] = llm_category_counts.get(category, 0) + _int(
            row.get("calls")
        )
    llm_failures = (
        sum(
            calls
            for category, calls in llm_category_counts.items()
            if category != "successful"
        )
        if llm_category_rows
        else sum(
            _int(row.get("calls"))
            for row in llm_summary
            if str(row.get("status") or "") not in {"success", "completed"}
        )
    )
    rate_limits = llm_category_counts.get("rate_limit_backoff", 0) or sum(
        _int(row.get("rate_limit_count")) for row in llm_summary
    )
    failed_reports = sum(
        _int(row.get("reports")) for row in reports if str(row.get("status")) != "completed"
    )
    # Explicit scheduler-grace breakdown so reports never have to speculate about the
    # regeneration cadence: threshold = runtime interval + grace; the bot refreshes each
    # report on its runtime interval and on-command generation may refresh anytime.
    report_freshness_details = [
        {
            "report_type": row.get("report_type"),
            "latest_status": row.get("latest_status"),
            "latest_generation_age_seconds": (
                _int(row.get("age_seconds")) if row.get("age_seconds") is not None else None
            ),
            "freshness_threshold_seconds": _int(row.get("max_age_seconds")),
            "runtime_interval_seconds": _int(row.get("runtime_interval_seconds")) or None,
            "scheduler_grace_seconds": (
                _int(row.get("max_age_seconds")) - _int(row.get("runtime_interval_seconds"))
                if row.get("runtime_interval_seconds") is not None
                else None
            ),
            "expected_next_scheduled_refresh_at": row.get("expected_next_scheduled_refresh_at"),
        }
        for row in report_freshness
    ]
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
    news_budget_counts: dict[str, int] = {}
    news_budget_by_impact: dict[str, int] = {}
    for row in news_budget_rows:
        category = str(row.get("outcome_category") or "unknown")
        impact = str(row.get("impact_bucket") or "low_or_null")
        items = _int(row.get("items"))
        news_budget_counts[category] = news_budget_counts.get(category, 0) + items
        if category == "skipped_budget":
            news_budget_by_impact[impact] = news_budget_by_impact.get(impact, 0) + items
    skipped_budget = news_budget_counts.get("skipped_budget", 0)
    failed_news_intelligence = news_budget_counts.get("failed", 0)
    pending_news_intelligence = news_budget_counts.get("pending", 0)
    unknown_news_intelligence = news_budget_counts.get("unknown", 0)
    high_medium_budget_skips = news_budget_by_impact.get("high", 0) + news_budget_by_impact.get(
        "medium", 0
    )
    total_news_intelligence = sum(news_budget_counts.values())
    excessive_budget_skips = skipped_budget >= 10 or high_medium_budget_skips >= 3 or (
        total_news_intelligence >= 20 and skipped_budget / total_news_intelligence >= 0.5
    )
    error_patterns = _int(period_logs.get("error"))
    tail_error_patterns = _int(tail_logs.get("error"))
    noisy_symbol_rows = [
        row
        for row in _list_payload_items(delivery_distribution_payload, "symbols")
        if _int(row.get("sent_deliveries")) >= 5
    ]
    repeated_content_groups = _list_payload_items(
        content_fingerprint_payload, "repeated_groups"
    )
    similar_alert_groups = _list_payload_items(similarity_payload, "groups")
    weak_identity_rows = [
        row
        for row in _list_payload_items(identity_payload, "rows")
        if _int(row.get("same_content_split_key_groups"))
        or _int(row.get("suspicious_key_count"))
        or (
            _int(row.get("market_events")) >= 5
            and float(row.get("event_key_churn_ratio") or 0) >= 0.8
        )
    ]
    split_key_groups = _list_payload_items(identity_payload, "same_content_split_key_groups")
    cooldown_gap_groups = [
        row
        for row in _list_payload_items(suppression_payload, "suppression_groups")
        if _int(row.get("delivered_inside_cooldown_candidates")) > 0
    ]
    repeated_alert_true_groups = [
        row
        for row in similar_alert_groups
        if _int(row.get("should_alert_true")) >= 2 and _int(row.get("market_events")) >= 2
    ]

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

    def file_result(
        detector_id: str,
        severity: str,
        required: list[str],
        clear_status: str,
        summary: str,
        refs: list[str],
        metrics: dict[str, Any],
    ) -> DetectorResult:
        gap = _missing_files_gap(evidence, required)
        if gap:
            return result(detector_id, severity, "unknown", "Required evidence is missing", refs, metrics, gap)
        gap = _incomplete_files_gap(evidence, required)
        if gap and clear_status == "clear":
            return result(detector_id, severity, "unknown", "Required evidence is incomplete", refs, metrics, gap)
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
    delivery_explanation_gap_count = sum(
        _int(row.get("gap_count")) for row in delivery_explanation_gap_rows
    )

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
            [
                (aggregate, "alerts_summary"),
                (aggregate, "telegram_delivery_failure_summary"),
                ("evidence/db/recent_alert_failures.json", "alerts_failures"),
            ],
            "triggered" if failed_deliveries else "clear",
            f"{failed_deliveries} actionable failed or retry-pending deliveries",
            ["evidence/db/recent_alert_failures.json", "evidence/db/aggregate_metrics.json"],
            {
                "failed": failed_deliveries,
                "total": total_deliveries,
                "failed_rate": failed_rate,
                "blocked_user_failures": blocked_user_failures,
                "retry_pending_actionable": retry_pending_actionable,
                "unexplained_telegram_failures": unexplained_telegram_failures,
                "failed_or_retry_pending_total": failed_or_retry_pending_total,
                "sample_failure_rows": len(alert_failures),
            },
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
        file_result(
            "noisy_alert_symbols",
            "medium",
            ["evidence/db/alert_delivery_distribution.json"],
            "triggered" if noisy_symbol_rows else "clear",
            f"{len(noisy_symbol_rows)} symbols sent at least 5 automatic alert deliveries",
            ["evidence/db/alert_delivery_distribution.json"],
            {
                "threshold_sent_deliveries": 5,
                "affected_symbols": [row.get("symbol") for row in noisy_symbol_rows[:10]],
                "top_symbols": _list_payload_items(delivery_distribution_payload, "symbols")[:10],
            },
        ),
        file_result(
            "repeated_alert_content",
            "medium",
            ["evidence/db/alert_content_fingerprints.json"],
            "triggered" if repeated_content_groups else "clear",
            f"{len(repeated_content_groups)} repeated exact alert-content hash groups",
            ["evidence/db/alert_content_fingerprints.json"],
            {
                "repeated_groups": len(repeated_content_groups),
                "max_sent_deliveries": max(
                    (_int(row.get("sent_deliveries")) for row in repeated_content_groups),
                    default=0,
                ),
                "sample_groups": repeated_content_groups[:5],
            },
        ),
        file_result(
            "similar_alert_groups",
            "medium",
            ["evidence/db/alert_similarity_groups.json"],
            "triggered" if similar_alert_groups else "clear",
            f"{len(similar_alert_groups)} near-similar alert groups",
            ["evidence/db/alert_similarity_groups.json"],
            {
                "similar_groups": len(similar_alert_groups),
                "max_market_events": max(
                    (_int(row.get("market_events")) for row in similar_alert_groups),
                    default=0,
                ),
                "sample_groups": similar_alert_groups[:5],
            },
        ),
        file_result(
            "llm_repeated_alert_true_for_similar_situations",
            "medium",
            ["evidence/db/alert_similarity_groups.json"],
            "triggered" if repeated_alert_true_groups else "clear",
            f"{len(repeated_alert_true_groups)} similar groups had repeated should_alert=true decisions",
            ["evidence/db/alert_similarity_groups.json"],
            {
                "groups": len(repeated_alert_true_groups),
                "max_should_alert_true": max(
                    (_int(row.get("should_alert_true")) for row in repeated_alert_true_groups),
                    default=0,
                ),
                "sample_groups": repeated_alert_true_groups[:5],
            },
        ),
        file_result(
            "weak_event_identity",
            "medium",
            ["evidence/db/event_identity_quality.json"],
            "triggered" if weak_identity_rows or split_key_groups else "clear",
            f"{len(weak_identity_rows)} symbols show weak event identity signals",
            ["evidence/db/event_identity_quality.json"],
            {
                "affected_symbols": [row.get("symbol") for row in weak_identity_rows[:10]],
                "same_content_split_key_groups": len(split_key_groups),
                "sample_split_groups": split_key_groups[:5],
                "sample_symbol_rows": weak_identity_rows[:5],
            },
        ),
        file_result(
            "cooldown_effectiveness_gap",
            "medium",
            ["evidence/db/backend_suppression_effectiveness.json"],
            "triggered" if cooldown_gap_groups else "clear",
            f"{len(cooldown_gap_groups)} semantic cooldown groups have delivered-inside-cooldown candidates",
            ["evidence/db/backend_suppression_effectiveness.json"],
            {
                "groups": len(cooldown_gap_groups),
                "candidate_deliveries": sum(
                    _int(row.get("delivered_inside_cooldown_candidates"))
                    for row in cooldown_gap_groups
                ),
                "sample_groups": cooldown_gap_groups[:5],
                "confidence_note": "suppression is inferred; no durable suppression rows exist",
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
            "event_alert_delivery_explanation_gaps",
            "high" if delivery_explanation_gap_count else "info",
            [(anomalies, "event_alert_delivery_explanation_gaps")],
            "triggered" if delivery_explanation_gap_count else "clear",
            f"{delivery_explanation_gap_count} should_alert=true analyses lack delivery or outcome explanation",
            ["evidence/db/anomalies.json"],
            {
                "should_alert_true_without_delivery_explanation": delivery_explanation_gap_count,
                "sample_groups": delivery_explanation_gap_rows[:5],
            },
        ),
        db_result(
            "repeated_llm_failures_or_rate_limits",
            "high" if llm_failures >= 3 else "medium",
            [(aggregate, "llm_usage_summary"), (aggregate, "llm_failure_category_summary")],
            "triggered" if llm_failures >= 3 or rate_limits else "clear",
            f"{llm_failures} LLM failures and {rate_limits} rate-limit signals",
            ["evidence/db/aggregate_metrics.json", "evidence/db/recent_llm_failures.json"],
            {
                "llm_failures": llm_failures,
                "rate_limits": rate_limits,
                "failure_categories": llm_category_counts,
            },
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
                "report_freshness": report_freshness_details,
                "regeneration_semantics": (
                    "scheduled refresh regenerates each report on its runtime interval; "
                    "on-command generation may refresh the cache at any time; the "
                    "freshness threshold adds scheduler grace on top of the interval"
                ),
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
            "high"
            if failed_news_intelligence
            else "medium"
            if excessive_budget_skips
            else "info",
            [(aggregate, "news_intelligence_budget_summary")],
            "triggered" if failed_news_intelligence or excessive_budget_skips else "clear",
            (
                f"{failed_news_intelligence} failed news intelligence rows, "
                f"{skipped_budget} budget skips ({high_medium_budget_skips} high/medium), "
                f"{news_failures} sample rows"
            ),
            ["evidence/db/aggregate_metrics.json", "evidence/db/recent_news_failures.json"],
            {
                "failed_news_intelligence": failed_news_intelligence,
                "skipped_budget": skipped_budget,
                "high_medium_budget_skips": high_medium_budget_skips,
                "pending_news_intelligence": pending_news_intelligence,
                "unknown_news_intelligence": unknown_news_intelligence,
                "total_news_intelligence": total_news_intelligence,
                "excessive_budget_skips": excessive_budget_skips,
                "sample_rows": len(news_rows),
            },
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
        _event_analysis_dead_detector(evidence, llm_summary, db_result),
        _event_analysis_model_drift_detector(evidence, llm_summary, db_result),
    ]
    return detectors


# Statuses that count as a working call in `llm_usage_logs`, which uses `success`/`completed`.
# `no_alert` belongs to `event_ai_analyses.status` and cannot appear here; it is listed only so
# this stays correct if the summary is ever widened to that table. Deliberately NOT the same set
# as bot/alerting/event_analysis.py's EVENT_ANALYSIS_SUCCESS_STATUSES, which describes a
# different table — do not "unify" them.
_EVENT_ANALYSIS_SUCCESS_STATUSES = {"success", "completed", "no_alert"}


def event_analysis_call_totals(llm_summary: list[dict[str, Any]]) -> tuple[int, int]:
    """Return ``(successful_calls, total_calls)`` for ``event_analysis`` in this period."""
    total = 0
    successful = 0
    for row in llm_summary:
        if str(row.get("call_type") or "") != "event_analysis":
            continue
        calls = _int(row.get("calls"))
        total += calls
        if str(row.get("status") or "") in _EVENT_ANALYSIS_SUCCESS_STATUSES:
            successful += calls
    return successful, total


def consecutive_zero_success_runs(state_snapshot: dict[str, Any]) -> int:
    """Count consecutive prior collection runs that recorded zero event-analysis successes.

    Reads the recorded per-run signal from the ops-agent state snapshot. A run with no signal
    (older state, or a run before this was recorded) stops the count rather than being assumed
    healthy or unhealthy.
    """
    runs = state_snapshot.get("recent_runs")
    if not isinstance(runs, list):
        return 0
    streak = 0
    for run in runs:
        if not isinstance(run, dict):
            break
        signal = run.get("event_analysis")
        if not isinstance(signal, dict) or signal.get("successful_calls") is None:
            break
        if _int(signal.get("total_calls")) == 0:
            # No attempts at all in that run says nothing about health — the bot may simply
            # have been stopped. Skip rather than counting it toward an outage streak.
            continue
        if _int(signal.get("successful_calls")) > 0:
            break
        streak += 1
    return streak


def _event_analysis_dead_detector(
    evidence: dict[str, Any],
    llm_summary: list[dict[str, Any]],
    db_result,
) -> DetectorResult:
    """Zero successful event analyses across this and prior collection cycles.

    This is the detector that would have caught the 2026-07 outage on day one. It keys on the
    *success rate*, not on error counts, because the failure mode produced a perfectly steady
    stream of identical failures that looked unremarkable in every aggregate.
    """
    successful, total = event_analysis_call_totals(llm_summary)
    state_snapshot = _file_payload(
        evidence, "evidence/local_state/ops_agent_state_snapshot.json"
    )
    prior_zero_runs = consecutive_zero_success_runs(state_snapshot)
    consecutive_cycles = prior_zero_runs + 1 if total > 0 and successful == 0 else 0

    if total == 0:
        # No event-analysis calls at all: nothing to judge. Unknown, never healthy.
        status = "unknown"
        summary = "No event_analysis calls recorded in this period"
    elif successful == 0:
        status = "triggered"
        summary = (
            f"Zero successful event_analysis calls across {consecutive_cycles} consecutive "
            f"collection cycle(s); {total} attempts in this period"
        )
    else:
        status = "clear"
        summary = f"{successful}/{total} event_analysis calls succeeded"

    return db_result(
        "event_analysis_success_rate_zero",
        "critical",
        [("evidence/db/aggregate_metrics.json", "llm_usage_summary")],
        status,
        summary,
        ["evidence/db/aggregate_metrics.json"],
        {
            "successful_calls": successful,
            "total_calls": total,
            "consecutive_zero_success_cycles": consecutive_cycles,
        },
    )


def _event_analysis_model_drift_detector(
    evidence: dict[str, Any],
    llm_summary: list[dict[str, Any]],
    db_result,
) -> DetectorResult:
    """Models actually used for event_analysis differ from the shipped default.

    A deployed `.env` silently overrides the code default, which is exactly how the outage
    persisted: the shipped default was changed while production kept calling a decommissioned
    model. Comparing what the database says was *used* against what the code ships makes that
    disagreement visible without reading `.env` on the server.
    """
    expected = expected_model("event_analysis")
    used_models = sorted(
        {
            str(row.get("model") or "").strip()
            for row in llm_summary
            if str(row.get("call_type") or "") == "event_analysis" and row.get("model")
        }
    )
    drifted = [model for model in used_models if expected and model != expected]
    decommissioned = [model for model in used_models if model in KNOWN_DECOMMISSIONED_MODELS]

    if not used_models:
        status = "unknown"
        summary = "No event_analysis model recorded in this period"
    elif decommissioned:
        status = "triggered"
        summary = (
            "event_analysis is calling a model the provider has withdrawn; "
            "expected the shipped default"
        )
    elif drifted:
        status = "triggered"
        summary = "event_analysis model in use differs from the shipped default"
    else:
        status = "clear"
        summary = "event_analysis model matches the shipped default"

    return db_result(
        "event_analysis_model_drift",
        "high" if decommissioned else "medium",
        [("evidence/db/aggregate_metrics.json", "llm_usage_summary")],
        status,
        summary,
        ["evidence/db/aggregate_metrics.json"],
        {
            "expected_model": expected,
            "models_in_use": used_models,
            "drifted_models": drifted,
            "decommissioned_models_in_use": decommissioned,
        },
    )


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
