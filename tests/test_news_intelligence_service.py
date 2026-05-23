import json

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.db.database import Base, NewsItem, SeenNews, make_news_key, mark_news_items_seen
from bot.services.news_intelligence_service import (
    NewsIntelligenceService,
    build_post_llm_dedup_group_id,
    build_pre_llm_dedup_group_id,
    derive_impact_level,
    normalize_news_item,
    validate_llm_output,
)


async def build_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_local = async_sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    return engine, session_local()


class FakeNewsLlm:
    def __init__(self, responses=None, error: Exception | None = None):
        self.responses = list(responses or [])
        self.error = error
        self.calls = 0

    async def __call__(self, messages, model, timeout):
        self.calls += 1
        if self.error:
            raise self.error
        response = self.responses.pop(0) if self.responses else _valid_response()
        return json.dumps(response), response


def _raw_item(title="Bitcoin ETF inflows rise", link="https://example.com/btc-etf"):
    return {
        "title": title,
        "source": "Example",
        "link": link,
        "summary": "Spot Bitcoin ETF inflows increased after macro data.",
        "published": "Fri, 22 May 2026 10:00:00 GMT",
    }


def _valid_response(**overrides):
    payload = {
        "summary": "Bitcoin ETF inflows rose as traders watched macro conditions.",
        "category": "etf",
        "related_symbols": ["btc"],
        "primary_symbol": "btc",
        "impact_score": 61,
        "impact_level": "high",
        "relevance_score": 74,
        "is_noise": False,
        "is_alert_worthy": False,
        "alert_reason": "Potentially relevant BTC market context.",
        "dedup_hint": "bitcoin etf inflows rise",
    }
    payload.update(overrides)
    return payload


def test_llm_json_is_validated_and_sanitized():
    validated = validate_llm_output(
        _valid_response(
            category="invalid",
            related_symbols=["BTC", "fake", "eth", "btc"],
            primary_symbol="fake",
            impact_score=120,
            impact_level="not-real",
            relevance_score=-10,
        )
    )

    assert validated["category"] == "market"
    assert validated["related_symbols"] == ["btc", "eth"]
    assert validated["primary_symbol"] == "btc"
    assert validated["impact_score"] == 100
    assert validated["impact_level"] == "critical"
    assert validated["relevance_score"] == 0


def test_noise_cannot_be_alert_worthy():
    validated = validate_llm_output(
        _valid_response(category="noise", is_noise=True, is_alert_worthy=True)
    )

    assert validated["is_noise"] is True
    assert validated["is_alert_worthy"] is False


def test_impact_level_derives_from_score():
    assert derive_impact_level(0) == "low"
    assert derive_impact_level(25) == "medium"
    assert derive_impact_level(60) == "high"
    assert derive_impact_level(85) == "critical"


