"""Regression checks for zero-cost Groq pacing, day quota, symbol fairness and fallback."""

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.services.llm.base_provider import ProviderResult
from bot.services.llm.budget import GroqBudget, GroqBudgetExhausted, groq_budget
from bot.services.llm.groq_provider import GroqProvider
from bot.services.llm.router import LLMRouter


@pytest.fixture(autouse=True)
def clean_budget(monkeypatch):
    groq_budget.reset()
    monkeypatch.setenv("GROQ_API_KEY", "unit-test")
    monkeypatch.setenv("GEMINI_API_KEY", "unit-test")
    yield
    groq_budget.reset()


@pytest.mark.asyncio
async def test_day_token_limit_reserves_before_request_and_uses_actual_usage(monkeypatch):
    budget = GroqBudget()
    budget._loaded.add("m")
    monkeypatch.setenv("GROQ_FREE_TOKEN_BUDGET_DAY", "2000")
    first = await budget.reserve(
        model="m",
        symbol="BTC",
        call_type="daily_report",
        input_chars=0,
        max_tokens=6300,
    )
    await budget.settle(first, actual_tokens=180, headers=None)
    second = await budget.reserve(
        model="m",
        symbol="ETH",
        call_type="market_heartbeat",
        input_chars=0,
        max_tokens=350,
    )
    await budget.settle(second, actual_tokens=180, headers=None)
    with pytest.raises(GroqBudgetExhausted, match="rate-limited") as error:
        await budget.reserve(
            model="m",
            symbol="SOL",
            call_type="daily_report",
            input_chars=0,
            max_tokens=6300,
        )
    assert error.value.budget_dimension == "local_tpd"
    assert len(budget._history["m"]) == 2


@pytest.mark.asyncio
async def test_four_symbols_each_get_a_fair_share_without_extra_provider_calls(monkeypatch):
    budget = GroqBudget()
    budget._loaded.add("m")
    monkeypatch.setenv("GROQ_FREE_TOKEN_BUDGET_DAY", "10000")
    monkeypatch.setenv("GROQ_FREE_TOKEN_BUDGET_MINUTE", "10000")

    async def request(symbol):
        try:
            await budget.reserve(
                model="m",
                symbol=symbol,
                call_type="event_analysis",
                input_chars=0,
                max_tokens=6300,
            )
            return "accepted"
        except GroqBudgetExhausted as error:
            return error.budget_dimension

    pairs = await asyncio.gather(
        *(request(symbol) for symbol in ["BTC", "BTC", "ETH", "ETH", "GRAM", "GRAM", "SOL", "SOL"])
    )
    assert pairs == ["accepted", "symbol_fair_share"] * 4
    assert len(budget._history["m"]) == 4


@pytest.mark.asyncio
async def test_tpm_pacing_and_reset_header(monkeypatch):
    budget = GroqBudget()
    budget._loaded.add("m")
    monkeypatch.setenv("GROQ_FREE_TOKEN_BUDGET_MINUTE", "2200")
    first = await budget.reserve(
        model="m", symbol=None, call_type="daily_report", input_chars=0, max_tokens=800
    )
    await budget.settle(
        first,
        actual_tokens=600,
        headers={
            "x-ratelimit-remaining-tokens": "500",
            "x-ratelimit-reset-tokens": "1m10s",
            "x-ratelimit-remaining-requests": "0",
            "x-ratelimit-reset-requests": "2h30m",
        },
    )
    with pytest.raises(GroqBudgetExhausted) as error:
        await budget.reserve(
            model="m",
            symbol="BTC",
            call_type="event_analysis",
            input_chars=0,
            max_tokens=6300,
        )
    assert error.value.budget_dimension == "header_rpd"
    assert error.value.limited_until > datetime.now(timezone.utc) + timedelta(hours=2)
    budget._headers["m"]["requests"] = (20, datetime.now(timezone.utc) + timedelta(hours=1))
    with pytest.raises(GroqBudgetExhausted) as error:
        await budget.reserve(
            model="m",
            symbol="BTC",
            call_type="event_analysis",
            input_chars=0,
            max_tokens=6300,
        )
    assert error.value.budget_dimension == "header_tpm"
    budget._headers["m"]["tokens"] = (8000, datetime.now(timezone.utc) - timedelta(seconds=1))
    with pytest.raises(GroqBudgetExhausted) as error:
        await budget.reserve(
            model="m",
            symbol="BTC",
            call_type="event_analysis",
            input_chars=0,
            max_tokens=6300,
        )
    assert error.value.budget_dimension == "local_tpm"


@pytest.mark.asyncio
async def test_quota_skip_routes_to_fallback_once_and_preserves_operation(monkeypatch):
    model = "openai/gpt-oss-120b"
    groq_budget._loaded.add(model)
    groq_budget._headers[model] = {"requests": (0, datetime.now(timezone.utc) + timedelta(hours=1))}
    # No network requests are permitted. The real Groq provider must reject before SDK.
    groq = GroqProvider()
    groq._client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=AsyncMock(side_effect=AssertionError("Groq called")))
        )
    )
    fallback = SimpleNamespace(
        chat_completion=AsyncMock(
            return_value=ProviderResult(
                provider="gemini",
                model="gemini-3.8-flash",
                raw_content="{}",
                input_chars=0,
                response=SimpleNamespace(),
            )
        )
    )
    monkeypatch.setenv("LLM_EVENT_PROVIDERS", "groq,gemini")
    router = LLMRouter(registry={"groq": groq, "gemini": fallback})
    result = await router.chat_completion(
        call_type="event_analysis",
        messages=[{"role": "user", "content": "test"}],
        max_tokens=300,
        response_format=None,
        symbol="GRAM",
    )
    assert result.provider == "gemini"
    assert result.operation_id
    fallback.chat_completion.assert_awaited_once()
    groq._client.chat.completions.create.assert_not_awaited()
    assert groq_budget._history[model] == []


