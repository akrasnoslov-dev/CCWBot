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
    AllProvidersFailedError,
    LLMRateLimitBackoffActive,
)
from bot.services.llm.operation import current_llm_operation_id

logger = logging.getLogger(__name__)
_SAFE_PROVIDER_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_UNSAFE_PROVIDER_REQUEST_ID_RE = re.compile(
    r"^(?:bearer|sk-|gsk_|pk_|rk_|whsec_|ghp_|github_pat_|xox|akia|aiza|api[_-]?key|token|secret|password)",
    re.IGNORECASE,
)


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
RATE_LIMIT_BACKOFF_CALL_TYPES = {
    "event_analysis",
    "market_heartbeat",
    "daily_report",
    "weekly_report",
    "market_report",
    "news_intelligence",
    "legacy_alert_payload",
}

# Temporary in-memory backoff keyed by (provider, model). Shared process-wide.
_llm_rate_limit_backoffs: dict[tuple[str, str], datetime] = {}
_llm_rate_limit_backoff_call_types: dict[tuple[str, str], set[str]] = {}


# A 4xx is not one thing. "This model no longer exists" is a provider-side fact that the next
# provider in the chain can answer, while "this request is malformed" would fail identically
# everywhere. Collapsing both into `provider_4xx` is what kept the fallback chain from engaging
# when Groq decommissioned the event-analysis model. Each sub-kind keeps the `provider_` prefix
# so existing consumers that match `provider_%` continue to bucket them.
# Unambiguous provider error codes. Matched anywhere in the haystack.
_MODEL_ERROR_MARKERS = (
    "model_not_found",
    "model_decommissioned",
    "model_not_available",
    "model_unavailable",
    "unknown_model",
    "invalid_model",
)

# Billing/quota errors are provider availability failures, not client request defects and not
# temporary 429 rate limits. Keep this list to explicit provider error identifiers; arbitrary
# response text can contain user-controlled data and must not change routing semantics.
_QUOTA_EXHAUSTED_MARKERS = frozenset(
    {
        "payment_required",
        "payment_required_error",
        "quota",
        "quota_exceeded",
        "insufficient_quota",
        "credits_exhausted",
        "insufficient_credits",
        "billing_quota_exhausted",
        "account_quota_exhausted",
    }
)

# Free-text variants. These require the word "model" near the failure phrase: bare phrases like
# "does not exist" also appear in genuine request defects ("parameter 'foo' does not exist"),
# which must stay terminal rather than being retried across the whole chain.
_MODEL_ERROR_MESSAGE_RE = re.compile(
    r"models?\b[^\n]{0,60}?"
    r"(?:does not exist|is not found|not found|decommissioned|no longer supported"
    r"|unsupported|unknown|invalid|deprecated)"
    r"|(?:unknown|invalid|unsupported|decommissioned)\s+models?\b"
)

# Genuine request defects: retrying these across the chain only multiplies cost.
_BAD_REQUEST_MARKERS = (
    "context_length_exceeded",
    "context length",
    "too many tokens",
    "string too long",
    "request too large",
    "payload too large",
    "invalid_request_error",
    "unsupported parameter",
    "unknown parameter",
    "unrecognized request argument",
    "invalid value",
    "missing required",
)


def is_model_unavailable_error(error: Exception) -> bool:
    """True when the provider says the requested model cannot serve this request.

    Covers ``404 model_not_found`` and the ``model_decommissioned`` / equivalent identifiers
    the other providers use. A 404 from a chat-completions endpoint is treated as a model or
    endpoint addressing failure either way — in both cases the next provider is worth trying.
    """
    status_code = _effective_status_code(error)
    haystack = _error_haystack(error)
    if any(marker in haystack for marker in _MODEL_ERROR_MARKERS):
        return True
    if _MODEL_ERROR_MESSAGE_RE.search(haystack):
        return True
    return status_code == 404


def is_provider_bad_request_error(error: Exception) -> bool:
    """True when the request itself is defective, so every provider would reject it."""
    haystack = _error_haystack(error)
    if any(marker in haystack for marker in _BAD_REQUEST_MARKERS):
        return True
    return _effective_status_code(error) == 413


