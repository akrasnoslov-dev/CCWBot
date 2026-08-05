"""Shared LLM usage telemetry, error classification, and rate-limit backoff.

This module generalizes the telemetry that previously lived inside
``bot/services/ai_agent_groq.py``. It is provider-agnostic: every provider passes its own
``provider`` name so usage logs and the ``(provider, model)`` backoff registry are correct
for Groq and all fallback providers alike.

Belongs here: error classification, usage-log write/update, rate-limit header parsing, and
the in-memory backoff registry. Does not belong here: HTTP calls, prompt construction, or
alert/report domain logic.
"""

import asyncio
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import httpx

from bot.services.llm.env import get_int_env
from bot.services.llm.errors import (
    AIInvalidJsonError,
    AIProviderRateLimitError,
    AISchemaValidationError,
    LLMRateLimitBackoffActive,
)

logger = logging.getLogger(__name__)


def _get_int_env(name: str, default: int, minimum: int = 0) -> int:
    """Thin wrapper over the shared parser, which warns instead of failing silently."""
    return get_int_env(name, default, minimum=minimum)


def _rate_limit_fallback_backoff_seconds() -> int:
    """Fallback backoff when a provider gives no usable retry hint.

    Prefers the provider-agnostic env var, falling back to the historical Groq name so
    existing deployments keep their configured value.
    """
    raw = os.getenv("LLM_RATE_LIMIT_FALLBACK_BACKOFF_SECONDS")
    if raw is not None:
        return _get_int_env("LLM_RATE_LIMIT_FALLBACK_BACKOFF_SECONDS", 300, minimum=1)
    return _get_int_env("GROQ_RATE_LIMIT_FALLBACK_BACKOFF_SECONDS", 300, minimum=1)


# Only these call types consult the pre-call backoff registry before attempting a request.
RATE_LIMIT_BACKOFF_CALL_TYPES = {"event_analysis", "market_heartbeat"}

# Temporary in-memory backoff keyed by (provider, model). Shared process-wide.
_llm_rate_limit_backoffs: dict[tuple[str, str], datetime] = {}


def classify_ai_error_reason(error: Exception) -> str:
    """Return an admin-safe LLM failure reason (stable across all providers)."""
    if isinstance(error, LLMRateLimitBackoffActive):
        return "rate_limit_backoff_active"
    if isinstance(error, AIProviderRateLimitError) or is_rate_limit_error(error):
        return "rate_limit"
    if isinstance(error, AIInvalidJsonError):
        return "invalid_json"
    if isinstance(error, AISchemaValidationError):
        return "schema_validation_failed"
    if isinstance(error, (TimeoutError, asyncio.TimeoutError, httpx.TimeoutException)):
        return "timeout"
    status_code = getattr(error, "status_code", None)
    response = getattr(error, "response", None)
    response_status_code = getattr(response, "status_code", None)
    effective_status_code = status_code or response_status_code
    if effective_status_code in {401, 403}:
        return "auth_error"
    if effective_status_code is not None:
        try:
            status_code_int = int(effective_status_code)
        except (TypeError, ValueError):
            status_code_int = None
        if status_code_int is not None and 400 <= status_code_int < 500:
            return "provider_4xx"
        if status_code_int is not None and status_code_int >= 500:
            return "provider_5xx"
    message = str(error).lower()
    class_name = error.__class__.__name__.lower()
    if (
        "api key" in message
        or "api_key" in message
        or "unauthorized" in message
        or "forbidden" in message
    ):
        if "not configured" in message or "missing" in message:
            return "config_missing"
        return "auth_error"
    if "timeout" in message or "timed out" in message:
        return "timeout"
    if "empty response" in message or "response was empty" in message:
        return "empty_response"
    if "connection" in message or "network" in message or "apiconnectionerror" in class_name:
        return "network_error"
    return "other_error"


def usage_status_for_error(error: Exception) -> str:
    reason = classify_ai_error_reason(error)
    if reason == "rate_limit":
        return "rate_limit"
    if reason == "invalid_json":
        return "invalid_json"
    if reason == "schema_validation_failed" or is_json_validation_error(error):
        return "schema_error"
    if reason == "timeout":
        return "timeout"
    if reason == "auth_error":
        return "auth_error"
    return "other_error"


