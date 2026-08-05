"""Environment-driven configuration for the LLM provider fallback chain.

All lookups read ``os.getenv`` at call time so provider priority, API keys, model selection,
completion-token budgets, and reasoning effort can be changed via environment without code
changes (and monkeypatched in tests). A provider with no API key is excluded from the chain
by the router, not here.

Resolving at call time also means an unparseable value warns while the bot is running with
logging configured, instead of during module import before ``configure_logging()`` has run.
"""

import logging
import os
import re

from bot.services.llm.env import (
    get_choice_env,
    get_int_env,
    reset_env_warning_cache,
    warn_rejected_value,
)

logger = logging.getLogger(__name__)

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

# Groq keeps per-call-type models. Fallback providers use a single model each, overridable
# via {PROVIDER}_MODEL. Defaults name models proven to work in production; none of them may
# point at a model the provider has decommissioned.
_GROQ_MODEL_ENV_BY_CALL_TYPE = {
    "event_analysis": ("GROQ_EVENT_ANALYSIS_MODEL", "llama-3.3-70b-versatile"),
    "market_heartbeat": ("GROQ_MARKET_HEARTBEAT_MODEL", "llama-3.1-8b-instant"),
    "daily_report": ("GROQ_REPORT_MODEL", "llama-3.1-8b-instant"),
    "weekly_report": ("GROQ_REPORT_MODEL", "llama-3.1-8b-instant"),
    "market_report": ("GROQ_REPORT_MODEL", "llama-3.1-8b-instant"),
    "news_intelligence": ("GROQ_NEWS_INTELLIGENCE_MODEL", "llama-3.1-8b-instant"),
}
_GROQ_DEFAULT_MODEL = ("GROQ_MODEL", "llama-3.3-70b-versatile")

_FALLBACK_MODEL_ENV = {
    "cerebras": ("CEREBRAS_MODEL", "gpt-oss-120b"),
    "gemini": ("GEMINI_MODEL", "gemini-2.5-flash"),
    "mistral": ("MISTRAL_MODEL", "mistral-small-latest"),
}

# Every call type that reaches a provider, in a stable order for the startup configuration log.
# ``legacy_alert_payload`` is the older price-alert path; it is listed so the startup log covers
# every call type that can actually spend tokens, not only the ones with a dedicated env var.
KNOWN_CALL_TYPES = (
    "event_analysis",
    "market_heartbeat",
    "daily_report",
    "weekly_report",
    "market_report",
    "news_intelligence",
    "legacy_alert_payload",
)

# Per-call-type completion-token budget. The default column preserves the values that were
# previously hardcoded in bot/services/ai_agent_groq.py, so an unconfigured deployment behaves
# exactly as before. ``daily_report`` / ``weekly_report`` / ``market_report`` intentionally
# share one variable, mirroring how they share GROQ_REPORT_MODEL and LLM_REPORT_PROVIDERS.
_CALL_TYPE_MAX_TOKENS_ENV = {
    "event_analysis": ("LLM_EVENT_ANALYSIS_MAX_TOKENS", 300),
    "market_heartbeat": ("LLM_MARKET_HEARTBEAT_MAX_TOKENS", 350),
    "daily_report": ("LLM_REPORT_MAX_TOKENS", 800),
    "weekly_report": ("LLM_REPORT_MAX_TOKENS", 800),
    "market_report": ("LLM_REPORT_MAX_TOKENS", 800),
    "news_intelligence": ("LLM_NEWS_INTELLIGENCE_MAX_TOKENS", 350),
    "legacy_alert_payload": ("LLM_LEGACY_ALERT_PAYLOAD_MAX_TOKENS", 450),
}
_DEFAULT_MAX_TOKENS = 450

# Generous sanity ceiling. Budgets are meant to be raised substantially for reasoning models,
# so this is not a tuning limit — it exists so an obvious typo (300000 for 300) is rejected
# loudly instead of silently multiplying the per-call token ceiling.
_MAX_TOKENS_CEILING = 32768

