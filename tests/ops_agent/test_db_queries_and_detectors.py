from __future__ import annotations

from datetime import datetime, timezone

from ops_agent.collectors.db import ALERT_EVIDENCE_SQL
from ops_agent.db_queries import QUERIES, validate_read_only_queries
from ops_agent.detectors import run_detectors
from ops_agent.schemas import Period


def test_all_db_queries_are_read_only_and_parameterized():
    assert validate_read_only_queries() == []
    assert all(query.sql.strip().lower().startswith(("select", "with")) for query in QUERIES)
    assert any(":since" in query.sql for query in QUERIES)
    assert ALERT_EVIDENCE_SQL.strip().lower().startswith(("select", "with"))
    assert ";" not in ALERT_EVIDENCE_SQL
    assert ":since" in ALERT_EVIDENCE_SQL


def test_price_state_query_uses_existing_price_state_columns_only():
    price_state_query = next(query for query in QUERIES if query.name == "price_state_current")

    assert "last_7d_change" not in price_state_query.sql


def test_ops_agent_queries_include_hardened_anomaly_evidence():
    query_names = {query.name for query in QUERIES}

    assert "premium_payment_inconsistencies" in query_names
    assert "market_reports_freshness" in query_names
    assert "market_heartbeats_freshness" in query_names
    assert "event_ai_analysis_invariant_checks" in query_names
    assert "event_alert_llm_estimates" in query_names
    assert "user_impact_summary" in query_names
    assert "delivery_funnel" in query_names
    assert "alert_quality_summary" in query_names
    assert "event_alert_delivery_explanation_gaps" in query_names


def test_ops_agent_event_alert_estimate_query_exposes_cadence_fields():
    query = next(query for query in QUERIES if query.name == "event_alert_llm_estimates")

    assert "event_analysis_interval_seconds" in query.sql
    assert "payload_points" in query.sql
    assert "analysed_window_minutes" in query.sql
    assert "estimated_event_alert_llm_calls_per_hour" in query.sql
    assert "estimated_event_alert_llm_calls_per_day" in query.sql


def test_delivery_funnel_downstream_counts_are_event_alert_only():
    query = next(query for query in QUERIES if query.name == "delivery_funnel")

    assert query.sql.count("alert_type = 'event_alert'") >= 4
    assert "AS alert_records_created" in query.sql
    assert "AS telegram_delivery_attempts" in query.sql
    assert "AS telegram_delivered" in query.sql
    assert "AS telegram_failed" in query.sql


def test_event_ai_invariant_query_scopes_to_attached_successful_event_analyses():
    query = next(query for query in QUERIES if query.name == "event_ai_analysis_invariant_checks")

    assert "market_event_id IS NOT NULL" in query.sql
    assert "coalesce(analysis_type, 'event_analysis') = 'event_analysis'" in query.sql
    assert "status IN ('success', 'completed')" in query.sql


def test_event_alert_delivery_explanation_gap_query_accepts_expected_outcomes():
    query = next(
        query for query in QUERIES if query.name == "event_alert_delivery_explanation_gaps"
    )

    assert "should_alert = true" in query.sql
    assert "AND market_event_id IS NOT NULL" in query.sql
    assert "status = 'sent'" in query.sql
    for expected_status in (
        "delivered",
        "suppressed",
        "cooldown",
        "failed",
        "rate_limited",
        "no_eligible_recipients",
        "filtered",
        "not_scheduled",
    ):
        assert expected_status in query.sql


def test_alert_quality_summary_uses_token_boundary_placeholder_regexes():
    query = next(query for query in QUERIES if query.name == "alert_quality_summary")

    assert "~* '(^|[^a-z0-9])unknown([^a-z0-9]|$)'" in query.sql
    assert "~* '(^|[^a-z0-9])unavailable([^a-z0-9]|$)'" in query.sql
    assert "~* '(^|[^a-z0-9])null([^a-z0-9]|$)'" in query.sql


def test_alert_repetition_detectors_unknown_when_evidence_missing():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )

    results = {
        result.id: result
        for result in run_detectors(
            {
                "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
                "evidence/health/health.json": {"status": "ok"},
            },
            period,
        )
    }

    assert results["noisy_alert_symbols"].status == "unknown"
    assert results["repeated_alert_content"].status == "unknown"
    assert results["similar_alert_groups"].status == "unknown"
    assert results["weak_event_identity"].status == "unknown"
    assert results["cooldown_effectiveness_gap"].status == "unknown"
    assert results["llm_repeated_alert_true_for_similar_situations"].status == "unknown"


