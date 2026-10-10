"""Offline Event Alert Render provider/exhaustion contracts.

All provider calls are in-memory fakes. No network, Telegram, or production DB.
"""
import asyncio
import json
from unittest.mock import AsyncMock

import pytest

import bot.alerts as alerts
from bot.services import ai_agent_groq
from bot.services.llm.base_provider import ProviderResult
from bot.services.llm.errors import (
    AIInvalidJsonError, AISchemaValidationError, AllProvidersFailedError,
)
from bot.services.llm.router import LLMRouter
from bot.services.llm.telemetry import classify_ai_error_reason


class ProviderError(RuntimeError):
    def __init__(self, status_code, code=None):
        super().__init__("provider refused output")
        self.status_code = status_code
        self.code = code


class FakeProvider:
    def __init__(self, name, answers):
        self.name = name
        self.answers = answers
        self.calls = []

    async def chat_completion(self, *, model, response_format, **kwargs):
        self.calls.append((model, response_format))
        answer = self.answers[model]
        if isinstance(answer, BaseException):
            raise answer
        return ProviderResult(
            provider=self.name, model=model, raw_content=answer, input_chars=42,
        )


@pytest.fixture
def render_chain(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "fake")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "fake")
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    monkeypatch.setenv("LLM_BREAKER_ENABLED", "false")
    for key in (
        "GROQ_EVENT_ANALYSIS_MODEL", "GROQ_EVENT_RENDER_FALLBACK_MODEL",
        "CLOUDFLARE_EVENT_RENDER_MODEL", "GEMINI_EVENT_RENDER_MODEL",
    ):
        monkeypatch.delenv(key, raising=False)
    from bot.services.llm.config import provider_attempts
    entries = provider_attempts("event_alert_render")
    assert [provider for provider, _ in entries] == [
        "groq", "groq", "cloudflare", "gemini"
    ]
    return entries


def install(monkeypatch, entries, answers):
    registry = {
        name: FakeProvider(name, {
            model: answers[index]
            for index, (provider, model) in enumerate(entries) if provider == name
        })
        for name in ("groq", "cloudflare", "gemini")
    }
    monkeypatch.setattr(ai_agent_groq, "get_router", lambda: LLMRouter(registry=registry))
    return registry


def input_payload():
    return {
        "symbol": "BTC", "timestamp_utc": "2026-10-09T09:00:00+00:00",
        "market": {
            "price": 105.0,
            "snapshots": [{"m": -180, "p": 108.0}, {"m": 0, "p": 105.0}],
            "analysed_window_minutes": 180,
            "chg_window_percent": -3.1, "chg24h_percent": 2.4,
            "chg_since_msg_percent": None,
        },
        "last_msg": {"time": None, "price": None}, "news": [],
    }


def good_render():
    return json.dumps({
        "message_body": "The measured market move merits watching.",
        "related_news_ids": [],
        "possible_action": "Watch the next market observation.",
    })


