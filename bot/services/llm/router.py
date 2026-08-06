"""LLM router: iterate providers by priority for a call type, falling back on failure.

The router is the single common path every LLM call goes through. It resolves the ordered
provider chain for a call type, skips providers with no API key, and attempts each in turn.
On a transient/transport failure (rate limit, timeout, 5xx, auth, network) it advances to the
next provider; on a deterministic error (e.g. a 4xx bad request) it surfaces the error to the
caller unchanged. Per-attempt usage logging and ``(provider, model)`` backoff are handled
inside each provider via the shared telemetry module.

When callers pass ``validate_response``, invalid provider *output* is also fallback-eligible:
the callback parses/validates each provider's raw response and raises ``AIInvalidJsonError``
or ``AISchemaValidationError`` when the output cannot be trusted, which makes the router
advance to the next provider (logged as ``llm_provider_switch reason=invalid_output``).
Each provider is attempted at most once per logical call — one full pass over the chain,
never a retry loop on the same provider.

Exhaustion mapping preserves the exception contract existing callers already handle:
- if any provider returned invalid output -> the last ``AIInvalidJsonError`` /
  ``AISchemaValidationError`` is re-raised, so reports/event-analysis keep their existing
  deterministic-fallback handling for malformed model output.
- every provider skipped because it was already in active backoff -> ``LLMRateLimitBackoffActive``
  (so Event Analysis / Heartbeat still record ``skipped_due_to_rate_limit``).
- otherwise, if any provider in the chain hit a rate limit -> ``AIProviderRateLimitError``
  (== ``AIGroqRateLimitError`` alias, so the price-alert path still produces its rate-limited
  deterministic fallback, and reports/event-analysis fall through to their existing handlers);
  attributed to the first rate-limited provider.
- otherwise (timeouts / 5xx / other transport failures) -> ``AllProvidersFailedError``.
"""

import logging

from bot.services.llm import config
from bot.services.llm.cerebras_provider import get_provider as _cerebras_provider
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
from bot.services.llm.telemetry import classify_ai_error_reason

logger = logging.getLogger(__name__)

# Reasons that mean "this provider is unusable right now, try the next one".
_FALLBACK_REASONS = frozenset(
    {
        "rate_limit",
        "timeout",
        "provider_5xx",
        "auth_error",
        "network_error",
        "empty_response",
        "config_missing",
    }
)

# Providers whose missing API key we have already logged, to avoid per-call log spam.
_warned_missing_keys: set[str] = set()


def _default_registry() -> dict:
    return {
        "groq": _groq_provider(),
        "cerebras": _cerebras_provider(),
        "gemini": _gemini_provider(),
        "mistral": _mistral_provider(),
    }


class LLMRouter:
    def __init__(self, registry: dict | None = None):
        self._registry = registry if registry is not None else _default_registry()

    def _providers_for(self, call_type: str) -> list[tuple[str, object]]:
        selected: list[tuple[str, object]] = []
        for name in config.provider_priority(call_type):
            provider = self._registry.get(name)
            if provider is None:
                continue
            if config.api_key(name) is None:
                if name not in _warned_missing_keys:
                    _warned_missing_keys.add(name)
                    logger.info(
                        "ops_event=llm_provider_excluded provider=%s reason=missing_api_key",
                        name,
                    )
                continue
            selected.append((name, provider))
        return selected

    async def chat_completion(
        self,
        *,
        call_type: str,
        messages: list[dict],
        max_tokens: int,
        response_format: dict | None,
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
        providers = self._providers_for(call_type)
        if not providers:
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
        rate_limit_untils: list = []
        last_error: Exception | None = None
        invalid_output_error: Exception | None = None

        for index, (name, provider) in enumerate(providers):
            model = (model_overrides or {}).get(name) or config.model_for(name, call_type)
            # Resolved from the model this attempt will actually use: a chain that mixes
            # reasoning and non-reasoning models sends the parameter only to the attempts that
            # accept it, and omits it entirely everywhere else.
            reasoning_effort = config.reasoning_effort_for(model, call_type)
            try:
                result = await provider.chat_completion(
                    call_type=call_type,
                    symbol=symbol,
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    response_format=response_format,
                    timeout=timeout,
                    reasoning_effort=reasoning_effort,
                )
            except LLMRateLimitBackoffActive as error:
                # Provider was already in active backoff and did not make an HTTP call.
                if first_backoff_error is None:
                    first_backoff_error = error
                last_error = error
                continue
            except AIProviderRateLimitError as error:
                attempted += 1
                saw_rate_limit = True
                last_error = error
                if rate_limited_name is None:
                    rate_limited_name = name
                if error.limited_until is not None:
                    rate_limit_untils.append(error.limited_until)
                logger.warning(
                    "ops_event=llm_provider_switch provider=%s call_type=%s reason=rate_limit",
                    name,
                    call_type,
                )
                continue
            except Exception as error:
                reason = classify_ai_error_reason(error)
                if reason in _FALLBACK_REASONS:
                    attempted += 1
                    last_error = error
                    if reason == "rate_limit":
                        saw_rate_limit = True
                        if rate_limited_name is None:
                            rate_limited_name = name
                    else:
                        saw_other_fallback = True
                    logger.warning(
                        "ops_event=llm_provider_switch provider=%s call_type=%s reason=%s",
                        name,
                        call_type,
                        reason,
                    )
                    continue
                # Deterministic error (e.g. 4xx / JSON-mode validation) — surface unchanged.
                raise

            if validate_response is not None:
                try:
                    validated = await validate_response(result)
                except (AIInvalidJsonError, AISchemaValidationError) as error:
                    # Unusable output (broken JSON / schema mismatch) is fallback-eligible,
                    # same as a provider 5xx: advance to the next provider in the chain.
                    attempted += 1
                    invalid_output_error = error
                    last_error = error
                    logger.warning(
                        "ops_event=llm_provider_switch provider=%s call_type=%s "
                        "reason=invalid_output",
                        name,
                        call_type,
                    )
                    continue
            else:
                validated = result

            if index > 0:
                logger.info(
                    "ops_event=llm_provider_used provider=%s call_type=%s after_fallback=true",
                    name,
                    call_type,
                )
            return validated

        # Chain exhausted. Choose the exception that matches existing caller handling.
        if invalid_output_error is not None:
            # Re-raise the last invalid-output error so callers keep their existing
            # AIInvalidJsonError / AISchemaValidationError terminal handling
            # (deterministic fallbacks for reports, failed-analysis records for events).
            raise invalid_output_error

        only_pre_backoff = (
            first_backoff_error is not None
            and attempted == 0
            and not saw_rate_limit
            and not saw_other_fallback
        )
        if only_pre_backoff:
            raise first_backoff_error

        if saw_rate_limit:
            # Attribute to the first provider that was actually rate limited, not just the last
            # provider in the chain (which may have failed for a different reason).
            terminal_name = rate_limited_name or providers[-1][0]
            limited_until = min(rate_limit_untils) if rate_limit_untils else None
            raise AIProviderRateLimitError(
                f"All providers rate limited for call_type={call_type}",
                provider=terminal_name,
                model=config.model_for(terminal_name, call_type),
                limited_until=limited_until,
            ) from last_error

        raise AllProvidersFailedError(
            f"All providers failed for call_type={call_type}",
            last_error=last_error,
            rate_limited=False,
            attempts=[name for name, _ in providers],
        ) from last_error


_router: LLMRouter | None = None


def get_router() -> LLMRouter:
    """Return the process-wide router singleton (lazily created)."""
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router
