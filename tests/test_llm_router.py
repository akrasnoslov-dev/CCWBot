"""Router fallback behaviour with mocked providers (no real provider calls)."""

import asyncio
import json

import pytest

from bot.services.llm import config
from bot.services.llm.base_provider import BaseProvider, ProviderResult
from bot.services.llm.errors import (
    AIInvalidJsonError,
    AIProviderRateLimitError,
    AISchemaValidationError,
    AllProvidersFailedError,
    LLMRateLimitBackoffActive,
)
from bot.services.llm.router import LLMRouter
from bot.services.llm.telemetry import classify_ai_error_reason


class FakeProvider(BaseProvider):
    def __init__(self, name, behavior):
        self.name = name
        self._behavior = behavior
        self.calls = 0
        self.last_reasoning_effort = None

    async def chat_completion(self, *, call_type, symbol, model, messages, max_tokens,
                              response_format, timeout=15, reasoning_effort=None):
        self.calls += 1
        self.last_reasoning_effort = reasoning_effort
        behavior = self._behavior
        if isinstance(behavior, BaseException):
            raise behavior
        if callable(behavior):
            return behavior(name=self.name, model=model)
        return behavior


def _result(name, model="m"):
    return ProviderResult(provider=name, model=model, raw_content="{}", input_chars=1)


def _http_error(status_code):
    err = RuntimeError(f"status {status_code}")
    err.status_code = status_code
    return err


def _configure(monkeypatch, priority, keys):
    monkeypatch.setenv("LLM_PROVIDER_PRIORITY", ",".join(priority))
    for provider in ("groq", "gemini", "mistral"):
        env = config.api_key_env(provider)
        if provider in keys:
            monkeypatch.setenv(env, f"{provider}-key")
        else:
            monkeypatch.delenv(env, raising=False)


async def _call(router, call_type="event_analysis"):
    return await router.chat_completion(
        call_type=call_type,
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=10,
        response_format=None,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_name", ["groq", "gemini", "mistral"])
async def test_success_through_each_provider(monkeypatch, provider_name):
    _configure(monkeypatch, [provider_name], {provider_name})
    provider = FakeProvider(provider_name, lambda name, model: _result(name, model))
    router = LLMRouter(registry={provider_name: provider})

    result = await _call(router)

    assert result.provider == provider_name
    assert provider.calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure",
    [
        AIProviderRateLimitError("429", provider="groq", model="m"),
        asyncio.TimeoutError(),
        _http_error(503),
        _http_error(401),  # auth_error -> unusable provider, advance
        RuntimeError("connection failed"),  # network_error -> advance
    ],
)
async def test_fallback_to_next_provider(monkeypatch, failure):
    _configure(monkeypatch, ["groq", "gemini"], {"groq", "gemini"})
    groq = FakeProvider("groq", failure)
    gemini = FakeProvider("gemini", lambda name, model: _result(name, model))
    router = LLMRouter(registry={"groq": groq, "gemini": gemini})

    result = await _call(router)

    assert result.provider == "gemini"
    assert groq.calls == 1
    assert gemini.calls == 1


@pytest.mark.asyncio
async def test_all_providers_rate_limited_raises_rate_limit(monkeypatch):
    _configure(monkeypatch, ["groq", "gemini"], {"groq", "gemini"})
    router = LLMRouter(
        registry={
            "groq": FakeProvider("groq", AIProviderRateLimitError("429", provider="groq")),
            "gemini": FakeProvider(
                "gemini", AIProviderRateLimitError("429", provider="gemini")
            ),
        }
    )

    with pytest.raises(AIProviderRateLimitError):
        await _call(router)


@pytest.mark.asyncio
async def test_all_providers_timeout_raises_all_failed(monkeypatch):
    _configure(monkeypatch, ["groq", "gemini"], {"groq", "gemini"})
    router = LLMRouter(
        registry={
            "groq": FakeProvider("groq", asyncio.TimeoutError()),
            "gemini": FakeProvider("gemini", _http_error(500)),
        }
    )

    with pytest.raises(AllProvidersFailedError):
        await _call(router)


