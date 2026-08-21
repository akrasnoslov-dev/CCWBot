"""Per-call-type token budgets, reasoning effort, loud env parsing, and the startup log.

All provider interaction is mocked; nothing here reaches a real provider.
"""

import logging

import pytest

from bot.services.llm import config as llm_config
from bot.services.llm import env as llm_env
from bot.services.llm.base_provider import BaseProvider, ProviderResult
from bot.services.llm.router import LLMRouter

_BUDGET_ENV_VARS = (
    "LLM_EVENT_ANALYSIS_MAX_TOKENS",
    "LLM_MARKET_HEARTBEAT_MAX_TOKENS",
    "LLM_REPORT_MAX_TOKENS",
    "LLM_NEWS_INTELLIGENCE_MAX_TOKENS",
    "GROQ_EVENT_ANALYSIS_MAX_TOKENS",
)

_EFFORT_ENV_VARS = (
    "LLM_REASONING_EFFORT",
    "LLM_REASONING_MODEL_MARKERS",
    "LLM_EVENT_ANALYSIS_REASONING_EFFORT",
    "LLM_MARKET_HEARTBEAT_REASONING_EFFORT",
    "LLM_REPORT_REASONING_EFFORT",
    "LLM_NEWS_INTELLIGENCE_REASONING_EFFORT",
)


@pytest.fixture(autouse=True)
def _clean_llm_env(monkeypatch):
    """Start every test from an unconfigured environment.

    The developer .env is loaded into the process by ``load_dotenv()``, so without this a test
    asserting a *default* would silently assert whatever the developer happens to have pinned.
    """
    for name in _BUDGET_ENV_VARS + _EFFORT_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    llm_env.reset_env_warning_cache()
    yield
    llm_env.reset_env_warning_cache()


# --- token budgets ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("call_type", "default"),
    [
        ("event_analysis", 300),
        ("market_heartbeat", 350),
        ("daily_report", 800),
        ("weekly_report", 800),
        ("market_report", 800),
        ("news_intelligence", 350),
    ],
)
def test_default_budget_matches_previous_hardcoded_value(call_type, default):
    assert llm_config.max_tokens_for(call_type) == default


@pytest.mark.parametrize(
    ("call_type", "env_name"),
    [
        ("event_analysis", "LLM_EVENT_ANALYSIS_MAX_TOKENS"),
        ("market_heartbeat", "LLM_MARKET_HEARTBEAT_MAX_TOKENS"),
        ("daily_report", "LLM_REPORT_MAX_TOKENS"),
        ("weekly_report", "LLM_REPORT_MAX_TOKENS"),
        ("market_report", "LLM_REPORT_MAX_TOKENS"),
        ("news_intelligence", "LLM_NEWS_INTELLIGENCE_MAX_TOKENS"),
    ],
)
def test_each_call_type_honours_its_env_budget(monkeypatch, call_type, env_name):
    monkeypatch.setenv(env_name, "4096")
    assert llm_config.max_tokens_for(call_type) == 4096


def test_legacy_event_analysis_budget_name_still_works(monkeypatch):
    monkeypatch.setenv("GROQ_EVENT_ANALYSIS_MAX_TOKENS", "1234")
    assert llm_config.max_tokens_for("event_analysis") == 1234


def test_current_budget_name_wins_over_legacy_name(monkeypatch):
    monkeypatch.setenv("GROQ_EVENT_ANALYSIS_MAX_TOKENS", "1234")
    monkeypatch.setenv("LLM_EVENT_ANALYSIS_MAX_TOKENS", "5678")
    assert llm_config.max_tokens_for("event_analysis") == 5678


def test_report_call_types_share_one_budget_variable(monkeypatch):
    monkeypatch.setenv("LLM_REPORT_MAX_TOKENS", "999")
    budgets = {llm_config.max_tokens_for(c) for c in ("daily_report", "weekly_report",
                                                     "market_report")}
    assert budgets == {999}


# --- loud parsing ----------------------------------------------------------------------


