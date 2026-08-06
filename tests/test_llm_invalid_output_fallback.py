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
        return ProviderResult(
            provider=self.name,
            model=model,
            raw_content=self._content,
            input_chars=1,
        )


def _configure(monkeypatch, priority, keys):
    monkeypatch.setenv("LLM_PROVIDER_PRIORITY", ",".join(priority))
    for provider in ("groq", "cerebras", "gemini", "mistral"):
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
    _configure(monkeypatch, ["groq", "cerebras"], {"groq", "cerebras"})
    valid = _valid_no_alert_analysis()
    groq = ContentProvider("groq", "not json at all")
    cerebras = ContentProvider("cerebras", json.dumps(valid))
    _install_router(monkeypatch, {"groq": groq, "cerebras": cerebras})

    result = await ai_agent_groq.ask_event_analysis_raw(
        {"symbol": "BTC", "analysis_id": "a1", "news": [], "market": {}}
    )

    raw_content, parsed = result
    assert parsed == valid
    assert result.provider == "cerebras"
    # One analysis, one pass over providers: each provider was called exactly once.
    assert groq.calls == 1
    assert cerebras.calls == 1


@pytest.mark.asyncio
async def test_event_analysis_all_providers_invalid_json_keeps_terminal_error(monkeypatch):
    _configure(monkeypatch, ["groq", "cerebras"], {"groq", "cerebras"})
    groq = ContentProvider("groq", "not json")
    cerebras = ContentProvider("cerebras", "still not json")
    _install_router(monkeypatch, {"groq": groq, "cerebras": cerebras})

    with pytest.raises(AIInvalidJsonError):
        await ai_agent_groq.ask_event_analysis_raw(
            {"symbol": "BTC", "analysis_id": "a1", "news": [], "market": {}}
        )

    assert groq.calls == 1
    assert cerebras.calls == 1


@pytest.mark.asyncio
async def test_event_analysis_schema_failure_falls_back_to_next_provider(monkeypatch):
    _configure(monkeypatch, ["groq", "cerebras"], {"groq", "cerebras"})
    valid = _valid_no_alert_analysis()
    schema_invalid = dict(valid)
    schema_invalid.pop("reason_for_no_alert")
    groq = ContentProvider("groq", json.dumps(schema_invalid))
    cerebras = ContentProvider("cerebras", json.dumps(valid))
    _install_router(monkeypatch, {"groq": groq, "cerebras": cerebras})

    def schema_check(parsed):
        if "reason_for_no_alert" not in parsed:
            raise AISchemaValidationError("missing fields: ['reason_for_no_alert']")

    result = await ai_agent_groq.ask_event_analysis_raw(
        {"symbol": "BTC", "analysis_id": "a1", "news": [], "market": {}},
        schema_check=schema_check,
    )

    assert result.provider == "cerebras"
    assert groq.calls == 1
    assert cerebras.calls == 1


@pytest.mark.asyncio
async def test_report_schema_failure_falls_back_to_next_provider(monkeypatch):
    _configure(monkeypatch, ["groq", "cerebras"], {"groq", "cerebras"})
    schema_invalid = {"report_type": "daily", "title": "Daily Market Report"}
    groq = ContentProvider("groq", json.dumps(schema_invalid))
    cerebras = ContentProvider("cerebras", json.dumps(_valid_report_payload()))
    _install_router(monkeypatch, {"groq": groq, "cerebras": cerebras})

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
    assert report["provider"] == "cerebras"
    assert groq.calls == 1
    assert cerebras.calls == 1


@pytest.mark.asyncio
async def test_report_all_providers_schema_invalid_uses_deterministic_fallback(
    monkeypatch, caplog
):
    _configure(monkeypatch, ["groq", "cerebras"], {"groq", "cerebras"})
    schema_invalid = {"report_type": "daily", "title": "Daily Market Report"}
    groq = ContentProvider("groq", json.dumps(schema_invalid))
    cerebras = ContentProvider("cerebras", json.dumps(schema_invalid))
    _install_router(monkeypatch, {"groq": groq, "cerebras": cerebras})

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
    failed_records = [
        record for record in caplog.records if "market_report_failed" in record.getMessage()
    ]
    assert failed_records, "market_report_failed must be logged"
    assert all(record.levelno == logging.WARNING for record in failed_records)
    # The sanitized failure reason (field names only) makes the schema_error diagnosable.
    assert any("detail=" in record.getMessage() for record in failed_records)
    assert any("missing_fields" in record.getMessage() for record in failed_records)
