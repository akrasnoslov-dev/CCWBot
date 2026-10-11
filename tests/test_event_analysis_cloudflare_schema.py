"""Cloudflare Event Analysis schema contract and synthetic offline failures.

No production responses, credentials, external inference, or network calls.
These tests establish request-shape and fail-closed behavior, NOT live model quality.
"""

import json

import pytest

import bot.services.ai_agent_groq as agent
from bot.alerting.event_analysis import (
    EventAnalysisValidationError,
    validate_event_significance_output,
)
from bot.services.llm import config
from bot.services.llm.base_provider import BaseProvider, ProviderResult
from bot.services.llm.errors import AIInvalidJsonError, AISchemaValidationError
from bot.services.llm.operation import current_llm_operation_id, llm_operation_scope
from bot.services.llm.router import LLMRouter


_VALID = {
    "symbol": "BTC",
    "materiality": "routine",
    "novelty": "unclear",
    "should_alert": False,
    "reason_code": "routine_move",
    "confidence": "medium",
}


class RecordedProvider(BaseProvider):
    def __init__(self, name, content):
        self.name = name
        self.content = content
        self.calls = []

    async def chat_completion(self, **kwargs):
        self.calls.append((kwargs, current_llm_operation_id()))
        return ProviderResult(
            provider=self.name,
            model=kwargs["model"],
            raw_content=self.content,
            input_chars=100,
        )


def _schema_check(parsed):
    try:
        validate_event_significance_output(parsed, expected_symbol="BTC")
    except EventAnalysisValidationError as error:
        raise AISchemaValidationError(str(error)) from error


def _configure(monkeypatch, providers=("cloudflare",)):
    monkeypatch.setenv("GROQ_JSON_MODE", "true")
    monkeypatch.setenv("LLM_EVENT_PROVIDERS", ",".join(providers))
    monkeypatch.delenv("CLOUDFLARE_MODEL", raising=False)
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "synthetic-token-not-real")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "synthetic-account")
    if "gemini" in providers:
        monkeypatch.setenv("GEMINI_API_KEY", "synthetic-key-not-real")


def test_cloudflare_gets_bare_json_schema_not_groq_envelope(monkeypatch):
    _configure(monkeypatch, ("groq", "gemini", "cloudflare"))
    fmt, overrides = agent._structured_response_formats(
        call_type="event_analysis",
        schema_name="event_significance",
        schema=agent._EVENT_SIGNIFICANCE_JSON_SCHEMA,
    )
    cloudflare_model = config.model_for("cloudflare", "event_analysis")
    groq_model = config.model_for("groq", "event_analysis")

    assert fmt == {"type": "json_object"}
    assert overrides[f"cloudflare:{cloudflare_model}"] == {
        "type": "json_schema",
        "json_schema": agent._EVENT_SIGNIFICANCE_JSON_SCHEMA,
    }
    assert list(overrides[f"cloudflare:{cloudflare_model}"]["json_schema"]["required"]) == [
        "symbol", "materiality", "novelty", "should_alert", "reason_code", "confidence",
    ]
    assert overrides[f"cloudflare:{cloudflare_model}"]["json_schema"]["additionalProperties"] is False
    assert overrides[f"groq:{groq_model}"]["json_schema"]["strict"] is True
    assert "gemini" not in overrides


def test_cloudflare_override_only_on_supported_event_model(monkeypatch):
    _configure(monkeypatch)
    schema = agent._EVENT_SIGNIFICANCE_JSON_SCHEMA
    _, overrides = agent._structured_response_formats(
        call_type="event_analysis", schema_name="event_significance", schema=schema
    )
    assert overrides is not None
    monkeypatch.setenv("CLOUDFLARE_MODEL", "@cf/unsupported-test-model")
    fmt, overrides = agent._structured_response_formats(
        call_type="event_analysis", schema_name="event_significance", schema=schema
    )
    assert fmt == {"type": "json_object"}
    assert overrides is None


def test_render_and_json_mode_disabled_are_unchanged(monkeypatch):
    _configure(monkeypatch)
    fmt, overrides = agent._structured_response_formats(
        call_type="event_alert_render",
        schema_name="event_alert_render",
        schema=agent._EVENT_ALERT_RENDER_JSON_SCHEMA,
    )
    assert fmt == {"type": "json_object"}
    assert not overrides or not any(key.startswith("cloudflare:") for key in overrides)

    monkeypatch.setenv("GROQ_JSON_MODE", "false")
    assert agent._structured_response_formats(
        call_type="event_analysis",
        schema_name="event_significance",
        schema=agent._EVENT_SIGNIFICANCE_JSON_SCHEMA,
    ) == (None, None)


