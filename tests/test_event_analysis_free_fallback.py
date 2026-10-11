"""Event Analysis provider redundancy, no live external requests."""

import asyncio
from types import SimpleNamespace

import pytest

from bot.services.llm import breaker, config, telemetry
from bot.services.llm.base_provider import BaseProvider, ProviderResult
from bot.services.llm.errors import AIProviderRateLimitError, AllProvidersFailedError
from bot.services.llm.router import LLMRouter


class StubProvider(BaseProvider):
    def __init__(self, name, outcome):
        self.name = name
        self.outcome = outcome
        self.calls = []

    async def chat_completion(
        self, *, call_type, symbol, model, messages, max_tokens,
        response_format, timeout=15, reasoning_effort=None,
    ):
        self.calls.append((call_type, model))
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return ProviderResult(
            provider=self.name, model=model, raw_content='{"should_alert": false}',
            input_chars=8,
        )


def _http_error(status, *, code=None):
    error = RuntimeError("synthetic provider refusal")
    error.status_code = status
    if code:
        error.body = {"error": {"code": code}}
    error.response = SimpleNamespace(status_code=status, headers={})
    return error


def _configure(monkeypatch, providers):
    monkeypatch.setenv("LLM_EVENT_PROVIDERS", ",".join(providers))
    for name in ("groq", "gemini", "cloudflare"):
        key = config.api_key_env(name)
        if name in providers:
            monkeypatch.setenv(key, "fake-test-key")
        else:
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "test-account")


async def _event_call(router):
    return await router.chat_completion(
        call_type="event_analysis",
        messages=[{"role": "user", "content": "fixed sample"}],
        max_tokens=300,
        response_format={"type": "json_object"},
    )


@pytest.fixture(autouse=True)
def _reset_state():
    breaker.reset_breakers()
    telemetry.reset_llm_rate_limit_backoffs()
    yield
    breaker.reset_breakers()
    telemetry.reset_llm_rate_limit_backoffs()


def test_event_default_adds_optional_cloudflare_without_changing_other_tasks(monkeypatch):
    monkeypatch.delenv("LLM_EVENT_PROVIDERS", raising=False)
    monkeypatch.delenv("LLM_PROVIDER_PRIORITY", raising=False)
    assert config.provider_priority("event_analysis") == ["groq", "gemini", "cloudflare"]
    assert config.provider_priority("daily_report") == ["groq", "gemini"]


def test_explicit_global_and_event_priority_remain_authoritative(monkeypatch):
    monkeypatch.delenv("LLM_EVENT_PROVIDERS", raising=False)
    monkeypatch.setenv("LLM_PROVIDER_PRIORITY", "gemini,groq")
    assert config.provider_priority("event_analysis") == ["gemini", "groq"]
    monkeypatch.setenv("LLM_EVENT_PROVIDERS", "groq,cloudflare")
    assert config.provider_priority("event_analysis") == ["groq", "cloudflare"]


def test_retired_provider_cannot_be_enabled_even_with_legacy_keys(monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "unused-legacy-key")
    monkeypatch.setenv("MISTRAL_MODEL", "unused-legacy-model")
    monkeypatch.setenv("LLM_PROVIDER_PRIORITY", "groq,mistral,gemini")
    monkeypatch.setenv("LLM_EVENT_PROVIDERS", "mistral,cloudflare,groq")
    assert config.KNOWN_PROVIDERS == {"groq", "gemini", "cloudflare"}
    assert config.api_key("mistral") is None
    assert config.global_provider_priority() == ["groq", "gemini"]
    assert config.provider_priority("event_analysis") == ["cloudflare", "groq"]


@pytest.mark.asyncio
async def test_cloudflare_success_preserves_serving_provider_and_model(monkeypatch):
    _configure(monkeypatch, ["groq", "gemini", "cloudflare"])
    groq = StubProvider("groq", AIProviderRateLimitError("429", provider="groq"))
    gemini = StubProvider("gemini", asyncio.TimeoutError())
    cloudflare = StubProvider("cloudflare", None)
    result = await _event_call(LLMRouter(registry={
        "groq": groq, "gemini": gemini, "cloudflare": cloudflare,
    }))
    assert result.provider == "cloudflare"
    assert result.model == config.model_for("cloudflare", "event_analysis")
    assert groq.calls and gemini.calls and cloudflare.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [
    AIProviderRateLimitError("429", provider="cloudflare"),
    _http_error(404, code="model_not_found"),
])
async def test_cloudflare_failure_advances_no_further_when_last(monkeypatch, error):
    _configure(monkeypatch, ["cloudflare"])
    cloudflare = StubProvider("cloudflare", error)
    with pytest.raises((AIProviderRateLimitError, AllProvidersFailedError)):
        await _event_call(LLMRouter(registry={"cloudflare": cloudflare}))
    assert len(cloudflare.calls) == 1


@pytest.mark.asyncio
async def test_cloudflare_json_mode_output_rejection_reaches_next_gemini(monkeypatch):
    _configure(monkeypatch, ["cloudflare", "gemini"])
    error = _http_error(400, code="invalid_request_error")
    error.args = ("JSON Mode couldn't be met",)
    assert telemetry.classify_ai_error_reason(error) == "provider_json_validate_failed"
    cloudflare = StubProvider("cloudflare", error)
    gemini = StubProvider("gemini", None)
    result = await _event_call(LLMRouter(registry={"cloudflare": cloudflare, "gemini": gemini}))
    assert result.provider == "gemini"
    assert len(cloudflare.calls) == len(gemini.calls) == 1


@pytest.mark.asyncio
async def test_cloudflare_credentials_are_optional(monkeypatch):
    _configure(monkeypatch, ["groq", "cloudflare"])
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID")
    groq = StubProvider("groq", None)
    cloudflare = StubProvider("cloudflare", RuntimeError("should be excluded"))
    result = await _event_call(LLMRouter(registry={"groq": groq, "cloudflare": cloudflare}))
    assert result.provider == "groq"
    assert cloudflare.calls == []


@pytest.mark.asyncio
async def test_mixed_rate_limit_and_timeout_remains_terminal(monkeypatch):
    _configure(monkeypatch, ["gemini", "cloudflare"])
    router = LLMRouter(registry={
        "gemini": StubProvider("gemini", AIProviderRateLimitError("429", provider="gemini")),
        "cloudflare": StubProvider("cloudflare", asyncio.TimeoutError()),
    })
    with pytest.raises(AllProvidersFailedError) as caught:
        await _event_call(router)
    assert caught.value.mixed_failure is True
    assert telemetry.classify_ai_error_reason(caught.value) == "mixed_provider_failures"


@pytest.mark.asyncio
async def test_every_provider_429_is_terminal_rate_limit(monkeypatch):
    _configure(monkeypatch, ["gemini", "cloudflare"])
    router = LLMRouter(registry={
        "gemini": StubProvider("gemini", AIProviderRateLimitError("429", provider="gemini")),
        "cloudflare": StubProvider(
            "cloudflare", AIProviderRateLimitError("429", provider="cloudflare")
        ),
    })
    with pytest.raises(AIProviderRateLimitError):
        await _event_call(router)