def test_unparseable_budget_falls_back_and_warns(monkeypatch, caplog):
    monkeypatch.setenv("LLM_EVENT_ANALYSIS_MAX_TOKENS", "3OO")

    with caplog.at_level(logging.WARNING, logger="bot.services.llm.env"):
        assert llm_config.max_tokens_for("event_analysis") == 300

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    message = warnings[0].getMessage()
    assert "LLM_EVENT_ANALYSIS_MAX_TOKENS" in message
    assert "3OO" in message
    assert "using_default=300" in message


def test_out_of_range_budget_falls_back_and_warns(monkeypatch, caplog):
    monkeypatch.setenv("LLM_REPORT_MAX_TOKENS", "0")

    with caplog.at_level(logging.WARNING, logger="bot.services.llm.env"):
        assert llm_config.max_tokens_for("daily_report") == 800

    assert any("below_minimum_1" in r.getMessage() for r in caplog.records)


def test_bad_value_warns_once_not_once_per_call(monkeypatch, caplog):
    monkeypatch.setenv("LLM_EVENT_ANALYSIS_MAX_TOKENS", "not-a-number")

    with caplog.at_level(logging.WARNING, logger="bot.services.llm.env"):
        for _ in range(5):
            llm_config.max_tokens_for("event_analysis")

    assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 1


def test_unset_and_empty_values_do_not_warn(monkeypatch, caplog):
    monkeypatch.setenv("LLM_REPORT_MAX_TOKENS", "   ")

    with caplog.at_level(logging.WARNING, logger="bot.services.llm.env"):
        assert llm_config.max_tokens_for("daily_report") == 800
        assert llm_config.max_tokens_for("news_intelligence") == 350

    assert [r for r in caplog.records if r.levelno == logging.WARNING] == []


def test_key_shaped_value_is_redacted_even_under_a_harmless_variable_name(monkeypatch, caplog):
    # The realistic operator error: a key pasted onto the wrong .env line. The name gate
    # cannot catch that, and this WARNING goes to stdout where the redacting file formatter
    # does not run.
    monkeypatch.setenv("LLM_EVENT_ANALYSIS_MAX_TOKENS", "gsk_liveKeyValue1234567890abcdef")

    with caplog.at_level(logging.WARNING, logger="bot.services.llm.env"):
        assert llm_config.max_tokens_for("event_analysis") == 300

    joined = " ".join(r.getMessage() for r in caplog.records)
    assert "gsk_liveKeyValue1234567890abcdef" not in joined
    assert "[redacted]" in joined


def test_credential_like_variable_value_is_never_logged(monkeypatch, caplog):
    # Defense in depth: these helpers are only wired to non-secret variables, but if one were
    # ever pointed at a credential the value must not reach the log line.
    monkeypatch.setenv("SOME_API_KEY", "sk-supersecret-value")

    with caplog.at_level(logging.WARNING, logger="bot.services.llm.env"):
        assert llm_env.get_int_env("SOME_API_KEY", 7) == 7

    joined = " ".join(r.getMessage() for r in caplog.records)
    assert "sk-supersecret-value" not in joined
    assert "SOME_API_KEY" in joined
    assert "[redacted]" in joined


def test_invalid_reasoning_effort_falls_back_and_warns(monkeypatch, caplog):
    monkeypatch.setenv("LLM_EVENT_ANALYSIS_REASONING_EFFORT", "extreme")

    with caplog.at_level(logging.WARNING, logger="bot.services.llm.env"):
        assert llm_config.reasoning_effort_for("openai/gpt-oss-120b", "event_analysis") == "low"

    assert any("LLM_EVENT_ANALYSIS_REASONING_EFFORT" in r.getMessage() for r in caplog.records)


def test_unknown_provider_name_in_a_chain_warns(monkeypatch, caplog):
    # A typo here silently shortens the fallback chain, which is the same class of invisible
    # misconfiguration as a bad token budget.
    monkeypatch.setenv("LLM_EVENT_PROVIDERS", "grok,cerebras")

    with caplog.at_level(logging.WARNING, logger="bot.services.llm.env"):
        assert llm_config.provider_priority("event_analysis") == ["cerebras"]

    assert any("LLM_EVENT_PROVIDERS" in r.getMessage() for r in caplog.records)