@pytest.mark.asyncio
async def test_cloudflare_uses_schema_and_keeps_one_logical_call(monkeypatch):
    _configure(monkeypatch)
    cloudflare = RecordedProvider("cloudflare", json.dumps(_VALID))
    router = LLMRouter(registry={"cloudflare": cloudflare})
    monkeypatch.setattr(agent, "get_router", lambda: router)

    with llm_operation_scope("synthetic-operation"):
        result = await agent.ask_event_significance_raw(
            {"symbol": "BTC", "market": {}, "news": []}, schema_check=_schema_check
        )

    assert result.provider == "cloudflare"
    assert result[1] == _VALID
    assert len(cloudflare.calls) == 1
    kwargs, operation_id = cloudflare.calls[0]
    assert operation_id == "synthetic-operation"
    assert kwargs["response_format"]["json_schema"] == agent._EVENT_SIGNIFICANCE_JSON_SCHEMA
    assert kwargs["max_tokens"] == config.max_tokens_for("event_analysis")
    assert kwargs["call_type"] == "event_analysis"


# Synthetic categories, not a claim about which categories occurred in production.
_INVALID_CASES = [
    ("truncated_json", '{"symbol":"BTC"', AIInvalidJsonError),
    ("missing_decision_field", json.dumps({key: val for key, val in _VALID.items() if key != "should_alert"}), AISchemaValidationError),
    ("incorrect_boolean_type", json.dumps({**_VALID, "should_alert": "false"}), AISchemaValidationError),
    ("incorrect_enum_type", json.dumps({**_VALID, "confidence": 42}), AISchemaValidationError),
    ("invalid_enum_value", json.dumps({**_VALID, "novelty": "probably_new"}), AISchemaValidationError),
    ("wrong_symbol", json.dumps({**_VALID, "symbol": "ETH"}), AISchemaValidationError),
    ("conflicting_polarity", json.dumps({**_VALID, "reason_code": "unusual_move"}), AISchemaValidationError),
    ("positive_without_materiality", json.dumps({
        **_VALID, "should_alert": True, "reason_code": "fast_move", "novelty": "new"
    }), AISchemaValidationError),
    ("news_only_positive", json.dumps({
        **_VALID, "should_alert": True, "materiality": "material",
        "novelty": "new", "reason_code": "news_only",
    }), AISchemaValidationError),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("category", "output", "expected_error"), _INVALID_CASES)
async def test_offline_invalid_categories_still_fail_closed(
    monkeypatch, category, output, expected_error
):
    _configure(monkeypatch)
    cloudflare = RecordedProvider("cloudflare", output)
    monkeypatch.setattr(agent, "get_router", lambda: LLMRouter(
        registry={"cloudflare": cloudflare}
    ))

    with pytest.raises(expected_error):
        await agent.ask_event_significance_raw(
            {"symbol": "BTC", "market": {}, "news": []}, schema_check=_schema_check
        )
    assert len(cloudflare.calls) == 1, category


@pytest.mark.asyncio
async def test_invalid_cloudflare_output_falls_back_without_new_operation(monkeypatch):
    _configure(monkeypatch, ("cloudflare", "gemini"))
    cloudflare = RecordedProvider("cloudflare", json.dumps({
        **_VALID, "should_alert": "false"
    }))
    gemini = RecordedProvider("gemini", json.dumps(_VALID))
    monkeypatch.setattr(agent, "get_router", lambda: LLMRouter(
        registry={"cloudflare": cloudflare, "gemini": gemini}
    ))

    with llm_operation_scope("same-synthetic-operation"):
        result = await agent.ask_event_significance_raw(
            {"symbol": "BTC", "market": {}, "news": []}, schema_check=_schema_check
        )
    assert result.provider == "gemini"
    assert len(cloudflare.calls) == len(gemini.calls) == 1
    assert cloudflare.calls[0][1] == gemini.calls[0][1] == "same-synthetic-operation"
    assert gemini.calls[0][0]["response_format"] == {"type": "json_object"}
