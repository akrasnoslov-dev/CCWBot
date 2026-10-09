"""LLM router: iterate providers by priority for a call type, falling back on failure.

The router is the single common path every LLM call goes through. It resolves the ordered
provider chain for a call type, skips providers with no API key, and attempts each in turn.
It advances to the next provider on a transient/transport failure (rate limit, timeout, 5xx,
auth, network) and on a provider-side model failure (``404 model_not_found``,
``model_decommissioned``, and the equivalents from the other providers). It surfaces a genuine
request defect — malformed parameters, oversized payload — to the caller unchanged, because
retrying that across the chain only multiplies cost. Per-attempt usage logging and
``(provider, model)`` backoff are handled inside each provider via the shared telemetry module.

A ``(call_type, provider, model)`` triple that keeps failing deterministically is opened by
the circuit breaker in :mod:`bot.services.llm.breaker` and skipped on later cycles until its
backoff elapses. Skipping advances the chain immediately, so a broken primary means the
fallback answers this cycle rather than the cycle being lost.

When callers pass ``validate_response``, invalid provider *output* is also fallback-eligible:
the callback parses/validates each provider's raw response and raises ``AIInvalidJsonError``
or ``AISchemaValidationError`` when the output cannot be trusted, which makes the router
advance to the next provider (logged as ``llm_provider_switch reason=invalid_output``).
Each concrete provider/model entry is attempted at most once per logical call. A provider may
appear more than once when the chain intentionally tries distinct models (Event Alert Render uses
this for GPT-OSS followed by Qwen on Groq); there is still no retry loop for the same entry.

Exhaustion mapping preserves the exception contract existing callers already handle:
- if any provider returned invalid output -> the last ``AIInvalidJsonError`` /
  ``AISchemaValidationError`` is re-raised, so reports/event-analysis keep their existing
  deterministic-fallback handling for malformed model output.
- every provider skipped because it was already in active backoff -> ``LLMRateLimitBackoffActive``
  (so Event Analysis / Heartbeat still record ``skipped_due_to_rate_limit``).
- otherwise, if every provider that made a request hit a rate limit -> ``AIProviderRateLimitError``
  (== ``AIGroqRateLimitError`` alias, so the price-alert path still produces its rate-limited
  deterministic fallback, and reports/event-analysis fall through to their existing handlers);
  attributed to the first rate-limited provider.
- otherwise (timeouts / 5xx / other transport failures) -> ``AllProvidersFailedError``.
"""

import logging

from bot.services.llm import breaker, config
from bot.services.llm.cloudflare_provider import get_provider as _cloudflare_provider
from bot.services.llm.errors import (
    AIInvalidJsonError,
    AIProviderRateLimitError,
    AISchemaValidationError,
    AllProvidersFailedError,
    LLMRateLimitBackoffActive,
)
from bot.services.llm.gemini_provider import get_provider as _gemini_provider
from bot.services.llm.groq_provider import get_provider as _groq_provider
from bot.services.llm.mistral_provider import get_provider as _mistral_provider
from bot.services.llm.operation import (
    current_llm_operation_id,
    llm_operation_scope,
    new_llm_operation_id,
)
from bot.services.llm.telemetry import (
    classify_ai_error_reason,
    message_input_chars,
    write_llm_usage_log,
)

logger = logging.getLogger(__name__)

# Reasons that mean "this provider is unusable right now, try the next one".
#
# ``provider_model_error`` and ``provider_json_validate_failed`` are 4xx responses that are
# nonetheless *provider-side* facts, so they belong here:
#
# - ``provider_model_error`` is "this model cannot serve the request" (404 model_not_found,
#   model_decommissioned, and the equivalents from the other three providers). A different
#   provider running a different model can answer it. This omission is what kept the fallback
#   chain from engaging for 18 days when Groq decommissioned the event-analysis model.
# - ``provider_json_validate_failed`` is the provider's own JSON-mode validation rejecting the
#   model's output. That is unusable *output*, not a defective request — the same condition as
#   ``AIInvalidJsonError``, which this router has always treated as fallback-eligible. It is
#   here so the two paths agree regardless of whether the broken JSON was caught server-side
#   or client-side.
#
# Deliberately NOT here: ``provider_bad_request`` and the residual ``provider_4xx``. A
# malformed request, an oversized payload, or an unsupported parameter fails identically on
# every provider, so retrying it across the chain only multiplies cost.
_FALLBACK_REASONS = frozenset(
    {
        "rate_limit",
        "timeout",
        "provider_5xx",
        "auth_error",
        "network_error",
        "empty_response",
        "config_missing",
        "provider_model_error",
        "provider_json_validate_failed",
        "provider_quota_exhausted",
    }
)

