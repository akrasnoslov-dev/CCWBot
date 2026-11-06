"""CCW-50: per-stage operational streaks never become market alert gates."""
import logging

import pytest

from bot.alerting.alert_failure_streaks import (
    STREAK_WARNING_THRESHOLD,
    AlertFailureStreaks,
)


def test_stage_and_coin_failure_streaks_are_independent():
    counters = AlertFailureStreaks()
    assert STREAK_WARNING_THRESHOLD == 3
    assert counters.failure("stage1", "SOL") == 1
    assert counters.failure("render", "SOL") == 1
    assert counters.failure("render", "sol") == 2
    assert counters.failure("render", "BTC") == 1
    assert counters.get("stage1", "SOL") == 1
    assert counters.get("render", "SOL") == 2
    assert counters.get("render", "BTC") == 1
    assert counters.success("render", "SOL") == 2
    assert counters.failure("render", "SOL") == 1
    assert counters.get("stage1", "SOL") == 1
    assert counters.success("stage1", "sol") == 1
    assert counters.get("stage1", "SOL") == 0


def test_unknown_stage_rejected_and_reset_is_safe():
    counters = AlertFailureStreaks()
    with pytest.raises(ValueError):
        counters.failure("unknown", "SOL")
    assert counters.success("render", "SOL") == 0
    assert counters.failure("render", "SOL") == 1
    counters.clear()
    assert counters.get("render", "SOL") == 0


@pytest.mark.asyncio
async def test_terminal_render_outcomes_log_one_streak_per_operation(
    monkeypatch, caplog
):
    from bot import alerts

    counters = AlertFailureStreaks()
    monkeypatch.setattr(alerts, "alert_failure_streaks", counters)
    monkeypatch.setattr(alerts, "DB_ENABLED", False)
    caplog.set_level(logging.INFO)
    for index in range(3):
        await alerts._save_event_alert_render_outcome(
            llm_operation_id=f"mock-operation-{index}",
            symbol="SOL",
            status="schema_error",
            error_reason="schema_validation_failed",
        )
    assert counters.get("render", "SOL") == 3
    warning = [
        record for record in caplog.records
        if "ops_event=event_alert_render_failure_streak" in record.message
    ]
    assert len(warning) == 3
    assert warning[0].levelno == logging.WARNING
    assert warning[-1].levelno == logging.ERROR
    await alerts._save_event_alert_render_outcome(
        llm_operation_id="mock-operation-recovered",
        symbol="SOL",
        status="success",
    )
    assert counters.get("render", "SOL") == 0
    assert any(
        "ops_event=event_alert_render_recovered" in rec.message
        for rec in caplog.records
    )


def test_render_failure_does_not_increment_stage1_failure_count(monkeypatch):
    from bot import alerts

    counters = AlertFailureStreaks()
    monkeypatch.setattr(alerts, "alert_failure_streaks", counters)

    class FakeHealth:
        def record_failure(self, *, reason):
            return 1

        def failure_escalation_threshold(self):
            return 5

    monkeypatch.setattr(alerts, "event_analysis_health", FakeHealth())
    alerts._log_event_analysis_failure("SOL", "schema_validation_failed", stage="render")
    assert counters.get("stage1", "SOL") == 0
    alerts._log_event_analysis_failure("SOL", "schema_validation_failed")
    assert counters.get("stage1", "SOL") == 1
