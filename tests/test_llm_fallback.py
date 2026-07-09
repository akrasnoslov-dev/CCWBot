"""End-to-end facade fallback and backward-compatibility (no real provider calls)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import bot.services.ai_agent_groq as ai_agent_groq
from bot.services.llm import cerebras_provider, config, groq_provider, telemetry
from bot.services.llm.errors import AIProviderRateLimitError


def _json_client(content):
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=None,
    )
    return SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(return_value=response)))
    )


def _rate_limited_client():
    return SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=AsyncMock(side_effect=RuntimeError("rate_limit_exceeded 429 rate limit"))
            )
        )
    )


@pytest.fixture(autouse=True)
def two_provider_chain(monkeypatch):
    telemetry.reset_llm_rate_limit_backoffs()
    monkeypatch.setenv("GROQ_API_KEY", "groq-key")
    monkeypatch.setenv("CEREBRAS_API_KEY", "cerebras-key")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER_PRIORITY", "groq,cerebras")
    monkeypatch.setattr(groq_provider.get_provider(), "_client", None)
    monkeypatch.setattr(cerebras_provider.get_provider(), "_client", None)
    yield
    telemetry.reset_llm_rate_limit_backoffs()
    monkeypatch.setattr(groq_provider.get_provider(), "_client", None)
    monkeypatch.setattr(cerebras_provider.get_provider(), "_client", None)


@pytest.mark.asyncio
async def test_event_analysis_falls_back_to_cerebras(monkeypatch):
    monkeypatch.setattr(groq_provider.get_provider(), "_client", _rate_limited_client())
    monkeypatch.setattr(
        cerebras_provider.get_provider(), "_client", _json_client('{"should_alert": false}')
    )

    result = await ai_agent_groq.ask_event_analysis_raw(
        {"symbol": "BTC", "news": [], "market": {"price": 1.0}}
    )

    raw, parsed = result
    assert parsed == {"should_alert": False}
    assert result.provider == "cerebras"
    # Groq's rate limit armed its (provider, model) backoff.
    groq_model = config.model_for("groq", "event_analysis")
    assert telemetry.get_llm_rate_limit_backoff(provider="groq", model=groq_model) is not None


@pytest.mark.asyncio
async def test_event_analysis_all_providers_rate_limited(monkeypatch):
    monkeypatch.setattr(groq_provider.get_provider(), "_client", _rate_limited_client())
    monkeypatch.setattr(cerebras_provider.get_provider(), "_client", _rate_limited_client())

    with pytest.raises(AIProviderRateLimitError):
        await ai_agent_groq.ask_event_analysis_raw(
            {"symbol": "BTC", "news": [], "market": {"price": 1.0}}
        )


@pytest.mark.asyncio
async def test_price_alert_payload_uses_deterministic_fallback_when_all_rate_limited(monkeypatch):
    monkeypatch.setattr(groq_provider.get_provider(), "_client", _rate_limited_client())
    monkeypatch.setattr(cerebras_provider.get_provider(), "_client", _rate_limited_client())

    payload = await ai_agent_groq.create_ai_alert_payload(
        previous_price=100.0,
        current_price=102.0,
        price_change_percent=2.0,
        change_24h=1.0,
        change_7d=None,
        news_items=None,
        alert_threshold_percent=1.0,
        check_interval_seconds=3600,
        symbol="BTC",
        coin_name="Bitcoin",
    )

    assert payload.get("rate_limited") is True
    assert "AI analysis is temporarily unavailable" in payload["plain_text"]


def test_backward_compatible_public_api():
    # AIGroqRateLimitError stays an alias of the provider-agnostic error.
    assert ai_agent_groq.AIGroqRateLimitError is ai_agent_groq.AIProviderRateLimitError
    # LLMJsonResult remains a 2-tuple and exposes usage_log_id, provider, model.
    result = ai_agent_groq.LLMJsonResult("raw", {"a": 1}, 7, provider="cerebras", model="m")
    raw, parsed = result
    assert (raw, parsed) == ("raw", {"a": 1})
    assert result.usage_log_id == 7
    assert result.provider == "cerebras"
    assert result.model == "m"
