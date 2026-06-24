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
                "alert_delivery_outcome_summary": {
                    "rows": [
                        {
                            "status": "allowed",
                            "reason_code": "llm_should_alert",
                            "decision_stage": "llm",
                            "decision_reason": "llm_should_alert",
                            "outcomes": 5,
                            "news_only_rejected_count": 0,
                            "llm_should_alert_count": 5,
                            "llm_no_alert_count": 0,
                            "semantic_cooldown_suppressed_count": 0,
                            "similar_context_reused_count": 0,
                            "allowed_market_context_changed_count": 0,
                            "pre_llm_similar_context_reused_count": 0,
                            "delivered_with_decision_reason_count": 0,
                            "decision_reason_unknown_count": 0,
                        },
                        {
                            "status": "not_scheduled",
                            "reason_code": "news_only_rejected",
                            "decision_stage": "llm",
                            "decision_reason": "news_only_rejected",
                            "outcomes": 3,
                            "news_only_rejected_count": 3,
                            "llm_should_alert_count": 0,
                            "llm_no_alert_count": 0,
                            "semantic_cooldown_suppressed_count": 0,
                            "similar_context_reused_count": 0,
                            "allowed_market_context_changed_count": 0,
                            "pre_llm_similar_context_reused_count": 0,
                            "delivered_with_decision_reason_count": 0,
                            "decision_reason_unknown_count": 0,
                        },
                        {
                            "status": "delivered",
                            "reason_code": "delivered",
                            "decision_stage": "delivery",
                            "decision_reason": "delivered",
                            "outcomes": 8,
                            "news_only_rejected_count": 0,
                            "llm_should_alert_count": 0,
                            "llm_no_alert_count": 0,
                            "semantic_cooldown_suppressed_count": 0,
                            "similar_context_reused_count": 0,
                            "allowed_market_context_changed_count": 0,
                            "pre_llm_similar_context_reused_count": 0,
                            "delivered_with_decision_reason_count": 8,
                            "decision_reason_unknown_count": 0,
                        },
                        {
                            "status": "not_scheduled",
                            "reason_code": "similar_context_reused",
                            "decision_stage": "pre_llm",
                            "decision_reason": "similar_context_reused",
                            "outcomes": 4,
                            "news_only_rejected_count": 0,
                            "llm_should_alert_count": 0,
                            "llm_no_alert_count": 0,
                            "semantic_cooldown_suppressed_count": 0,
                            "similar_context_reused_count": 4,
                            "allowed_market_context_changed_count": 0,
                            "pre_llm_similar_context_reused_count": 4,
                            "delivered_with_decision_reason_count": 0,
                            "decision_reason_unknown_count": 0,
                        },
                    ]
                },
                "event_alert_similar_context_reuse": {
                    "rows": [
                        {
                            "symbol": "BTC",
                            "semantic_family": "price_level_range",
                            "similar_context_reused_count": 4,
                            "pre_llm_reused_count": 4,
                            "eventless_reused_count": 4,
                            "llm_skipped_count": 4,
                            "context_fingerprint_count": 1,
                        }
                    ]
                },
                "event_alert_possible_action_quality": {
                    "rows": [
                        {
                            "event_alert_actions": 10,
                            "generic_possible_action_count": 2,
                        }
                    ]
                },
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
            "old_label_issue_counts": {
                "old_since_last_btc_alert_label": 451,
                "old_generic_price_change_label": 3,
            },
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
    assert "## Decision Reasons" in markdown
    assert "| `news_only_rejected` | 3 |" in markdown
    assert "| `llm_should_alert` | 5 |" in markdown
    assert "| `similar_context_reused` | 4 |" in markdown
    assert "| Pre-LLM similar-context skips | 4 |" in markdown
    assert "| `allowed_market_context_changed` | 0 |" in markdown
    assert "Top similar-context reuse groups: BTC/price_level_range: 4." in markdown
    assert "| Delivered rows with decision reason | 8 |" in markdown
    assert "| Generic possible action quality signals | 2 / 10 |" in markdown
    assert "Status: Critical" in markdown
    duplicate_row = (
        "| Affected market events with duplicate attached analyses | 1 | "
        "Critical invariant regression; 1 extra successful analyses |"
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
    assert "| Old/confusing percentage labels | 454 | User-facing copy regression |" in markdown
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
    assert "`sample_unknown`: Unknown - Required evidence missing: sample" in markdown


def test_decision_report_context_distinguishes_collector_failure_from_unknown():
    markdown = render_decision_report_context(
        period=_period(),
        evidence={"evidence/health/health.json": {"status": "ok"}},
        detector_results=[
            DetectorResult(
                "event_alert_delivery_explanation_gaps",
                "high",
                "unknown",
                "Required evidence is missing",
                evidence_gap=(
                    "Required evidence missing: "
                    "evidence/db/anomalies.json:event_alert_delivery_explanation_gaps"
                ),
            ),
            DetectorResult(
                "health_endpoint_unavailable",
                "critical",
                "clear",
                "Health collector status: ok",
            ),
        ],
        collection_status="partial",
        collector_status=[
            {
                "name": "db.event_alert_delivery_explanation_gaps",
                "status": "failed",
                "error": "ProgrammingError: sql_syntax_or_schema_error",
            },
            {"name": "health", "status": "ok", "error": None},
        ],
        bundle_id="bundle",
    )

    assert "## Collector Status" in markdown
    assert (
        "| `db.event_alert_delivery_explanation_gaps` | Collector failed | "
        "ProgrammingError: sql_syntax_or_schema_error |"
    ) in markdown
    assert "| `health` | OK | none | None. |" in markdown
    assert (
        "`event_alert_delivery_explanation_gaps`: Collector failed - Required evidence missing"
    ) in markdown
    assert "Failed collectors mean evidence is missing because collection failed" in markdown


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
