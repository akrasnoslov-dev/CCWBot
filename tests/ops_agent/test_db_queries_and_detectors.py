from __future__ import annotations

from datetime import datetime, timezone

from ops_agent.db_queries import QUERIES, validate_read_only_queries
from ops_agent.detectors import run_detectors
from ops_agent.schemas import Period


def test_all_db_queries_are_read_only_and_parameterized():
    assert validate_read_only_queries() == []
    assert all(query.sql.strip().lower().startswith(("select", "with")) for query in QUERIES)
    assert any(":since" in query.sql for query in QUERIES)


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

