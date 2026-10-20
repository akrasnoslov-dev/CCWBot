"""Router fallback behaviour with mocked providers (no real provider calls)."""

import asyncio
import json
import logging

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
from bot.services.llm.operation import current_llm_operation_id, llm_operation_scope
from bot.services.llm.router import LLMRouter
from bot.services.llm.telemetry import classify_ai_error_reason


class FakeProvider(BaseProvider):
    def __init__(self, name, behavior):
        self.name = name
        self._behavior = behavior
        self.calls = 0
        self.last_reasoning_effort = None
        self.last_response_format = None
        self.last_timeout = None
        self.operation_ids = []

    async def chat_completion(
        self,
        *,
        call_type,
        symbol,
        model,
        messages,
        max_tokens,
        response_format,
        timeout=15,
        reasoning_effort=None,
    ):
        self.calls += 1
        self.operation_ids.append(current_llm_operation_id())
        self.last_reasoning_effort = reasoning_effort
        self.last_response_format = response_format
        self.last_timeout = timeout
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


def _cloudflare_error(status_code, *, code, message):
    err = RuntimeError(message)
    err.status_code = status_code
    err.body = {"error": {"code": code, "message": message}}
    return err


def _configure(monkeypatch, priority, keys):
    monkeypatch.setenv("LLM_PROVIDER_PRIORITY", ",".join(priority))
    monkeypatch.setenv("OPENAI_ENABLED", "true" if "openai" in keys else "false")
    for provider in ("groq", "openai", "cloudflare"):
        env = config.api_key_env(provider)
        if provider in keys:
            monkeypatch.setenv(env, f"{provider}-key")
        else:
            monkeypatch.delenv(env, raising=False)
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "test-account")


async def _call(router, call_type="event_analysis"):
    return await router.chat_completion(
        call_type=call_type,
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=10,
        response_format=None,
    )


