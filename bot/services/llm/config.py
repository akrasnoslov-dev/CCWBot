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

# Ordered default chain for general LLM work. Event Alert rendering has a dedicated
# model-level chain because it deliberately retries a second Groq model before changing providers.
DEFAULT_PROVIDER_PRIORITY = ["groq", "gemini", "mistral"]
# Event Analysis needs one more independent free-tier route when the general priority
# has not been explicitly set. Cloudflare is optional and skipped without its credentials.
DEFAULT_EVENT_ANALYSIS_PROVIDER_PRIORITY = ["groq", "gemini", "cloudflare", "mistral"]
KNOWN_PROVIDERS = frozenset((*DEFAULT_PROVIDER_PRIORITY, "cloudflare"))

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
    "gemini": "GEMINI_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "cloudflare": "CLOUDFLARE_API_TOKEN",
}

# All providers are reached through OpenAI-compatible chat-completions endpoints. Cloudflare's
# base URL is account-scoped and therefore resolved dynamically in base_url().
_PROVIDER_BASE_URL = {
    "groq": "https://api.groq.com/openai/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "mistral": "https://api.mistral.ai/v1",
}

# Groq keeps per-call-type models. Fallback providers use a single model each, overridable
# via {PROVIDER}_MODEL. Defaults name models proven to work in production; none of them may
# point at a model the provider has decommissioned.
_GROQ_MODEL_ENV_BY_CALL_TYPE = {
    "event_analysis": ("GROQ_EVENT_ANALYSIS_MODEL", "openai/gpt-oss-120b"),
    "event_alert_render": ("GROQ_EVENT_ANALYSIS_MODEL", "openai/gpt-oss-120b"),
    "market_heartbeat": ("GROQ_MARKET_HEARTBEAT_MODEL", "openai/gpt-oss-20b"),
    "daily_report": ("GROQ_REPORT_MODEL", "openai/gpt-oss-20b"),
    "weekly_report": ("GROQ_REPORT_MODEL", "openai/gpt-oss-20b"),
    "market_report": ("GROQ_REPORT_MODEL", "openai/gpt-oss-20b"),
    "news_intelligence": ("GROQ_NEWS_INTELLIGENCE_MODEL", "openai/gpt-oss-20b"),
}
_GROQ_DEFAULT_MODEL = ("GROQ_MODEL", "openai/gpt-oss-20b")