# --- reasoning effort ------------------------------------------------------------------


def test_reasoning_effort_defaults_to_low_for_reasoning_models():
    for call_type in llm_config.KNOWN_CALL_TYPES:
        assert llm_config.reasoning_effort_for("openai/gpt-oss-120b", call_type) == "low"


def test_reasoning_effort_per_call_type_wins_over_global(monkeypatch):
    monkeypatch.setenv("LLM_REASONING_EFFORT", "high")
    monkeypatch.setenv("LLM_EVENT_ANALYSIS_REASONING_EFFORT", "low")

    assert llm_config.reasoning_effort_for("gpt-oss-120b", "event_analysis") == "low"
    assert llm_config.reasoning_effort_for("gpt-oss-120b", "market_heartbeat") == "high"


def test_reasoning_effort_only_reaches_reasoning_models(monkeypatch):
    # The gate is the model, not the provider: the same provider serves both kinds, and
    # sending the parameter to a non-reasoning model is a 400 the router will not fall back on.
    monkeypatch.setenv("LLM_REASONING_EFFORT", "medium")

    assert llm_config.reasoning_effort_for("openai/gpt-oss-120b", "event_analysis") == "medium"
    assert llm_config.reasoning_effort_for("gpt-oss-20b", "event_analysis") == "medium"
    assert llm_config.reasoning_effort_for("llama-3.3-70b-versatile", "event_analysis") is None
    assert llm_config.reasoning_effort_for("gemini-2.5-flash", "event_analysis") == "medium"
    assert llm_config.reasoning_effort_for(None, "event_analysis") is None


def test_empty_marker_list_falls_back_instead_of_silently_disabling(monkeypatch, caplog):
    monkeypatch.setenv("LLM_REASONING_EFFORT", "low")
    monkeypatch.setenv("LLM_REASONING_MODEL_MARKERS", "  ")

    with caplog.at_level(logging.WARNING, logger="bot.services.llm.env"):
        assert llm_config.reasoning_effort_for("gpt-oss-120b", "event_analysis") == "low"

    assert any("LLM_REASONING_MODEL_MARKERS" in r.getMessage() for r in caplog.records)


def test_invalid_per_call_type_effort_does_not_inherit_the_global_value(monkeypatch, caplog):
    # An explicitly-set-but-invalid value must not silently apply a third value the operator
    # never asked for.
    monkeypatch.setenv("LLM_REASONING_EFFORT", "high")
    monkeypatch.setenv("LLM_EVENT_ANALYSIS_REASONING_EFFORT", "extreme")

    with caplog.at_level(logging.WARNING, logger="bot.services.llm.env"):
        assert llm_config.reasoning_effort_for("gpt-oss-120b", "event_analysis") == "low"
        assert llm_config.effective_max_tokens_for(
            call_type="event_analysis",
            provider="groq",
            model="gpt-oss-120b",
        ) == llm_config.max_tokens_for("event_analysis") + 1024

    assert any("LLM_EVENT_ANALYSIS_REASONING_EFFORT" in r.getMessage() for r in caplog.records)


def test_reasoning_model_markers_are_configurable(monkeypatch):
    monkeypatch.setenv("LLM_REASONING_EFFORT", "low")
    monkeypatch.setenv("LLM_REASONING_MODEL_MARKERS", "magistral")

    assert llm_config.reasoning_effort_for("magistral-medium-latest", "event_analysis") == "low"
    assert llm_config.reasoning_effort_for("gpt-oss-120b", "event_analysis") == "low"


def test_global_reasoning_effort_reaches_only_reasoning_models_in_default_chain(monkeypatch):
    monkeypatch.setenv("LLM_REASONING_EFFORT", "high")
    for name in ("GROQ_EVENT_ANALYSIS_MODEL", "GROQ_MARKET_HEARTBEAT_MODEL", "GROQ_REPORT_MODEL",
                 "GROQ_NEWS_INTELLIGENCE_MODEL", "GEMINI_MODEL", "MISTRAL_MODEL"):
        monkeypatch.delenv(name, raising=False)

    for call_type in llm_config.KNOWN_CALL_TYPES:
        for provider in ("groq", "gemini", "mistral"):
            model = llm_config.model_for(provider, call_type)
            expected = "high" if llm_config.is_reasoning_model(model) else None
            assert llm_config.reasoning_effort_for(model, call_type) == expected