@pytest.mark.asyncio
async def test_event_analysis_openai_timeout_keeps_cloudflare_fallback_and_operation_id(
    monkeypatch,
):
    _configure(monkeypatch, ["groq", "openai", "cloudflare"], {"groq", "openai", "cloudflare"})
    for name in (
        "LLM_OPENAI_EVENT_ANALYSIS_TIMEOUT_SECONDS",
        "LLM_EVENT_ANALYSIS_OPERATION_BUDGET_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)
    groq = FakeProvider("groq", _http_error(503))
    openai = FakeProvider("openai", asyncio.TimeoutError())
    cloudflare = FakeProvider("cloudflare", lambda name, model: _result(name, model))
    router = LLMRouter(registry={"groq": groq, "openai": openai, "cloudflare": cloudflare})

    result = await _call(router)

    assert result.provider == "cloudflare"
    assert [groq.last_timeout, openai.last_timeout, cloudflare.last_timeout] == [15, 15, 15]
    assert [groq.calls, openai.calls, cloudflare.calls] == [1, 1, 1]
    assert groq.operation_ids == openai.operation_ids == cloudflare.operation_ids == [
        result.operation_id
    ]


@pytest.mark.asyncio
async def test_openai_5xx_and_quota_fall_through_without_retries(monkeypatch):
    _configure(monkeypatch, ["openai", "cloudflare"], {"openai", "cloudflare"})
    for failure in (_http_error(503), _http_error(429)):
        if failure.status_code == 429:
            failure.body = {"error": {"code": "quota_exceeded"}}
        openai = FakeProvider("openai", failure)
        cloudflare = FakeProvider("cloudflare", lambda name, model: _result(name, model))
        result = await _call(LLMRouter(registry={"openai": openai, "cloudflare": cloudflare}))
        assert result.provider == "cloudflare"
        assert (openai.calls, cloudflare.calls) == (1, 1)


@pytest.mark.asyncio
async def test_event_analysis_budget_stops_chain_before_new_http_request(monkeypatch):
    from bot.services.llm import router as router_module

    _configure(monkeypatch, ["groq", "openai", "cloudflare"], {"groq", "openai", "cloudflare"})
    monkeypatch.setattr(config, "event_analysis_operation_budget_seconds", lambda: 60)
    clock = iter((100.0, 100.0, 120.0, 161.0))
    monkeypatch.setattr(router_module, "_monotonic", lambda: next(clock))
    groq = FakeProvider("groq", asyncio.TimeoutError())
    openai = FakeProvider("openai", _http_error(503))
    cloudflare = FakeProvider("cloudflare", lambda name, model: _result(name, model))
    router = LLMRouter(registry={"groq": groq, "openai": openai, "cloudflare": cloudflare})

    with pytest.raises(AllProvidersFailedError) as raised:
        await _call(router)
    assert raised.value.operation_budget_exhausted is True
    assert classify_ai_error_reason(raised.value) == "operation_budget_exhausted"
    assert (groq.calls, openai.calls, cloudflare.calls) == (1, 1, 0)
    assert groq.operation_ids == openai.operation_ids == [raised.value.operation_id]


@pytest.mark.asyncio
@pytest.mark.parametrize("stall_at", ["provider_telemetry", "output_validation"])
async def test_event_analysis_deadline_covers_provider_and_validator(monkeypatch, stall_at):
    """One stalled DB/validation await cannot hold the Event Analysis chain open."""
    import time

    _configure(monkeypatch, ["openai", "cloudflare"], {"openai", "cloudflare"})
    monkeypatch.setattr(config, "event_analysis_operation_budget_seconds", lambda: 1.1)

    class SlowProvider(FakeProvider):
        async def chat_completion(self, **kwargs):
            self.calls += 1
            self.operation_ids.append(current_llm_operation_id())
            if stall_at == "provider_telemetry":
                # Simulate a provider finishing HTTP but hanging on its usage-log write.
                await asyncio.sleep(1.7)
            return _result(self.name)

    openai = SlowProvider("openai", None)
    cloudflare = FakeProvider("cloudflare", lambda name, model: _result(name, model))
    router = LLMRouter(registry={"openai": openai, "cloudflare": cloudflare})

    async def validate(_result_value):
        if stall_at == "output_validation":
            # Successful HTTP response followed by a stalled validator telemetry write.
            await asyncio.sleep(1.7)
        return _result_value

    started = time.monotonic()
    with pytest.raises(AllProvidersFailedError) as caught:
        await router.chat_completion(
            call_type="event_analysis",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=10,
            response_format=None,
            validate_response=validate,
        )

    assert time.monotonic() - started < 1.45
    assert caught.value.operation_budget_exhausted is True
    assert classify_ai_error_reason(caught.value) == "operation_budget_exhausted"
    assert openai.calls == 1
    assert cloudflare.calls == 0
    assert openai.operation_ids == [caught.value.operation_id]


@pytest.mark.asyncio
async def test_final_deadline_capped_timeout_is_recorded_as_budget_exhaustion(monkeypatch):
    from bot.services.llm import router as router_module

    _configure(monkeypatch, ["groq", "openai"], {"groq", "openai"})
    monkeypatch.setattr(config, "event_analysis_operation_budget_seconds", lambda: 60)
    clock = iter((100.0, 100.0, 156.0))
    monkeypatch.setattr(router_module, "_monotonic", lambda: next(clock))
    groq = FakeProvider("groq", _http_error(503))
    openai = FakeProvider("openai", asyncio.TimeoutError())
    router = LLMRouter(registry={"groq": groq, "openai": openai})

    with pytest.raises(AllProvidersFailedError) as caught:
        await _call(router)

    assert openai.last_timeout == pytest.approx(4.0)
    assert caught.value.operation_budget_exhausted is True
    assert classify_ai_error_reason(caught.value) == "operation_budget_exhausted"
    assert groq.operation_ids == openai.operation_ids == [caught.value.operation_id]


@pytest.mark.asyncio
async def test_event_analysis_budget_caps_late_cloudflare_timeout(monkeypatch):
    from bot.services.llm import router as router_module

    _configure(monkeypatch, ["groq", "openai", "cloudflare"], {"groq", "openai", "cloudflare"})
    monkeypatch.setattr(config, "event_analysis_operation_budget_seconds", lambda: 60)
    clock = iter((100.0, 100.0, 120.0, 154.0))
    monkeypatch.setattr(router_module, "_monotonic", lambda: next(clock))
    groq = FakeProvider("groq", asyncio.TimeoutError())
    openai = FakeProvider("openai", asyncio.TimeoutError())
    cloudflare = FakeProvider("cloudflare", lambda name, model: _result(name, model))
    result = await _call(LLMRouter(registry={
        "groq": groq, "openai": openai, "cloudflare": cloudflare,
    }))

    assert result.provider == "cloudflare"
    assert cloudflare.last_timeout == pytest.approx(6.0)


@pytest.mark.asyncio
async def test_openai_timeout_policy_does_not_change_other_tasks_or_explicit_override(monkeypatch):
    _configure(monkeypatch, ["openai"], {"openai"})
    openai = FakeProvider("openai", lambda name, model: _result(name, model))
    router = LLMRouter(registry={"openai": openai})

    await _call(router, "daily_report")
    assert openai.last_timeout == 15

    await router.chat_completion(
        call_type="event_analysis",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=10,
        response_format=None,
        timeout=7,
    )
    assert openai.last_timeout == 7


def test_event_analysis_timeout_configuration_is_bounded_and_logged(monkeypatch, caplog):
    monkeypatch.delenv("LLM_EVENT_ANALYSIS_OPERATION_BUDGET_SECONDS", raising=False)
    assert config.request_timeout_seconds_for(
        call_type="event_analysis", provider="openai"
    ) == 15
    assert config.event_analysis_operation_budget_seconds() == 90
    monkeypatch.setenv("LLM_EVENT_ANALYSIS_OPERATION_BUDGET_SECONDS", "65")
    assert config.request_timeout_seconds_for(
        call_type="event_analysis", provider="openai"
    ) == 15
    assert config.event_analysis_operation_budget_seconds() == 65
    monkeypatch.setenv("LLM_EVENT_ANALYSIS_OPERATION_BUDGET_SECONDS", "-1")
    assert config.request_timeout_seconds_for(
        call_type="event_analysis", provider="openai"
    ) == 15
    assert config.event_analysis_operation_budget_seconds() == 90
    with caplog.at_level(logging.INFO, logger=config.logger.name):
        config.log_resolved_configuration()
    assert any(
        "operation_budget_seconds=90" in rec.getMessage()
        for rec in caplog.records
    )


@pytest.mark.asyncio
async def test_groq_backoff_openai_5xx_cloudflare_429_exhausts_once(monkeypatch):
    from datetime import datetime, timezone

    _configure(monkeypatch, ["groq", "openai", "cloudflare"], {"groq", "openai", "cloudflare"})
    groq = FakeProvider(
        "groq",
        LLMRateLimitBackoffActive(
            provider="groq", model="m", limited_until=datetime.now(timezone.utc)
        ),
    )
    openai = FakeProvider("openai", _http_error(503))
    cloudflare = FakeProvider(
        "cloudflare", AIProviderRateLimitError("429", provider="cloudflare")
    )
    router = LLMRouter(registry={"groq": groq, "openai": openai, "cloudflare": cloudflare})

    with pytest.raises(AllProvidersFailedError) as raised:
        await _call(router)

    assert raised.value.mixed_failure is True
    assert classify_ai_error_reason(raised.value) == "mixed_provider_failures"
    assert [groq.calls, openai.calls, cloudflare.calls] == [1, 1, 1]
    assert groq.operation_ids == openai.operation_ids == cloudflare.operation_ids == [
        raised.value.operation_id
    ]


@pytest.mark.asyncio
async def test_openai_request_defect_does_not_spend_cloudflare_quota(monkeypatch):
    _configure(monkeypatch, ["openai", "cloudflare"], {"openai", "cloudflare"})
    openai = FakeProvider("openai", _http_error(400))
    cloudflare = FakeProvider("cloudflare", lambda name, model: _result(name, model))
    with pytest.raises(RuntimeError):
        await _call(LLMRouter(registry={"openai": openai, "cloudflare": cloudflare}))
    assert openai.calls == 1
    assert cloudflare.calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_name", ["groq", "openai", "cloudflare"])
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
    _configure(monkeypatch, ["groq", "openai"], {"groq", "openai"})
    groq = FakeProvider("groq", failure)
    openai = FakeProvider("openai", lambda name, model: _result(name, model))
    router = LLMRouter(registry={"groq": groq, "openai": openai})

    result = await _call(router)

    assert result.provider == "openai"
    assert groq.calls == 1
    assert openai.calls == 1


@pytest.mark.asyncio
async def test_provider_specific_response_format_does_not_leak_to_fallback(monkeypatch):
    _configure(monkeypatch, ["groq", "openai"], {"groq", "openai"})
    groq = FakeProvider("groq", RuntimeError("connection failed"))
    openai = FakeProvider("openai", lambda name, model: _result(name, model))
    router = LLMRouter(registry={"groq": groq, "openai": openai})
    strict_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "event_analysis",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {"symbol": {"type": "string"}},
                "required": ["symbol"],
                "additionalProperties": False,
            },
        },
    }

    result = await router.chat_completion(
        call_type="event_analysis",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=10,
        response_format={"type": "json_object"},
        response_format_overrides={"groq": strict_format},
    )

    assert result.provider == "openai"
    assert groq.last_response_format == strict_format
    assert openai.last_response_format == {"type": "json_object"}