# Redact key/token-like fragments some providers echo in auth-error bodies before the message
# is persisted to llm_usage_logs.error_message (defense-in-depth; admin rendering also redacts).
_SECRET_FRAGMENT_RE = re.compile(
    r"(?i)(?:bearer\s+\S+|sk-[A-Za-z0-9_-]{6,}|(?:api[_-]?key|token|secret)\s*[:=]?\s*\S+)"
)


def safe_error_message(error: Exception, max_chars: int = 500) -> str:
    message = " ".join(str(error).split())
    message = _SECRET_FRAGMENT_RE.sub("[redacted]", message)
    return message[:max_chars]


def is_json_validation_error(error: Exception) -> bool:
    message = str(error).lower()
    return (
        "json_validate_failed" in message
        or "validate json" in message
        or "json validation" in message
    )


def is_rate_limit_error(error: Exception) -> bool:
    if isinstance(error, AIProviderRateLimitError):
        return True
    status_code = getattr(error, "status_code", None)
    response = getattr(error, "response", None)
    if status_code == 429 or getattr(response, "status_code", None) == 429:
        return True
    message = str(error).lower()
    return (
        "429" in message
        or "rate limit" in message
        or "rate_limit" in message
        or "tokens per day" in message
    )


def message_input_chars(messages: list[dict]) -> int:
    return sum(len(str(message.get("content") or "")) for message in messages)


def response_content(response) -> str:
    try:
        return response.choices[0].message.content or ""
    except (AttributeError, IndexError, TypeError):
        return ""


def usage_int(response, name: str) -> int | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    value = usage.get(name) if isinstance(usage, dict) else getattr(usage, name, None)
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def headers_from_error(error: Exception):
    response = getattr(error, "response", None)
    return getattr(response, "headers", None)


def header_value(headers, name: str) -> str | None:
    if headers is None:
        return None
    for candidate in (name, name.lower(), name.upper()):
        try:
            value = headers.get(candidate)
        except AttributeError:
            value = None
        if value is not None:
            return str(value)
    return None


def rate_limit_header_payload(headers) -> dict:
    return {
        "rate_limit_limit_requests": header_value(headers, "x-ratelimit-limit-requests"),
        "rate_limit_remaining_requests": header_value(headers, "x-ratelimit-remaining-requests"),
        "rate_limit_reset_requests": header_value(headers, "x-ratelimit-reset-requests"),
        "rate_limit_limit_tokens": header_value(headers, "x-ratelimit-limit-tokens"),
        "rate_limit_remaining_tokens": header_value(headers, "x-ratelimit-remaining-tokens"),
        "rate_limit_reset_tokens": header_value(headers, "x-ratelimit-reset-tokens"),
        "retry_after": header_value(headers, "retry-after"),
    }


def _parse_retry_after_header(value: str | None, now: datetime) -> int | None:
    if not value:
        return None
    stripped = str(value).strip()
    try:
        seconds = int(float(stripped))
    except ValueError:
        seconds = None
    if seconds is not None:
        return max(seconds, 1)
    try:
        retry_at = parsedate_to_datetime(stripped)
    except (TypeError, ValueError, IndexError, OverflowError):
        return None
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=timezone.utc)
    return max(int((retry_at.astimezone(timezone.utc) - now).total_seconds()), 1)


def _parse_retry_delay_text(value: str | None) -> int | None:
    if not value:
        return None
    text = str(value).lower()
    match = re.search(
        r"(?:try again in|retry after|retry in)\s+"
        r"(?:(?P<hours>\d+(?:\.\d+)?)\s*h(?:ours?)?)?\s*"
        r"(?:(?P<minutes>\d+(?:\.\d+)?)\s*m(?:in(?:ute)?s?)?)?\s*"
        r"(?:(?P<seconds>\d+(?:\.\d+)?)\s*s(?:ec(?:ond)?s?)?)?",
        text,
    )
    if not match:
        return None
    total = 0.0
    for name, multiplier in (("hours", 3600), ("minutes", 60), ("seconds", 1)):
        raw = match.group(name)
        if raw:
            total += float(raw) * multiplier
    if total <= 0:
        return None
    return max(int(total), 1)