@pytest.mark.asyncio
async def test_failed_attempt_releases_token_reservation_but_counts_request(monkeypatch):
    budget = GroqBudget()
    budget._loaded.add("m")
    lease = await budget.reserve(
        model="m",
        symbol="SOL",
        call_type="event_analysis",
        input_chars=200,
        max_tokens=6300,
    )
    await budget.settle(lease, actual_tokens=None, headers=None, failed=True)
    assert sum(x.tokens for x in budget._history["m"]) == 0
    assert sum(x.request for x in budget._history["m"]) == 1


@pytest.mark.asyncio
async def test_request_burst_limit_is_nonblocking(monkeypatch):
    budget = GroqBudget()
    budget._loaded.add("m")
    monkeypatch.setenv("GROQ_FREE_REQUEST_BUDGET_MINUTE", "1")
    await budget.reserve(
        model="m", symbol=None, call_type="daily_report", input_chars=0, max_tokens=300
    )
    with pytest.raises(GroqBudgetExhausted) as error:
        await budget.reserve(
            model="m", symbol=None, call_type="daily_report", input_chars=0, max_tokens=300
        )
    assert error.value.budget_dimension == "local_rpm"
    assert len(budget._history["m"]) == 1


@pytest.mark.asyncio
async def test_history_reloads_real_attempts_not_skips_after_restart(monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    import bot.runtime as runtime
    from bot.db.database import Base, LlmUsageLog

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        async with session_factory() as session:
            session.add_all(
                [
                    LlmUsageLog(
                        provider="groq",
                        model="m",
                        call_type="daily_report",
                        symbol="BTC",
                        status="success",
                        total_tokens=1800,
                    ),
                    LlmUsageLog(
                        provider="groq",
                        model="m",
                        call_type="event_analysis",
                        symbol="ETH",
                        status="skipped_due_to_rate_limit",
                        total_tokens=9999,
                    ),
                ]
            )
            await session.commit()
        monkeypatch.setattr(runtime, "DB_ENABLED", True)
        monkeypatch.setattr(runtime, "DB_SESSION_LOCAL", session_factory)
        monkeypatch.setenv("GROQ_FREE_TOKEN_BUDGET_DAY", "2000")
        budget = GroqBudget()
        with pytest.raises(GroqBudgetExhausted) as error:
            await budget.reserve(
                model="m",
                symbol="GRAM",
                call_type="daily_report",
                input_chars=0,
                max_tokens=400,
            )
        assert error.value.budget_dimension == "local_tpd"
        assert len(budget._history["m"]) == 1
        assert budget._history["m"][0].tokens == 1800
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_budget_failure_is_persisted_as_logical_event_analysis_outcome(monkeypatch):
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    import bot.alerts as alerts
    import bot.runtime as runtime
    from bot.db.database import AlertDeliveryOutcome, Base, EventAiAnalysis, LlmUsageLog
    from bot.services.llm import groq_provider

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        monkeypatch.setattr(runtime, "DB_ENABLED", True)
        monkeypatch.setattr(runtime, "DB_SESSION_LOCAL", session_factory)
        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_factory)
        monkeypatch.setenv("LLM_EVENT_PROVIDERS", "groq")
        model = "openai/gpt-oss-120b"
        monkeypatch.setenv("GROQ_EVENT_ANALYSIS_MODEL", model)
        groq_budget._loaded.add(model)
        groq_budget._headers[model] = {
            "requests": (0, datetime.now(timezone.utc) + timedelta(hours=2))
        }
        create = AsyncMock(side_effect=AssertionError("Network call on exhausted budget"))
        monkeypatch.setattr(
            groq_provider.get_provider(),
            "_client",
            SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))),
        )
        decision, row_id = await alerts._create_event_analysis_decision(
            {
                "analysis_id": "event_btc_budget",
                "symbol": "BTC",
                "news": [],
                "market": {
                    "price": 100_000.0,
                    "chg24h_percent": 1.0,
                    "chg_since_msg_percent": None,
                },
            }
        )
        assert (decision, row_id) == (None, None)
        create.assert_not_awaited()
        async with session_factory() as session:
            analysis = await session.scalar(select(EventAiAnalysis))
            outcome = await session.scalar(select(AlertDeliveryOutcome))
            attempts = (await session.scalars(select(LlmUsageLog))).all()
        assert analysis.status == "skipped_due_to_rate_limit"
        assert analysis.error_reason == "rate_limit_budget_exhausted"
        assert outcome.status == "rate_limited"
        assert outcome.event_ai_analysis_id == analysis.id
        assert len(attempts) == 1
        assert attempts[0].status == "skipped_due_to_rate_limit"
        assert attempts[0].error_reason == "rate_limit_budget_exhausted"
        assert attempts[0].llm_operation_id == analysis.llm_operation_id
    finally:
        await engine.dispose()