@pytest.mark.asyncio
async def test_chain_exhaustion_log_contains_only_safe_failure_categories(monkeypatch, caplog):
    _configure(monkeypatch, ["groq", "openai"], {"groq", "openai"})
    groq = FakeProvider(
        "groq",
        AIProviderRateLimitError(
            "429 provider body must-not-appear",
            provider="groq",
            model="m",
        ),
    )
    openai = FakeProvider("openai", asyncio.TimeoutError("must-not-appear"))
    router = LLMRouter(registry={"groq": groq, "openai": openai})

    with caplog.at_level(logging.WARNING, logger="bot.services.llm.router"):
        with pytest.raises(AllProvidersFailedError):
            await _call(router)

    exhausted = [
        record.getMessage()
        for record in caplog.records
        if "ops_event=llm_chain_exhausted" in record.getMessage()
    ]
    assert len(exhausted) == 1
    assert "groq:rate_limit" in exhausted[0]
    assert "openai:timeout" in exhausted[0]
    assert "provider body must-not-appear" not in exhausted[0]
    assert "must-not-appear" not in exhausted[0]


@pytest.mark.asyncio
async def test_fallback_attempts_share_one_opaque_logical_operation_id(monkeypatch):
    _configure(monkeypatch, ["groq", "openai"], {"groq", "openai"})
    groq = FakeProvider("groq", asyncio.TimeoutError())
    openai = FakeProvider("openai", lambda name, model: _result(name, model))
    router = LLMRouter(registry={"groq": groq, "openai": openai})
    operation_id = "123e4567-e89b-42d3-a456-426614174000"

    with llm_operation_scope(operation_id):
        result = await _call(router)

    assert groq.operation_ids == [operation_id]
    assert openai.operation_ids == [operation_id]
    assert result.operation_id == operation_id