# Providers whose incomplete configuration we have already logged, to avoid per-call log spam.
_warned_unconfigured: set[str] = set()


def _default_registry() -> dict:
    return {
        "groq": _groq_provider(),
        "gemini": _gemini_provider(),
        "mistral": _mistral_provider(),
        "cloudflare": _cloudflare_provider(),
    }


class LLMRouter:
    def __init__(self, registry: dict | None = None):
        self._registry = registry if registry is not None else _default_registry()

    def _attempts_for(self, call_type: str) -> list[tuple[str, object, str]]:
        selected: list[tuple[str, object, str]] = []
        for name, model in config.provider_attempts(call_type):
            provider = self._registry.get(name)
            if provider is None:
                continue
            if not config.provider_is_configured(name):
                if name not in _warned_unconfigured:
                    _warned_unconfigured.add(name)
                    logger.info(
                        "ops_event=llm_provider_excluded provider=%s reason=missing_config",
                        name,
                    )
                continue
            selected.append((name, provider, model))
        return selected

    async def chat_completion(
        self,
        *,
        call_type: str,
        messages: list[dict],
        max_tokens: int,
        response_format: dict | None,
        response_format_overrides: dict[str, dict | None] | None = None,
        timeout: int = 15,
        symbol: str | None = None,
        model_overrides: dict | None = None,
        validate_response=None,
    ):
        operation_id = current_llm_operation_id() or new_llm_operation_id()
        with llm_operation_scope(operation_id):
            try:
                result = await self._chat_completion(
                    call_type=call_type,
                    messages=messages,
                    max_tokens=max_tokens,
                    response_format=response_format,
                    response_format_overrides=response_format_overrides,
                    timeout=timeout,
                    symbol=symbol,
                    model_overrides=model_overrides,
                    validate_response=validate_response,
                )
            except Exception as error:
                error.operation_id = operation_id
                raise
            try:
                result.operation_id = operation_id
            except AttributeError:
                pass
            return result

    async def _chat_completion(
        self,
        *,
        call_type: str,
        messages: list[dict],
        max_tokens: int,
        response_format: dict | None,
        response_format_overrides: dict[str, dict | None] | None = None,
        timeout: int = 15,
        symbol: str | None = None,
        model_overrides: dict | None = None,
        validate_response=None,
    ):
        """Run one logical LLM call over the provider chain.

        ``validate_response`` is an optional async callback receiving the
        :class:`ProviderResult`; it must return the validated value (which becomes this
        method's return value) or raise ``AIInvalidJsonError`` / ``AISchemaValidationError``
        to mark the provider's output as unusable and advance the chain. Without it the raw
        :class:`ProviderResult` is returned unchanged.
        """
        attempts = self._attempts_for(call_type)
        if not attempts:
            raise AllProvidersFailedError(
                f"No configured LLM providers for call_type={call_type}",
                rate_limited=False,
                attempts=[],
            )

        first_backoff_error: LLMRateLimitBackoffActive | None = None
        attempted = 0
        saw_rate_limit = False
        saw_other_fallback = False
        rate_limited_name: str | None = None
        rate_limited_model: str | None = None
        rate_limit_untils: list = []
        last_error: Exception | None = None
        invalid_output_error: Exception | None = None
        breaker_skipped: list[str] = []
        attempted_names: list[str] = []
        failure_categories: list[str] = []
        input_chars = message_input_chars(messages)

        for index, (name, provider, configured_model) in enumerate(attempts):
            model = (model_overrides or {}).get(name) or configured_model
            attempt_max_tokens = config.effective_max_tokens_for(
                call_type=call_type,
                provider=name,
                model=model,
                requested_max_tokens=max_tokens,
            )
            # An open breaker means "do not spend a request on this pair", not "give up this
            # cycle": skipping here advances immediately to the next provider, so a dead
            # primary costs nothing and the fallback still answers.
            if breaker.should_skip(call_type=call_type, provider=name, model=model):
                breaker_skipped.append(name)
                # Record the skip in llm_usage_logs, mirroring the rate-limit pre-call skip.
                # Without this a broken provider simply stops appearing in the table once its
                # breaker opens, so the evidence of an ongoing outage would fade out a few
                # cycles after it starts — the opposite of what this work is for.
                await write_llm_usage_log(
                    provider=name,
                    call_type=call_type,
                    symbol=symbol,
                    model=model,
                    status="skipped_due_to_circuit_breaker",
                    input_chars=input_chars,
                    output_chars=None,
                    max_tokens=attempt_max_tokens,
                    error_reason="provider_circuit_broken",
                    error_message=f"{name} model {model} is circuit-broken for {call_type}",
                )
                logger.info(
                    "ops_event=llm_call_completed provider=%s model=%s call_type=%s "
                    "status=skipped_due_to_circuit_breaker operation_id=%s",
                    name,
                    model,
                    call_type,
                    current_llm_operation_id(),
                )
                continue
            # Resolved from the model this attempt will actually use: a chain that mixes
            # reasoning and non-reasoning models sends the parameter only to the attempts that
            # accept it, and omits it entirely everywhere else.
            reasoning_effort = config.reasoning_effort_for(model, call_type)
            attempt_response_format = response_format
            if response_format_overrides is not None:
                model_key = f"{name}:{model}"
                if model_key in response_format_overrides:
                    attempt_response_format = response_format_overrides[model_key]
                elif name in response_format_overrides:
                    attempt_response_format = response_format_overrides[name]
            attempted_names.append(name)
            try:
                result = await provider.chat_completion(
                    call_type=call_type,
                    symbol=symbol,
                    model=model,
                    messages=messages,
                    max_tokens=attempt_max_tokens,
                    response_format=attempt_response_format,
                    timeout=timeout,
                    reasoning_effort=reasoning_effort,
                )
            except LLMRateLimitBackoffActive as error:
                # Provider was already in active backoff and did not make an HTTP call, so a
                # half-open breaker probe spent here learned nothing — give it back.
                breaker.record_not_attempted(call_type=call_type, provider=name, model=model)
                if attempted_names and attempted_names[-1] == name:
                    attempted_names.pop()
                if first_backoff_error is None:
                    first_backoff_error = error
                last_error = error
                failure_categories.append(f"{name}:rate_limit_backoff_active")
                continue
            except AIProviderRateLimitError as error:
                attempted += 1
                saw_rate_limit = True
                last_error = error
                if rate_limited_name is None:
                    rate_limited_name = name
                    rate_limited_model = model
                if error.limited_until is not None:
                    rate_limit_untils.append(error.limited_until)
                failure_categories.append(f"{name}:rate_limit")
                logger.warning(
                    "ops_event=llm_provider_switch provider=%s call_type=%s "
                    "reason=rate_limit operation_id=%s",
                    name,
                    call_type,
                    current_llm_operation_id(),
                )
                continue
            except Exception as error:
                reason = classify_ai_error_reason(error)
                breaker.record_failure(
                    call_type=call_type, provider=name, model=model, reason=reason
                )
                if reason in _FALLBACK_REASONS:
                    attempted += 1
                    last_error = error
                    if reason == "rate_limit":
                        saw_rate_limit = True
                        if rate_limited_name is None:
                            rate_limited_name = name
                            rate_limited_model = model
                    else:
                        saw_other_fallback = True
                    failure_categories.append(f"{name}:{reason}")
                    logger.warning(
                        "ops_event=llm_provider_switch provider=%s call_type=%s "
                        "reason=%s operation_id=%s",
                        name,
                        call_type,
                        reason,
                        current_llm_operation_id(),
                    )
                    continue
                # Genuine request defect — surface unchanged, without advancing the chain.
                raise

            # The provider answered over HTTP, so the pair is reachable and serving this model.
            # Output that turns out to be unusable is handled by the chain below; it is not a
            # reason to keep a breaker latched against a working endpoint.
            breaker.record_success(call_type=call_type, provider=name, model=model)
            # Validators persist usage after parsing/schema checks. Carry the actual per-attempt
            # budget so telemetry never reports the smaller plain-model base for a thinking model.
            result.max_tokens = attempt_max_tokens

            if validate_response is not None:
                try:
                    validated = await validate_response(result)
                except (AIInvalidJsonError, AISchemaValidationError) as error:
                    # Unusable output (broken JSON / schema mismatch) is fallback-eligible,
                    # same as a provider 5xx: advance to the next provider in the chain.
                    attempted += 1
                    invalid_output_error = error
                    last_error = error
                    failure_categories.append(
                        f"{name}:{classify_ai_error_reason(error)}"
                    )
                    logger.warning(
                        "ops_event=llm_provider_switch provider=%s call_type=%s "
                        "reason=invalid_output operation_id=%s",
                        name,
                        call_type,
                        current_llm_operation_id(),
                    )
                    continue
            else:
                validated = result

            if index > 0:
                logger.info(
                    "ops_event=llm_provider_used provider=%s call_type=%s "
                    "after_fallback=true operation_id=%s",
                    name,
                    call_type,
                    current_llm_operation_id(),
                )
            return validated

        # Chain exhausted. Emit categories only: no provider body, prompt, output, or secret.
        # Per-attempt sanitized details remain available in llm_usage_logs.
        if failure_categories or breaker_skipped:
            logger.warning(
                "ops_event=llm_chain_exhausted call_type=%s failures=%s "
                "breaker_skipped=%s operation_id=%s",
                call_type,
                ",".join(failure_categories) or "none",
                ",".join(breaker_skipped) or "none",
                current_llm_operation_id(),
            )

        # Choose the exception that matches existing caller handling.
        if invalid_output_error is not None:
            # Preserve the existing exception contract for other call types, but expose
            # whether every attempted provider failed on invalid output. Render may
            # recover only in this case; mixed transport, rate-limit, backoff, and
            # open-breaker exhaustion must remain terminal.
            invalid_output_reasons = {"invalid_json", "schema_validation_failed"}
            invalid_output_error._llm_all_exhausted_attempts_invalid_output = (
                bool(failure_categories)
                and not breaker_skipped
                and all(
                    category.rsplit(":", 1)[-1] in invalid_output_reasons
                    for category in failure_categories
                )
            )
            raise invalid_output_error

        only_pre_backoff = (
            first_backoff_error is not None
            and attempted == 0
            and not saw_rate_limit
            and not saw_other_fallback
        )
        if only_pre_backoff:
            raise first_backoff_error

        if saw_rate_limit and not saw_other_fallback:
            # A terminal rate-limit outcome is accurate only when every provider that made a
            # request was rate-limited. Mixed exhausted chains remain AllProvidersFailedError:
            # a 429 from one provider is provider pressure, not proof that the logical call was
            # terminally rate-limited.
            terminal_name = rate_limited_name or attempts[-1][0]
            terminal_model = rate_limited_model or attempts[-1][2]
            limited_until = min(rate_limit_untils) if rate_limit_untils else None
            raise AIProviderRateLimitError(
                f"All providers rate limited for call_type={call_type}",
                provider=terminal_name,
                model=terminal_model,
                limited_until=limited_until,
            ) from last_error

        if breaker_skipped and attempted == 0:
            # Every configured provider is in an open breaker. Report that distinctly so the
            # cause is "all known-bad, waiting to probe" rather than "all attempted and failed".
            raise AllProvidersFailedError(
                f"All providers circuit-broken for call_type={call_type}",
                last_error=last_error,
                rate_limited=False,
                attempts=[],
                circuit_broken=True,
            ) from last_error

        raise AllProvidersFailedError(
            f"All providers failed for call_type={call_type}",
            last_error=last_error,
            rate_limited=False,
            attempts=attempted_names,
            mixed_failure=saw_rate_limit and saw_other_fallback,
        ) from last_error


_router: LLMRouter | None = None


def get_router() -> LLMRouter:
    """Return the process-wide router singleton (lazily created)."""
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router
