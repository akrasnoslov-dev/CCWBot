from __future__ import annotations

from datetime import datetime, timezone

from ops_agent.report_context import render_report_context
from ops_agent.schemas import DetectorResult, Period


def _period() -> Period:
    return Period(
        start=datetime(2026, 10, 1, tzinfo=timezone.utc),
        end=datetime(2026, 10, 6, tzinfo=timezone.utc),
        source="explicit",
    )


def test_report_context_is_compact_and_lazy_for_healthy_bundle():
    evidence = {
        "evidence/db/aggregate_metrics.json": {
            "queries": {
                "user_impact_summary": {
                    "rows": [
                        {
                            "active_users_current": 100,
                            "users_received_event_alerts": 80,
                            "users_affected_by_delivery_failures": 0,
                            "users_affected_by_duplicate_alerts": 0,
                            "users_affected_by_content_quality_issues": 0,
                        }
                    ]
                },
                "delivery_funnel": {
                    "rows": [
                        {
                            "market_events": 20,
                            "ai_analyses": 20,
                            "should_alert_true": 5,
                            "telegram_delivery_attempts": 100,
                            "telegram_delivered": 100,
                            "telegram_failed": 0,
                        }
                    ]
                },
            }
        },
        "evidence/db/alert_quality.json": {
            "total_event_alert_deliveries": 100,
            "issues": [],
        },
        "evidence/db/event_alert_regression_checks.json": {"status": "ok"},
        "evidence/health/health.json": {"status": "ok"},
        "evidence/docker/container_state.json": {"status": "ok", "services": []},
    }
    markdown = render_report_context(
        period=_period(),
        evidence=evidence,
        detector_results=[
            DetectorResult(
                id="healthy_detector",
                severity="info",
                status="ok",
                summary="Healthy.",
            )
        ],
        collection_status="complete",
        collector_status=[{"name": "db.aggregate", "status": "ok", "error": None}],
        bundle_id="bundle",
        generated_at=datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc),
    )

    assert "Report status: `healthy`" in markdown
    assert "Do not preload other bundle files." in markdown
    assert "No triggered or unknown detector findings." in markdown
    assert "No extra evidence read is required" in markdown
    assert "healthy_detector" not in markdown
    assert "## Severity Model" not in markdown
    assert len(markdown) < 5000


def test_report_context_exposes_only_attention_findings_and_targeted_evidence():
    evidence = {
        "evidence/db/aggregate_metrics.json": {"queries": {}},
        "evidence/db/alert_quality.json": {
            "total_event_alert_deliveries": 10,
            "issues": [
                {
                    "issue": "contains_n_a",
                    "delivery_count": 2,
                }
            ],
        },
        "evidence/db/event_alert_regression_checks.json": {
            "status": "critical",
            "delivery_gap_count": 1,
        },
        "evidence/health/health.json": {"status": "ok"},
        "evidence/docker/container_state.json": {"status": "ok"},
    }
    markdown = render_report_context(
        period=_period(),
        evidence=evidence,
        detector_results=[
            DetectorResult(
                id="delivery_gap",
                severity="high",
                status="triggered",
                summary="Delivery gap found.",
                evidence_refs=["evidence/db/anomalies.json"],
            ),
            DetectorResult(
                id="insufficient_logs",
                severity="medium",
                status="unknown",
                summary="Cannot establish log state.",
                evidence_refs=["evidence/logs/pattern_counts.json"],
                evidence_gap="period logs unavailable",
            ),
            DetectorResult(
                id="normal_detector",
                severity="info",
                status="ok",
                summary="Normal.",
            ),
        ],
        collection_status="partial",
        collector_status=[
            {"name": "db.aggregate", "status": "ok", "error": None},
            {"name": "logs.structured_evidence", "status": "partial", "error": "truncated"},
        ],
        bundle_id="bundle",
    )

    assert "Report status: `degraded`" in markdown
    assert "`logs.structured_evidence`: `partial` (truncated)" in markdown
    assert "delivery_gap" in markdown
    assert "insufficient_logs" in markdown
    assert "normal_detector" not in markdown
    assert "`evidence/db/anomalies.json`" in markdown
    assert "`evidence/logs/pattern_counts.json`" in markdown
    assert "`evidence/db/alert_quality.json`" in markdown
    assert "`evidence/db/event_alert_regression_checks.json`" in markdown
