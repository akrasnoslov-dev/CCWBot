import logging
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import bot.alerts as alerts
from bot.db.database import AlertDeliveryOutcome, Base, EventAiAnalysis
from bot.observability import event_analysis_health
from bot.services.llm import groq_provider, telemetry
from bot.services.llm.errors import AIGroqRateLimitError, LLMRateLimitBackoffActive
from bot.services.llm.operation import llm_operation_scope, new_llm_operation_id

# The Groq chat-completion mechanism (and its (provider, model) rate-limit backoff) now lives in
# bot.services.llm. These tests exercise the GroqProvider directly and the production event-analysis
# path through the router; the backoff-registry semantics are unchanged from the old facade.


async def build_session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_local = async_sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    return engine, session_local


def _fake_groq_client(create_mock):
    return SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=create_mock),
        )
    )


def _set_groq_client(monkeypatch, client):
    monkeypatch.setattr(groq_provider.get_provider(), "_client", client)


@pytest.fixture(autouse=True)
def clear_rate_limit_backoffs(monkeypatch):
    telemetry.reset_llm_rate_limit_backoffs()
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    # Keep the fallback chain single-provider so these unit tests are deterministic.
    monkeypatch.setenv("LLM_PROVIDER_PRIORITY", "groq")
    monkeypatch.setattr(groq_provider.get_provider(), "_client", None)
    yield
    telemetry.reset_llm_rate_limit_backoffs()
    monkeypatch.setattr(groq_provider.get_provider(), "_client", None)


def test_active_backoff_snapshot_preserves_triggering_call_types(caplog):
    error = RuntimeError("429 rate limit")
    operation_id = new_llm_operation_id()
    with caplog.at_level(logging.WARNING, logger=telemetry.logger.name):
        with llm_operation_scope(operation_id):
            telemetry.start_llm_rate_limit_backoff(
                provider="mistral",
                model="shared-model",
                call_type="daily_report",
                error=error,
                headers=None,
            )
            telemetry.start_llm_rate_limit_backoff(
                provider="mistral",
                model="shared-model",
                call_type="news_intelligence",
                error=error,
                headers=None,
            )

    rows = telemetry.get_active_llm_rate_limit_backoffs()

    assert len(rows) == 1
    assert rows[0]["provider"] == "mistral"
    assert rows[0]["model"] == "shared-model"
    assert rows[0]["call_types"] == ("daily_report", "news_intelligence")
    assert all(
        f"operation_id={operation_id}" in record.getMessage()
        for record in caplog.records
        if "ops_event=llm_rate_limit_started" in record.getMessage()
    )


@pytest.mark.asyncio
async def test_rate_limit_error_starts_provider_model_backoff(monkeypatch):
    create_mock = AsyncMock(
        side_effect=RuntimeError("rate_limit_exceeded: try again in 2m10s")
    )
    _set_groq_client(monkeypatch, _fake_groq_client(create_mock))

    with pytest.raises(AIGroqRateLimitError) as raised:
        await groq_provider.get_provider().chat_completion(
            call_type="event_analysis",
            symbol="SOL",
            model="test-model",
            messages=[{"role": "user", "content": "hello"}],
            max_tokens=10,
            response_format=None,
        )

    assert raised.value.retry_after_seconds == 130
    assert telemetry.get_llm_rate_limit_backoff(model="test-model") is not None


@pytest.mark.asyncio
async def test_active_backoff_skips_event_analysis_without_no_alert(monkeypatch):
    engine, session_local = await build_session_factory()
    event_analysis_health.reset()
    try:
        # The backoff registry is keyed by (provider, model). The first call below arms the
        # backoff using the event-analysis model, and the production path (through the router)
        # must look it up under the exact same model. The router resolves the groq event-analysis
        # model from GROQ_EVENT_ANALYSIS_MODEL, so pin that env var to one shared value.
        event_analysis_model = "test-event-analysis-model"
        monkeypatch.setenv("GROQ_EVENT_ANALYSIS_MODEL", event_analysis_model)

        rate_limited_create = AsyncMock(
            side_effect=RuntimeError("rate_limit_exceeded: try again in 30s")
        )
        _set_groq_client(monkeypatch, _fake_groq_client(rate_limited_create))
        with pytest.raises(AIGroqRateLimitError):
            await groq_provider.get_provider().chat_completion(
                call_type="event_analysis",
                symbol="BTC",
                model=event_analysis_model,
                messages=[{"role": "user", "content": "hello"}],
                max_tokens=10,
                response_format=None,
            )

        assert telemetry.get_llm_rate_limit_backoff(model=event_analysis_model) is not None

        blocked_create = AsyncMock(return_value=SimpleNamespace(headers={}, choices=[]))
        _set_groq_client(monkeypatch, _fake_groq_client(blocked_create))
        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)

        decision, analysis_id = await alerts._create_event_analysis_decision(
            {
                "analysis_id": "event_analysis_btc_backoff",
                "symbol": "BTC",
                "news": [],
                "market": {"price": 100000.0, "chg24h": 1.0, "chg_since_msg": None},
            }
        )

        assert decision is None
        assert analysis_id is None
        blocked_create.assert_not_awaited()
        async with session_local() as session:
            row = await session.scalar(select(EventAiAnalysis))
            outcome = await session.scalar(select(AlertDeliveryOutcome))
        assert row.status == "skipped_due_to_rate_limit"
        assert row.status != "no_alert"
        assert outcome.status == "rate_limited"
        assert outcome.reason_code == "llm_rate_limited"
        assert outcome.event_ai_analysis_id == row.id
        assert outcome.decision_stage == "llm"
        assert outcome.decision_reason == "unknown"
        assert outcome.context_fingerprint
        assert event_analysis_health.consecutive_failures() == 0
    finally:
        event_analysis_health.reset()
        await engine.dispose()


@pytest.mark.asyncio
async def test_backoff_expiry_allows_provider_calls(monkeypatch):
    model = "test-model"
    telemetry._llm_rate_limit_backoffs[("groq", model)] = datetime.now(
        timezone.utc
    ) - timedelta(seconds=1)
    create_mock = AsyncMock(return_value=SimpleNamespace(headers={}))
    _set_groq_client(monkeypatch, _fake_groq_client(create_mock))

    result = await groq_provider.get_provider().chat_completion(
        call_type="market_heartbeat",
        symbol="BTC",
        model=model,
        messages=[{"role": "user", "content": "hello"}],
        max_tokens=10,
        response_format=None,
    )

    assert result.response is not None
    assert result.headers == {}
    assert result.input_chars == 5
    create_mock.assert_awaited_once()
    assert telemetry.get_llm_rate_limit_backoff(model=model) is None


@pytest.mark.asyncio
async def test_active_backoff_raises_before_provider_call(monkeypatch):
    model = "test-model"
    limited_until = datetime.now(timezone.utc) + timedelta(minutes=5)
    telemetry._llm_rate_limit_backoffs[("groq", model)] = limited_until
    create_mock = AsyncMock(return_value=SimpleNamespace(headers={}))
    _set_groq_client(monkeypatch, _fake_groq_client(create_mock))

    with pytest.raises(LLMRateLimitBackoffActive):
        await groq_provider.get_provider().chat_completion(
            call_type="market_heartbeat",
            symbol="BTC",
            model=model,
            messages=[{"role": "user", "content": "hello"}],
            max_tokens=10,
            response_format=None,
        )

    create_mock.assert_not_awaited()