class _RecordingProvider(BaseProvider):
    """Captures the kwargs the router passes, without making any provider call."""

    def __init__(self, name):
        self.name = name
        self.seen = []

    async def chat_completion(self, *, call_type, symbol, model, messages, max_tokens,
                              response_format, timeout=15, reasoning_effort=None):
        self.seen.append({"model": model, "max_tokens": max_tokens,
                          "reasoning_effort": reasoning_effort})
        return ProviderResult(provider=self.name, model=model, raw_content="{}", input_chars=1)


async def _route(monkeypatch, provider, *, call_type="event_analysis", max_tokens=10):
    monkeypatch.setenv("LLM_PROVIDER_PRIORITY", provider.name)
    monkeypatch.setenv(llm_config.api_key_env(provider.name), "test-key")
    router = LLMRouter(registry={provider.name: provider})
    return await router.chat_completion(
        call_type=call_type,
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=max_tokens,
        response_format=None,
    )


@pytest.mark.asyncio
async def test_router_uses_low_reasoning_effort_by_default(monkeypatch):
    monkeypatch.setenv("GROQ_EVENT_ANALYSIS_MODEL", "openai/gpt-oss-120b")
    provider = _RecordingProvider("groq")
    await _route(monkeypatch, provider)
    assert provider.seen[0]["reasoning_effort"] == "low"


@pytest.mark.asyncio
async def test_router_raises_only_thinking_attempt_budget(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER_PRIORITY", "groq,mistral")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_EVENT_ANALYSIS_MODEL", "openai/gpt-oss-120b")
    monkeypatch.setenv("MISTRAL_MODEL", "mistral-small-latest")
    groq = _RecordingProvider("groq")
    mistral = _RecordingProvider("mistral")
    router = LLMRouter(registry={"groq": groq, "mistral": mistral})

    await router.chat_completion(
        call_type="event_analysis",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=300,
        response_format=None,
    )

    assert groq.seen[0]["max_tokens"] == 1324
    assert mistral.seen == []


@pytest.mark.asyncio
async def test_router_passes_configured_reasoning_effort(monkeypatch):
    monkeypatch.setenv("LLM_EVENT_ANALYSIS_REASONING_EFFORT", "high")
    monkeypatch.setenv("GROQ_EVENT_ANALYSIS_MODEL", "openai/gpt-oss-120b")
    provider = _RecordingProvider("groq")
    await _route(monkeypatch, provider)
    assert provider.seen[0]["reasoning_effort"] == "high"


@pytest.mark.asyncio
async def test_router_uses_low_effort_and_matching_headroom_after_invalid_override(monkeypatch):
    monkeypatch.setenv("LLM_EVENT_ANALYSIS_REASONING_EFFORT", "extreme")
    monkeypatch.setenv("GROQ_EVENT_ANALYSIS_MODEL", "openai/gpt-oss-120b")
    provider = _RecordingProvider("groq")

    await _route(monkeypatch, provider, max_tokens=300)

    assert provider.seen[0] == {
        "model": "openai/gpt-oss-120b",
        "max_tokens": 1324,
        "reasoning_effort": "low",
    }


@pytest.mark.asyncio
async def test_router_omits_reasoning_effort_for_a_non_reasoning_model(monkeypatch):
    monkeypatch.setenv("LLM_REASONING_EFFORT", "high")
    monkeypatch.setenv("GROQ_EVENT_ANALYSIS_MODEL", "llama-3.3-70b-versatile")
    provider = _RecordingProvider("groq")
    await _route(monkeypatch, provider)
    assert provider.seen[0]["reasoning_effort"] is None


# --- request payload -------------------------------------------------------------------


class _CapturingCompletions:
    def __init__(self):
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs

        class _Message:
            content = "{}"

        class _Choice:
            message = _Message()

        class _Response:
            choices = [_Choice()]
            usage = None

        return _Response()