def test_alert_repetition_detectors_trigger_with_evidence():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/alert_delivery_distribution.json": {
            "symbols": [{"symbol": "BTC", "sent_deliveries": 8}]
        },
        "evidence/db/alert_content_fingerprints.json": {
            "repeated_groups": [{"symbol": "BTC", "sent_deliveries": 8, "market_events": 2}]
        },
        "evidence/db/alert_similarity_groups.json": {
            "groups": [
                {
                    "symbols": ["BTC"],
                    "market_events": 2,
                    "sent_deliveries": 8,
                    "should_alert_true": 2,
                }
            ]
        },
        "evidence/db/event_identity_quality.json": {
            "rows": [
                {
                    "symbol": "BTC",
                    "market_events": 6,
                    "event_key_churn_ratio": 1.0,
                    "same_content_split_key_groups": 1,
                }
            ],
            "same_content_split_key_groups": [{"symbol": "BTC", "event_key_count": 2}],
        },
        "evidence/db/backend_suppression_effectiveness.json": {
            "suppression_groups": [
                {
                    "symbol": "BTC",
                    "event_key": "btc_price_volatility",
                    "delivered_inside_cooldown_candidates": 1,
                }
            ]
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    assert results["noisy_alert_symbols"].status == "triggered"
    assert results["repeated_alert_content"].status == "triggered"
    assert results["similar_alert_groups"].status == "triggered"
    assert results["weak_event_identity"].status == "triggered"
    assert results["cooldown_effectiveness_gap"].status == "triggered"
    assert results["llm_repeated_alert_true_for_similar_situations"].status == "triggered"


def test_failed_delivery_detector_triggers():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/aggregate_metrics.json": {
            "queries": {
                "alerts_summary": {
                    "rows": [{"deliveries": 10, "failed": 5}],
                }
            }
        },
        "evidence/db/recent_alert_failures.json": {
            "queries": {"alerts_failures": {"rows": [{"alert_id": 1}]}}
        },
        "evidence/health/health.json": {"status": "ok"},
        "evidence/logs/pattern_counts.json": {"pattern_counts": {}},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    assert results["failed_telegram_deliveries"].status == "triggered"
    assert results["failed_telegram_deliveries"].severity == "high"


def test_health_detector_triggers_when_unavailable():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )

    results = {
        result.id: result
        for result in run_detectors(
            {
                "evidence/health/health.json": {"status": "failed"},
                "evidence/logs/pattern_counts.json": {"pattern_counts": {}},
            },
            period,
        )
    }

    assert results["health_endpoint_unavailable"].status == "triggered"


def test_duplicate_market_event_detector_clear_when_evidence_exists():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/anomalies.json": {
            "queries": {
                "duplicate_market_event_buckets": {
                    "rows": [],
                    "parameters": {"bucket_minutes": 15},
                }
            }
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    assert results["duplicate_market_events"].status == "clear"
    assert results["duplicate_market_events"].metrics["duplicate_like_group_count"] == 0


def test_duplicate_market_event_detector_triggers_with_bucket_groups():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/anomalies.json": {
            "queries": {
                "duplicate_market_event_buckets": {
                    "parameters": {"bucket_minutes": 30},
                    "rows": [
                        {
                            "symbol": "BTC",
                            "event_type": "price_movement",
                            "event_key": "btc_move",
                            "group_size": 3,
                            "sample_market_event_ids": [10, 11, 12],
                        }
                    ],
                }
            }
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    duplicate = results["duplicate_market_events"]
    assert duplicate.status == "triggered"
    assert duplicate.metrics["bucket_minutes"] == 30
    assert duplicate.metrics["max_group_size"] == 3
    assert duplicate.metrics["affected_symbols"] == ["BTC"]


def test_duplicate_market_event_detector_unknown_when_db_evidence_missing():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )

    results = {
        result.id: result
        for result in run_detectors(
            {
                "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
                "evidence/health/health.json": {"status": "ok"},
            },
            period,
        )
    }

    assert results["duplicate_market_events"].status == "unknown"
    assert "duplicate_market_event_buckets" in results["duplicate_market_events"].evidence_gap


def test_missing_required_db_evidence_returns_unknown_not_clear():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )

    results = {
        result.id: result
        for result in run_detectors(
            {
                "evidence/health/health.json": {"status": "ok"},
                "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
            },
            period,
        )
    }

    assert results["failed_telegram_deliveries"].status == "unknown"
    assert results["failed_telegram_deliveries"].evidence_gap is not None


def test_no_delivery_classification_clear_for_expected_no_alert():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/anomalies.json": {
            "queries": {
                "market_events_without_delivery_classification": {
                    "rows": [
                        {
                            "classification": "expected_should_alert_false",
                            "events": 4,
                            "sample_events": [{"market_event_id": 20}],
                        }
                    ]
                }
            }
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    detector = results["market_events_without_alert_deliveries"]
    assert detector.status == "clear"
    assert detector.metrics["expected_no_delivery"] == 4


