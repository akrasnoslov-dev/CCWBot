"""Free-tier Event Analysis redundancy: mocked providers, no external API calls."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.services.llm import breaker, config, telemetry
from bot.services.llm.base_provider import BaseProvider, ProviderResult
from bot.services.llm.errors import AIProviderRateLimitError, AllProvidersFailedError
from bot.services.llm.mistral_provider import MistralProvider
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


def _http_error(status, *, code=None, retry_after=None):
    error = RuntimeError("synthetic provider refusal")
    error.status_code = status
    if code:
        error.body = {"error": {"code": code}}
    error.response = SimpleNamespace(
        status_code=status,
        headers={"retry-after": retry_after} if retry_after else {},
    )
    return error


def _configure(monkeypatch, providers):
    monkeypatch.setenv("LLM_EVENT_PROVIDERS", ",".join(providers))
    for name in ("groq", "gemini", "mistral", "cloudflare"):
        key = config.api_key_env(name)
        if name in providers:
            monkeypatch.setenv(key, "fake-test-key")
        else:
            monkeypatch.delenv(key, raising=False)
    if "cloudflare" in providers:
        monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "fake-account")
    else:
        monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)


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
    assert config.provider_priority("event_analysis") == [
        "groq", "gemini", "cloudflare", "mistral"
    ]
    assert config.provider_priority("daily_report") == ["groq", "gemini", "mistral"]


def test_explicit_global_and_event_priority_remain_authoritative(monkeypatch):
    monkeypatch.delenv("LLM_EVENT_PROVIDERS", raising=False)
    monkeypatch.setenv("LLM_PROVIDER_PRIORITY", "mistral,groq")
    assert config.provider_priority("event_analysis") == ["mistral", "groq"]
    monkeypatch.setenv("LLM_EVENT_PROVIDERS", "groq,mistral,cloudflare")
    assert config.provider_priority("event_analysis") == [
        "groq", "mistral", "cloudflare"
    ]


@pytest.mark.asyncio
async def test_cloudflare_success_preserves_serving_provider_and_model(monkeypatch):
    _configure(monkeypatch, ["groq", "gemini", "cloudflare", "mistral"])
    groq = StubProvider("groq", AIProviderRateLimitError("429", provider="groq"))
    gemini = StubProvider("gemini", asyncio.TimeoutError())
    cloudflare = StubProvider("cloudflare", None)
    mistral = StubProvider("mistral", RuntimeError("must not run"))
    result = await _event_call(LLMRouter(registry={
        "groq": groq, "gemini": gemini, "cloudflare": cloudflare, "mistral": mistral,
    }))
    assert result.provider == "cloudflare"
    assert result.model == config.model_for("cloudflare", "event_analysis")
    assert groq.calls and gemini.calls and cloudflare.calls
    assert mistral.calls == []


@pytest.mark.asyncio
async def test_mistral_429_starts_backoff_and_reaches_cloudflare(monkeypatch):
    _configure(monkeypatch, ["mistral", "cloudflare"])
    client_call = AsyncMock(side_effect=_http_error(429, retry_after="600"))
    mistral = MistralProvider()
    mistral._client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=client_call))
    )
    cloudflare = StubProvider("cloudflare", None)
    router = LLMRouter(registry={"mistral": mistral, "cloudflare": cloudflare})
    first = await _event_call(router)
    second = await _event_call(router)
    assert first.provider == second.provider == "cloudflare"
    assert first.model == second.model == config.model_for("cloudflare", "event_analysis")
    assert client_call.await_count == 1  # second call skips backoff without a request
    assert len(cloudflare.calls) == 2
    assert telemetry.get_llm_rate_limit_backoff(
        provider="mistral", model=config.model_for("mistral", "event_analysis")
    ) is not None


@pytest.mark.asyncio
async def test_unavailable_mistral_model_advances_to_cloudflare(monkeypatch):
    _configure(monkeypatch, ["mistral", "cloudflare"])
    mistral = StubProvider("mistral", _http_error(404, code="model_not_found"))
    cloudflare = StubProvider("cloudflare", None)
    result = await _event_call(LLMRouter(registry={
        "mistral": mistral, "cloudflare": cloudflare,
    }))
    assert result.provider == "cloudflare"
    assert len(mistral.calls) == len(cloudflare.calls) == 1


@pytest.mark.asyncio
async def test_cloudflare_credentials_optional_mistral_still_works(monkeypatch):
    _configure(monkeypatch, ["mistral"])
    monkeypatch.setenv("LLM_EVENT_PROVIDERS", "cloudflare,mistral")
    mistral = StubProvider("mistral", None)
    cloudflare = StubProvider("cloudflare", RuntimeError("must be excluded"))
    result = await _event_call(LLMRouter(registry={
        "mistral": mistral, "cloudflare": cloudflare,
    }))
    assert result.provider == "mistral"
    assert cloudflare.calls == []


@pytest.mark.asyncio
async def test_exhaustion_after_mistral_limit_and_cloudflare_timeout_is_not_no_alert(monkeypatch):
    _configure(monkeypatch, ["mistral", "cloudflare"])
    router = LLMRouter(registry={
        "mistral": StubProvider(
            "mistral", AIProviderRateLimitError("429", provider="mistral")
        ),
        "cloudflare": StubProvider("cloudflare", asyncio.TimeoutError()),
    })
    with pytest.raises(AllProvidersFailedError) as caught:
        await _event_call(router)
    assert caught.value.mixed_failure is True
    assert telemetry.classify_ai_error_reason(caught.value) == "mixed_provider_failures"


@pytest.mark.asyncio
async def test_every_provider_429_reports_rate_limit_not_success(monkeypatch):
    _configure(monkeypatch, ["mistral", "cloudflare"])
    router = LLMRouter(registry={
        "mistral": StubProvider(
            "mistral", AIProviderRateLimitError("429", provider="mistral")
        ),
        "cloudflare": StubProvider(
            "cloudflare", AIProviderRateLimitError("429", provider="cloudflare")
        ),
    })
    with pytest.raises(AIProviderRateLimitError):
        await _event_call(router)
