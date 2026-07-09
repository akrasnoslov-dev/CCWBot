"""Environment-driven configuration for the LLM provider fallback chain.

All lookups read ``os.getenv`` at call time so provider priority, API keys, and model
selection can be changed via environment without code changes (and monkeypatched in tests).
A provider with no API key is excluded from the chain by the router, not here.
"""

import os

# Ordered default chain: Groq primary, then Cerebras, Gemini, Mistral.
DEFAULT_PROVIDER_PRIORITY = ["groq", "cerebras", "gemini", "mistral"]
KNOWN_PROVIDERS = frozenset(DEFAULT_PROVIDER_PRIORITY)

# Per-call-type priority override env vars; fall back to LLM_PROVIDER_PRIORITY when unset.
_CALL_TYPE_PRIORITY_ENV = {
    "event_analysis": "LLM_EVENT_PROVIDERS",
    "market_heartbeat": "LLM_HEARTBEAT_PROVIDERS",
    "daily_report": "LLM_REPORT_PROVIDERS",
    "weekly_report": "LLM_REPORT_PROVIDERS",
    "market_report": "LLM_REPORT_PROVIDERS",
}

_PROVIDER_API_KEY_ENV = {
    "groq": "GROQ_API_KEY",
    "cerebras": "CEREBRAS_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "mistral": "MISTRAL_API_KEY",
}

# All four providers are reached through the OpenAI-compatible chat-completions API, so we
# only need a base URL per provider — no extra client library. Gemini exposes an
# OpenAI-compatible endpoint, which keeps the provider code uniform and avoids a new dependency.
_PROVIDER_BASE_URL = {
    "groq": "https://api.groq.com/openai/v1",
    "cerebras": "https://api.cerebras.ai/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "mistral": "https://api.mistral.ai/v1",
}

# Groq keeps per-call-type models (unchanged from the historical constants). Fallback
# providers use a single model each, overridable via {PROVIDER}_MODEL.
_GROQ_MODEL_ENV_BY_CALL_TYPE = {
    "event_analysis": ("GROQ_EVENT_ANALYSIS_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct"),
    "market_heartbeat": ("GROQ_MARKET_HEARTBEAT_MODEL", "llama-3.1-8b-instant"),
    "daily_report": ("GROQ_REPORT_MODEL", "llama-3.1-8b-instant"),
    "weekly_report": ("GROQ_REPORT_MODEL", "llama-3.1-8b-instant"),
    "market_report": ("GROQ_REPORT_MODEL", "llama-3.1-8b-instant"),
    "news_intelligence": ("GROQ_NEWS_INTELLIGENCE_MODEL", "llama-3.1-8b-instant"),
}
_GROQ_DEFAULT_MODEL = ("GROQ_MODEL", "llama-3.3-70b-versatile")

_FALLBACK_MODEL_ENV = {
    "cerebras": ("CEREBRAS_MODEL", "llama-3.3-70b"),
    "gemini": ("GEMINI_MODEL", "gemini-2.0-flash"),
    "mistral": ("MISTRAL_MODEL", "mistral-small-latest"),
}


def _parse_priority_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    seen: set[str] = set()
    ordered: list[str] = []
    for token in raw.split(","):
        name = token.strip().lower()
        if name in KNOWN_PROVIDERS and name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered


def global_provider_priority() -> list[str]:
    parsed = _parse_priority_list(os.getenv("LLM_PROVIDER_PRIORITY"))
    return parsed or list(DEFAULT_PROVIDER_PRIORITY)


def provider_priority(call_type: str) -> list[str]:
    """Resolve the ordered provider chain for a call type.

    Per-call-type override env wins when set and non-empty; otherwise the global
    priority; otherwise the built-in default.
    """
    override_env = _CALL_TYPE_PRIORITY_ENV.get(call_type)
    if override_env:
        parsed = _parse_priority_list(os.getenv(override_env))
        if parsed:
            return parsed
    return global_provider_priority()


def api_key(provider: str) -> str | None:
    env_name = _PROVIDER_API_KEY_ENV.get(provider)
    if not env_name:
        return None
    value = os.getenv(env_name)
    return value or None


def base_url(provider: str) -> str | None:
    return _PROVIDER_BASE_URL.get(provider)


def api_key_env(provider: str) -> str | None:
    return _PROVIDER_API_KEY_ENV.get(provider)


def model_for(provider: str, call_type: str) -> str:
    """Resolve the model for a (provider, call_type) pair from env, with defaults."""
    if provider == "groq":
        env_name, default = _GROQ_MODEL_ENV_BY_CALL_TYPE.get(call_type, _GROQ_DEFAULT_MODEL)
        return os.getenv(env_name, default)
    env_name, default = _FALLBACK_MODEL_ENV.get(provider, ("", ""))
    if not env_name:
        return default
    return os.getenv(env_name, default)
