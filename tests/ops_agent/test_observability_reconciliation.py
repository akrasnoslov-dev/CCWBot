"""Regression contracts for sanitized ops-agent evidence and report denominators."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from ops_agent.alert_similarity import build_alert_evidence_payloads
from ops_agent.collectors.db import ALERT_EVIDENCE_SQL
from ops_agent.db_queries import QUERIES
from ops_agent.report_context import _alert_quality_summary, _current_status
from ops_agent.schemas import Period


def _period():
    return Period(
        start=datetime(2026, 10, 8, tzinfo=timezone.utc),
        end=datetime(2026, 10, 9, tzinfo=timezone.utc),
        source="test",
    )


def _row(event_id, when, recipient_ids, *, sent=True, message="Market move."):
    return {
        "symbol": "BTC",
        "market_event_id": event_id,
        "event_ai_analysis_id": event_id + 100,
        "event_key": "btc_price_uptrend",
        "analysis_event_key": "btc_price_uptrend",
        "analysis_created_at": when,
        "first_delivery_at": when,
        "last_delivery_at": when,
        "should_alert": True,
        "alert_type": "event_alert",
        "status": "sent" if sent else "failed",
        "alert_message": message,
        "related_news_ids": '["n1"]',
        "delivery_count": len(recipient_ids),
        "sent_delivery_count": len(recipient_ids) if sent else 0,
        "failed_delivery_count": 0 if sent else len(recipient_ids),
        "distinct_recipient_count": len(recipient_ids),
        "delivery_members": [
            {
                "recipient_id": recipient,
                "alert_id": event_id * 1000 + recipient,
                "status": "sent" if sent else "failed",
                "sent_delivery_at": when if sent else None,
            }
            for recipient in recipient_ids
        ],
    }


def _payload(*rows):
    return build_alert_evidence_payloads(
        list(rows), period=_period(), row_cap=100, semantic_cooldown_seconds=14400
    )


def test_disjoint_recipients_do_not_trigger_global_family_cooldown():
    first = _row(10, "2026-10-08T10:00:00Z", list(range(1, 480)))
    second = _row(11, "2026-10-08T13:30:00Z", [480])
    payloads = _payload(first, second)
    suppression = payloads["evidence/db/backend_suppression_effectiveness.json"]
    group = suppression["suppression_groups"][0]
    assert group["delivered_inside_cooldown_candidates"] == 0
    assert group["unverified_sent_deliveries"] == 0
    assert payloads["evidence/db/event_alert_regression_checks.json"]["status"] == "ok"
    text = json.dumps(payloads["evidence/db/alert_similarity_groups.json"])
    assert '"recipient_id"' not in text
    assert "recipient_ref:h_" in text


def test_same_recipient_repeat_is_detected_but_exact_four_hours_is_allowed():
    payloads = _payload(
        _row(10, "2026-10-08T10:00:00Z", [21]),
        _row(11, "2026-10-08T13:30:00Z", [21]),
        _row(12, "2026-10-08T17:30:00Z", [21]),
    )
    group = payloads["evidence/db/backend_suppression_effectiveness.json"]["suppression_groups"][0]
    assert group["delivered_inside_cooldown_candidates"] == 1
    assert payloads["evidence/db/event_alert_regression_checks.json"]["status"] == "warning"


def test_failed_delivery_does_not_create_sent_cooldown_violation():
    payloads = _payload(
        _row(10, "2026-10-08T10:00:00Z", [21], sent=False),
        _row(11, "2026-10-08T11:00:00Z", [21]),
    )
    group = payloads["evidence/db/backend_suppression_effectiveness.json"]["suppression_groups"][0]
    assert group["delivered_inside_cooldown_candidates"] == 0
    assert group["unverified_sent_deliveries"] == 0


def test_missing_recipient_evidence_is_unknown_not_healthy():
    candidate = _row(10, "2026-10-08T10:00:00Z", [21])
    candidate["delivery_members"] = []
    payloads = _payload(candidate)
    group = payloads["evidence/db/backend_suppression_effectiveness.json"]["suppression_groups"][0]
    assert group["unverified_sent_deliveries"] == 1
    assert payloads["evidence/db/event_alert_regression_checks.json"]["status"] == "unknown"


def test_quality_counts_sent_sample_only_and_excludes_failed_placeholder():
    payloads = _payload(
        _row(10, "2026-10-08T10:00:00Z", [21, 22]),
        _row(11, "2026-10-08T11:00:00Z", [23], sent=False, message="value null"),
    )
    quality = payloads["evidence/db/alert_quality.json"]
    assert quality["total_event_alert_deliveries"] == 2
    assert quality["sampled_event_alert_attempts"] == 3
    assert quality["sampled_non_sent_event_alerts"] == 1
    assert quality["quality_issue_occurrences"] == 0
    context = _alert_quality_summary(
        {
            "evidence/db/alert_quality.json": quality,
            "evidence/db/aggregate_metrics.json": {
                "queries": {"delivery_funnel": {"rows": [{"telegram_delivered": 4}]}}
            },
        }
    )
    assert any("2 of 4" in line for line in context["lines"])


def test_docker_health_summary_uses_sanitized_collector_contract():
    evidence = {
        "evidence/health/health.json": {"status": "ok"},
        "evidence/docker/container_state.json": {
            "status": "ok",
            "service_count": 2,
            "running_count": 2,
            "unhealthy_count": 0,
            "services": [
                {
                    "service": "bot",
                    "running_state": "running",
                    "health": "healthy",
                    "is_running": True,
                },
                {
                    "service": "postgres",
                    "running_state": "running",
                    "health": "healthy",
                    "is_running": True,
                },
            ],
        },
    }
    assert "2 services, 0 non-healthy" in _current_status(evidence)[1]
    evidence["evidence/docker/container_state.json"]["services"][1]["health"] = "unhealthy"
    assert "2 services, 1 non-healthy" in _current_status(evidence)[1]


def test_sql_quality_and_membership_use_real_sent_status_and_timestamp():
    query = next(query for query in QUERIES if query.name == "alert_quality_summary")
    assert "AND a.status = 'sent'" in query.sql
    assert "sent_delivery_at" in ALERT_EVIDENCE_SQL
    assert "status = 'sent'" in ALERT_EVIDENCE_SQL


def test_mixed_delivery_status_rollup_is_not_labeled_as_one_status():
    assert "CASE WHEN count(DISTINCT a.status) > 1 THEN 'mixed'" in ALERT_EVIDENCE_SQL
    assert "FILTER (WHERE a.status = 'sent'))[1] AS alert_message" in ALERT_EVIDENCE_SQL
    impact = next(query for query in QUERIES if query.name == "user_impact_summary")
    assert "AND status = 'sent' AND alert_type = 'event_alert'" in impact.sql
    assert "AND pa.status = 'sent') AS users_received_event_alerts" in impact.sql
    assert "AND pa.status = 'sent') AS users_received_heartbeats" in impact.sql
    assert "AND pa.status = 'sent' AND (" in impact.sql


def test_one_alert_with_multiple_outcomes_counts_as_one_delivery():
    assert "count(DISTINCT a.id) AS delivery_count" in ALERT_EVIDENCE_SQL
    assert (
        "count(DISTINCT a.id) FILTER (WHERE a.status = 'sent') AS sent_delivery_count"
        in ALERT_EVIDENCE_SQL
    )
    assert "AND sent_alert.user_id = ado.user_id" in ALERT_EVIDENCE_SQL
    assert "AND sent_alert.created_at >= :since" in ALERT_EVIDENCE_SQL