def retry_after_seconds_from_rate_limit(error: Exception, headers, *, now: datetime) -> int:
    for header_name in (
        "retry-after",
        "x-ratelimit-reset-tokens",
        "x-ratelimit-reset-requests",
    ):
        retry_after = _parse_retry_after_header(header_value(headers, header_name), now)
        if retry_after is not None:
            return retry_after
        retry_after = _parse_retry_delay_text(header_value(headers, header_name))
        if retry_after is not None:
            return retry_after
    retry_after = _parse_retry_delay_text(str(error))
    if retry_after is not None:
        return retry_after
    return _rate_limit_fallback_backoff_seconds()


def active_rate_limit_backoff(
    *,
    provider: str,
    model: str,
    now: datetime | None = None,
) -> datetime | None:
    now = now or datetime.now(timezone.utc)
    key = (provider, model)
    limited_until = _llm_rate_limit_backoffs.get(key)
    if limited_until is None:
        return None
    if limited_until.tzinfo is None:
        limited_until = limited_until.replace(tzinfo=timezone.utc)
    limited_until = limited_until.astimezone(timezone.utc)
    if limited_until <= now:
        _llm_rate_limit_backoffs.pop(key, None)
        return None
    return limited_until


def get_llm_rate_limit_backoff(
    *,
    provider: str = "groq",
    model: str,
    now: datetime | None = None,
) -> datetime | None:
    """Return the active provider/model backoff expiry, if any."""
    return active_rate_limit_backoff(provider=provider, model=model, now=now)


def reset_llm_rate_limit_backoffs() -> None:
    """Clear in-memory provider/model backoffs for tests and controlled restarts."""
    _llm_rate_limit_backoffs.clear()


def start_llm_rate_limit_backoff(
    *,
    provider: str,
    model: str,
    error: Exception,
    headers,
) -> tuple[int, datetime]:
    now = datetime.now(timezone.utc)
    retry_after_seconds = retry_after_seconds_from_rate_limit(error, headers, now=now)
    limited_until = now + timedelta(seconds=retry_after_seconds)
    key = (provider, model)
    existing = active_rate_limit_backoff(provider=provider, model=model, now=now)
    if existing and existing > limited_until:
        limited_until = existing
        retry_after_seconds = max(int((limited_until - now).total_seconds()), 1)
    _llm_rate_limit_backoffs[key] = limited_until
    logger.warning(
        "ops_event=llm_rate_limit_started provider=%s model=%s retry_after_seconds=%s",
        provider,
        model,
        retry_after_seconds,
    )
    return retry_after_seconds, limited_until


async def write_llm_usage_log(
    *,
    provider: str,
    call_type: str,
    symbol: str | None,
    model: str,
    status: str,
    input_chars: int | None,
    output_chars: int | None,
    max_tokens: int | None,
    headers=None,
    response=None,
    error_reason: str | None = None,
    error_message: str | None = None,
) -> int | None:
    try:
        from bot.db.database import save_llm_usage_log
        from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL

        if not DB_ENABLED or not DB_SESSION_LOCAL:
            return None
        async with DB_SESSION_LOCAL() as session:
            row = await save_llm_usage_log(
                session,
                provider=provider,
                model=model,
                call_type=call_type,
                symbol=symbol,
                status=status,
                prompt_tokens=usage_int(response, "prompt_tokens"),
                completion_tokens=usage_int(response, "completion_tokens"),
                total_tokens=usage_int(response, "total_tokens"),
                input_chars=input_chars,
                output_chars=output_chars,
                max_tokens=max_tokens,
                error_reason=error_reason,
                error_message=error_message,
                **rate_limit_header_payload(headers),
            )
            return row.id
    except Exception as log_error:
        logger.debug("LLM usage logging failed: %s", log_error)
        return None


async def mark_llm_usage_log_status(
    usage_log_id: int | None,
    *,
    status: str,
    error_reason: str | None = None,
    error_message: str | None = None,
) -> None:
    if usage_log_id is None:
        return
    try:
        from bot.db.database import update_llm_usage_log_status
        from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL

        if not DB_ENABLED or not DB_SESSION_LOCAL:
            return
        async with DB_SESSION_LOCAL() as session:
            await update_llm_usage_log_status(
                session,
                usage_log_id=usage_log_id,
                status=status,
                error_reason=error_reason,
                error_message=error_message,
            )
    except Exception as log_error:
        logger.debug("LLM usage status update failed: %s", log_error)