@pytest.mark.asyncio
async def test_all_providers_in_backoff_raises_backoff_active(monkeypatch):
    from datetime import datetime, timezone

    _configure(monkeypatch, ["groq", "gemini"], {"groq", "gemini"})
    until = datetime.now(timezone.utc)
    router = LLMRouter(
        registry={
            "groq": FakeProvider(
                "groq", LLMRateLimitBackoffActive(provider="groq", model="m", limited_until=until)
            ),
            "gemini": FakeProvider(
                "gemini",
                LLMRateLimitBackoffActive(provider="gemini", model="m", limited_until=until),
            ),
        }
    )

    with pytest.raises(LLMRateLimitBackoffActive):
        await _call(router)


@pytest.mark.asyncio
async def test_deterministic_error_is_not_retried(monkeypatch):
    _configure(monkeypatch, ["groq", "gemini"], {"groq", "gemini"})
    groq = FakeProvider("groq", _http_error(400))
    gemini = FakeProvider("gemini", lambda name, model: _result(name, model))
    router = LLMRouter(registry={"groq": groq, "gemini": gemini})

    with pytest.raises(RuntimeError):
        await _call(router)
    assert gemini.calls == 0  # 4xx is deterministic; do not fall through


@pytest.mark.asyncio
async def test_provider_without_api_key_is_excluded(monkeypatch):
    # gemini has no key, so it is excluded even though it is next in priority.
    _configure(monkeypatch, ["groq", "gemini"], {"groq"})
    groq = FakeProvider("groq", lambda name, model: _result(name, model))
    gemini = FakeProvider("gemini", RuntimeError("should not be called"))
    router = LLMRouter(registry={"groq": groq, "gemini": gemini})

    result = await _call(router)

    assert result.provider == "groq"
    assert gemini.calls == 0


@pytest.mark.asyncio
async def test_no_configured_providers_raises_all_failed(monkeypatch):
    _configure(monkeypatch, ["groq"], set())
    router = LLMRouter(registry={"groq": FakeProvider("groq", RuntimeError("x"))})

    with pytest.raises(AllProvidersFailedError):
        await _call(router)


