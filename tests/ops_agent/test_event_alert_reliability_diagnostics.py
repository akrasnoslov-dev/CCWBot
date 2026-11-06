"""Contract tests for sanitized CCW-50 alert degradation observability."""
from datetime import datetime, timezone

from ops_agent.db_queries import QUERIES, validate_read_only_queries
from ops_agent.detectors import run_detectors
from ops_agent.schemas import Period


AGGREGATE = "evidence/db/aggregate_metrics.json"


def _find(evidence, detector_id):
    period = Period(
        start=datetime(2026, 11, 5, tzinfo=timezone.utc),
        end=datetime(2026, 11, 6, tzinfo=timezone.utc),
        source="test",
    )
    detectors = run_detectors(evidence, period)
    return next(item for item in detectors if item.id == detector_id)


def _evidence(**queries):
    return {
        AGGREGATE: {
            "queries": {name: {"rows": rows} for name, rows in queries.items()}
        }
    }


def test_reliability_queries_are_sanitized_and_read_only():
    queries = {query.name: query for query in QUERIES}
    assert validate_read_only_queries() == []
    for name in (
        "event_alert_render_failure_streaks",
        "event_alert_positive_render_loss_summary",
        "event_alert_check_gap_summary",
    ):
        query = queries[name]
        assert query.evidence_file == AGGREGATE
        assert query.sql.startswith(("WITH ", "SELECT "))
        assert ":since" in query.sql and ":until" in query.sql
        for secret_column in ("raw_output_json", "raw_input_json", "telegram_id", "chat_id"):
            assert secret_column not in query.sql.lower()

    streak = queries["event_alert_render_failure_streaks"].sql
    assert "llm_operation_outcomes" in streak
    assert "call_type = 'event_alert_render'" in streak
    assert "trailing_failed_render_operations" in streak
    assert "interruptions_seen = 0" in streak
    assert "status = 'success'" in streak
    assert "ORDER BY created_at DESC, id DESC" in streak
    loss = queries["event_alert_positive_render_loss_summary"].sql
    assert "parsed_result_json" in loss
    assert "stage1_positive_render_failures" in loss
    gaps = queries["event_alert_check_gap_summary"].sql
    assert "lag(checked_at)" in gaps
    assert "gaps_over_32_minutes" in gaps
    assert "price_snapshots" in gaps


def test_three_consecutive_render_failures_trigger_symbol_warning():
    evidence = _evidence(
        event_alert_render_failure_streaks=[
            {"symbol": "sol", "observed_render_operations": 4,
             "failed_render_operations": 3,
             "trailing_failed_render_operations": 3},
            {"symbol": "btc", "observed_render_operations": 5,
             "failed_render_operations": 3,
             "trailing_failed_render_operations": 0},
        ]
    )
    detector = _find(evidence, "event_alert_render_consecutive_failures")
    assert detector.status == "triggered"
    assert detector.severity == "high"
    assert detector.metrics["affected_symbols"] == ["sol"]
    assert detector.metrics["threshold"] == 3


def test_recovered_render_streak_is_not_reported_as_active():
    evidence = _evidence(
        event_alert_render_failure_streaks=[
            {"symbol": "sol", "observed_render_operations": 7,
             "successful_render_operations": 1,
             "failed_render_operations": 6,
             "trailing_failed_render_operations": 0},
        ]
    )
    assert _find(evidence, "event_alert_render_consecutive_failures").status == "clear"


def test_no_render_observations_is_unknown_not_healthy():
    evidence = _evidence(event_alert_render_failure_streaks=[])
    assert _find(evidence, "event_alert_render_consecutive_failures").status == "unknown"


def test_stage1_positive_render_loss_is_separate_from_stage1_provider_errors():
    evidence = _evidence(
        event_alert_positive_render_loss_summary=[
            {"symbol": "sol", "total_event_analyses": 48,
             "stage1_positive_render_failures": 6},
            {"symbol": "btc", "total_event_analyses": 48,
             "stage1_positive_render_failures": 0},
        ]
    )
    detector = _find(evidence, "event_alert_positive_render_loss")
    assert detector.status == "triggered"
    assert detector.metrics["stage1_positive_render_failures"] == 6


def test_news_candidates_without_links_are_investigation_only():
    evidence = _evidence(
        event_analysis_news_candidates_summary=[
            {"symbol": "sol", "alerts_with_candidates_but_no_attached_news": 3}
        ]
    )
    detector = _find(evidence, "event_alert_news_context_missing_with_candidates")
    assert detector.status == "triggered"
    assert detector.metrics["interpretation"] == "investigation_signal_not_confirmed_attachment_defect"
    recovered = _evidence(
        event_analysis_news_candidates_summary=[
            {"symbol": "sol", "alerts_with_candidates_but_no_attached_news": 0}
        ]
    )
    assert _find(recovered, detector.id).status == "clear"


def test_price_snapshot_gaps_do_not_claim_scheduler_failure():
    evidence = _evidence(
        event_alert_check_gap_summary=[
            {"symbol": "sol", "observed_snapshots": 7,
             "gaps_over_32_minutes": 1},
        ]
    )
    detector = _find(evidence, "event_alert_market_snapshot_gaps")
    assert detector.status == "triggered"
    assert detector.metrics["scope"] == "price_snapshot_proxy_not_direct_scheduler_execution"
