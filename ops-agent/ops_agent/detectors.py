# ruff: noqa: E501
from __future__ import annotations

from typing import Any

from ops_agent.schemas import DetectorResult, Period


def _query_rows(evidence: dict[str, Any], file_name: str, query_name: str) -> list[dict[str, Any]]:
    file_payload = evidence.get(file_name) or {}
    query = (file_payload.get("queries") or {}).get(query_name) or {}
    return list(query.get("rows") or [])


def run_detectors(evidence: dict[str, Any], period: Period) -> list[DetectorResult]:
    aggregate = "evidence/db/aggregate_metrics.json"
    anomalies = "evidence/db/anomalies.json"
    alert_failures = _query_rows(evidence, "evidence/db/recent_alert_failures.json", "alerts_failures")
    alert_summary = _query_rows(evidence, aggregate, "alerts_summary")
    llm_summary = _query_rows(evidence, aggregate, "llm_usage_summary")
    reports = _query_rows(evidence, aggregate, "market_reports_summary")
    heartbeats = _query_rows(evidence, aggregate, "market_heartbeats_summary")
    price_state = _query_rows(evidence, aggregate, "price_state_current")
    market_events = _query_rows(evidence, "evidence/db/recent_market_events.json", "market_events_recent")
    invariant_rows = _query_rows(evidence, anomalies, "delivery_invariant_checks")
    blocked_users = _query_rows(evidence, anomalies, "blocked_users_still_active")
    duplicate_payments = _query_rows(evidence, anomalies, "duplicate_provider_payment_ids")
    news_rows = _query_rows(evidence, "evidence/db/recent_news_failures.json", "news_items_recent_high_impact")
    logs = ((evidence.get("evidence/logs/pattern_counts.json") or {}).get("pattern_counts") or {})
    health = evidence.get("evidence/health/health.json") or {}

    failed_deliveries = sum(int(row.get("failed") or 0) for row in alert_summary)
    total_deliveries = sum(int(row.get("deliveries") or 0) for row in alert_summary)
    failed_rate = failed_deliveries / total_deliveries if total_deliveries else 0
    llm_failures = sum(
        int(row.get("calls") or 0)
        for row in llm_summary
        if str(row.get("status") or "") not in {"success", "completed"}
    )
    rate_limits = sum(int(row.get("rate_limit_count") or 0) for row in llm_summary)
    failed_reports = sum(
        int(row.get("reports") or 0) for row in reports if str(row.get("status")) != "completed"
    )
    heartbeat_failures = sum(
        int(row.get("heartbeats") or 0)
        for row in heartbeats
        if str(row.get("status")) != "completed"
    )
    news_failures = sum(1 for row in news_rows if str(row.get("llm_status")) != "success")
    error_patterns = int(logs.get("error") or 0)

    def result(
        detector_id: str,
        severity: str,
        status: str,
        summary: str,
        refs: list[str],
        metrics: dict[str, Any],
    ) -> DetectorResult:
        return DetectorResult(detector_id, severity, status, summary, refs, metrics)

    invariant_by_type: dict[str, int] = {}
    for row in invariant_rows:
        key = str(row.get("anomaly") or "unknown")
        invariant_by_type[key] = invariant_by_type.get(key, 0) + int(row.get("count") or 1)

    detectors = [
        result(
            "failed_telegram_deliveries",
            "high" if failed_deliveries >= 5 or failed_rate >= 0.2 else "info",
            "triggered" if failed_deliveries or alert_failures else "clear",
            f"{failed_deliveries} failed or retry-pending deliveries",
            ["evidence/db/recent_alert_failures.json", "evidence/db/aggregate_metrics.json"],
            {"failed": failed_deliveries, "total": total_deliveries, "failed_rate": failed_rate},
        ),
        result(
            "no_alerts_generated_active_period",
            "medium",
            "triggered" if price_state and not total_deliveries else "clear",
            "Price state exists but no alert deliveries were created in the period",
            ["evidence/db/aggregate_metrics.json"],
            {"price_state_rows": len(price_state), "deliveries": total_deliveries},
        ),
        result(
            "market_events_without_alert_deliveries",
            "high",
            "triggered" if invariant_by_type.get("market_events_without_alert_deliveries", 0) else "clear",
            f"{invariant_by_type.get('market_events_without_alert_deliveries', 0)} events without deliveries",
            ["evidence/db/anomalies.json"],
            {"events_without_deliveries": invariant_by_type.get("market_events_without_alert_deliveries", 0)},
        ),
        result(
            "repeated_llm_failures_or_rate_limits",
            "high" if llm_failures >= 3 else "medium",
            "triggered" if llm_failures >= 3 or rate_limits else "clear",
            f"{llm_failures} LLM failures and {rate_limits} rate-limit signals",
            ["evidence/db/aggregate_metrics.json", "evidence/db/recent_llm_failures.json"],
            {"llm_failures": llm_failures, "rate_limits": rate_limits},
        ),
        result(
            "failed_daily_weekly_reports",
            "high",
            "triggered" if failed_reports else "clear",
            f"{failed_reports} failed market report generations",
            ["evidence/db/aggregate_metrics.json"],
            {"failed_reports": failed_reports},
        ),
        result(
            "stale_or_failed_market_heartbeats",
            "medium",
            "triggered" if heartbeat_failures else "clear",
            f"{heartbeat_failures} failed heartbeat generations",
            ["evidence/db/aggregate_metrics.json"],
            {"failed_heartbeats": heartbeat_failures},
        ),
        result(
            "duplicate_market_events",
            "medium",
            "unknown",
            "Duplicate market-event detection requires event-key distribution review",
            ["evidence/db/aggregate_metrics.json"],
            {"recent_events": len(market_events)},
        ),
        result(
            "duplicate_alert_deliveries",
            "high",
            "triggered" if invariant_by_type.get("duplicate_alert_deliveries", 0) else "clear",
            f"{invariant_by_type.get('duplicate_alert_deliveries', 0)} duplicate delivery groups",
            ["evidence/db/anomalies.json"],
            {"duplicate_deliveries": invariant_by_type.get("duplicate_alert_deliveries", 0)},
        ),
        result(
            "blocked_users_still_active",
            "high",
            "triggered" if blocked_users else "clear",
            f"{len(blocked_users)} blocked users still active",
            ["evidence/db/anomalies.json"],
            {"blocked_active_users": len(blocked_users)},
        ),
        result(
            "payment_premium_inconsistencies",
            "high",
            "triggered" if duplicate_payments else "clear",
            f"{len(duplicate_payments)} duplicate provider payment id groups",
            ["evidence/db/anomalies.json"],
            {"duplicate_provider_payment_ids": len(duplicate_payments)},
        ),
        result(
            "news_intelligence_failures",
            "medium",
            "triggered" if news_failures else "clear",
            f"{news_failures} failed or skipped high-impact news intelligence rows",
            ["evidence/db/recent_news_failures.json"],
            {"news_failures": news_failures},
        ),
        result(
            "stale_price_snapshots",
            "medium",
            "unknown" if not price_state else "clear",
            "Review latest price_state timestamps for staleness",
            ["evidence/db/aggregate_metrics.json"],
            {"price_state_rows": len(price_state)},
        ),
        result(
            "health_endpoint_unavailable",
            "critical",
            "triggered" if health.get("status") != "ok" else "clear",
            f"Health collector status: {health.get('status', 'unknown')}",
            ["evidence/health/health.json"],
            {"http_status": health.get("http_status")},
        ),
        result(
            "exception_patterns_in_logs",
            "medium",
            "triggered" if error_patterns else "clear",
            f"{error_patterns} error or exception log pattern matches",
            ["evidence/logs/pattern_counts.json"],
            {"error_patterns": error_patterns},
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
    for result in results:
        lines.append(f"- `{result.id}`: {result.status} ({result.severity}) - {result.summary}")
    lines.append("")
    return "\n".join(lines)
