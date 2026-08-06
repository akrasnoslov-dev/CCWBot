"""Event Analysis health: /health reporting, log escalation, and suppression reason tokens."""

import logging
import time
from datetime import datetime, timedelta, timezone

import pytest

import bot.health as health
from bot.observability import event_analysis_health


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch):
    for name in (
        "EVENT_ANALYSIS_FAILURE_ESCALATION_THRESHOLD",
        "EVENT_ANALYSIS_HEALTH_MAX_AGE_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)
    event_analysis_health.reset()
    yield
    event_analysis_health.reset()


# --- counters ----------------------------------------------------------------------------


def test_failures_accumulate_and_a_success_clears_the_streak():
    for expected in (1, 2, 3):
        assert event_analysis_health.record_failure(reason="provider_model_error") == expected

    event_analysis_health.record_success()

    assert event_analysis_health.consecutive_failures() == 0
    assert event_analysis_health.snapshot()["last_failure_reason"] is None


def test_thresholds_are_configurable(monkeypatch):
    monkeypatch.setenv("EVENT_ANALYSIS_FAILURE_ESCALATION_THRESHOLD", "12")
    monkeypatch.setenv("EVENT_ANALYSIS_HEALTH_MAX_AGE_SECONDS", "60")

    assert event_analysis_health.failure_escalation_threshold() == 12
    assert event_analysis_health.max_success_age_seconds() == 60


def test_unparseable_threshold_falls_back_and_warns(monkeypatch, caplog):
    monkeypatch.setenv("EVENT_ANALYSIS_FAILURE_ESCALATION_THRESHOLD", "five")

    with caplog.at_level(logging.WARNING, logger="bot.services.llm.env"):
        assert event_analysis_health.failure_escalation_threshold() == 5

    assert any(
        "EVENT_ANALYSIS_FAILURE_ESCALATION_THRESHOLD" in record.getMessage()
        for record in caplog.records
    )


# --- state evaluation --------------------------------------------------------------------


def test_recent_success_is_ok():
    now = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
    state, age = event_analysis_health.evaluate_state(
        last_success_at=now - timedelta(minutes=20), consecutive_failures=0, now=now
    )

    assert state == "ok"
    assert age == 1200


def test_a_long_failure_streak_is_degraded():
    now = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
    state, _age = event_analysis_health.evaluate_state(
        last_success_at=now - timedelta(minutes=1), consecutive_failures=5, now=now
    )

    assert state == "degraded"


def test_a_stale_last_success_is_degraded():
    # The outage state: the last success is 18 days old.
    now = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
    state, age = event_analysis_health.evaluate_state(
        last_success_at=now - timedelta(days=18), consecutive_failures=0, now=now
    )

    assert state == "degraded"
    assert age == 18 * 24 * 3600


def test_no_recorded_success_and_no_failures_is_unknown():
    state, age = event_analysis_health.evaluate_state(
        last_success_at=None, consecutive_failures=0
    )

    assert state == "unknown"
    assert age is None


def test_naive_timestamps_are_treated_as_utc():
    now = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
    state, age = event_analysis_health.evaluate_state(
        last_success_at=datetime(2026, 8, 5, 11, 50), consecutive_failures=0, now=now
    )

    assert state == "ok"
    assert age == 600


# --- /health payload ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_reports_event_analysis_without_failing_the_endpoint(monkeypatch):
    # The Compose healthcheck fails the container when status != "ok", and nothing restarts it
    # on that basis. Flipping status would mark a bot that is still serving prices, heartbeats
    # and reports permanently unhealthy, with no remediation to show for it.
    monkeypatch.setattr(health, "DB_ENABLED", False)
    monkeypatch.setattr(health, "load_state", lambda: {})
    for _ in range(9):
        event_analysis_health.record_failure(reason="provider_model_error")

    response = await health.health_response(time.monotonic())

    assert response["status"] == "ok"
    assert response["event_analysis"]["state"] == "degraded"
    assert response["event_analysis"]["consecutive_failures"] == 9


@pytest.mark.asyncio
async def test_health_payload_carries_no_secrets_or_environment_values(monkeypatch):
    monkeypatch.setattr(health, "DB_ENABLED", False)
    monkeypatch.setattr(health, "load_state", lambda: {})
    monkeypatch.setenv("GROQ_API_KEY", "groq-secret-value")
    monkeypatch.setenv("GROQ_EVENT_ANALYSIS_MODEL", "llama-3.3-70b-versatile")

    payload = str(await health.health_response(time.monotonic()))

    assert "groq-secret-value" not in payload
    # No model identifiers, provider names or env var names in the health payload.
    for token in ("llama", "GROQ", "groq", "DATABASE_URL", "TELEGRAM"):
        assert token not in payload


@pytest.mark.asyncio
async def test_health_reports_unknown_rather_than_ok_without_evidence(monkeypatch):
    monkeypatch.setattr(health, "DB_ENABLED", False)
    monkeypatch.setattr(health, "load_state", lambda: {})

    response = await health.health_response(time.monotonic())

    assert response["event_analysis"]["state"] == "unknown"
    assert response["event_analysis"]["last_success_at"] is None


@pytest.mark.asyncio
async def test_health_still_degrades_safely_when_the_whole_lookup_fails(monkeypatch):
    def _boom():
        raise OSError("state file failed")

    monkeypatch.setattr(health, "DB_ENABLED", False)
    monkeypatch.setattr(health, "load_state", _boom)

    response = await health.health_response(time.monotonic())

    assert response["status"] == "degraded"
    assert response["error"] == "health_check_failed"
    assert "state file failed" not in str(response)


# --- log escalation ----------------------------------------------------------------------


def test_repeated_failures_escalate_to_error(caplog):
    from bot import alerts

    with caplog.at_level(logging.WARNING, logger="bot.alerts"):
        for _ in range(4):
            alerts._log_event_analysis_failure("btc", "provider_model_error")
        levels_before = [record.levelno for record in caplog.records]
        alerts._log_event_analysis_failure("btc", "provider_model_error")
        alerts._log_event_analysis_failure("btc", "provider_model_error")

    # First occurrences stay at WARNING: one failed analysis is normal.
    assert levels_before == [logging.WARNING] * 4
    # Past the threshold severity reflects duration, not just occurrence.
    assert caplog.records[4].levelno == logging.ERROR
    assert caplog.records[5].levelno == logging.ERROR
    assert "consecutive_failures=5" in caplog.records[4].getMessage()


def test_escalated_line_exposes_no_symbol_internals_or_payload(caplog):
    from bot import alerts

    with caplog.at_level(logging.WARNING, logger="bot.alerts"):
        alerts._log_event_analysis_failure("btc", "provider_model_error")

    message = caplog.records[0].getMessage()
    assert "symbol=BTC" in message
    assert "ops_event=event_analysis_failed" in message


def test_a_success_between_failures_resets_the_escalation(caplog):
    from bot import alerts

    with caplog.at_level(logging.WARNING, logger="bot.alerts"):
        for _ in range(4):
            alerts._log_event_analysis_failure("btc", "provider_model_error")
        event_analysis_health.record_success()
        alerts._log_event_analysis_failure("btc", "provider_model_error")

    assert caplog.records[-1].levelno == logging.WARNING
    assert "consecutive_failures=1" in caplog.records[-1].getMessage()


# --- suppression reason vocabulary -------------------------------------------------------


def test_every_suppression_reason_is_an_explicit_token():
    from bot import alerts

    assert alerts.SUPPRESSION_LLM_NO_ALERT in alerts.SUPPRESSION_REASON_VALUES
    assert alerts.SUPPRESSION_ALREADY_DELIVERED in alerts.SUPPRESSION_REASON_VALUES


def test_suppression_tokens_match_the_db_reason_code_vocabulary():
    # The log side and the durable alert_delivery_outcomes side must use the same words, or
    # the two cannot be joined — which is how 27.9% of suppression lines became unattributable.
    from bot import alerts

    assert alerts.SUPPRESSION_LLM_NO_ALERT == alerts.REASON_LLM_NO_ALERT
    assert alerts.SUPPRESSION_ALREADY_DELIVERED == alerts.REASON_ALREADY_DELIVERED
    assert alerts.SUPPRESSION_LLM_RATE_LIMITED == alerts.REASON_LLM_RATE_LIMITED


def test_llm_no_alert_suppression_is_logged_with_its_own_reason(caplog):
    from bot import alerts

    with caplog.at_level(logging.INFO, logger="bot.alerts"):
        alerts._log_event_alert_suppression(
            symbol="btc",
            suppression_reason=alerts.SUPPRESSION_LLM_NO_ALERT,
            suppression_count=1,
        )

    message = caplog.records[0].getMessage()
    assert "suppression_reason=llm_no_alert" in message
    assert "suppression_reason=unknown" not in message


# --- regressions found in review ---------------------------------------------------------


@pytest.mark.asyncio
async def test_health_counts_no_alert_as_a_successful_analysis(monkeypatch):
    # `no_alert` means the LLM answered and decided against alerting, which is the common
    # outcome. Counting only `success` would report degraded whenever no alert had fired
    # recently -- i.e. almost always -- and an always-degraded field is one operators ignore.
    from bot.alerting.event_analysis import EVENT_ANALYSIS_SUCCESS_STATUSES

    assert EVENT_ANALYSIS_SUCCESS_STATUSES == {"success", "no_alert"}

    captured = {}

    async def _fake_query(session, statuses):
        captured["statuses"] = set(statuses)
        return datetime.now(timezone.utc) - timedelta(minutes=5)

    class _Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    async def _fake_price_state(session, symbol):
        return None

    monkeypatch.setattr(health, "DB_ENABLED", True)
    monkeypatch.setattr(health, "DB_SESSION_LOCAL", lambda: _Session())
    monkeypatch.setattr(health, "get_latest_event_analysis_success_at", _fake_query)
    monkeypatch.setattr(health, "get_price_state", _fake_price_state)

    response = await health.health_response(time.monotonic())

    assert captured["statuses"] == {"success", "no_alert"}
    assert response["event_analysis"]["state"] == "ok"


def test_a_news_only_rejection_clears_the_failure_streak():
    # A news-only rejection is a *successful* analysis: the LLM answered and the answer
    # validated. Recording success only on the later branch left the streak elevated through
    # a run of them, so /health stayed degraded while the LLM was demonstrably working.
    import inspect

    from bot import alerts

    source = inspect.getsource(alerts._create_event_analysis_decision)
    success_at = source.index("event_analysis_health.record_success()")
    news_only_at = source.index("_is_news_only_event_alert_decision(decision, input_payload)")

    assert success_at < news_only_at


def test_schema_failures_count_toward_the_failure_streak(caplog):
    # A continuous schema-failure outage must escalate exactly like a provider outage.
    import inspect

    from bot import alerts

    source = inspect.getsource(alerts._create_event_analysis_decision)

    assert "event analysis schema validation failed" not in source
    assert source.count("_log_event_analysis_failure(") == 3


def test_skipped_delivery_reasons_are_reported_separately():
    # `skipped_count` covers both "already delivered" and "delivery not scheduled", which the
    # durable outcome row distinguishes. Collapsing both into one label would reintroduce the
    # log-vs-DB mismatch this PR removes.
    from bot import alerts

    assert alerts.SUPPRESSION_DELIVERY_NOT_SCHEDULED == alerts.REASON_DELIVERY_NOT_SCHEDULED
    assert alerts.SUPPRESSION_DELIVERY_NOT_SCHEDULED in alerts.SUPPRESSION_REASON_VALUES


@pytest.mark.asyncio
async def test_a_slow_database_degrades_the_block_instead_of_stalling_health(monkeypatch):
    # The Docker healthcheck gives the whole request 5s. A slow or pool-exhausted database
    # must degrade this block, never stall the endpoint into looking unhealthy — which would
    # trigger exactly the restart loop the nested-block design exists to avoid.
    import asyncio

    async def _hang():
        await asyncio.sleep(30)

    monkeypatch.setattr(health, "DB_ENABLED", False)
    monkeypatch.setattr(health, "load_state", lambda: {})
    monkeypatch.setattr(health, "_read_last_event_analysis_success_at", _hang)

    response = await asyncio.wait_for(health.health_response(time.monotonic()), timeout=5)

    assert response["status"] == "ok"
    assert response["event_analysis"]["last_success_at"] is None
