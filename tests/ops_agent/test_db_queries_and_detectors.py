from __future__ import annotations

from datetime import datetime, timezone

from ops_agent.db_queries import QUERIES, validate_read_only_queries
from ops_agent.detectors import run_detectors
from ops_agent.schemas import Period


def test_all_db_queries_are_read_only_and_parameterized():
    assert validate_read_only_queries() == []
    assert all(query.sql.strip().lower().startswith(("select", "with")) for query in QUERIES)
    assert any(":since" in query.sql for query in QUERIES)


def test_price_state_query_uses_existing_price_state_columns_only():
    price_state_query = next(query for query in QUERIES if query.name == "price_state_current")

    assert "last_7d_change" not in price_state_query.sql


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
