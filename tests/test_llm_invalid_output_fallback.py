"""Invalid-output fallback through the real facade functions and router.

Covers the post-ops-report Task 2 contract end to end: broken JSON or schema-invalid
output from the primary provider advances the chain and the analysis/report is produced
by the fallback provider; when every provider returns invalid output, the existing
terminal behaviour (AIInvalidJsonError / deterministic report fallback) is preserved.
"""

import json
import logging

import pytest

import bot.reports as reports
import bot.services.ai_agent_groq as ai_agent_groq
from bot.services.llm import config
from bot.services.llm.base_provider import BaseProvider, ProviderResult
from bot.services.llm.errors import AIInvalidJsonError, AISchemaValidationError
from bot.services.llm.router import LLMRouter


class ContentProvider(BaseProvider):
    """Fake provider returning fixed raw content."""

    def __init__(self, name, content):
        self.name = name
        self._content = content
        self.calls = 0

    async def chat_completion(self, *, call_type, symbol, model, messages, max_tokens,
                              response_format, timeout=15, reasoning_effort=None):
        self.calls += 1
        if isinstance(self._content, Exception):
            raise self._content
        return ProviderResult(
            provider=self.name,
            model=model,
            raw_content=self._content,
            input_chars=1,
        )


class ProviderHttpError(RuntimeError):
    def __init__(self, message, *, status_code, code=None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code


def _configure(monkeypatch, priority, keys):
    monkeypatch.setenv("LLM_PROVIDER_PRIORITY", ",".join(priority))
    for provider in ("groq", "gemini", "mistral"):
        env = config.api_key_env(provider)
        if provider in keys:
            monkeypatch.setenv(env, f"{provider}-key")
        else:
            monkeypatch.delenv(env, raising=False)


def _install_router(monkeypatch, registry):
    router = LLMRouter(registry=registry)
    monkeypatch.setattr(ai_agent_groq, "get_router", lambda: router)
    return router


def _valid_no_alert_analysis():
    return {
        "symbol": "BTC",
        "should_alert": False,
        "event_key": None,
        "title": None,
        "message_body": None,
        "related_news_ids": [],
        "possible_action": None,
        "urgency": None,
        "confidence": "medium",
        "reason_for_no_alert": "The analysed-window change is small and news is absent.",
    }


def _valid_report_payload(report_type="daily"):
    return {
        "report_type": report_type,
        "title": "Daily Market Report" if report_type == "daily" else "Weekly Market Report",
        "market_pulse": "Mixed market.",
        "dashboard": ["BTC is steady.", "ETH is mixed."],
        "coin_cards": [
            {"symbol": "BTC", "summary": "BTC is steady.", "watch": "Watch the range."},
            {"symbol": "ETH", "summary": "ETH is mixed.", "watch": "Watch ETF flow news."},
            {"symbol": "GRAM", "summary": "GRAM is steady.", "watch": "Watch liquidity."},
            {"symbol": "SOL", "summary": "SOL is steady.", "watch": "Watch network news."},
        ],
        "market_catalysts": [],
        "why_it_matters": "Mixed conditions make confirmation more useful than speed.",
        "watch_next": "Monitor risk without rushing.",
        "week_timeline": [],
        "themes": [],
        "next_week_focus": "",
    }


def _market_data():
    coin = {
        "price": 100.0,
        "change_1h": 0.1,
        "change_24h": 0.5,
        "change_7d": 1.0,
        "volume_24h": 1000.0,
        "market_cap": 100000.0,
        "rank": 1,
        "sparkline_7d": [99.0, 100.0],
        "weekly_start": 99.0,
        "weekly_end": 100.0,
        "weekly_high": 101.0,
        "weekly_low": 98.0,
        "range_position": 0.5,
    }
    return {symbol: dict(coin) for symbol in ("btc", "eth", "gram", "sol")}


def _empty_report_news_context():
    return (
        {
            "market_news": [],
            "coin_news": {"BTC": [], "ETH": [], "GRAM": [], "SOL": []},
            "fallback": "No clearly relevant fresh news found for tracked coins",
        },
        [],
    )


@pytest.fixture(autouse=True)
def _clear_report_caches():
    reports._memory_report_cache.clear()
    reports._report_provider_backoff_until.clear()
    yield
    reports._memory_report_cache.clear()
    reports._report_provider_backoff_until.clear()


@pytest.mark.asyncio
async def test_event_analysis_invalid_json_falls_back_to_next_provider(monkeypatch):
    _configure(monkeypatch, ["groq", "gemini"], {"groq", "gemini"})
    valid = _valid_no_alert_analysis()
    groq = ContentProvider("groq", "not json at all")
    gemini = ContentProvider("gemini", json.dumps(valid))
    _install_router(monkeypatch, {"groq": groq, "gemini": gemini})

    result = await ai_agent_groq.ask_event_analysis_raw(
        {"symbol": "BTC", "analysis_id": "a1", "news": [], "market": {}}
    )

    raw_content, parsed = result
    assert parsed == valid
    assert result.provider == "gemini"
    # One analysis, one pass over providers: each provider was called exactly once.
    assert groq.calls == 1
    assert gemini.calls == 1


@pytest.mark.asyncio
async def test_event_analysis_all_providers_invalid_json_keeps_terminal_error(monkeypatch):
    _configure(monkeypatch, ["groq", "gemini"], {"groq", "gemini"})
    groq = ContentProvider("groq", "not json")
    gemini = ContentProvider("gemini", "still not json")
    _install_router(monkeypatch, {"groq": groq, "gemini": gemini})

    with pytest.raises(AIInvalidJsonError):
        await ai_agent_groq.ask_event_analysis_raw(
            {"symbol": "BTC", "analysis_id": "a1", "news": [], "market": {}}
        )

    assert groq.calls == 1
    assert gemini.calls == 1


@pytest.mark.asyncio
async def test_event_analysis_schema_failure_falls_back_to_next_provider(monkeypatch):
    _configure(monkeypatch, ["groq", "gemini"], {"groq", "gemini"})
    valid = _valid_no_alert_analysis()
    schema_invalid = dict(valid)
    schema_invalid.pop("reason_for_no_alert")
    groq = ContentProvider("groq", json.dumps(schema_invalid))
    gemini = ContentProvider("gemini", json.dumps(valid))
    _install_router(monkeypatch, {"groq": groq, "gemini": gemini})

    def schema_check(parsed):
        if "reason_for_no_alert" not in parsed:
            raise AISchemaValidationError("missing fields: ['reason_for_no_alert']")

    result = await ai_agent_groq.ask_event_analysis_raw(
        {"symbol": "BTC", "analysis_id": "a1", "news": [], "market": {}},
        schema_check=schema_check,
    )

    assert result.provider == "gemini"
    assert groq.calls == 1
    assert gemini.calls == 1


@pytest.mark.asyncio
async def test_market_heartbeat_schema_failure_falls_back_to_next_provider(monkeypatch):
    _configure(monkeypatch, ["groq", "gemini"], {"groq", "gemini"})
    invalid = {
        "symbol": "ETH",
        "title": "Wrong symbol",
        "message_body": "Routine conditions.",
        "related_news_ids": [],
        "possible_action": "Watch the range.",
        "confidence": "low",
    }
    valid = dict(invalid, symbol="BTC", title="BTC heartbeat")
    groq = ContentProvider("groq", json.dumps(invalid))
    gemini = ContentProvider("gemini", json.dumps(valid))
    _install_router(monkeypatch, {"groq": groq, "gemini": gemini})

    def schema_check(parsed):
        if parsed.get("symbol") != "BTC":
            raise AISchemaValidationError("symbol mismatch")

    result = await ai_agent_groq.ask_market_heartbeat_raw(
        {"symbol": "BTC", "candidate_news": []}, schema_check=schema_check
    )

    assert result.provider == "gemini"
    assert result[1] == valid
    assert groq.calls == 1
    assert gemini.calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("call_path", ["news_intelligence", "legacy_alert_payload"])
async def test_other_structured_call_paths_fall_back_on_schema_invalid_json(
    monkeypatch, call_path
):
    _configure(monkeypatch, ["groq", "gemini"], {"groq", "gemini"})
    valid_legacy = {
        "news_relevance": "not_relevant",
        "risk_level": "low",
        "risk_reason": "The move is limited.",
        "context_sentence": "Conditions remain routine.",
        "possible_action": "Watch the next alert window.",
        "related_news_ids": [],
    }
    valid_news = {
        "summary": "Routine market update.",
        "category": "market",
        "related_symbols": ["btc"],
        "primary_symbol": "btc",
        "impact_score": 25,
        "impact_level": "medium",
        "relevance_score": 50,
        "is_noise": False,
        "is_alert_worthy": False,
        "alert_reason": "No immediate alert condition.",
        "dedup_hint": "routine market update",
    }
    valid = valid_news if call_path == "news_intelligence" else valid_legacy
    groq = ContentProvider("groq", '{"ok": true}')
    gemini = ContentProvider("gemini", json.dumps(valid))
    _install_router(monkeypatch, {"groq": groq, "gemini": gemini})

    if call_path == "news_intelligence":
        from bot.services.news_intelligence_service import validate_news_intelligence_schema

        def schema_check(parsed):
            try:
                validate_news_intelligence_schema(parsed)
            except ValueError as error:
                raise AISchemaValidationError(str(error)) from error

        result = await ai_agent_groq.ask_news_intelligence_raw(
            [{"role": "user", "content": "classify"}], schema_check=schema_check
        )
        parsed = result[1]
    else:
        def schema_check(parsed):
            if ai_agent_groq._normalize_alert_structured_fields(parsed) is None:
                raise AISchemaValidationError("legacy alert payload schema mismatch")

        parsed, _usage_log_id = await ai_agent_groq._ask_json_with_usage(
            "build a legacy alert",
            call_type="legacy_alert_payload",
            schema_check=schema_check,
        )

    assert parsed == valid
    assert groq.calls == 1
    assert gemini.calls == 1


@pytest.mark.asyncio
async def test_legacy_schema_exhaustion_preserves_none_contract(monkeypatch):
    _configure(monkeypatch, ["groq", "gemini"], {"groq", "gemini"})
    groq = ContentProvider("groq", '{"ok": true}')
    gemini = ContentProvider("gemini", '{"risk_level": "low"}')
    _install_router(monkeypatch, {"groq": groq, "gemini": gemini})

    assert await ai_agent_groq._ask_json("build a legacy alert") is None
    assert groq.calls == 1
    assert gemini.calls == 1


@pytest.mark.asyncio
async def test_report_schema_failure_falls_back_to_next_provider(monkeypatch):
    _configure(monkeypatch, ["groq", "gemini"], {"groq", "gemini"})
    schema_invalid = {"report_type": "daily", "title": "Daily Market Report"}
    groq = ContentProvider("groq", json.dumps(schema_invalid))
    gemini = ContentProvider("gemini", json.dumps(_valid_report_payload()))
    _install_router(monkeypatch, {"groq": groq, "gemini": gemini})

    async def fake_market_data(symbols):
        return _market_data()

    monkeypatch.setattr(reports, "get_report_market_data_batch", fake_market_data)

    async def fake_news(symbols, prefer_unseen=True):
        return _empty_report_news_context()

    monkeypatch.setattr(reports, "fetch_report_news_context", fake_news)

    async def fake_remember(news_items):
        return None

    monkeypatch.setattr(reports, "remember_news_context", fake_remember)

    report = await reports.generate_report_cache("daily")

    assert report["status"] == "completed"
    # The fallback provider answered, so this is a real LLM report, not the
    # deterministic fallback.
    assert report["error_message"] is None
    assert report["provider"] == "gemini"
    assert groq.calls == 1
    assert gemini.calls == 1


@pytest.mark.asyncio
async def test_report_all_providers_schema_invalid_uses_deterministic_fallback(
    monkeypatch, caplog
):
    _configure(monkeypatch, ["groq", "gemini"], {"groq", "gemini"})
    schema_invalid = {"report_type": "daily", "title": "Daily Market Report"}
    groq = ContentProvider("groq", json.dumps(schema_invalid))
    gemini = ContentProvider("gemini", json.dumps(schema_invalid))
    _install_router(monkeypatch, {"groq": groq, "gemini": gemini})

    async def fake_market_data(symbols):
        return _market_data()

    monkeypatch.setattr(reports, "get_report_market_data_batch", fake_market_data)

    async def fake_news(symbols, prefer_unseen=True):
        return _empty_report_news_context()

    monkeypatch.setattr(reports, "fetch_report_news_context", fake_news)

    async def fake_remember(news_items):
        return None

    monkeypatch.setattr(reports, "remember_news_context", fake_remember)

    with caplog.at_level(logging.WARNING):
        report = await reports.generate_report_cache("daily")

    # Terminal behaviour is unchanged: deterministic fallback, completed report.
    assert report["status"] == "completed"
    assert "deterministic fallback after schema_validation_failed" in report["error_message"]
    assert report["provider"] == reports.DETERMINISTIC_REPORT_PROVIDER
    assert report["model"] == reports.DETERMINISTIC_REPORT_MODEL
    failed_records = [
        record for record in caplog.records if "market_report_failed" in record.getMessage()
    ]
    assert failed_records, "market_report_failed must be logged"
    assert all(record.levelno == logging.WARNING for record in failed_records)
    # The sanitized failure reason (field names only) makes the schema_error diagnosable.
    assert any("detail=" in record.getMessage() for record in failed_records)
    assert any("missing_fields" in record.getMessage() for record in failed_records)


async def _install_report_inputs(monkeypatch):
    async def fake_market_data(symbols):
        return _market_data()

    async def fake_news(symbols, prefer_unseen=True):
        return _empty_report_news_context()

    async def fake_remember(news_items):
        return None

    monkeypatch.setattr(reports, "get_report_market_data_batch", fake_market_data)
    monkeypatch.setattr(reports, "fetch_report_news_context", fake_news)
    monkeypatch.setattr(reports, "remember_news_context", fake_remember)


@pytest.mark.asyncio
async def test_production_report_chain_reaches_mistral_and_persists_actual_route(monkeypatch):
    providers = ("groq", "gemini", "mistral")
    _configure(monkeypatch, providers, set(providers))
    schema_invalid = json.dumps({"report_type": "daily", "title": "Daily Market Report"})
    registry = {
        "groq": ContentProvider("groq", schema_invalid),
        "gemini": ContentProvider(
            "gemini",
            ProviderHttpError("model route unavailable", status_code=404, code="model_not_found"),
        ),
        "mistral": ContentProvider("mistral", json.dumps(_valid_report_payload())),
    }
    _install_router(monkeypatch, registry)
    await _install_report_inputs(monkeypatch)

    report = await reports.generate_report_cache("daily")

    assert report["status"] == "completed"
    assert report["provider"] == "mistral"
    assert report["model"] == config.model_for("mistral", "daily_report")
    assert [registry[name].calls for name in providers] == [1, 1, 1]


@pytest.mark.asyncio
async def test_production_report_chain_can_succeed_before_final_provider(monkeypatch):
    providers = ("groq", "gemini", "mistral")
    _configure(monkeypatch, providers, set(providers))
    schema_invalid = json.dumps({"report_type": "daily", "title": "Daily Market Report"})
    registry = {
        "groq": ContentProvider("groq", schema_invalid),
        "gemini": ContentProvider("gemini", json.dumps(_valid_report_payload())),
        "mistral": ContentProvider("mistral", RuntimeError("must not be called")),
    }
    _install_router(monkeypatch, registry)
    await _install_report_inputs(monkeypatch)

    report = await reports.generate_report_cache("daily")

    assert report["provider"] == "gemini"
    assert report["model"] == config.model_for("gemini", "daily_report")
    assert [registry[name].calls for name in providers] == [1, 1, 0]


@pytest.mark.asyncio
async def test_report_bad_request_is_terminal_without_fanout(monkeypatch):
    providers = ("groq", "gemini", "mistral")
    _configure(monkeypatch, providers, set(providers))
    registry = {
        "groq": ContentProvider(
            "groq", ProviderHttpError("malformed request", status_code=400, code="bad_request")
        ),
        "gemini": ContentProvider("gemini", RuntimeError("must not be called")),
        "mistral": ContentProvider("mistral", RuntimeError("must not be called")),
    }
    _install_router(monkeypatch, registry)

    with pytest.raises(ProviderHttpError):
        await ai_agent_groq.ask_market_report_raw(
            {"report_type": "daily", "active_symbols": ["BTC", "ETH", "GRAM", "SOL"]}
        )

    assert [registry[name].calls for name in providers] == [1, 0, 0]


@pytest.mark.asyncio
async def test_three_provider_schema_exhaustion_uses_safe_deterministic_report(monkeypatch):
    providers = ("groq", "gemini", "mistral")
    _configure(monkeypatch, providers, set(providers))
    schema_invalid = json.dumps({"report_type": "daily", "title": "Daily Market Report"})
    registry = {name: ContentProvider(name, schema_invalid) for name in providers}
    _install_router(monkeypatch, registry)
    await _install_report_inputs(monkeypatch)

    report = await reports.generate_report_cache("daily")

    assert report["status"] == "completed"
    assert report["provider"] == reports.DETERMINISTIC_REPORT_PROVIDER
    assert report["model"] == reports.DETERMINISTIC_REPORT_MODEL
    assert report["error_message"] == "deterministic fallback after schema_validation_failed"
    assert [registry[name].calls for name in providers] == [1, 1, 1]
