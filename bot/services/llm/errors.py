"""Provider-agnostic LLM error types shared across the provider router.

These were previously defined inside ``bot/services/ai_agent_groq.py`` with Groq-specific
names. They now live here so every provider (Groq, Cerebras, Gemini, Mistral) and the
router raise the same types. ``AIGroqRateLimitError`` is kept as an alias of
``AIProviderRateLimitError`` for backward compatibility with existing callers and tests.
"""

from datetime import datetime


class AIProviderRateLimitError(RuntimeError):
    """Raised when a provider refuses a request because the account is rate limited."""

    def __init__(
        self,
        message: str,
        *,
        provider: str = "groq",
        model: str | None = None,
        retry_after_seconds: int | None = None,
        limited_until: datetime | None = None,
    ):
        super().__init__(message)
        self.provider = provider
        self.model = model
        self.retry_after_seconds = retry_after_seconds
        self.limited_until = limited_until


# Backward-compatible alias. Existing callers/tests import ``AIGroqRateLimitError``.
AIGroqRateLimitError = AIProviderRateLimitError


class LLMRateLimitBackoffActive(RuntimeError):
    """Raised when a provider/model is already in temporary rate-limit backoff."""

    def __init__(self, *, provider: str, model: str, limited_until: datetime):
        super().__init__(
            f"{provider} model {model} is rate-limited until {limited_until.isoformat()}"
        )
        self.provider = provider
        self.model = model
        self.limited_until = limited_until


class AIInvalidJsonError(RuntimeError):
    """Raised when the provider response is not valid JSON."""

    def __init__(self, message: str, raw_content: str | None = None):
        super().__init__(message)
        self.raw_content = raw_content


class AISchemaValidationError(RuntimeError):
    """Raised when validated JSON does not match the expected schema.

    ``raw_content`` optionally carries the offending provider output so terminal
    handlers can persist it for diagnosis, mirroring ``AIInvalidJsonError``.
    """

    def __init__(self, message: str, raw_content: str | None = None):
        super().__init__(message)
        self.raw_content = raw_content


class AllProvidersFailedError(RuntimeError):
    """Raised when every provider in the fallback chain has been exhausted.

    ``last_error`` is the final underlying exception; ``rate_limited`` is True when the
    terminal failure was a rate limit, so callers can preserve the existing
    rate-limited deterministic-fallback behaviour.

    ``circuit_broken`` is True when no provider was actually attempted because every one of
    them was in an open circuit breaker. That is a materially different state from "attempted
    them all and they failed", and it must survive to the persisted ``error_reason`` so the
    evidence trail distinguishes "known-bad, waiting to probe" from a fresh failure.

    ``mixed_failure`` is True when some providers were rate-limited while others failed for
    another fallback-eligible reason. This is a terminal logical failure, not proof that the
    logical call itself was rate-limited.
    """

    def __init__(
        self,
        message: str,
        *,
        last_error: Exception | None = None,
        rate_limited: bool = False,
        attempts: list[str] | None = None,
        circuit_broken: bool = False,
        mixed_failure: bool = False,
    ):
        super().__init__(message)
        self.last_error = last_error
        self.rate_limited = rate_limited
        self.attempts = attempts or []
        self.circuit_broken = circuit_broken
        self.mixed_failure = mixed_failure