# Historical per-call-type names kept working so an existing .env keeps its configured value.
_LEGACY_MAX_TOKENS_ENV = {
    "event_analysis": "GROQ_EVENT_ANALYSIS_MAX_TOKENS",
}

# Optional reasoning effort, per call type with a global default.
_CALL_TYPE_REASONING_EFFORT_ENV = {
    "event_analysis": "LLM_EVENT_ANALYSIS_REASONING_EFFORT",
    "market_heartbeat": "LLM_MARKET_HEARTBEAT_REASONING_EFFORT",
    "daily_report": "LLM_REPORT_REASONING_EFFORT",
    "weekly_report": "LLM_REPORT_REASONING_EFFORT",
    "market_report": "LLM_REPORT_REASONING_EFFORT",
    "news_intelligence": "LLM_NEWS_INTELLIGENCE_REASONING_EFFORT",
}
REASONING_EFFORT_CHOICES = ("low", "medium", "high")

# ``reasoning_effort`` is a *model* capability, not a provider one: the same provider serves
# reasoning and non-reasoning models side by side. Sending the parameter to a non-reasoning
# model is a 400, which the router treats as deterministic and does not fall back on — the
# exact failure shape this work exists to remove. So the parameter is gated on the resolved
# model identifier, matched against these substrings, and never on the provider name.
_DEFAULT_REASONING_MODEL_MARKERS = ("gpt-oss",)

# Models whose internal reasoning/thinking is billed against the *completion* budget, so a
# budget sized for a plain chat model leaves nothing for the answer. This is deliberately a
# superset of the reasoning-effort markers above: Gemini 2.5 thinks by default but its
# OpenAI-compatible endpoint does not accept ``reasoning_effort``, so it belongs here (warn
# about the budget) but not there (never send the parameter).
_THINKING_MODEL_MARKERS = ("gpt-oss", "gemini-2.5", "magistral", "deepseek-r", "-o1", "-o3")

# Below this, a thinking model has no realistic room to emit JSON after reasoning. Used only
# to warn at startup; it never changes the budget that is actually sent.
_THINKING_MODEL_MIN_RECOMMENDED_MAX_TOKENS = 1024


def _parse_priority_list(raw: str | None, *, env_name: str | None = None) -> list[str]:
    """Parse a comma-separated provider list, warning about names that are not providers.

    A dropped token silently shortens or empties the fallback chain, which is the same
    invisible-misconfiguration failure mode the token budgets fix, so it warns too.
    """
    if not raw:
        return []
    seen: set[str] = set()
    ordered: list[str] = []
    unknown: list[str] = []
    for token in raw.split(","):
        name = token.strip().lower()
        if not name:
            continue
        if name not in KNOWN_PROVIDERS:
            unknown.append(name)
            continue
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    if unknown and env_name:
        warn_rejected_value(
            env_name,
            ",".join(unknown),
            "unknown_provider_names",
            ",".join(ordered) or "built-in default",
        )
    return ordered


def global_provider_priority() -> list[str]:
    parsed = _parse_priority_list(
        os.getenv("LLM_PROVIDER_PRIORITY"), env_name="LLM_PROVIDER_PRIORITY"
    )
    return parsed or list(DEFAULT_PROVIDER_PRIORITY)


def provider_priority(call_type: str) -> list[str]:
    """Resolve the ordered provider chain for a call type.

    Per-call-type override env wins when set and non-empty; otherwise the global
    priority; otherwise the built-in default.
    """
    override_env = _CALL_TYPE_PRIORITY_ENV.get(call_type)
    if override_env:
        parsed = _parse_priority_list(os.getenv(override_env), env_name=override_env)
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