_FALLBACK_MODEL_ENV = {
    "gemini": ("GEMINI_MODEL", "gemini-3.8-flash"),
    "mistral": ("MISTRAL_MODEL", "mistral-small-2603"),
    "cloudflare": (
        "CLOUDFLARE_MODEL",
        "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    ),
}

# Event Alert rendering intentionally uses a model-level chain rather than the generic
# provider-only chain. The second step reuses Groq with a different model, so this cannot be
# represented by a de-duplicated provider priority list.
_EVENT_ALERT_RENDER_ATTEMPTS = (
    ("groq", "GROQ_EVENT_ANALYSIS_MODEL", "openai/gpt-oss-120b"),
    ("groq", "GROQ_EVENT_RENDER_FALLBACK_MODEL", "qwen/qwen3.8-27b"),
    (
        "cloudflare",
        "CLOUDFLARE_EVENT_RENDER_MODEL",
        "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    ),
    ("gemini", "GEMINI_EVENT_RENDER_MODEL", "gemini-3.5-flash-lite"),
)

# Every call type that reaches a provider, in a stable order for the startup configuration log.
# ``legacy_alert_payload`` is the older price-alert path; it is listed so the startup log covers
# every call type that can actually spend tokens, not only the ones with a dedicated env var.
KNOWN_CALL_TYPES = (
    "event_analysis",
    "event_alert_render",
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
    "event_alert_render": ("LLM_EVENT_ANALYSIS_MAX_TOKENS", 300),
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
    "event_alert_render": "GROQ_EVENT_ANALYSIS_MAX_TOKENS",
}

# Optional reasoning effort, per call type with a global default.
_CALL_TYPE_REASONING_EFFORT_ENV = {
    "event_analysis": "LLM_EVENT_ANALYSIS_REASONING_EFFORT",
    "event_alert_render": "LLM_EVENT_ANALYSIS_REASONING_EFFORT",
    "market_heartbeat": "LLM_MARKET_HEARTBEAT_REASONING_EFFORT",
    "daily_report": "LLM_REPORT_REASONING_EFFORT",
    "weekly_report": "LLM_REPORT_REASONING_EFFORT",
    "market_report": "LLM_REPORT_REASONING_EFFORT",
    "news_intelligence": "LLM_NEWS_INTELLIGENCE_REASONING_EFFORT",
}
REASONING_EFFORT_CHOICES = ("low", "medium", "high")
_DEFAULT_REASONING_EFFORT = "low"
_GROQ_EVENT_ANALYSIS_MEDIUM_MAX_TOKENS = 6300
_DEFAULT_REASONING_EFFORT_BY_CALL_TYPE = {
    # Production replay showed that low effort systematically over-classified routine
    # market moves after the significance/render split. Event Analysis needs the extra
    # reasoning depth; rendering and the other structured call types remain on low by default.
    "event_analysis": "medium",
}

# ``reasoning_effort`` is a *model* capability, not a provider one: the same provider serves
# reasoning and non-reasoning models side by side. Sending the parameter to a non-reasoning
# model is a 400, which the router treats as deterministic and does not fall back on — the
# exact failure shape this work exists to remove. So the parameter is gated on the resolved
# model identifier, matched against these substrings, and never on the provider name.
_DEFAULT_REASONING_MODEL_MARKERS = ("gpt-oss", "gemini-2.5", "gemini-3.")

# Models whose internal reasoning/thinking is billed against the *completion* budget, so a
# budget sized for a plain chat model leaves nothing for the answer. Gemini 2.5 and Gemini 3
# accept ``reasoning_effort`` through Google's OpenAI-compatible endpoint. Gemini 2.5 maps
# effort to fixed thinking budgets while Gemini 3 uses dynamic thinking levels, so both stay in
# the reasoning and thinking capability sets.
_THINKING_MODEL_MARKERS = (
    "gpt-oss",
    "gemini-2.5",
    "gemini-3.",
    "magistral",
    "deepseek-r",
    "-o1",
    "-o3",
)

# Reserve this much completion capacity for a thinking model's internal reasoning in addition
# to the call type's configured answer budget. Gemini 2.5 maps these efforts to fixed budgets;
# Gemini 3 uses dynamic thinking levels, so these values are our bounded safety headroom rather
# than a provider-guaranteed Gemini 3 thinking budget. The goal is to avoid giving a reasoning
# model only the small schema-answer budget used by plain models.
_REASONING_HEADROOM_TOKENS_BY_EFFORT = {
    "low": 1024,
    "medium": 8192,
    "high": 24576,
}


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
    # Respect an explicit global priority. With no global/event override, insert the
    # existing Cloudflare adapter before Mistral for Event Analysis only; the router
    # excludes it automatically when its token or account ID is missing.
    if call_type == "event_analysis" and not os.getenv("LLM_PROVIDER_PRIORITY"):
        return list(DEFAULT_EVENT_ANALYSIS_PROVIDER_PRIORITY)
    return global_provider_priority()


def api_key(provider: str) -> str | None:
    env_name = _PROVIDER_API_KEY_ENV.get(provider)
    if not env_name:
        return None
    value = os.getenv(env_name)
    return value or None


def provider_is_configured(provider: str) -> bool:
    """True when all non-secret configuration required by a provider is present."""
    if api_key(provider) is None:
        return False
    if provider == "cloudflare":
        return bool(str(os.getenv("CLOUDFLARE_ACCOUNT_ID") or "").strip())
    return True


def base_url(provider: str) -> str | None:
    if provider == "cloudflare":
        account_id = str(os.getenv("CLOUDFLARE_ACCOUNT_ID") or "").strip()
        if not account_id:
            return None
        return f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1"
    return _PROVIDER_BASE_URL.get(provider)


def api_key_env(provider: str) -> str | None:
    return _PROVIDER_API_KEY_ENV.get(provider)


def _model_from_env(env_name: str, default: str) -> str:
    """Resolve a model identifier, treating a present-but-empty value as unset.

    ``os.getenv(name, default)`` only falls back when the variable is *absent*, so
    An empty model override would otherwise resolve to ``""`` and be sent as the model — a 400 the
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


def provider_attempts(call_type: str) -> list[tuple[str, str]]:
    """Return the ordered concrete provider/model attempts for one logical LLM operation."""
    if call_type == "event_alert_render":
        return [
            (provider, _model_from_env(env_name, default))
            for provider, env_name, default in _EVENT_ALERT_RENDER_ATTEMPTS
        ]
    return [(provider, model_for(provider, call_type)) for provider in provider_priority(call_type)]


def request_timeout_seconds_for(
    *, call_type: str, provider: str, requested_timeout: int | float | None = None
) -> int | float:
    """Choose a per-attempt HTTP timeout; explicit caller overrides remain authoritative."""
    if requested_timeout is not None:
        return requested_timeout
    if call_type == "event_analysis" and provider == "gemini":
        # Gemini reasoning occasionally exceeds the shared 15s limit. Keep this bounded so
        # the third provider still has a full 15s within the 60s logical-operation budget.
        return get_int_env(
            "LLM_GEMINI_EVENT_ANALYSIS_TIMEOUT_SECONDS", 25, minimum=15, maximum=30
        )
    return 15


def event_analysis_operation_budget_seconds() -> int:
    """Bound the complete Event Analysis provider chain, not each provider independently."""
    return get_int_env(
        "LLM_EVENT_ANALYSIS_OPERATION_BUDGET_SECONDS", 60, minimum=15, maximum=120
    )


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


def effective_max_tokens_for(
    *,
    call_type: str,
    provider: str,
    model: str | None,
    requested_max_tokens: int | None = None,
) -> int:
    """Return the completion budget for one concrete provider attempt.

    The public call-type budget remains the primary/plain-model ceiling. Thinking models need
    room for hidden reasoning before emitting the JSON answer, so only those attempts receive
    explicit reasoning headroom in addition to the configured answer ceiling. This avoids
    raising plain-model attempts merely because a thinking model exists later in the chain.
    """
    budget = max_tokens_for(call_type) if requested_max_tokens is None else requested_max_tokens
    if is_thinking_model(model):
        headroom = reasoning_headroom_tokens_for(model=model, call_type=call_type)
        effective = min(budget + headroom, _MAX_TOKENS_CEILING)
        # Groq Free exposes an 8K TPM limit for GPT-OSS. Keep the shipped medium Event Analysis
        # request below that ceiling with room for the compact prompt. This is a provider-capacity
        # guard only; it does not change alert significance or add a market threshold.
        if (
            provider.strip().lower() == "groq"
            and call_type == "event_analysis"
            and reasoning_effort_for(model, call_type) == "medium"
        ):
            return min(effective, _GROQ_EVENT_ANALYSIS_MEDIUM_MAX_TOKENS)
        return effective
    return budget


def reasoning_headroom_tokens_for(*, model: str | None, call_type: str) -> int:
    """Return reasoning capacity reserved in addition to the configured answer budget."""
    if not is_thinking_model(model):
        return 0
    effort = reasoning_effort_for(model, call_type) or "low"
    return _REASONING_HEADROOM_TOKENS_BY_EFFORT[effort]


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
    return tuple(dict.fromkeys((*_DEFAULT_REASONING_MODEL_MARKERS, *parsed)))


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
    shipped_default = _DEFAULT_REASONING_EFFORT_BY_CALL_TYPE.get(
        call_type, _DEFAULT_REASONING_EFFORT
    )
    if env_name and os.getenv(env_name) is not None and os.getenv(env_name, "").strip():
        # Do not inherit a different global value after rejecting a call-type override. Use the
        # shipped safe default explicitly so request effort and reserved headroom stay aligned.
        return get_choice_env(env_name, REASONING_EFFORT_CHOICES) or shipped_default
    configured = get_choice_env("LLM_REASONING_EFFORT", REASONING_EFFORT_CHOICES)
    # Event Analysis is the exception to the low shipped default: production replay of the
    # significance classifier showed low effort over-classifying routine moves, while medium
    # correctly rejected the representative false-positive cases. Other call types stay low.
    return configured or shipped_default


def resolved_configuration() -> list[dict]:
    """Return the fully resolved per-call-type LLM configuration.

    Model identifiers, provider names, token budgets, and reasoning effort only — never API
    keys or any other credential value. Attempts are kept as an ordered list because Event Alert
    rendering deliberately contains two Groq attempts with different models.
    """
    resolved: list[dict] = []
    for call_type in KNOWN_CALL_TYPES:
        attempts = []
        for provider, model in provider_attempts(call_type):
            attempts.append(
                {
                    "provider": provider,
                    "model": model,
                    "configured": provider_is_configured(provider),
                    "effective_max_tokens": effective_max_tokens_for(
                        call_type=call_type,
                        provider=provider,
                        model=model,
                    ),
                    "reasoning_effort": reasoning_effort_for(model, call_type),
                    "timeout_seconds": request_timeout_seconds_for(
                        call_type=call_type, provider=provider
                    ),
                }
            )
        resolved.append(
            {
                "call_type": call_type,
                "attempts": attempts,
                "max_tokens": max_tokens_for(call_type),
                "operation_budget_seconds": (
                    event_analysis_operation_budget_seconds()
                    if call_type == "event_analysis"
                    else None
                ),
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
    for attempt in entry["attempts"]:
        effort = attempt["reasoning_effort"]
        parts.append(
            "{provider}:{model}{effort}/max={effective_budget}{unconfigured}".format(
                provider=attempt["provider"],
                model=_safe_log_value(attempt["model"]),
                effort=f"/effort={effort}" if effort else "",
                effective_budget=attempt["effective_max_tokens"],
                unconfigured=(
                    ""
                    if attempt["configured"]
                    else "(no_api_key)"
                    if api_key(attempt["provider"]) is None
                    else "(missing_config)"
                ),
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
        timing = ""
        if entry["call_type"] == "event_analysis":
            gemini_timeout = next(
                (
                    item["timeout_seconds"]
                    for item in entry["attempts"]
                    if item["provider"] == "gemini"
                ),
                "none",
            )
            timing = (
                f" operation_budget_seconds={entry['operation_budget_seconds']}"
                f" gemini_timeout_seconds={gemini_timeout}"
            )
        logger.info(
            "ops_event=llm_config call_type=%s max_tokens=%s chain=%s%s",
            entry["call_type"],
            entry["max_tokens"],
            _format_chain(entry),
            timing,
        )
        _warn_undersized_thinking_budgets(entry)


def _warn_undersized_thinking_budgets(entry: dict) -> None:
    """Warn when a chain member reasons internally but has no budget left to answer."""
    for attempt in entry["attempts"]:
        if not attempt["configured"]:
            continue
        model = attempt["model"]
        if not is_thinking_model(model):
            continue
        budget = attempt["effective_max_tokens"]
        desired_budget = entry["max_tokens"] + reasoning_headroom_tokens_for(
            model=model,
            call_type=entry["call_type"],
        )
        if desired_budget <= _MAX_TOKENS_CEILING and budget >= desired_budget:
            continue
        logger.warning(
            "ops_event=llm_config_budget_risk call_type=%s provider=%s model=%s max_tokens=%s "
            "recommended_min=%s reason=reasoning_tokens_consume_completion_budget",
            entry["call_type"],
            attempt["provider"],
            _safe_log_value(model),
            budget,
            desired_budget,
        )
