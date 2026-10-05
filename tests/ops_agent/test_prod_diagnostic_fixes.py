from datetime import datetime, timezone

from ops_agent.alert_similarity import build_alert_evidence_payloads
from ops_agent.collectors.db import ALERT_EVIDENCE_SQL
from ops_agent.detectors import run_detectors
from ops_agent.schemas import Period


def _period():
    return Period(
        start=datetime(2026, 10, 3, tzinfo=timezone.utc),
        end=datetime(2026, 10, 4, tzinfo=timezone.utc),
        source="test",
    )


def test_similarity_detector_ignores_analysis_only_no_alert_group():
    evidence = {
        "evidence/db/alert_similarity_groups.json": {
            "groups": [{
                "symbols": ["GRAM"],
                "market_events": 0,
                "sent_deliveries": 0,
                "should_alert_true": 0,
                "analyses": 191,
            }]
        }
    }
    results = {item.id: item for item in run_detectors(evidence, _period())}
    assert results["similar_alert_groups"].status == "clear"
    assert results["llm_repeated_alert_true_for_similar_situations"].status == "clear"


def test_alert_evidence_projects_no_alert_market_context():
    assert "analysed_window_change_percent" in ALERT_EVIDENCE_SQL
    assert "relative_window_percentile_30d" in ALERT_EVIDENCE_SQL
    assert "relative_24h_percentile_30d" in ALERT_EVIDENCE_SQL

    payloads = build_alert_evidence_payloads(
        [{
            "symbol": "GRAM",
            "analysis_symbol": "gram",
            "analysis_status": "no_alert",
            "should_alert": False,
            "analysis_reason_for_no_alert": "routine_move",
            "analysis_created_at": datetime(2026, 10, 4, tzinfo=timezone.utc),
            "analysed_window_change_percent": 1.11,
            "last_24h_change": 3.2,
            "relative_window_percentile_30d": 97.0,
            "relative_24h_percentile_30d": 99.0,
        }],
        period=_period(),
        row_cap=100,
        semantic_cooldown_seconds=14400,
    )
    row = payloads["evidence/db/event_analysis_decision_timeline.json"]["rows"][0]
    assert row["analysed_window_change_percent"] == 1.11
    assert row["last_24h_change"] == 3.2
    assert row["relative_window_percentile_30d"] == 97.0
    assert row["relative_24h_percentile_30d"] == 99.0
