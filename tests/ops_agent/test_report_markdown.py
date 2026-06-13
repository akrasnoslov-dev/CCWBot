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
            "severe_affected_event_alert_deliveries": 451,
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
        "evidence/db/event_alert_regression_checks.json": {
            "status": "critical",
            "placeholder_issue_counts": {"contains_n_a": 451},
            "old_label_issue_counts": {"old_since_last_btc_alert_label": 451},
            "same_family_repeat_noise_groups": 1,
            "same_family_allowed_escalation_groups": 1,
        },
        "evidence/db/anomalies.json": {
            "queries": {
                "event_ai_analysis_invariant_checks": {
                    "rows": [
                        {
                            "symbol": "BTC",
                            "market_event_id": 100,
                            "analysis_count": 2,
                        }
                    ]
                },
                "event_alert_delivery_explanation_gaps": {
                    "rows": [{"gap_count": 2, "affected_market_events": 2}]
                },
            }
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
    assert "| Current active users | 100 | Current active-user count from DB. |" in markdown
    assert "Active users during report period" not in markdown
    assert "451 / 451 unique affected Event Alert deliveries, 100.0%" in markdown
    assert "| contains_n_a | BTC | news | event_alert | 451 | 100.0% | 82 |" in markdown
    assert "## Event Alert Regression Checks" in markdown
    assert "Status: Critical" in markdown
    duplicate_row = (
        "| Duplicate attached successful event analyses | 1 | "
        "Critical invariant regression |"
    )
    repeat_row = (
        "| Same-family repeats without escalation | 1 | Likely alert noise; "
        "1 escalation groups were counted separately. |"
    )
    delivery_gap_row = (
        "| should_alert=true without delivery explanation | 2 | Observability gap |"
    )
    assert duplicate_row in markdown
    assert repeat_row in markdown
    assert delivery_gap_row in markdown
    assert "| Bad placeholder text | 451 | User-facing copy regression |" in markdown
    assert "| Old/confusing percentage labels | 451 | User-facing copy regression |" in markdown
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


def test_quality_summary_evidence_uses_unique_affected_deliveries_not_issue_occurrences():
    evidence = {
        "evidence/db/aggregate_metrics.json": {
            "queries": {
                "user_impact_summary": {
                    "rows": [
                        {
                            "active_users_current": 10,
                            "users_received_event_alerts": 10,
                            "users_received_heartbeats": 0,
                            "users_affected_by_delivery_failures": 0,
                            "users_affected_by_duplicate_alerts": 0,
                            "users_affected_by_content_quality_issues": 10,
                        }
                    ]
                }
            }
        },
        "evidence/db/alert_quality.json": {
            "total_event_alert_deliveries": 10,
            "severe_affected_event_alert_deliveries": 10,
            "quality_issue_occurrences": 30,
            "issues": [
                {
                    "issue": "contains_n_a",
                    "symbol": "BTC",
                    "trigger_source": "news",
                    "alert_type": "event_alert",
                    "delivery_count": 10,
                    "affected_users_estimate": 10,
                },
                {
                    "issue": "old_since_last_btc_alert_label",
                    "symbol": "BTC",
                    "trigger_source": "news",
                    "alert_type": "event_alert",
                    "delivery_count": 10,
                    "affected_users_estimate": 10,
                },
                {
                    "issue": "empty_related_context",
                    "symbol": "BTC",
                    "trigger_source": "news",
                    "alert_type": "event_alert",
                    "delivery_count": 10,
                    "affected_users_estimate": 10,
                },
            ],
        },
    }

    markdown = render_decision_report_context(
        period=_period(),
        evidence=evidence,
        detector_results=[],
        collection_status="complete",
        bundle_id="bundle",
    )

    assert "10 / 10 unique affected Event Alert deliveries, 100.0%" in markdown
    assert "20 / 10" not in markdown
    assert "200.0%" not in markdown
