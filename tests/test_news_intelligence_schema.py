"""Offline News Intelligence symbol-contract regression tests; no provider calls."""

import json
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from test_news_intelligence_service import _raw_item, build_session

import bot.services.ai_agent_groq as agent
from bot.db.database import LlmOperationOutcome, NewsItem
from bot.services.llm import config
from bot.services.llm.base_provider import BaseProvider, ProviderResult
from bot.services.llm.errors import AISchemaValidationError, LLMRateLimitBackoffActive
from bot.services.llm.router import LLMRouter
from bot.services.news_intelligence_service import (
    NewsIntelligenceService,
    _default_llm_client,
    validate_llm_output,
    validate_news_intelligence_schema,
)


def _valid(**changes):
    result = {
        "summary": "Synthetic market context.",
        "category": "market",
        "related_symbols": ["btc"],
        "primary_symbol": "btc",
        "impact_score": 35,
        "impact_level": "medium",
        "relevance_score": 40,
        "is_noise": False,
        "is_alert_worthy": False,
        "alert_reason": "No alert.",
        "dedup_hint": "",
    }
    result.update(changes)
    return result


class RecordedProvider(BaseProvider):
    def __init__(self, name, response):
        self.name = name
        self.response = response
        self.calls = []

    async def chat_completion(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.response, Exception):
            raise self.response
        return ProviderResult(
            provider=self.name,
            model=kwargs["model"],
            raw_content=json.dumps(self.response),
            input_chars=30,
        )


def _router(monkeypatch, groq_response, gemini_response):
    monkeypatch.setenv("LLM_PROVIDER_PRIORITY", "groq,gemini")
    monkeypatch.setenv("GROQ_JSON_MODE", "true")
    monkeypatch.setenv("GROQ_API_KEY", "synthetic-test-key")
    monkeypatch.setenv("GEMINI_API_KEY", "synthetic-test-key")
    groq = RecordedProvider("groq", groq_response)
    gemini = RecordedProvider("gemini", gemini_response)
    monkeypatch.setattr(agent, "get_router", lambda: LLMRouter(
        registry={"groq": groq, "gemini": gemini},
    ))
    return groq, gemini


@pytest.mark.asyncio
async def test_groq_news_uses_strict_schema_and_gemini_keeps_json_mode(monkeypatch):
    groq, gemini = _router(monkeypatch, _valid(primary_symbol="not-supported"), _valid())
    result = await _default_llm_client(
        [{"role": "user", "content": "Synthetic classification"}],
        config.model_for("groq", "news_intelligence"),
        15,
    )
    assert result.provider == "gemini"
    assert len(groq.calls) == len(gemini.calls) == 1
    assert gemini.calls[0]["response_format"] == {"type": "json_object"}
    fmt = groq.calls[0]["response_format"]
    assert fmt["type"] == "json_schema"
    assert fmt["json_schema"]["strict"] is True
    schema = fmt["json_schema"]["schema"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(_valid())
    assert schema["properties"]["primary_symbol"]["enum"] == [None, "btc", "eth", "gram", "sol"]


@pytest.mark.asyncio
async def test_unsupported_override_stays_json_object(monkeypatch):
    groq, _ = _router(monkeypatch, _valid(), _valid())
    await _default_llm_client(
        [{"role": "user", "content": "Synthetic classification"}],
        "unsupported-groq-test-model",
        15,
    )
    assert groq.calls[0]["response_format"] == {"type": "json_object"}


@pytest.mark.parametrize(
    ("primary", "related"),
    [(None, ["btc", "eth"]), (None, []), ("", ["btc", "eth"]), (None, ["sol"])],
)
def test_unknown_or_multicoin_stays_without_primary(primary, related):
    output = _valid(primary_symbol=primary, related_symbols=related)
    validate_news_intelligence_schema(output)
    assert validate_llm_output(output)["primary_symbol"] is None


def test_invalid_primary_is_not_silently_reassigned():
    for invalid in ("doge", "bitcoin", ["btc"], 123):
        output = _valid(primary_symbol=invalid, related_symbols=["btc", "eth"])
        with pytest.raises(ValueError, match="invalid primary_symbol"):
            validate_news_intelligence_schema(output)
        with pytest.raises(ValueError, match="invalid primary_symbol"):
            validate_llm_output(output)


def test_irrelevant_news_without_symbol_remains_noise():
    output = _valid(
        primary_symbol=None, related_symbols=[], category="noise", is_noise=True,
        is_alert_worthy=False, impact_score=0, relevance_score=0, impact_level="low",
    )
    validate_news_intelligence_schema(output)
    normalized = validate_llm_output(output)
    assert normalized["is_noise"] is True
    assert normalized["primary_symbol"] is None
    assert normalized["related_symbols"] == []
    assert normalized["is_alert_worthy"] is False


@pytest.mark.asyncio
async def test_invalid_primary_and_gemini_backoff_stay_failed_not_cached_success(monkeypatch):
    backoff = LLMRateLimitBackoffActive(
        provider="gemini", model=config.model_for("gemini", "news_intelligence"),
        limited_until=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    groq, gemini = _router(
        monkeypatch, _valid(primary_symbol="doge", is_alert_worthy=True), backoff,
    )
    engine, session = await build_session()
    try:
        rows = await NewsIntelligenceService(session).analyze_items([_raw_item()])
        assert len(rows) == 1
        row = await session.scalar(select(NewsItem))
        assert row.llm_status == "failed"
        assert row.primary_symbol is None
        assert row.is_alert_worthy is False
        assert len(groq.calls) == len(gemini.calls) == 1
        outcomes = (await session.execute(select(LlmOperationOutcome))).scalars().all()
        assert len(outcomes) == 1
        assert outcomes[0].status == "failed"
        assert outcomes[0].error_reason == "schema_validation_failed"
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_all_invalid_symbols_remain_schema_error(monkeypatch):
    groq, gemini = _router(
        monkeypatch, _valid(primary_symbol="doge"), _valid(primary_symbol="xrp"),
    )
    with pytest.raises(AISchemaValidationError, match="invalid primary_symbol"):
        await _default_llm_client(
            [{"role": "user", "content": "Synthetic classification"}],
            config.model_for("groq", "news_intelligence"), 15,
        )
    assert len(groq.calls) == len(gemini.calls) == 1