def test_provider_priority_per_call_type_override(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER_PRIORITY", "groq,gemini")
    monkeypatch.setenv("LLM_EVENT_PROVIDERS", "mistral,groq")
    assert config.provider_priority("event_analysis") == ["mistral", "groq"]
    # Report/heartbeat with no override fall back to the global priority.
    assert config.provider_priority("daily_report") == ["groq", "gemini"]


def test_provider_priority_filters_unknown_tokens(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER_PRIORITY", "foo, cerebras, groq , bar,gemini")
    monkeypatch.delenv("LLM_EVENT_PROVIDERS", raising=False)
    assert config.provider_priority("event_analysis") == ["groq", "gemini"]


def test_retired_provider_is_not_configurable_or_registered(monkeypatch, caplog):
    monkeypatch.setenv("LLM_PROVIDER_PRIORITY", "cerebras")

    with caplog.at_level("WARNING", logger="bot.services.llm.env"):
        assert config.global_provider_priority() == ["groq", "gemini", "mistral"]

    assert config.api_key_env("cerebras") is None
    assert config.api_key("cerebras") is None
    assert config.base_url("cerebras") is None
    assert config.model_for("cerebras", "event_analysis") == ""
    assert "cerebras" not in LLMRouter()._registry
    assert any("LLM_PROVIDER_PRIORITY" in record.getMessage() for record in caplog.records)


def test_provider_priority_defaults_when_unset(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER_PRIORITY", raising=False)
    monkeypatch.delenv("LLM_EVENT_PROVIDERS", raising=False)
    assert config.provider_priority("event_analysis") == ["groq", "gemini", "mistral"]


def test_model_for_resolves_per_provider(monkeypatch):
    monkeypatch.delenv("GROQ_MARKET_HEARTBEAT_MODEL", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    assert config.model_for("groq", "market_heartbeat") == "openai/gpt-oss-20b"
    assert config.model_for("gemini", "daily_report") == "gemini-2.5-flash"
    monkeypatch.setenv("GEMINI_MODEL", "custom-gemini")
    assert config.model_for("gemini", "event_analysis") == "custom-gemini"


@pytest.mark.asyncio
async def test_backoff_skip_then_next_provider_succeeds(monkeypatch):
    # The feature's core payoff: a provider already in active backoff is skipped (no HTTP call)
    # and the next configured provider answers.
    from datetime import datetime, timezone

    _configure(monkeypatch, ["groq", "gemini"], {"groq", "gemini"})
    groq = FakeProvider(
        "groq",
        LLMRateLimitBackoffActive(
            provider="groq", model="m", limited_until=datetime.now(timezone.utc)
        ),
    )
    gemini = FakeProvider("gemini", lambda name, model: _result(name, model))
    router = LLMRouter(registry={"groq": groq, "gemini": gemini})

    result = await _call(router)

    assert result.provider == "gemini"
    assert groq.calls == 1  # the skip still counts as one chat_completion invocation
    assert gemini.calls == 1


@pytest.mark.asyncio
async def test_mixed_timeout_and_rate_limit_remains_a_terminal_failure(monkeypatch):
    # A late 429 does not erase the earlier timeout from this exhausted logical call.
    _configure(monkeypatch, ["groq", "gemini"], {"groq", "gemini"})
    router = LLMRouter(
        registry={
            "groq": FakeProvider("groq", asyncio.TimeoutError()),
            "gemini": FakeProvider(
                "gemini", AIProviderRateLimitError("429", provider="gemini")
            ),
        }
    )

    with pytest.raises(AllProvidersFailedError) as raised:
        await _call(router)
    assert raised.value.mixed_failure is True
    assert classify_ai_error_reason(raised.value) == "mixed_provider_failures"


@pytest.mark.asyncio
async def test_mixed_prebackoff_and_live_rate_limit_raises_rate_limit(monkeypatch):
    # First provider is in active backoff (skip), second returns a live 429. Because a real
    # attempt happened, this is NOT only-pre-backoff, so it surfaces as a rate-limit error
    # (recorded as a failure), not skipped_due_to_rate_limit.
    from datetime import datetime, timezone

    _configure(monkeypatch, ["groq", "gemini"], {"groq", "gemini"})
    router = LLMRouter(
        registry={
            "groq": FakeProvider(
                "groq",
                LLMRateLimitBackoffActive(
                    provider="groq", model="m", limited_until=datetime.now(timezone.utc)
                ),
            ),
            "gemini": FakeProvider(
                "gemini", AIProviderRateLimitError("429", provider="gemini")
            ),
        }
    )

    with pytest.raises(AIProviderRateLimitError):
        await _call(router)


@pytest.mark.asyncio
async def test_mixed_rate_limit_and_timeout_raises_all_failed(monkeypatch):
    # A 429 from Groq is provider pressure, but does not make the logical call terminally
    # rate-limited after later fallbacks time out.
    _configure(monkeypatch, ["groq", "gemini", "mistral"], {"groq", "gemini", "mistral"})
    router = LLMRouter(
        registry={
            "groq": FakeProvider("groq", AIProviderRateLimitError("429", provider="groq")),
            "gemini": FakeProvider("gemini", asyncio.TimeoutError()),
            "mistral": FakeProvider("mistral", asyncio.TimeoutError()),
        }
    )

    with pytest.raises(AllProvidersFailedError) as raised:
        await _call(router)
    assert isinstance(raised.value.last_error, asyncio.TimeoutError)
    assert raised.value.rate_limited is False
    assert raised.value.mixed_failure is True
    assert classify_ai_error_reason(raised.value) == "mixed_provider_failures"


def _content_result(name, model="m", content="{}"):
    return ProviderResult(provider=name, model=model, raw_content=content, input_chars=1)


async def _parse_json_validate(result):
    try:
        parsed = json.loads(result.raw_content)
    except json.JSONDecodeError as error:
        raise AIInvalidJsonError(str(error), raw_content=result.raw_content) from error
    return (result.provider, parsed)


async def _call_validated(router, validate, call_type="event_analysis"):
    return await router.chat_completion(
        call_type=call_type,
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=10,
        response_format=None,
        validate_response=validate,
    )


@pytest.mark.asyncio
async def test_invalid_json_output_advances_to_next_provider(monkeypatch):
    # The production 2026-07-10 case: primary switched out on 5xx is one thing, but a
    # provider that answers with unparseable JSON must also advance the chain.
    _configure(monkeypatch, ["groq", "gemini"], {"groq", "gemini"})
    groq = FakeProvider("groq", lambda name, model: _content_result(name, model, "not json"))
    gemini = FakeProvider(
        "gemini", lambda name, model: _content_result(name, model, '{"ok": true}')
    )
    router = LLMRouter(registry={"groq": groq, "gemini": gemini})

    provider, parsed = await _call_validated(router, _parse_json_validate)

    assert provider == "gemini"
    assert parsed == {"ok": True}
    assert groq.calls == 1
    assert gemini.calls == 1


@pytest.mark.asyncio
async def test_all_providers_invalid_json_raises_last_invalid_error(monkeypatch):
    # Exhaustion keeps the AIInvalidJsonError contract, and the chain is bounded to one
    # full pass: each provider is attempted exactly once for this logical call.
    _configure(monkeypatch, ["groq", "gemini"], {"groq", "gemini"})
    groq = FakeProvider("groq", lambda name, model: _content_result(name, model, "not json"))
    gemini = FakeProvider(
        "gemini", lambda name, model: _content_result(name, model, "also not json")
    )
    router = LLMRouter(registry={"groq": groq, "gemini": gemini})

    with pytest.raises(AIInvalidJsonError) as raised:
        await _call_validated(router, _parse_json_validate)

    assert raised.value.raw_content == "also not json"
    assert groq.calls == 1
    assert gemini.calls == 1


@pytest.mark.asyncio
async def test_schema_validation_failure_advances_to_next_provider(monkeypatch):
    _configure(monkeypatch, ["groq", "gemini"], {"groq", "gemini"})
    groq = FakeProvider(
        "groq", lambda name, model: _content_result(name, model, '{"wrong_schema": true}')
    )
    gemini = FakeProvider(
        "gemini", lambda name, model: _content_result(name, model, '{"symbol": "BTC"}')
    )
    router = LLMRouter(registry={"groq": groq, "gemini": gemini})

    async def _schema_validate(result):
        parsed = json.loads(result.raw_content)
        if "symbol" not in parsed:
            raise AISchemaValidationError("missing fields: ['symbol']")
        return (result.provider, parsed)

    provider, parsed = await _call_validated(router, _schema_validate)

    assert provider == "gemini"
    assert parsed == {"symbol": "BTC"}
    assert groq.calls == 1
    assert gemini.calls == 1


@pytest.mark.asyncio
async def test_invalid_output_then_rate_limit_exhaustion_raises_invalid_error(monkeypatch):
    # Mixed exhaustion: invalid output was seen, so the invalid-output error wins and the
    # caller reaches its deterministic-fallback handling instead of a rate-limit path.
    _configure(monkeypatch, ["groq", "gemini"], {"groq", "gemini"})
    router = LLMRouter(
        registry={
            "groq": FakeProvider(
                "groq", lambda name, model: _content_result(name, model, "not json")
            ),
            "gemini": FakeProvider(
                "gemini", AIProviderRateLimitError("429", provider="gemini")
            ),
        }
    )

    with pytest.raises(AIInvalidJsonError):
        await _call_validated(router, _parse_json_validate)


def test_safe_error_message_redacts_secret_fragments():
    from bot.services.llm.telemetry import safe_error_message

    msg = safe_error_message(
        RuntimeError("Incorrect API key provided: sk-abcd1234efgh. Authorization: Bearer zzz9999")
    )
    assert "sk-abcd1234efgh" not in msg
    assert "Bearer zzz9999" not in msg
    assert "[redacted]" in msg