def _effective_status_code(error: Exception) -> int | None:
    status_code = getattr(error, "status_code", None)
    response = getattr(error, "response", None)
    effective = status_code if status_code is not None else getattr(response, "status_code", None)
    try:
        return int(effective) if effective is not None else None
    except (TypeError, ValueError):
        return None


def _error_fields(error: Exception) -> list[str]:
    parts = [str(error)]
    for attribute in ("code", "type"):
        value = getattr(error, attribute, None)
        if isinstance(value, str):
            parts.append(value)
    body = getattr(error, "body", None)
    if isinstance(body, dict):
        nested = body.get("error")
        source = nested if isinstance(nested, dict) else body
        for key in ("code", "type", "message"):
            value = source.get(key)
            if isinstance(value, str):
                parts.append(value)
    return parts


def _provider_error_identifiers(error: Exception) -> set[str]:
    """Return provider code/type fields without inspecting free-text response messages."""
    identifiers: set[str] = set()
    for attribute in ("code", "type"):
        value = getattr(error, attribute, None)
        if isinstance(value, str):
            identifiers.add(value.strip().lower())
    body = getattr(error, "body", None)
    if isinstance(body, dict):
        nested = body.get("error")
        source = nested if isinstance(nested, dict) else body
        for key in ("code", "type"):
            value = source.get(key)
            if isinstance(value, str):
                identifiers.add(value.strip().lower())
    return identifiers


def is_provider_quota_exhausted_error(error: Exception) -> bool:
    """True for a provider billing/quota refusal that another provider can serve."""
    candidates = [error]
    for attribute in ("last_error", "__cause__"):
        wrapped = getattr(error, attribute, None)
        if isinstance(wrapped, BaseException) and wrapped is not error:
            candidates.append(wrapped)
    return any(
        _effective_status_code(candidate) == 402
        or bool(_provider_error_identifiers(candidate) & _QUOTA_EXHAUSTED_MARKERS)
        for candidate in candidates
    )


def _error_haystack(error: Exception) -> str:
    """Lowercased text to match markers against: message, provider error code, and body.

    Also folds in one level of wrapping (``last_error`` / ``__cause__``). Once a failure is
    fallback-eligible the router surfaces it wrapped in ``AllProvidersFailedError``, and
    callers that ask "was this a JSON-mode validation failure?" would otherwise see only the
    wrapper's generic message — which silently disabled the ``GROQ_JSON_MODE_RETRY_PLAIN``
    path. One level is enough and keeps this bounded.
    """
    parts = _error_fields(error)
    for attribute in ("last_error", "__cause__"):
        wrapped = getattr(error, attribute, None)
        if isinstance(wrapped, BaseException) and wrapped is not error:
            parts.extend(_error_fields(wrapped))
    return " ".join(parts).lower()