@pytest.mark.asyncio
async def test_separate_logical_operations_receive_different_ids(monkeypatch):
    _configure(monkeypatch, ["groq"], {"groq"})
    provider = FakeProvider("groq", lambda name, model: _result(name, model))
    router = LLMRouter(registry={"groq": provider})

    first = await _call(router)
    second = await _call(router)

    assert first.operation_id != second.operation_id
    assert "user" not in first.operation_id


@pytest.mark.asyncio
async def test_all_providers_rate_limited_raises_rate_limit(monkeypatch):
    _configure(monkeypatch, ["groq", "openai"], {"groq", "openai"})
    router = LLMRouter(
        registry={
            "groq": FakeProvider("groq", AIProviderRateLimitError("429", provider="groq")),
            "openai": FakeProvider("openai", AIProviderRateLimitError("429", provider="openai")),
        }
    )

    with pytest.raises(AIProviderRateLimitError):
        await _call(router)


@pytest.mark.asyncio
async def test_all_providers_timeout_raises_all_failed(monkeypatch):
    _configure(monkeypatch, ["groq", "openai"], {"groq", "openai"})
    router = LLMRouter(
        registry={
            "groq": FakeProvider("groq", asyncio.TimeoutError()),
            "openai": FakeProvider("openai", _http_error(500)),
        }
    )

    with pytest.raises(AllProvidersFailedError):
        await _call(router)