class _CapturingClient:
    def __init__(self):
        self.completions = _CapturingCompletions()

    @property
    def chat(self):
        return self


async def _provider_payload(monkeypatch, **call_kwargs):
    from bot.services.llm.groq_provider import GroqProvider

    provider = GroqProvider()
    client = _CapturingClient()
    monkeypatch.setattr(provider, "get_client", lambda: client)
    await provider.chat_completion(
        call_type="event_analysis",
        symbol="BTC",
        model="test-model",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=1234,
        response_format=None,
        **call_kwargs,
    )
    return client.completions.kwargs


@pytest.mark.asyncio
async def test_request_payload_omits_reasoning_effort_when_unset(monkeypatch):
    kwargs = await _provider_payload(monkeypatch)
    assert "reasoning_effort" not in kwargs
    assert kwargs["max_tokens"] == 1234


@pytest.mark.asyncio
async def test_request_payload_includes_reasoning_effort_when_set(monkeypatch):
    kwargs = await _provider_payload(monkeypatch, reasoning_effort="low")
    assert kwargs["reasoning_effort"] == "low"


@pytest.mark.asyncio
async def test_gemini_adapter_uses_verified_openai_compatible_reasoning_contract(monkeypatch):
    from bot.services.llm.gemini_provider import GeminiProvider

    provider = GeminiProvider()
    client = _CapturingClient()
    monkeypatch.setattr(provider, "get_client", lambda: client)
    model = "gemini-2.5-flash"
    max_tokens = llm_config.effective_max_tokens_for(
        call_type="daily_report",
        provider="gemini",
        model=model,
        requested_max_tokens=800,
    )
    await provider.chat_completion(
        call_type="daily_report",
        symbol=None,
        model=model,
        messages=[{"role": "user", "content": "Return JSON."}],
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
        reasoning_effort=llm_config.reasoning_effort_for(model, "daily_report"),
    )

    assert client.completions.kwargs["reasoning_effort"] == "low"
    assert client.completions.kwargs["max_tokens"] == 1824
    assert client.completions.kwargs["response_format"] == {"type": "json_object"}


def test_out_of_range_high_budget_falls_back_and_warns(monkeypatch, caplog):
    monkeypatch.setenv("LLM_EVENT_ANALYSIS_MAX_TOKENS", "300000")

    with caplog.at_level(logging.WARNING, logger="bot.services.llm.env"):
        assert llm_config.max_tokens_for("event_analysis") == 300

    assert any("above_maximum" in r.getMessage() for r in caplog.records)


# --- model resolution ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("provider", "env_name", "expected"),
    [
        ("groq", "GROQ_EVENT_ANALYSIS_MODEL", "openai/gpt-oss-120b"),
        ("cerebras", "CEREBRAS_MODEL", "gpt-oss-120b"),
        ("gemini", "GEMINI_MODEL", "gemini-2.5-flash"),
        ("mistral", "MISTRAL_MODEL", "mistral-small-latest"),
    ],
)
def test_empty_model_value_falls_back_and_warns(monkeypatch, caplog, provider, env_name,
                                                expected):
    # A present-but-empty model would otherwise be sent as model="" — a 400 the router treats
    # as deterministic, which aborts the chain instead of falling through to the next provider.
    monkeypatch.setenv(env_name, "")

    with caplog.at_level(logging.WARNING, logger="bot.services.llm.env"):
        assert llm_config.model_for(provider, "event_analysis") == expected

    assert any(env_name in r.getMessage() for r in caplog.records)


def test_model_value_is_stripped(monkeypatch):
    monkeypatch.setenv("GROQ_EVENT_ANALYSIS_MODEL", "  llama-3.1-8b-instant  ")
    assert llm_config.model_for("groq", "event_analysis") == "llama-3.1-8b-instant"


# --- startup configuration log ---------------------------------------------------------