async def call_render():
    return await ai_agent_groq.ask_event_alert_render_raw(
        input_payload(),
        schema_check=lambda data: (
            None if isinstance(data.get("message_body"), str)
            and isinstance(data.get("related_news_ids"), list)
            and isinstance(data.get("possible_action"), str)
            else (_ for _ in ()).throw(AISchemaValidationError("missing render fields"))
        ),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("winner", [0, 1, 2, 3])
async def test_success_after_each_model_and_no_later_calls(
    monkeypatch, render_chain, winner,
):
    answers = ["not json"] * winner + [good_render()] + [
        AssertionError("later provider must not be called")
    ] * (3 - winner)
    registry = install(monkeypatch, render_chain, answers)
    result = await call_render()
    assert result[1]["message_body"] == json.loads(good_render())["message_body"]
    assert result.provider == render_chain[winner][0]
    assert result.model == render_chain[winner][1]
    assert sum(len(provider.calls) for provider in registry.values()) == winner + 1
    if winner > 0:
        assert registry["groq"].calls[1][1]["type"] == "json_schema"


@pytest.mark.asyncio
async def test_provider_side_json_validation_only_is_recoverable(
    monkeypatch, render_chain,
):
    # Providers may reject malformed generated JSON server-side, before a response body exists.
    # This is invalid model output, not a malformed API request.
    registry = install(monkeypatch, render_chain, [
        ProviderError(400, "json_validate_failed") for _ in render_chain
    ])
    with pytest.raises(AISchemaValidationError) as caught:
        await call_render()
    assert caught.value._llm_all_exhausted_attempts_invalid_output is True
    assert [len(registry[name].calls) for name in ("groq", "cloudflare", "gemini")] == [2, 1, 1]


@pytest.mark.asyncio
@pytest.mark.parametrize("other_failure", [
    ProviderError(429, "rate_limit"), asyncio.TimeoutError(),
    ProviderError(503), ProviderError(404, "model_not_found"),
])
async def test_mixed_provider_failures_never_enable_deterministic_recovery(
    monkeypatch, render_chain, other_failure,
):
    answers = ["not json", "still not json", other_failure, "not json either"]
    install(monkeypatch, render_chain, answers)
    with pytest.raises(AIInvalidJsonError) as caught:
        await call_render()
    assert caught.value._llm_all_exhausted_attempts_invalid_output is False


@pytest.mark.asyncio
async def test_pure_client_schema_failures_allow_recovery_marker(
    monkeypatch, render_chain,
):
    install(monkeypatch, render_chain, [
        '{"message_body": 4, "related_news_ids": [], "possible_action": false}'
    ] * 4)
    with pytest.raises(AISchemaValidationError) as caught:
        await call_render()
    assert caught.value._llm_all_exhausted_attempts_invalid_output is True


@pytest.mark.asyncio
async def test_bad_request_aborts_without_calling_fallback(
    monkeypatch, render_chain,
):
    registry = install(monkeypatch, render_chain, [
        ProviderError(400, "invalid_request_error"), good_render(), good_render(), good_render()
    ])
    with pytest.raises(ProviderError) as caught:
        await call_render()
    assert classify_ai_error_reason(caught.value) == "provider_bad_request"
    assert [len(registry[name].calls) for name in ("groq", "cloudflare", "gemini")] == [1, 0, 0]


@pytest.mark.asyncio
async def test_no_configured_providers_is_terminal(monkeypatch, render_chain):
    for key in ("GROQ_API_KEY", "CLOUDFLARE_API_TOKEN", "GEMINI_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    install(monkeypatch, render_chain, [good_render()] * 4)
    with pytest.raises(AllProvidersFailedError):
        await call_render()


def patch_significance_and_storage(monkeypatch):
    significance = {
        "symbol": "BTC", "should_alert": True, "confidence": "high",
        "materiality": "material", "novelty": "new", "reason_code": "unusual_move",
    }
    significance_call = AsyncMock(return_value=("significance-json", significance))
    render_outcome = AsyncMock()
    delivery_outcome = AsyncMock()
    monkeypatch.setattr(alerts, "ask_event_significance_raw", significance_call)
    monkeypatch.setattr(alerts, "_save_event_alert_render_outcome", render_outcome)
    monkeypatch.setattr(alerts, "_save_event_analysis_attempt", AsyncMock(return_value=42))
    monkeypatch.setattr(alerts, "_record_alert_delivery_outcome", delivery_outcome)
    monkeypatch.setattr(alerts, "_get_previous_event_alert_id", AsyncMock(return_value=None))
    monkeypatch.setattr(alerts.event_analysis_health, "record_success", lambda: None)
    return significance_call, render_outcome, delivery_outcome


@pytest.mark.asyncio
@pytest.mark.parametrize("winner", [0, 1, 2, 3])
async def test_full_factual_validation_at_each_fallback_before_allowed_outcome(
    monkeypatch, render_chain, winner,
):
    invalid_claim = json.dumps({
        "message_body": "BTC rose 40% over the last 3 hours.",
        "related_news_ids": [], "possible_action": "Watch the next move.",
    })
    responses = [invalid_claim] * winner + [good_render()] + [
        AssertionError("provider after winner should not be called")
    ] * (3 - winner)
    registry = install(monkeypatch, render_chain, responses)
    significance_call, render_outcome, delivery_outcome = patch_significance_and_storage(
        monkeypatch
    )

    decision, analysis_id = await alerts._create_event_analysis_decision(input_payload())

    assert analysis_id == 42
    assert decision is not None and decision.should_alert is True
    assert decision.urgency == "normal"
    assert "40%" not in decision.message_body
    assert "{" not in decision.message_body
    assert render_outcome.await_args.kwargs["status"] == "success"
    assert delivery_outcome.await_args.kwargs["status"] == alerts.OUTCOME_ALLOWED
    significance_call.assert_awaited_once()
    assert sum(len(provider.calls) for provider in registry.values()) == winner + 1


@pytest.mark.asyncio
async def test_server_side_invalid_only_exhaustion_recovers_through_factual_validator(
    monkeypatch, render_chain,
):
    registry = install(monkeypatch, render_chain, [
        ProviderError(400, "json_validate_failed") for _ in render_chain
    ])
    significance_call, render_outcome, delivery_outcome = patch_significance_and_storage(
        monkeypatch
    )

    decision, analysis_id = await alerts._create_event_analysis_decision(input_payload())

    assert analysis_id == 42
    assert decision is not None and decision.should_alert
    assert decision.urgency == "normal"
    assert "40%" not in decision.message_body
    assert "{" not in decision.message_body
    assert render_outcome.await_args.kwargs["status"] == "success"
    assert render_outcome.await_args.kwargs["error_reason"] == (
        "deterministic_fallback_from_schema_validation_failed"
    )
    assert delivery_outcome.await_args.kwargs["status"] == alerts.OUTCOME_ALLOWED
    significance_call.assert_awaited_once()
    assert sum(len(provider.calls) for provider in registry.values()) == 4