@pytest.mark.asyncio
async def test_all_providers_in_backoff_raises_backoff_active(monkeypatch):
    from datetime import datetime, timezone

    _configure(monkeypatch, ["groq", "openai"], {"groq", "openai"})
    until = datetime.now(timezone.utc)
    router = LLMRouter(
        registry={
            "groq": FakeProvider(
                "groq", LLMRateLimitBackoffActive(provider="groq", model="m", limited_until=until)
            ),
            "openai": FakeProvider(
                "openai",
                LLMRateLimitBackoffActive(provider="openai", model="m", limited_until=until),
            ),
        }
    )

    with pytest.raises(LLMRateLimitBackoffActive):
        await _call(router)


@pytest.mark.asyncio
async def test_deterministic_error_is_not_retried(monkeypatch):
    _configure(monkeypatch, ["groq", "openai"], {"groq", "openai"})
    groq = FakeProvider("groq", _http_error(400))
    openai = FakeProvider("openai", lambda name, model: _result(name, model))
    router = LLMRouter(registry={"groq": groq, "openai": openai})

    with pytest.raises(RuntimeError):
        await _call(router)
    assert openai.calls == 0  # 4xx is deterministic; do not fall through


@pytest.mark.asyncio
async def test_provider_without_api_key_is_excluded(monkeypatch):
    # openai has no key, so it is excluded even though it is next in priority.
    _configure(monkeypatch, ["groq", "openai"], {"groq"})
    groq = FakeProvider("groq", lambda name, model: _result(name, model))
    openai = FakeProvider("openai", RuntimeError("should not be called"))
    router = LLMRouter(registry={"groq": groq, "openai": openai})

    result = await _call(router)

    assert result.provider == "groq"
    assert openai.calls == 0


@pytest.mark.asyncio
async def test_openai_disabled_with_stray_key_has_zero_calls_and_no_delay(monkeypatch):
    monkeypatch.setenv("LLM_EVENT_PROVIDERS", "groq,openai,cloudflare")
    monkeypatch.setenv("GROQ_API_KEY", "groq-key")
    monkeypatch.setenv("OPENAI_API_KEY", "stray-key-must-not-enable")
    monkeypatch.setenv("OPENAI_ENABLED", "false")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "cloudflare-token")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "account-id")
    groq = FakeProvider("groq", asyncio.TimeoutError())
    openai = FakeProvider("openai", RuntimeError("must not be called"))
    cloudflare = FakeProvider("cloudflare", lambda name, model: _result(name, model))

    result = await _call(
        LLMRouter(registry={"groq": groq, "openai": openai, "cloudflare": cloudflare})
    )

    assert result.provider == "cloudflare"
    assert openai.calls == 0


@pytest.mark.asyncio
async def test_runtime_model_override_cannot_reactivate_retired_qwen(monkeypatch):
    _configure(monkeypatch, ["groq"], {"groq"})
    groq = FakeProvider("groq", lambda name, model: _result(name, model))

    result = await LLMRouter(registry={"groq": groq}).chat_completion(
        call_type="event_analysis",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=10,
        response_format=None,
        model_overrides={"groq": "qwen/qwen3.8-27b"},
    )

    assert result.model == "openai/gpt-oss-120b"


@pytest.mark.asyncio
async def test_openai_budget_refusal_uses_cloudflare_without_constructing_client(monkeypatch):
    from bot.services.llm import base_provider
    from bot.services.llm.openai_provider import OpenAIProvider

    _configure(monkeypatch, ["openai", "cloudflare"], {"openai", "cloudflare"})
    for name in (
        "OPENAI_INPUT_USD_PER_1M_TOKENS",
        "OPENAI_OUTPUT_USD_PER_1M_TOKENS",
        "OPENAI_PRICED_MODEL",
        "OPENAI_MAX_INPUT_TOKENS",
    ):
        monkeypatch.delenv(name, raising=False)
    openai = OpenAIProvider()
    client_requested = False
    usage_rows = []

    async def write_usage(**kwargs):
        usage_rows.append(kwargs)

    def get_client():
        nonlocal client_requested
        client_requested = True
        raise AssertionError("budget refusal must happen before client construction")

    monkeypatch.setattr(openai, "get_client", get_client)
    monkeypatch.setattr(base_provider, "write_llm_usage_log", write_usage)
    cloudflare = FakeProvider("cloudflare", lambda name, model: _result(name, model))

    result = await _call(
        LLMRouter(registry={"openai": openai, "cloudflare": cloudflare})
    )

    assert result.provider == "cloudflare"
    assert client_requested is False
    assert cloudflare.calls == 1
    assert any(
        row["provider"] == "openai"
        and row["status"] == "skipped_due_to_budget"
        and row["error_reason"] == "openai_budget_unknown_pricing"
        for row in usage_rows
    )


