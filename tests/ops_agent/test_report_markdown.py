from __future__ import annotations

from datetime import datetime, timezone

from ops_agent.report_markdown import render_decision_report_context
from ops_agent.schemas import DetectorResult, Period


def _period() -> Period:
    return Period(
        start=datetime(2026, 6, 6, tzinfo=timezone.utc),
        end=datetime(2026, 6, 8, 7, 58, 5, tzinfo=timezone.utc),
        source="explicit",
    )


def test_decision_report_context_renders_required_decision_sections():
    evidence = {
        "evidence/db/aggregate_metrics.json": {
            "queries": {
                "user_impact_summary": {
                    "rows": [
                        {
                            "active_users_current": 100,
                            "users_received_event_alerts": 82,
                            "users_received_heartbeats": 90,
                            "users_affected_by_delivery_failures": 2,
                            "users_affected_by_duplicate_alerts": 3,
                            "users_affected_by_content_quality_issues": 82,
                        }
                    ]
                },
                "delivery_funnel": {
                    "rows": [
                        {
                            "market_events": 10,
                            "ai_analyses": 10,
                            "should_alert_true": 5,
                            "alert_records_created": 451,
                            "telegram_delivery_attempts": 500,
                            "telegram_delivered": 498,
                            "telegram_failed": 2,
                        }
                    ]
                },
                "market_events_summary": {"rows": [{"events": 10}]},
                "event_ai_analysis_summary": {"rows": [{"analyses": 10}]},
                "alerts_summary": {"rows": [{"deliveries": 500}]},
            }
        },
        "evidence/db/recent_alert_failures.json": {"queries": {"alerts_failures": {"rows": []}}},
        "evidence/logs/pattern_counts.json": {
            "period_matched_suppression_reason_counts": {"semantic_cooldown": 7}
        },
        "evidence/health/health.json": {"status": "ok"},
        "evidence/db/alert_quality.json": {
            "total_event_alert_deliveries": 451,
            "issues": [
                {
                    "issue": "contains_n_a",
                    "symbol": "BTC",
                    "trigger_source": "news",
                    "alert_type": "event_alert",
                    "delivery_count": 451,
                    "affected_users_estimate": 82,
                }
            ],
        },
        "evidence/db/alert_similarity_groups.json": {"groups": []},
    }
    markdown = render_decision_report_context(
        period=_period(),
        evidence=evidence,
        detector_results=[],
        collection_status="complete",
        bundle_id="bundle",
        generated_at=datetime(2026, 6, 8, 8, 0, tzinfo=timezone.utc),
    )

    assert "## Executive Summary" in markdown
    assert "Status: degraded" in markdown
    assert "Affected users: 82" in markdown
    assert "| contains_n_a | BTC | news | event_alert | 451 | 100.0% | 82 |" in markdown
    assert "| Telegram failed | 2 | 0.4% |" in markdown
    assert "| semantic_cooldown | 7 | 100.0% |" in markdown
    assert "## Confirmed Findings" in markdown
    assert "## Data Completeness and Limitations" in markdown
    assert "PR Mapping" in markdown


def test_decision_report_context_handles_missing_denominators():
    evidence = {
        "evidence/db/aggregate_metrics.json": {
            "queries": {
                "delivery_funnel": {
                    "rows": [
                        {
                            "market_events": 0,
                            "ai_analyses": 0,
                            "should_alert_true": 0,
                            "alert_records_created": 0,
                            "telegram_delivery_attempts": 0,
                            "telegram_delivered": 0,
                            "telegram_failed": 0,
                        }
                    ]
                }
            }
        },
        "evidence/db/alert_quality.json": {
            "total_event_alert_deliveries": 0,
            "issues": [
                {
                    "issue": "contains_unknown",
                    "symbol": "BTC",
                    "trigger_source": "unknown",
                    "alert_type": "event_alert",
                    "delivery_count": 0,
                    "affected_users_estimate": 0,
                }
            ],
        },
    }

    markdown = render_decision_report_context(
        period=_period(),
        evidence=evidence,
        detector_results=[
            DetectorResult(
                "sample_unknown",
                "medium",
                "unknown",
                "missing evidence",
                evidence_gap="Required evidence missing: sample",
            )
        ],
        collection_status="complete",
        bundle_id="bundle",
    )

    assert "| contains_unknown | BTC | unknown | event_alert | 0 | not available | 0 |" in markdown
    assert "| AI analyses | 0 | not available |" in markdown
    assert "`sample_unknown`: Required evidence missing: sample" in markdown