def _model_from_env(env_name: str, default: str) -> str:
    """Resolve a model identifier, treating a present-but-empty value as unset.

    ``os.getenv(name, default)`` only falls back when the variable is *absent*, so
    ``CEREBRAS_MODEL=`` would otherwise resolve to ``""`` and be sent as the model — a 400 the
    router treats as deterministic, which aborts the chain instead of falling through. Blanking
    the API key is the supported way to drop a provider; blanking the model is a mistake.
    """
    raw = os.getenv(env_name)
    if raw is None:
        return default
    stripped = raw.strip()
    if not stripped:
        warn_rejected_value(env_name, raw, "empty_model_identifier", default)
        return default
    return stripped


def model_for(provider: str, call_type: str) -> str:
    """Resolve the model for a (provider, call_type) pair from env, with defaults."""
    if provider == "groq":
        env_name, default = _GROQ_MODEL_ENV_BY_CALL_TYPE.get(call_type, _GROQ_DEFAULT_MODEL)
        return _model_from_env(env_name, default)
    env_name, default = _FALLBACK_MODEL_ENV.get(provider, ("", ""))
    if not env_name:
        return default
    return _model_from_env(env_name, default)


def max_tokens_for(call_type: str) -> int:
    """Resolve the completion-token budget for a call type.

    The current ``LLM_*`` name wins when set; otherwise the historical name for that call type
    (so an existing ``.env`` keeps working); otherwise the built-in default, which is the value
    that was previously hardcoded.
    """
    entry = _CALL_TYPE_MAX_TOKENS_ENV.get(call_type)
    if entry is None:
        # Unknown call type: use the built-in default rather than synthesizing an env name
        # from a caller-supplied string.
        return _DEFAULT_MAX_TOKENS
    env_name, default = entry
    if os.getenv(env_name) is not None:
        return get_int_env(env_name, default, minimum=1, maximum=_MAX_TOKENS_CEILING)
    legacy_name = _LEGACY_MAX_TOKENS_ENV.get(call_type)
    if legacy_name and os.getenv(legacy_name) is not None:
        return get_int_env(legacy_name, default, minimum=1, maximum=_MAX_TOKENS_CEILING)
    return default


def reasoning_model_markers() -> tuple[str, ...]:
    """Substrings that mark a model identifier as reasoning-capable (overridable via env)."""
    raw = os.getenv("LLM_REASONING_MODEL_MARKERS")
    if raw is None:
        return _DEFAULT_REASONING_MODEL_MARKERS
    parsed = tuple(token.strip().lower() for token in raw.split(",") if token.strip())
    if not parsed:
        # An empty value would silently disable reasoning effort everywhere, which is the
        # invisible misconfiguration this module exists to prevent.
        warn_rejected_value(
            "LLM_REASONING_MODEL_MARKERS",
            raw,
            "empty_marker_list",
            ",".join(_DEFAULT_REASONING_MODEL_MARKERS),
        )
        return _DEFAULT_REASONING_MODEL_MARKERS
    return parsed


def is_reasoning_model(model: str | None) -> bool:
    """True when this model identifier is known to accept ``reasoning_effort``."""
    if not model:
        return False
    lowered = model.lower()
    return any(marker in lowered for marker in reasoning_model_markers())


def reasoning_effort_for(model: str | None, call_type: str) -> str | None:
    """Resolve ``reasoning_effort`` for a (model, call_type) pair, or ``None`` when unset.

    ``None`` means the parameter is omitted from the request payload entirely, so a chain that
    mixes reasoning and non-reasoning models sends it only to the attempts that accept it.
    """
    if not is_reasoning_model(model):
        return None
    env_name = _CALL_TYPE_REASONING_EFFORT_ENV.get(call_type)
    if env_name and os.getenv(env_name) is not None and os.getenv(env_name, "").strip():
        # An explicitly-set-but-invalid per-call-type value must not silently inherit the
        # global default: the operator asked for something specific, and quietly applying a
        # third value is the kind of surprise this module exists to prevent.
        return get_choice_env(env_name, REASONING_EFFORT_CHOICES)
    return get_choice_env("LLM_REASONING_EFFORT", REASONING_EFFORT_CHOICES)