def _startup_log_messages(monkeypatch, caplog):
    monkeypatch.setenv("LLM_PROVIDER_PRIORITY", "groq,cerebras")
    monkeypatch.setenv("GROQ_API_KEY", "groq-secret-key-value")
    monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_EVENT_ANALYSIS_MODEL", "llama-3.3-70b-versatile")
    monkeypatch.setenv("CEREBRAS_MODEL", "gpt-oss-120b")
    for name in ("LLM_EVENT_PROVIDERS", "LLM_REPORT_PROVIDERS", "LLM_HEARTBEAT_PROVIDERS"):
        monkeypatch.delenv(name, raising=False)

    with caplog.at_level(logging.INFO, logger="bot.services.llm.config"):
        llm_config.log_resolved_configuration()
    return [r.getMessage() for r in caplog.records]


def test_startup_log_reports_every_call_type_with_models_and_budgets(monkeypatch, caplog):
    messages = _startup_log_messages(monkeypatch, caplog)

    joined = "\n".join(messages)
    for call_type in llm_config.KNOWN_CALL_TYPES:
        assert f"call_type={call_type}" in joined
    assert "groq:llama-3.3-70b-versatile" in joined
    assert "cerebras:gpt-oss-120b" in joined
    assert "max_tokens=300" in joined


def test_startup_log_marks_providers_without_an_api_key(monkeypatch, caplog):
    messages = _startup_log_messages(monkeypatch, caplog)
    joined = "\n".join(messages)

    assert "cerebras:gpt-oss-120b/effort=low/max=1324(no_api_key)" in joined
    assert "groq:llama-3.3-70b-versatile(no_api_key)" not in joined


def test_startup_log_contains_no_environment_values_or_credentials(monkeypatch, caplog):
    monkeypatch.setenv("LLM_EVENT_ANALYSIS_REASONING_EFFORT", "low")
    monkeypatch.setenv("CEREBRAS_MODEL", "gpt-oss-120b")
    messages = _startup_log_messages(monkeypatch, caplog)
    joined = "\n".join(messages)

    assert "groq-secret-key-value" not in joined
    # Credential variable *names* must not appear either, so no line can be mistaken for one.
    for name in ("GROQ_API_KEY", "CEREBRAS_API_KEY", "TELEGRAM_BOT_TOKEN", "DATABASE_URL"):
        assert name not in joined
    # Model identifiers and the resolved effort are explicitly allowed in operational logs.
    assert "effort=low" in joined


def test_startup_log_reports_safe_effective_budget_for_thinking_model(monkeypatch, caplog):
    monkeypatch.setenv("LLM_PROVIDER_PRIORITY", "groq,cerebras")
    monkeypatch.setenv("GROQ_API_KEY", "groq-key")
    monkeypatch.setenv("CEREBRAS_API_KEY", "cerebras-key")
    monkeypatch.setenv("GROQ_EVENT_ANALYSIS_MODEL", "llama-3.3-70b-versatile")
    monkeypatch.setenv("CEREBRAS_MODEL", "gpt-oss-120b")

    with caplog.at_level(logging.INFO, logger="bot.services.llm.config"):
        llm_config.log_resolved_configuration()

    joined = "\n".join(record.getMessage() for record in caplog.records)
    assert "cerebras:gpt-oss-120b/effort=low/max=1324" in joined
    assert "llm_config_budget_risk" not in joined


def test_budget_warning_is_silent_for_a_provider_with_no_api_key(monkeypatch, caplog):
    # A provider without a key is excluded from the chain, so warning about its budget is
    # noise on every start of a Groq-only deployment.
    monkeypatch.setenv("LLM_PROVIDER_PRIORITY", "groq,cerebras")
    monkeypatch.setenv("GROQ_API_KEY", "groq-key")
    monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_EVENT_ANALYSIS_MODEL", "llama-3.3-70b-versatile")
    monkeypatch.setenv("CEREBRAS_MODEL", "gpt-oss-120b")

    with caplog.at_level(logging.WARNING, logger="bot.services.llm.config"):
        llm_config.log_resolved_configuration()

    assert not [r for r in caplog.records if "llm_config_budget_risk" in r.getMessage()]


