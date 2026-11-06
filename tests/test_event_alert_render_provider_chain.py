"""Offline Event Alert Render provider/exhaustion contracts.

All provider calls are in-memory fakes. No network, Telegram, or production DB.
"""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import bot.alerts as alerts
from bot.services import ai_agent_groq
from bot.services.llm.base_provider import ProviderResult
from bot.services.llm.errors import (
    AIInvalidJsonError,
    AISchemaValidationError,
    AllProvidersFailedError,
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
        self.messages = []

    async def chat_completion(self, *, model, response_format, **kwargs):
        self.calls.append((model, response_format))
        self.messages.append(kwargs["messages"])
        answer = self.answers[model]
        if callable(answer):
            answer = answer(kwargs["messages"])
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
    monkeypatch.setenv("OPENAI_API_KEY", "fake")
    monkeypatch.setenv("OPENAI_ENABLED", "true")
    monkeypatch.setenv("LLM_BREAKER_ENABLED", "false")
    for key in (
        "GROQ_EVENT_RENDER_MODEL", "CLOUDFLARE_EVENT_RENDER_MODEL", "OPENAI_MODEL",
    ):
        monkeypatch.delenv(key, raising=False)
    from bot.services.llm.config import provider_attempts
    entries = provider_attempts("event_alert_render")
    assert [provider for provider, _ in entries] == ["groq", "openai", "cloudflare"]
    return entries


def install(monkeypatch, entries, answers):
    registry = {
        name: FakeProvider(name, {
            model: answers[index]
            for index, (provider, model) in enumerate(entries) if provider == name
        })
        for name in ("groq", "openai", "cloudflare")
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
@pytest.mark.parametrize("winner", [0, 1, 2])
async def test_success_after_each_model_and_no_later_calls(
    monkeypatch, render_chain, winner,
):
    answers = ["not json"] * winner + [good_render()] + [
        AssertionError("later provider must not be called")
    ] * (2 - winner)
    registry = install(monkeypatch, render_chain, answers)
    result = await call_render()
    assert result[1]["message_body"] == json.loads(good_render())["message_body"]
    assert result.provider == render_chain[winner][0]
    assert result.model == render_chain[winner][1]
    assert sum(len(provider.calls) for provider in registry.values()) == winner + 1


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", [
    "period_direction_mismatch", "unsupported_event_claim", "unsupported_trajectory",
    "window_duration_mismatch",
])
async def test_next_render_attempt_receives_safe_category_specific_repair_guidance(
    monkeypatch, render_chain, reason,
):
    bad = json.dumps({"message_body": "bad", "related_news_ids": [],
                      "possible_action": "Watch the next interval."})

    def repaired(messages):
        # A deterministic fake model improves only when the fallback gets feedback.
        assert "Previous render" in messages[-1]["content"]
        assert reason in messages[-1]["content"]
        assert "bad" not in messages[-1]["content"]
        if reason == "unsupported_event_claim":
            assert "pace claims not established" in messages[-1]["content"]
        return good_render()

    registry = install(monkeypatch, render_chain, [bad, repaired, bad])

    def validate(parsed):
        if parsed["message_body"] == "bad":
            raise AISchemaValidationError(reason, raw_content="private provider output")

    result = await ai_agent_groq.ask_event_alert_render_raw(input_payload(), schema_check=validate)
    assert result[1]["message_body"] == json.loads(good_render())["message_body"]
    assert sum(len(provider.calls) for provider in registry.values()) == 2
    first_messages = registry[render_chain[0][0]].messages[0]
    assert "Previous render" not in first_messages[-1]["content"]


@pytest.mark.asyncio
async def test_unknown_render_schema_error_never_copies_untrusted_error_or_output(
    monkeypatch, render_chain,
):
    bad = json.dumps({"message_body": "bad", "related_news_ids": [],
                      "possible_action": "Watch the next interval."})
    secret = "UNTRUSTED_PRIVATE_OUTPUT"

    def recovered(messages):
        assert secret not in json.dumps(messages)
        return good_render()

    install(monkeypatch, render_chain, [bad, recovered, bad])

    def validate(parsed):
        if parsed["message_body"] == "bad":
            raise AISchemaValidationError(secret, raw_content=secret)

    await ai_agent_groq.ask_event_alert_render_raw(input_payload(), schema_check=validate)


@pytest.mark.asyncio
async def test_single_openai_provider_invalid_output_does_not_add_a_paid_request(monkeypatch):
    monkeypatch.setenv("LLM_EVENT_RENDER_PROVIDERS", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "fake")
    monkeypatch.setenv("OPENAI_ENABLED", "true")
    monkeypatch.setenv("LLM_BREAKER_ENABLED", "false")
    from bot.services.llm.config import provider_attempts

    registry = install(monkeypatch, provider_attempts("event_alert_render"), ["not json"])
    with pytest.raises(AIInvalidJsonError):
        await call_render()
    assert len(registry["openai"].calls) == 1