@pytest.mark.asyncio
async def test_obvious_noise_skips_llm_and_persists_news_item():
    engine, session = await build_session()
    fake_llm = FakeNewsLlm()
    try:
        service = NewsIntelligenceService(session, llm_client=fake_llm)
        result = await service.analyze_items(
            [_raw_item(title="Best crypto to buy now before this presale could explode")]
        )
        row = await session.scalar(select(NewsItem))

        assert fake_llm.calls == 0
        assert row is not None
        assert row.is_noise is True
        assert row.is_alert_worthy is False
        assert row.llm_status == "skipped_noise"
        assert result[0].keys() >= {"title", "source", "link", "url", "summary", "published"}
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_existing_analysis_is_reused_without_repeated_llm_call():
    engine, session = await build_session()
    fake_llm = FakeNewsLlm([_valid_response()])
    try:
        service = NewsIntelligenceService(session, llm_client=fake_llm)
        await service.analyze_items([_raw_item()])
        await service.analyze_items([_raw_item()])

        assert fake_llm.calls == 1
        assert await session.scalar(select(func.count()).select_from(NewsItem)) == 1
        row = await session.scalar(select(NewsItem))
        assert row.llm_status == "success"
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_per_run_budget_is_respected_and_exhaustion_does_not_crash():
    engine, session = await build_session()
    fake_llm = FakeNewsLlm([_valid_response()])
    try:
        service = NewsIntelligenceService(
            session,
            llm_client=fake_llm,
            max_items_per_run=3,
            max_llm_calls_per_run=1,
            max_llm_calls_per_hour=20,
        )
        result = await service.analyze_items(
            [
                _raw_item(title="Bitcoin ETF inflows rise", link="https://example.com/1"),
                _raw_item(title="Ethereum exchange reserves fall", link="https://example.com/2"),
                _raw_item(title="Solana network upgrade scheduled", link="https://example.com/3"),
            ]
        )
        statuses = [
            row.llm_status
            for row in (
                await session.scalars(select(NewsItem).order_by(NewsItem.id.asc()))
            ).all()
        ]

        assert len(result) == 3
        assert fake_llm.calls == 1
        assert statuses == ["success", "skipped_budget", "skipped_budget"]
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_hourly_budget_exhaustion_persists_without_llm_call():
    engine, session = await build_session()
    fake_llm = FakeNewsLlm()
    try:
        service = NewsIntelligenceService(
            session,
            llm_client=fake_llm,
            max_llm_calls_per_hour=0,
        )
        await service.analyze_items([_raw_item()])
        row = await session.scalar(select(NewsItem))

        assert fake_llm.calls == 0
        assert row.llm_status == "skipped_budget"
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_llm_failure_does_not_crash_pipeline():
    engine, session = await build_session()
    fake_llm = FakeNewsLlm(error=RuntimeError("provider failed with safe message"))
    try:
        service = NewsIntelligenceService(session, llm_client=fake_llm)
        result = await service.analyze_items([_raw_item()])
        row = await session.scalar(select(NewsItem))

        assert result[0]["title"] == "Bitcoin ETF inflows rise"
        assert fake_llm.calls == 1
        assert row.llm_status == "failed"
        assert "provider failed" in row.llm_error
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_duplicate_news_receives_stable_dedup_handling():
    engine, session = await build_session()
    fake_llm = FakeNewsLlm([_valid_response()])
    try:
        service = NewsIntelligenceService(session, llm_client=fake_llm, max_items_per_run=2)
        await service.analyze_items(
            [
                _raw_item(title="Bitcoin ETF inflows rise", link="https://example.com/a"),
                _raw_item(title="Bitcoin ETF inflows rise", link="https://example.com/b"),
            ]
        )
        rows = (
            await session.scalars(select(NewsItem).order_by(NewsItem.id.asc()))
        ).all()

        assert fake_llm.calls == 1
        assert rows[0].llm_status == "success"
        assert rows[1].llm_status == "skipped_duplicate"
        assert rows[1].is_duplicate is True
        assert build_pre_llm_dedup_group_id(normalize_news_item(_raw_item())) != ""
        assert build_post_llm_dedup_group_id("Bitcoin ETF inflows rise", "fallback").startswith(
            "hint:"
        )
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_rss_items_normalize_persist_and_preserve_seen_news_contract():
    engine, session = await build_session()
    fake_llm = FakeNewsLlm([_valid_response()])
    try:
        service = NewsIntelligenceService(session, llm_client=fake_llm)
        compatibility_items = await service.analyze_items([_raw_item()])
        item = compatibility_items[0]

        assert item["link"] == item["url"] == "https://example.com/btc-etf"
        assert item["published_at"].year == 2026
        assert make_news_key(item).startswith("link:")

        await mark_news_items_seen(session, compatibility_items)
        assert await session.scalar(select(func.count()).select_from(SeenNews)) == 1
        assert await session.scalar(select(func.count()).select_from(NewsItem)) == 1
    finally:
        await session.close()
        await engine.dispose()
