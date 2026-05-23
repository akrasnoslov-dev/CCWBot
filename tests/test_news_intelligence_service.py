import json
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.db.database import (
    Base,
    NewsItem,
    SeenNews,
    make_news_key,
    mark_news_items_seen,
    upsert_news_item,
)
from bot.news import select_intelligence_news_for_symbol
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


async def _store_news_item(session, *, title: str, **overrides):
    now = overrides.pop("now", datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc))
    slug = title.lower().replace(" ", "-")
    news_key = overrides.pop("news_key", f"link:https://example.com/{slug}")
    return await upsert_news_item(
        session,
        news_key=news_key,
        title=title,
        source=overrides.pop("source", "Example"),
        url=overrides.pop("url", news_key.removeprefix("link:")),
        published_at=overrides.pop("published_at", now),
        fetched_at=now,
        raw_summary=overrides.pop("raw_summary", "RSS summary"),
        llm_summary=overrides.pop("llm_summary", "LLM summary"),
        related_symbols=overrides.pop("related_symbols", ["btc"]),
        primary_symbol=overrides.pop("primary_symbol", "btc"),
        category=overrides.pop("category", "market"),
        impact_score=overrides.pop("impact_score", 50),
        impact_level=overrides.pop("impact_level", "high"),
        relevance_score=overrides.pop("relevance_score", 50),
        dedup_group_id=overrides.pop("dedup_group_id", news_key),
        is_duplicate=overrides.pop("is_duplicate", False),
        is_noise=overrides.pop("is_noise", False),
        is_alert_worthy=overrides.pop("is_alert_worthy", False),
        llm_provider=overrides.pop("llm_provider", "groq"),
        llm_model=overrides.pop("llm_model", "test-model"),
        llm_input_hash=overrides.pop("llm_input_hash", "abc123"),
        llm_status=overrides.pop("llm_status", "success"),
        llm_error=overrides.pop("llm_error", None),
    )


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
async def test_intelligence_news_selector_matches_symbol_and_preserves_dict_shape():
    engine, session = await build_session()
    try:
        await _store_news_item(
            session,
            title="Ethereum ETF flows rise",
            primary_symbol="eth",
            related_symbols=["eth"],
            impact_score=90,
        )
        await _store_news_item(
            session,
            title="Bitcoin ETF flows rise",
            primary_symbol="btc",
            related_symbols=["btc", "eth"],
            impact_score=70,
        )
        await _store_news_item(
            session,
            title="Macro crypto story references BTC",
            primary_symbol="eth",
            related_symbols=["btc", "eth"],
            impact_score=95,
        )

        selected = await select_intelligence_news_for_symbol(session, "btc")

        assert [item["title"] for item in selected] == [
            "Bitcoin ETF flows rise",
            "Macro crypto story references BTC",
        ]
        assert selected[0].keys() >= {
            "title",
            "source",
            "link",
            "url",
            "summary",
            "published",
            "published_at",
        }
        assert selected[0]["link"] == selected[0]["url"]
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_intelligence_news_selector_excludes_noise():
    engine, session = await build_session()
    try:
        await _store_news_item(
            session,
            title="Bitcoin ETF flows rise",
            primary_symbol="btc",
            related_symbols=["btc"],
            is_noise=True,
            impact_score=100,
        )

        selected = await select_intelligence_news_for_symbol(session, "btc")

        assert selected == []
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_intelligence_news_selector_ranks_by_impact_relevance_and_recency():
    engine, session = await build_session()
    now = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)
    try:
        await _store_news_item(
            session,
            title="Lower impact recent BTC headline",
            primary_symbol="btc",
            impact_score=40,
            relevance_score=95,
            published_at=now,
        )
        await _store_news_item(
            session,
            title="Higher impact older BTC headline",
            primary_symbol="btc",
            impact_score=80,
            relevance_score=40,
            published_at=now - timedelta(hours=2),
        )
        await _store_news_item(
            session,
            title="Same impact newer BTC headline",
            primary_symbol="btc",
            impact_score=80,
            relevance_score=40,
            published_at=now - timedelta(minutes=30),
        )

        selected = await select_intelligence_news_for_symbol(session, "btc")

        assert [item["title"] for item in selected] == [
            "Same impact newer BTC headline",
            "Higher impact older BTC headline",
            "Lower impact recent BTC headline",
        ]
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_intelligence_news_selector_deduplicates_story_clusters():
    engine, session = await build_session()
    try:
        await _store_news_item(
            session,
            title="Lower impact duplicate BTC story",
            primary_symbol="btc",
            impact_score=30,
            dedup_group_id="btc-etf-flow",
            url="https://example.com/low",
        )
        await _store_news_item(
            session,
            title="Higher impact duplicate BTC story",
            primary_symbol="btc",
            impact_score=90,
            dedup_group_id="btc-etf-flow",
            url="https://example.com/high",
        )

        selected = await select_intelligence_news_for_symbol(session, "btc")

        assert [item["title"] for item in selected] == ["Higher impact duplicate BTC story"]
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