def test_startup_log_budget_warning_clears_once_the_budget_is_raised(monkeypatch, caplog):
    monkeypatch.setenv("LLM_PROVIDER_PRIORITY", "cerebras")
    monkeypatch.setenv("CEREBRAS_API_KEY", "cerebras-key")
    monkeypatch.setenv("CEREBRAS_MODEL", "gpt-oss-120b")
    monkeypatch.setenv("LLM_EVENT_ANALYSIS_MAX_TOKENS", "4000")
    monkeypatch.setenv("LLM_MARKET_HEARTBEAT_MAX_TOKENS", "4000")
    monkeypatch.setenv("LLM_REPORT_MAX_TOKENS", "4000")
    monkeypatch.setenv("LLM_NEWS_INTELLIGENCE_MAX_TOKENS", "4000")
    monkeypatch.setenv("LLM_LEGACY_ALERT_PAYLOAD_MAX_TOKENS", "4000")

    with caplog.at_level(logging.WARNING, logger="bot.services.llm.config"):
        llm_config.log_resolved_configuration()

    assert not [r for r in caplog.records if "llm_config_budget_risk" in r.getMessage()]


def test_gemini_thinking_model_uses_supported_low_reasoning_effort(monkeypatch):
    assert llm_config.is_thinking_model("gemini-2.5-flash") is True
    assert llm_config.reasoning_effort_for("gemini-2.5-flash", "event_analysis") == "low"


@pytest.mark.parametrize(
    ("call_type", "base_budget", "effective_budget"),
    [
        ("event_analysis", 300, 1324),
        ("market_heartbeat", 350, 1374),
        ("daily_report", 800, 1824),
        ("weekly_report", 800, 1824),
        ("news_intelligence", 350, 1374),
        ("legacy_alert_payload", 450, 1474),
    ],
)
def test_thinking_budget_preserves_call_type_answer_ceiling(
    call_type, base_budget, effective_budget
):
    assert llm_config.max_tokens_for(call_type) == base_budget
    assert llm_config.effective_max_tokens_for(
        call_type=call_type,
        provider="groq",
        model="openai/gpt-oss-20b",
    ) == effective_budget


@pytest.mark.parametrize(
    ("effort", "effective_budget"),
    [("low", 1824), ("medium", 8992), ("high", 25376)],
)
def test_gemini_budget_tracks_configured_reasoning_effort(
    monkeypatch, effort, effective_budget
):
    monkeypatch.setenv("LLM_REPORT_REASONING_EFFORT", effort)

    assert llm_config.effective_max_tokens_for(
        call_type="daily_report",
        provider="gemini",
        model="gemini-2.5-flash",
        requested_max_tokens=800,
    ) == effective_budget


def test_builtin_reasoning_markers_survive_legacy_extension_value(monkeypatch):
    monkeypatch.setenv("LLM_REASONING_MODEL_MARKERS", "gpt-oss")

    assert llm_config.reasoning_effort_for("gemini-2.5-flash", "daily_report") == "low"


def test_startup_log_cannot_be_forged_by_a_newline_in_a_model_value(monkeypatch, caplog):
    monkeypatch.setenv("LLM_PROVIDER_PRIORITY", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.setenv(
        "GROQ_EVENT_ANALYSIS_MODEL", "good\nops_event=llm_config call_type=forged max_tokens=1"
    )

    with caplog.at_level(logging.INFO, logger="bot.services.llm.config"):
        llm_config.log_resolved_configuration()

    for record in caplog.records:
        assert "\n" not in record.getMessage()
    assert not any("call_type=forged" in r.getMessage() for r in caplog.records)


def test_startup_log_re_emits_a_rejected_value_after_import_time(monkeypatch, caplog):
    # A value rejected during module import warns before configure_logging() has run, so the
    # warning is lost. The startup log clears the warn-once cache to guarantee it lands.
    monkeypatch.setenv("LLM_EVENT_ANALYSIS_MAX_TOKENS", "oops")
    llm_config.max_tokens_for("event_analysis")  # stands in for the import-time resolution

    with caplog.at_level(logging.WARNING, logger="bot.services.llm.env"):
        llm_config.log_resolved_configuration()

    assert any("LLM_EVENT_ANALYSIS_MAX_TOKENS" in r.getMessage() for r in caplog.records)
