from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import bot.alerts as alerts
from bot.db.database import AlertDeliveryOutcome, Base, EventAiAnalysis
from bot.services import ai_agent_groq
from bot.services.ai_agent_groq import AIGroqRateLimitError, LLMRateLimitBackoffActive


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


@pytest.fixture(autouse=True)
def clear_rate_limit_backoffs(monkeypatch):
    ai_agent_groq.reset_llm_rate_limit_backoffs()
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr(ai_agent_groq, "_groq_client", None)
    yield
    ai_agent_groq.reset_llm_rate_limit_backoffs()
    monkeypatch.setattr(ai_agent_groq, "_groq_client", None)


@pytest.mark.asyncio
async def test_rate_limit_error_starts_provider_model_backoff(monkeypatch):
    create_mock = AsyncMock(
        side_effect=RuntimeError("rate_limit_exceeded: try again in 2m10s")
    )
    monkeypatch.setattr(ai_agent_groq, "_groq_client", _fake_groq_client(create_mock))

    with pytest.raises(AIGroqRateLimitError) as raised:
        await ai_agent_groq._run_groq_chat_completion(
            call_type="event_analysis",
            symbol="SOL",
            model="test-model",
            messages=[{"role": "user", "content": "hello"}],
            max_tokens=10,
            response_format=None,
        )

    assert raised.value.retry_after_seconds == 130
    assert ai_agent_groq.get_llm_rate_limit_backoff(model="test-model") is not None


@pytest.mark.asyncio
async def test_active_backoff_skips_event_analysis_without_no_alert(monkeypatch):
    engine, session_local = await build_session_factory()
    try:
        # The backoff registry is keyed by (provider, model). The first call below
        # arms the backoff using the event-analysis model, and the second call
        # (through the production path) must look it up under the exact same model.
        # Both sides read GROQ_EVENT_ANALYSIS_MODEL, which is resolved from the
        # environment at import time and can differ between the two modules if the
        # environment or test ordering changed it. Pin both to one shared value so
        # the backoff key matches deterministically instead of relying on ambient
        # state, which previously made this test flaky in CI.
        event_analysis_model = "test-event-analysis-model"
        monkeypatch.setattr(ai_agent_groq, "GROQ_EVENT_ANALYSIS_MODEL", event_analysis_model)
        monkeypatch.setattr(alerts, "GROQ_EVENT_ANALYSIS_MODEL", event_analysis_model)

        rate_limited_create = AsyncMock(
            side_effect=RuntimeError("rate_limit_exceeded: try again in 30s")
        )
        monkeypatch.setattr(
            ai_agent_groq,
            "_groq_client",
            _fake_groq_client(rate_limited_create),
        )
        with pytest.raises(AIGroqRateLimitError):
            await ai_agent_groq._run_groq_chat_completion(
                call_type="event_analysis",
                symbol="BTC",
                model=event_analysis_model,
                messages=[{"role": "user", "content": "hello"}],
                max_tokens=10,
                response_format=None,
            )

        assert ai_agent_groq.get_llm_rate_limit_backoff(model=event_analysis_model) is not None

        blocked_create = AsyncMock(return_value=SimpleNamespace(headers={}, choices=[]))
        monkeypatch.setattr(ai_agent_groq, "_groq_client", _fake_groq_client(blocked_create))
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
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_backoff_expiry_allows_provider_calls(monkeypatch):
    model = "test-model"
    ai_agent_groq._llm_rate_limit_backoffs[("groq", model)] = datetime.now(
        timezone.utc
    ) - timedelta(seconds=1)
    create_mock = AsyncMock(return_value=SimpleNamespace(headers={}))
    monkeypatch.setattr(ai_agent_groq, "_groq_client", _fake_groq_client(create_mock))

    response, headers, input_chars = await ai_agent_groq._run_groq_chat_completion(
        call_type="market_heartbeat",
        symbol="BTC",
        model=model,
        messages=[{"role": "user", "content": "hello"}],
        max_tokens=10,
        response_format=None,
    )

    assert response is not None
    assert headers == {}
    assert input_chars == 5
    create_mock.assert_awaited_once()
    assert ai_agent_groq.get_llm_rate_limit_backoff(model=model) is None


@pytest.mark.asyncio
async def test_active_backoff_raises_before_provider_call(monkeypatch):
    model = "test-model"
    limited_until = datetime.now(timezone.utc) + timedelta(minutes=5)
    ai_agent_groq._llm_rate_limit_backoffs[("groq", model)] = limited_until
    create_mock = AsyncMock(return_value=SimpleNamespace(headers={}))
    monkeypatch.setattr(ai_agent_groq, "_groq_client", _fake_groq_client(create_mock))

    with pytest.raises(LLMRateLimitBackoffActive):
        await ai_agent_groq._run_groq_chat_completion(
            call_type="market_heartbeat",
            symbol="BTC",
            model=model,
            messages=[{"role": "user", "content": "hello"}],
            max_tokens=10,
            response_format=None,
        )

    create_mock.assert_not_awaited()