def resolved_configuration() -> list[dict]:
    """Return the fully resolved per-call-type LLM configuration.

    Model identifiers, provider names, token budgets, and reasoning effort only — never API
    keys or any other credential value. ``providers`` lists the chain as configured; a provider
    with no API key is excluded at call time by the router, which is reported separately as
    ``configured=false`` so "why did my fallback not engage?" is answerable from the log alone.
    """
    resolved: list[dict] = []
    for call_type in KNOWN_CALL_TYPES:
        chain = provider_priority(call_type)
        resolved.append(
            {
                "call_type": call_type,
                "providers": chain,
                "models": {name: model_for(name, call_type) for name in chain},
                "configured": {name: api_key(name) is not None for name in chain},
                "max_tokens": max_tokens_for(call_type),
                "reasoning_effort": {
                    name: reasoning_effort_for(model_for(name, call_type), call_type)
                    for name in chain
                },
            }
        )
    return resolved


def is_thinking_model(model: str | None) -> bool:
    """True when this model spends part of the completion budget on internal reasoning."""
    if not model:
        return False
    lowered = model.lower()
    return any(marker in lowered for marker in _THINKING_MODEL_MARKERS)


# Characters that legitimately appear in a model identifier. Everything else is replaced
# before logging so a hand-edited .env value cannot inject `key=value` pairs or extra lines
# into a log stream that collectors parse as structured events.
_MODEL_LOG_SAFE_RE = re.compile(r"[^A-Za-z0-9._/@-]")


def _safe_log_value(value: str | None, *, max_chars: int = 80) -> str:
    """Sanitize an env-sourced identifier before interpolating it into a log line."""
    collapsed = " ".join(str(value or "").split())
    return _MODEL_LOG_SAFE_RE.sub("?", collapsed)[:max_chars] or "?"


def _format_chain(entry: dict) -> str:
    parts = []
    for name in entry["providers"]:
        effort = entry["reasoning_effort"].get(name)
        parts.append(
            "{provider}:{model}{effort}{unconfigured}".format(
                provider=name,
                model=_safe_log_value(entry["models"].get(name)),
                effort=f"/effort={effort}" if effort else "",
                unconfigured="" if entry["configured"].get(name) else "(no_api_key)",
            )
        )
    return ",".join(parts) or "none"


def log_resolved_configuration() -> None:
    """Log the resolved LLM configuration once, at startup.

    This is the signal that answers "is the running deploy actually using what I configured?"
    without reading ``.env`` on the server. The warn-once cache is cleared first so an
    unparseable value that was already rejected during module import is reported again here,
    now that logging is configured.
    """
    reset_env_warning_cache()
    for entry in resolved_configuration():
        logger.info(
            "ops_event=llm_config call_type=%s max_tokens=%s chain=%s",
            entry["call_type"],
            entry["max_tokens"],
            _format_chain(entry),
        )
        _warn_undersized_thinking_budgets(entry)


def _warn_undersized_thinking_budgets(entry: dict) -> None:
    """Warn when a chain member reasons internally but has no budget left to answer.

    The shipped Cerebras/Gemini defaults are thinking models while the call-type budgets are
    sized for the llama primary. That combination fails with an empty completion rather than a
    recognisable error, so it is surfaced at startup instead of one dead call at a time.
    """
    budget = entry["max_tokens"]
    if budget >= _THINKING_MODEL_MIN_RECOMMENDED_MAX_TOKENS:
        return
    for name in entry["providers"]:
        if not entry["configured"].get(name):
            # No API key, so the router never attempts it; warning would be noise.
            continue
        model = entry["models"].get(name)
        if not is_thinking_model(model):
            continue
        logger.warning(
            "ops_event=llm_config_budget_risk call_type=%s provider=%s model=%s max_tokens=%s "
            "recommended_min=%s reason=reasoning_tokens_consume_completion_budget",
            entry["call_type"],
            name,
            _safe_log_value(model),
            budget,
            _THINKING_MODEL_MIN_RECOMMENDED_MAX_TOKENS,
        )