def classify_ai_error_reason(error: Exception) -> str:
    """Return an admin-safe LLM failure reason (stable across all providers)."""
    if isinstance(error, LLMRateLimitBackoffActive):
        return "rate_limit_backoff_active"
    if getattr(error, "circuit_broken", False):
        # Every provider was skipped by an open breaker, so nothing was attempted. Keeping
        # this distinct from a fresh failure is what makes "known-bad, waiting to probe"
        # readable in event_ai_analyses.error_reason instead of a generic other_error.
        return "provider_circuit_broken"
    if isinstance(error, AllProvidersFailedError) and error.mixed_failure:
        return "mixed_provider_failures"
    # Billing/quota codes are a provider availability failure even when a provider assigns a
    # 429 status or includes rate-limit-like wording. Rate limits without an explicit quota
    # code remain below, so only the provider's structured quota signal changes this routing.
    if is_provider_quota_exhausted_error(error):
        return "provider_quota_exhausted"
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
            # Sub-classify so the router can tell "this provider cannot serve this model"
            # (worth trying the next provider) from "this request is broken" (is not).
            #
            # Order is load-bearing. Groq's real decommission response carries BOTH
            # code="model_decommissioned" AND type="invalid_request_error", and the latter
            # matches _BAD_REQUEST_MARKERS. Checking the model case first is what keeps the
            # 2026-07 outage from reproducing; see the regression test that pins this.
            if is_model_unavailable_error(error):
                return "provider_model_error"
            if is_json_validation_error(error):
                return "provider_json_validate_failed"
            if is_provider_bad_request_error(error):
                return "provider_bad_request"
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
    # Matches the full haystack (message plus provider ``code``/``type``/``body``), not just
    # ``str(error)``: Groq carries the marker in ``code`` as well as the message, and a client
    # that surfaces only the structured fields would otherwise fall through to the
    # ``invalid_request_error`` marker and be misread as a defective request.
    haystack = _error_haystack(error)
    return (
        "json_validate_failed" in haystack
        or "validate json" in haystack
        or "json validation" in haystack
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


def _safe_provider_request_id(headers) -> str | None:
    """Return a bounded opaque provider trace ID, never a raw header value."""
    if headers is None:
        return None
    for name in ("x-request-id", "request-id"):
        try:
            value = headers.get(name)
        except AttributeError:
            continue
        if not isinstance(value, str):
            continue
        is_safe = _SAFE_PROVIDER_REQUEST_ID_RE.fullmatch(value) is not None
        is_secret_shaped = _UNSAFE_PROVIDER_REQUEST_ID_RE.match(value) is not None
        if is_safe and not is_secret_shaped:
            return value
    return None


def rate_limit_header_payload(headers) -> dict:
    provider_request_id = _safe_provider_request_id(headers)
    return {
        "rate_limit_limit_requests": header_value(headers, "x-ratelimit-limit-requests"),
        "rate_limit_remaining_requests": header_value(headers, "x-ratelimit-remaining-requests"),
        "rate_limit_reset_requests": header_value(headers, "x-ratelimit-reset-requests"),
        "rate_limit_limit_tokens": header_value(headers, "x-ratelimit-limit-tokens"),
        "rate_limit_remaining_tokens": header_value(headers, "x-ratelimit-remaining-tokens"),
        "rate_limit_reset_tokens": header_value(headers, "x-ratelimit-reset-tokens"),
        "retry_after": header_value(headers, "retry-after"),
        # This exact allowlist entry is an opaque provider trace identifier.  Do not add
        # arbitrary headers here: headers can include credentials or account metadata.
        "provider_request_id": provider_request_id,
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
        _llm_rate_limit_backoff_call_types.pop(key, None)
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


def get_active_llm_rate_limit_backoffs(
    *, now: datetime | None = None
) -> tuple[dict[str, object], ...]:
    """Return a sanitized snapshot of active provider/model backoffs and their call types."""
    now = now or datetime.now(timezone.utc)
    rows: list[dict[str, object]] = []
    for provider, model in sorted(_llm_rate_limit_backoffs):
        limited_until = active_rate_limit_backoff(provider=provider, model=model, now=now)
        if limited_until is None:
            continue
        rows.append(
            {
                "provider": provider,
                "model": model,
                "limited_until": limited_until,
                "call_types": tuple(
                    sorted(_llm_rate_limit_backoff_call_types.get((provider, model), set()))
                ),
            }
        )
    return tuple(rows)


def reset_llm_rate_limit_backoffs() -> None:
    """Clear in-memory provider/model backoffs for tests and controlled restarts."""
    _llm_rate_limit_backoffs.clear()
    _llm_rate_limit_backoff_call_types.clear()


def start_llm_rate_limit_backoff(
    *,
    provider: str,
    model: str,
    call_type: str,
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
    _llm_rate_limit_backoff_call_types.setdefault(key, set()).add(call_type)
    logger.warning(
        "ops_event=llm_rate_limit_started provider=%s model=%s call_type=%s "
        "retry_after_seconds=%s operation_id=%s",
        provider,
        model,
        call_type,
        retry_after_seconds,
        current_llm_operation_id(),
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
    operation_id: str | None = None,
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
                llm_operation_id=operation_id or current_llm_operation_id(),
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
    llm_operation_id: str | None = None,
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
                llm_operation_id=llm_operation_id,
            )
    except Exception as log_error:
        logger.debug("LLM usage status update failed: %s", log_error)
