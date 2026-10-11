"""Gemini quota and structured retry guidance regression tests; no live API calls."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest

from bot.services.llm import telemetry
from bot.services.llm.errors import AIProviderRateLimitError, LLMRateLimitBackoffActive
from bot.services.llm.gemini_provider import GeminiProvider


@pytest.fixture(autouse=True)
def clear_backoff(monkeypatch):
    telemetry.reset_llm_rate_limit_backoffs()
    monkeypatch.setenv("GEMINI_API_KEY", "unit-test")
    yield
    telemetry.reset_llm_rate_limit_backoffs()


def _failed_provider(error):
    provider = GeminiProvider()
    create = AsyncMock(side_effect=error)
    provider._client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    return provider, create


def _response_error(quota_id, *, retry_delay=None):
    error = RuntimeError("Gemini rejected request")
    error.status_code = 429
    details = [
        {
            "@type": "type.googleapis.com/google.rpc.QuotaFailure",
            "violations": [{"quotaId": quota_id}],
        }
    ]
    if retry_delay is not None:
        details.append({
            "@type": "type.googleapis.com/google.rpc.RetryInfo",
            "retryDelay": retry_delay,
        })
    error.body = {
        "error": {
            "code": 429,
            "status": "RESOURCE_EXHAUSTED",
            "details": details,
        },
    }
    return error


@pytest.mark.asyncio
async def test_structured_daily_quota_is_not_treated_as_short_retry():
    error = _response_error("GenerateRequestsPerDayPerProjectPerModel-FreeTier")
    assert telemetry.classify_ai_error_reason(error) == "provider_quota_exhausted"
    provider, create = _failed_provider(error)
    args = dict(
        call_type="event_analysis", symbol="SOL", model="gemini-test-day",
        messages=[{"role": "user", "content": "test"}],
        max_tokens=100, response_format=None,
    )

    with pytest.raises(RuntimeError):
        await provider.chat_completion(**args)
    until = telemetry.get_llm_rate_limit_backoff(provider="gemini", model="gemini-test-day")
    assert until is not None
    now = datetime.now(timezone.utc)
    pacific = ZoneInfo("America/Los_Angeles")
    assert until.astimezone(pacific).hour == 0
    assert until.astimezone(pacific).minute == 0
    assert now + timedelta(seconds=2) < until <= now + timedelta(hours=25)

    with pytest.raises(LLMRateLimitBackoffActive):
        await provider.chat_completion(**args)
    create.assert_awaited_once()  # No HTTP after daily quota is known


@pytest.mark.asyncio
async def test_daily_quota_respects_explicit_provider_reset_instead_of_local_timezone():
    # Production Gemini retries indicated an explicit 20,699s expiry near UTC midnight;
    # overriding it with a later Pacific reset would lose recoverable analysis capacity.
    error = _response_error(
        "GenerateRequestsPerDayPerProjectPerModel-FreeTier", retry_delay="20699s"
    )
    provider, create = _failed_provider(error)
    args = dict(
        call_type="event_analysis", symbol="ETH", model="gemini-explicit-reset",
        messages=[{"role": "user", "content": "test"}],
        max_tokens=100, response_format=None,
    )
    before = datetime.now(timezone.utc)
    with pytest.raises(RuntimeError):
        await provider.chat_completion(**args)
    until = telemetry.get_llm_rate_limit_backoff(
        provider="gemini", model="gemini-explicit-reset"
    )
    assert until is not None
    assert 20698 <= (until - before).total_seconds() <= 20702
    with pytest.raises(LLMRateLimitBackoffActive):
        await provider.chat_completion(**args)
    create.assert_awaited_once()


@pytest.mark.asyncio
async def test_minute_quota_uses_structured_retry_info_not_daily_backoff():
    error = _response_error(
        "GenerateRequestsPerMinutePerProjectPerModel-FreeTier", retry_delay="23.25s"
    )
    assert telemetry.classify_ai_error_reason(error) == "rate_limit"
    provider, create = _failed_provider(error)
    args = dict(
        call_type="market_heartbeat", symbol="BTC", model="gemini-test-minute",
        messages=[{"role": "user", "content": "test"}],
        max_tokens=100, response_format=None,
    )
    with pytest.raises(AIProviderRateLimitError) as exc:
        await provider.chat_completion(**args)
    assert exc.value.retry_after_seconds == 24
    with pytest.raises(LLMRateLimitBackoffActive):
        await provider.chat_completion(**args)
    create.assert_awaited_once()


@pytest.mark.asyncio
async def test_root_array_daily_quota_does_not_retry_exhausted_gemini():
    error = _response_error("GenerateRequestsPerDayPerProjectPerModel-FreeTier")
    error.body = [error.body]  # Observed Gemini OpenAI-compatible root-array wrapper
    assert telemetry.classify_ai_error_reason(error) == "provider_quota_exhausted"
    provider, create = _failed_provider(error)
    args = dict(
        call_type="event_analysis", symbol="BTC", model="gemini-root-array",
        messages=[{"role": "user", "content": "test"}],
        max_tokens=100, response_format=None,
    )
    with pytest.raises(RuntimeError):
        await provider.chat_completion(**args)
    until = telemetry.get_llm_rate_limit_backoff(provider="gemini", model="gemini-root-array")
    assert until is not None
    with pytest.raises(LLMRateLimitBackoffActive):
        await provider.chat_completion(**args)
    create.assert_awaited_once()


def test_root_array_transient_quota_uses_structured_retry_info():
    error = _response_error(
        "GenerateRequestsPerMinutePerProjectPerModel-FreeTier", retry_delay="11.2s"
    )
    error.body = [error.body]
    assert telemetry.classify_ai_error_reason(error) == "rate_limit"
    assert telemetry.retry_after_seconds_from_rate_limit(
        error, None, now=datetime.now(timezone.utc)
    ) == 12


def test_multi_item_error_list_is_not_misclassified_as_daily_quota():
    error = _response_error("GenerateRequestsPerDayPerProjectPerModel-FreeTier")
    error.body = [error.body, {"error": {"status": "RESOURCE_EXHAUSTED"}}]
    assert not telemetry.is_gemini_daily_quota_exhausted_error(error)
    assert telemetry.classify_ai_error_reason(error) == "rate_limit"


def test_retry_after_decimal_header_rounded_up():
    error = RuntimeError("429")
    assert telemetry.retry_after_seconds_from_rate_limit(
        error, {"retry-after": "3.2"}, now=datetime.now(timezone.utc)
    ) == 4


def test_no_daily_cooldown_for_5xx_or_timeout():
    error = RuntimeError("Gemini server unavailable")
    error.status_code = 503
    error.body = _response_error("GenerateRequestsPerDayPerProjectPerModel-FreeTier").body
    assert not telemetry.is_gemini_daily_quota_exhausted_error(error)
    assert telemetry.classify_ai_error_reason(error) == "provider_5xx"