@pytest.mark.asyncio
async def test_fallback_guidance_is_accounted_in_real_openai_provider_admission(
    monkeypatch, render_chain,
):
    from bot.services.llm.base_provider import openai_budget
    from bot.services.llm.openai_provider import OpenAIProvider
    from bot.services.llm.operation import current_llm_operation_id
    from bot.services.llm.telemetry import message_input_chars

    groq = FakeProvider("groq", {render_chain[0][1]: "not json"})
    reserve = AsyncMock(return_value=object())
    monkeypatch.setattr(openai_budget, "reserve", reserve)
    monkeypatch.setattr(openai_budget, "settle", AsyncMock())
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=good_render()))],
        usage={"prompt_tokens": 50, "completion_tokens": 20},
    )
    create = AsyncMock(return_value=response)
    client = SimpleNamespace(chat=SimpleNamespace(
        completions=SimpleNamespace(with_raw_response=None, create=create)
    ))
    provider = OpenAIProvider()
    monkeypatch.setattr(provider, "get_client", lambda: client)
    monkeypatch.setattr(
        ai_agent_groq, "get_router", lambda: LLMRouter(registry={"groq": groq, "openai": provider})
    )
    rows = []

    async def record_usage(**kwargs):
        rows.append((current_llm_operation_id(), kwargs))
        return 1

    monkeypatch.setattr(ai_agent_groq, "write_llm_usage_log", record_usage)
    await call_render()
    assert create.await_count == reserve.await_count == 1
    sent_messages = create.await_args.kwargs["messages"]
    assert message_input_chars(sent_messages) > message_input_chars(groq.messages[0])
    assert reserve.await_args.kwargs["input_chars"] == message_input_chars(sent_messages)
    assert len(rows) == 2 and rows[0][0] == rows[1][0] and rows[0][0] is not None
    assert rows[1][1]["input_chars"] == message_input_chars(sent_messages)


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
    assert [len(registry[name].calls) for name in ("groq", "openai", "cloudflare")] == [1, 1, 1]


@pytest.mark.asyncio
@pytest.mark.parametrize("other_failure", [
    ProviderError(429, "rate_limit"), asyncio.TimeoutError(),
    ProviderError(503), ProviderError(404, "model_not_found"),
])
async def test_mixed_provider_failures_never_enable_deterministic_recovery(
    monkeypatch, render_chain, other_failure,
):
    answers = ["not json", other_failure, "not json either"]
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
    ] * 3)
    with pytest.raises(AISchemaValidationError) as caught:
        await call_render()
    assert caught.value._llm_all_exhausted_attempts_invalid_output is True


@pytest.mark.asyncio
async def test_bad_request_aborts_without_calling_fallback(
    monkeypatch, render_chain,
):
    registry = install(monkeypatch, render_chain, [
        ProviderError(400, "invalid_request_error"), good_render(), good_render()
    ])
    with pytest.raises(ProviderError) as caught:
        await call_render()
    assert classify_ai_error_reason(caught.value) == "provider_bad_request"
    assert [len(registry[name].calls) for name in ("groq", "openai", "cloudflare")] == [1, 0, 0]


@pytest.mark.asyncio
async def test_no_configured_providers_is_terminal(monkeypatch, render_chain):
    for key in ("GROQ_API_KEY", "CLOUDFLARE_API_TOKEN", "OPENAI_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("OPENAI_ENABLED", "false")
    install(monkeypatch, render_chain, [good_render()] * 3)
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
@pytest.mark.parametrize("winner", [0, 1, 2])
async def test_full_factual_validation_at_each_fallback_before_allowed_outcome(
    monkeypatch, render_chain, winner,
):
    invalid_claim = json.dumps({
        "message_body": "BTC rose 40% over the last 3 hours.",
        "related_news_ids": [], "possible_action": "Watch the next move.",
    })
    responses = [invalid_claim] * winner + [good_render()] + [
        AssertionError("provider after winner should not be called")
    ] * (2 - winner)
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
async def test_repair_guidance_recovers_one_shared_positive_after_two_invalid_responses(
    monkeypatch, render_chain,
):
    wrong_direction = json.dumps({
        "message_body": "The short-term rise follows the broader 24-hour rise.",
        "related_news_ids": [], "possible_action": "Watch the next move.",
    })

    def still_wrong(messages):
        assert "period_direction_mismatch" in messages[-1]["content"]
        return wrong_direction

    def corrected(messages):
        assert "period_direction_mismatch" in messages[-1]["content"]
        return good_render()

    registry = install(monkeypatch, render_chain, [wrong_direction, still_wrong, corrected])
    significance_call, render_outcome, delivery_outcome = patch_significance_and_storage(
        monkeypatch
    )
    decision, analysis_id = await alerts._create_event_analysis_decision(input_payload())

    assert analysis_id == 42 and decision is not None and decision.should_alert
    assert decision.message_body == json.loads(good_render())["message_body"]
    significance_call.assert_awaited_once()
    assert render_outcome.await_args.kwargs["status"] == "success"
    assert delivery_outcome.await_args.kwargs["status"] == alerts.OUTCOME_ALLOWED
    assert sum(len(provider.calls) for provider in registry.values()) == 3


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

    assert decision is None and analysis_id is None
    assert render_outcome.await_args.kwargs["status"] == "llm_error"
    assert delivery_outcome.await_args.kwargs["status"] == alerts.OUTCOME_FAILED
    assert delivery_outcome.await_args.kwargs["reason_code"] == alerts.REASON_LLM_INVALID_RESPONSE
    significance_call.assert_awaited_once()
    assert sum(len(provider.calls) for provider in registry.values()) == 3
