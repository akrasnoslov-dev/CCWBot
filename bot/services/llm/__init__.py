"""LLM provider fallback package.

Groq stays the primary provider; Cerebras, Gemini, and Mistral form an ordered fallback
chain. ``bot/services/ai_agent_groq.py`` remains the public entry point / facade and delegates
its HTTP calls to :func:`bot.services.llm.router.get_router`. This package owns provider
abstraction, routing, error types, and shared usage/rate-limit telemetry.
"""

from bot.services.llm.base_provider import BaseProvider, ProviderResult
from bot.services.llm.errors import (
    AIGroqRateLimitError,
    AIInvalidJsonError,
    AIProviderRateLimitError,
    AISchemaValidationError,
    AllProvidersFailedError,
    LLMRateLimitBackoffActive,
)
from bot.services.llm.router import LLMRouter, get_router
from bot.services.llm.telemetry import (
    classify_ai_error_reason,
    get_llm_rate_limit_backoff,
    mark_llm_usage_log_status,
    reset_llm_rate_limit_backoffs,
    write_llm_usage_log,
)

__all__ = [
    "BaseProvider",
    "ProviderResult",
    "LLMRouter",
    "get_router",
    "AIProviderRateLimitError",
    "AIGroqRateLimitError",
    "AIInvalidJsonError",
    "AISchemaValidationError",
    "AllProvidersFailedError",
    "LLMRateLimitBackoffActive",
    "classify_ai_error_reason",
    "mark_llm_usage_log_status",
    "get_llm_rate_limit_backoff",
    "reset_llm_rate_limit_backoffs",
    "write_llm_usage_log",
]