@pytest.mark.asyncio
async def test_no_configured_providers_raises_all_failed(monkeypatch):
    _configure(monkeypatch, ["groq"], set())
    router = LLMRouter(registry={"groq": FakeProvider("groq", RuntimeError("x"))})

    with pytest.raises(AllProvidersFailedError):
        await _call(router)


def test_provider_priority_per_call_type_override(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER_PRIORITY", "groq,openai")
    monkeypatch.setenv("LLM_EVENT_PROVIDERS", "cloudflare,groq")
    assert config.provider_priority("event_analysis") == ["cloudflare", "groq"]
    # Report/heartbeat with no override fall back to the global priority.
    assert config.provider_priority("daily_report") == ["groq", "openai"]


def test_provider_priority_filters_unknown_tokens(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER_PRIORITY", "foo, cerebras, groq , bar,openai")
    monkeypatch.delenv("LLM_EVENT_PROVIDERS", raising=False)
    assert config.provider_priority("event_analysis") == ["groq", "openai"]


def test_retired_provider_is_not_configurable_or_registered(monkeypatch, caplog):
    monkeypatch.setenv("LLM_PROVIDER_PRIORITY", "cerebras,gemini")

    with caplog.at_level("WARNING", logger="bot.services.llm.env"):
        assert config.global_provider_priority() == ["groq", "openai", "cloudflare"]

    assert config.api_key_env("cerebras") is None
    assert config.api_key("cerebras") is None
    assert config.base_url("cerebras") is None
    assert config.model_for("cerebras", "event_analysis") == ""
    assert "cerebras" not in LLMRouter()._registry
    assert "gemini" not in LLMRouter()._registry
    assert any("LLM_PROVIDER_PRIORITY" in record.getMessage() for record in caplog.records)


def test_provider_priority_defaults_when_unset(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER_PRIORITY", raising=False)
    monkeypatch.delenv("LLM_EVENT_PROVIDERS", raising=False)
    assert config.provider_priority("event_analysis") == ["groq", "openai", "cloudflare"]
    assert config.provider_priority("daily_report") == ["groq", "openai"]
    assert config.provider_priority("weekly_report") == ["groq", "openai"]
    assert config.provider_priority("market_report") == ["groq", "openai"]


def test_model_for_resolves_per_provider(monkeypatch):
    monkeypatch.delenv("GROQ_MARKET_HEARTBEAT_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("CLOUDFLARE_MODEL", raising=False)
    assert config.model_for("groq", "market_heartbeat") == "openai/gpt-oss-20b"
    assert config.model_for("openai", "daily_report") == "gpt-6-luna"
    assert config.model_for("cloudflare", "event_analysis") == (
        "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
    )
    monkeypatch.setenv("OPENAI_MODEL", "custom-openai")
    assert config.model_for("openai", "event_analysis") == "custom-openai"


@pytest.mark.asyncio
async def test_backoff_skip_then_next_provider_succeeds(monkeypatch):
    # The feature's core payoff: a provider already in active backoff is skipped (no HTTP call)
    # and the next configured provider answers.
    from datetime import datetime, timezone

    _configure(monkeypatch, ["groq", "openai"], {"groq", "openai"})
    groq = FakeProvider(
        "groq",
        LLMRateLimitBackoffActive(
            provider="groq", model="m", limited_until=datetime.now(timezone.utc)
        ),
    )
    openai = FakeProvider("openai", lambda name, model: _result(name, model))
    router = LLMRouter(registry={"groq": groq, "openai": openai})

    result = await _call(router)

    assert result.provider == "openai"
    assert groq.calls == 1  # the skip still counts as one chat_completion invocation
    assert openai.calls == 1


@pytest.mark.asyncio
async def test_mixed_timeout_and_rate_limit_remains_a_terminal_failure(monkeypatch):
    # A late 429 does not erase the earlier timeout from this exhausted logical call.
    _configure(monkeypatch, ["groq", "openai"], {"groq", "openai"})
    router = LLMRouter(
        registry={
            "groq": FakeProvider("groq", asyncio.TimeoutError()),
            "openai": FakeProvider("openai", AIProviderRateLimitError("429", provider="openai")),
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

    _configure(monkeypatch, ["groq", "openai"], {"groq", "openai"})
    router = LLMRouter(
        registry={
            "groq": FakeProvider(
                "groq",
                LLMRateLimitBackoffActive(
                    provider="groq", model="m", limited_until=datetime.now(timezone.utc)
                ),
            ),
            "openai": FakeProvider("openai", AIProviderRateLimitError("429", provider="openai")),
        }
    )

    with pytest.raises(AIProviderRateLimitError):
        await _call(router)


@pytest.mark.asyncio
async def test_mixed_rate_limit_and_timeout_raises_all_failed(monkeypatch):
    # A 429 from Groq is provider pressure, but does not make the logical call terminally
    # rate-limited after later fallbacks time out.
    _configure(monkeypatch, ["groq", "openai", "cloudflare"], {"groq", "openai", "cloudflare"})
    router = LLMRouter(
        registry={
            "groq": FakeProvider("groq", AIProviderRateLimitError("429", provider="groq")),
            "openai": FakeProvider("openai", asyncio.TimeoutError()),
            "cloudflare": FakeProvider("cloudflare", asyncio.TimeoutError()),
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
async def test_event_alert_render_uses_three_step_model_chain(monkeypatch):
    for name in (
        "GROQ_EVENT_RENDER_MODEL",
        "CLOUDFLARE_EVENT_RENDER_MODEL",
        "OPENAI_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "groq-key")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "cloudflare-token")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "account-id")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("OPENAI_ENABLED", "true")

    call_order = []

    def groq_behavior(name, model):
        call_order.append((name, model))
        return _content_result(name, model, "not json")

    def openai_behavior(name, model):
        call_order.append((name, model))
        return _content_result(name, model, '{"ok": true}')

    groq = FakeProvider("groq", groq_behavior)
    cloudflare = FakeProvider("cloudflare", RuntimeError("should not be called"))
    openai = FakeProvider("openai", openai_behavior)
    router = LLMRouter(
        registry={
            "groq": groq,
            "cloudflare": cloudflare,
            "openai": openai,
        }
    )

    provider, parsed = await _call_validated(
        router,
        _parse_json_validate,
        call_type="event_alert_render",
    )

    assert provider == "openai"
    assert parsed == {"ok": True}
    assert call_order == [
        ("groq", "openai/gpt-oss-20b"),
        ("openai", "gpt-6-luna"),
    ]
    assert groq.calls == 1
    assert cloudflare.calls == 0
    assert openai.calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "cloudflare_error",
    [
        _cloudflare_error(408, code=3007, message="Request timeout"),
        _cloudflare_error(400, code=5007, message="No such model"),
    ],
)
async def test_event_alert_render_openai_failure_reaches_cloudflare(
    monkeypatch, cloudflare_error
):
    for name in (
        "GROQ_EVENT_RENDER_MODEL",
        "CLOUDFLARE_EVENT_RENDER_MODEL",
        "OPENAI_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "groq-key")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "cloudflare-token")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "account-id")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("OPENAI_ENABLED", "true")

    groq = FakeProvider(
        "groq", lambda name, model: _content_result(name, model, "not json")
    )
    cloudflare = FakeProvider(
        "cloudflare", lambda name, model: _content_result(name, model, '{"ok": true}')
    )
    openai = FakeProvider("openai", cloudflare_error)
    router = LLMRouter(
        registry={
            "groq": groq,
            "cloudflare": cloudflare,
            "openai": openai,
        }
    )

    provider, parsed = await _call_validated(
        router,
        _parse_json_validate,
        call_type="event_alert_render",
    )

    assert provider == "cloudflare"
    assert parsed == {"ok": True}
    assert groq.calls == 1
    assert cloudflare.calls == 1
    assert openai.calls == 1


@pytest.mark.asyncio
async def test_invalid_json_output_advances_to_next_provider(monkeypatch):
    # The production 2026-07-10 case: primary switched out on 5xx is one thing, but a
    # provider that answers with unparseable JSON must also advance the chain.
    _configure(monkeypatch, ["groq", "openai"], {"groq", "openai"})
    groq = FakeProvider("groq", lambda name, model: _content_result(name, model, "not json"))
    openai = FakeProvider(
        "openai", lambda name, model: _content_result(name, model, '{"ok": true}')
    )
    router = LLMRouter(registry={"groq": groq, "openai": openai})

    provider, parsed = await _call_validated(router, _parse_json_validate)

    assert provider == "openai"
    assert parsed == {"ok": True}
    assert groq.calls == 1
    assert openai.calls == 1


@pytest.mark.asyncio
async def test_all_providers_invalid_json_raises_last_invalid_error(monkeypatch):
    # Exhaustion keeps the AIInvalidJsonError contract, and the chain is bounded to one
    # full pass: each provider is attempted exactly once for this logical call.
    _configure(monkeypatch, ["groq", "openai"], {"groq", "openai"})
    groq = FakeProvider("groq", lambda name, model: _content_result(name, model, "not json"))
    openai = FakeProvider(
        "openai", lambda name, model: _content_result(name, model, "also not json")
    )
    router = LLMRouter(registry={"groq": groq, "openai": openai})

    with pytest.raises(AIInvalidJsonError) as raised:
        await _call_validated(router, _parse_json_validate)

    assert raised.value.raw_content == "also not json"
    assert groq.calls == 1
    assert openai.calls == 1


@pytest.mark.asyncio
async def test_schema_validation_failure_advances_to_next_provider(monkeypatch, caplog):
    _configure(monkeypatch, ["groq", "openai"], {"groq", "openai"})
    groq = FakeProvider(
        "groq", lambda name, model: _content_result(name, model, '{"wrong_schema": true}')
    )
    openai = FakeProvider(
        "openai", lambda name, model: _content_result(name, model, '{"symbol": "BTC"}')
    )
    router = LLMRouter(registry={"groq": groq, "openai": openai})

    async def _schema_validate(result):
        parsed = json.loads(result.raw_content)
        if "symbol" not in parsed:
            raise AISchemaValidationError("missing fields: ['symbol']")
        return (result.provider, parsed)

    with caplog.at_level(logging.WARNING, logger="bot.services.llm.router"):
        provider, parsed = await _call_validated(router, _schema_validate)

    assert provider == "openai"
    assert parsed == {"symbol": "BTC"}
    assert groq.calls == 1
    assert openai.calls == 1
    switch_log = next(
        record.getMessage()
        for record in caplog.records
        if "ops_event=llm_provider_switch" in record.getMessage()
    )
    assert f"operation_id={groq.operation_ids[0]}" in switch_log


@pytest.mark.asyncio
async def test_invalid_output_then_rate_limit_exhaustion_raises_invalid_error(monkeypatch):
    # Mixed exhaustion: invalid output was seen, so the invalid-output error wins and the
    # caller reaches its deterministic-fallback handling instead of a rate-limit path.
    _configure(monkeypatch, ["groq", "openai"], {"groq", "openai"})
    router = LLMRouter(
        registry={
            "groq": FakeProvider(
                "groq", lambda name, model: _content_result(name, model, "not json")
            ),
            "openai": FakeProvider("openai", AIProviderRateLimitError("429", provider="openai")),
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


@pytest.mark.asyncio
@pytest.mark.parametrize(("first_behavior", "all_invalid"), [
    (asyncio.TimeoutError(), False),
    (_result("groq"), True),
])
async def test_invalid_output_exhaustion_marks_only_pure_invalid_chains(
    monkeypatch, first_behavior, all_invalid
):
    _configure(monkeypatch, ["groq", "openai"], {"groq", "openai"})
    router = LLMRouter(registry={
        "groq": FakeProvider("groq", first_behavior),
        "openai": FakeProvider("openai", _result("openai")),
    })

    async def reject(_result):
        raise AISchemaValidationError("untrusted generated market facts")

    with pytest.raises(AISchemaValidationError) as caught:
        await router.chat_completion(
            call_type="event_alert_render",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=300,
            response_format=None,
            validate_response=reject,
        )

    assert getattr(
        caught.value, "_llm_all_exhausted_attempts_invalid_output", False
    ) is all_invalid