def test_no_delivery_classification_triggers_for_true_alert_gap():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/anomalies.json": {
            "queries": {
                "market_events_without_delivery_classification": {
                    "rows": [
                        {
                            "classification": "delivery_gap_should_alert_true",
                            "events": 2,
                            "sample_events": [{"market_event_id": 30}],
                        }
                    ]
                }
            }
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    detector = results["market_events_without_alert_deliveries"]
    assert detector.status == "triggered"
    assert detector.metrics["delivery_gap_should_alert_true"] == 2


def test_event_alert_delivery_explanation_gap_detector_triggers():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/anomalies.json": {
            "queries": {
                "event_alert_delivery_explanation_gaps": {
                    "rows": [
                        {
                            "anomaly": "should_alert_true_without_delivery_explanation",
                            "gap_count": 3,
                            "affected_market_events": 2,
                        }
                    ]
                }
            }
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    detector = results["event_alert_delivery_explanation_gaps"]
    assert detector.status == "triggered"
    assert detector.metrics["should_alert_true_without_delivery_explanation"] == 3


def test_no_delivery_classification_unknown_when_reason_missing():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/anomalies.json": {
            "queries": {
                "market_events_without_delivery_classification": {
                    "rows": [{"classification": "unknown_no_analysis", "events": 1}]
                }
            }
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    assert results["market_events_without_alert_deliveries"].status == "unknown"


def test_no_delivery_classification_clear_for_backend_cooldown():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/anomalies.json": {
            "queries": {
                "market_events_without_delivery_classification": {
                    "rows": [
                        {
                            "classification": "expected_backend_cooldown_active",
                            "events": 2,
                            "sample_events": [{"market_event_id": 40}],
                        }
                    ]
                }
            }
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    detector = results["market_events_without_alert_deliveries"]
    assert detector.status == "clear"
    assert detector.metrics["expected_backend_cooldown_active"] == 2


def test_no_alert_deliveries_clear_when_active_period_has_no_market_events():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/aggregate_metrics.json": {
            "queries": {
                "alerts_summary": {"rows": []},
                "price_state_current": {"rows": [{"symbol": "BTC"}]},
                "market_events_summary": {"rows": []},
            }
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    assert results["no_alert_deliveries_observed"].status == "clear"


def test_payment_premium_detector_aggregates_inconsistency_types():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/anomalies.json": {
            "queries": {
                "premium_payment_inconsistencies": {
                    "rows": [
                        {"anomaly": "paid_without_premium"},
                        {"anomaly": "expired_active_subscription"},
                        {"anomaly": "active_premium_without_trail"},
                    ]
                }
            }
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    detector = results["payment_premium_inconsistencies"]
    assert detector.status == "triggered"
    assert detector.severity == "high"
    assert detector.metrics["anomalies_by_type"]["paid_without_premium"] == 1
    assert detector.metrics["anomalies_by_type"]["expired_active_subscription"] == 1


def test_market_event_analysis_invariant_surfaces_multiple_analysis_ids():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/anomalies.json": {
            "queries": {
                "delivery_invariant_checks": {
                    "rows": [{"anomaly": "multiple_analysis_ids_for_event", "count": 2}]
                },
                "event_ai_analysis_invariant_checks": {"rows": []},
            }
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    detector = results["market_event_analysis_invariant"]
    assert detector.status == "triggered"
    assert detector.severity == "critical"
    assert detector.metrics["multiple_analysis_ids_for_event"] == 2


def test_report_freshness_detector_triggers_for_stale_or_missing_reports():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/aggregate_metrics.json": {
            "queries": {
                "market_reports_summary": {"rows": []},
                "market_reports_freshness": {
                    "rows": [
                        {
                            "report_type": "daily",
                            "latest_status": "completed",
                            "latest_generated_at": "2026-06-01T00:00:00Z",
                            "latest_expires_at": "2026-06-01T04:00:00Z",
                            "age_seconds": 86400,
                            "max_age_seconds": 14400,
                        },
                        {"report_type": "weekly", "latest_generated_at": None},
                    ]
                },
            }
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    detector = results["failed_daily_weekly_reports"]
    assert detector.status == "triggered"
    assert detector.metrics["stale_or_missing_reports"] == 2
    assert detector.metrics["affected_report_types"] == ["daily", "weekly"]


def test_heartbeat_freshness_detector_triggers_for_stale_or_missing_cache():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/aggregate_metrics.json": {
            "queries": {
                "market_heartbeats_summary": {"rows": []},
                "market_heartbeats_freshness": {
                    "rows": [
                        {
                            "symbol": "BTC",
                            "latest_status": "completed",
                            "latest_generated_at": "2026-06-01T00:00:00Z",
                            "age_seconds": 86400,
                        },
                        {"symbol": "ETH", "latest_generated_at": None},
                    ]
                },
            }
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    detector = results["stale_or_failed_market_heartbeats"]
    assert detector.status == "triggered"
    assert detector.metrics["stale_or_missing_heartbeats"] == 2
    assert detector.metrics["affected_symbols"] == ["BTC", "ETH"]
