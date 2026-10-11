"""Regression tests for the independent, bounded RSS ingestion path."""

from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from types import SimpleNamespace

import feedparser
import pytest
from sqlalchemy import select

import bot.news as news
import bot.runtime.scheduler as scheduler
import bot.services.news_service as rss
from bot.db.database import NewsItem
from bot.services.news_intelligence_service import NewsIntelligenceService
from tests.test_news_intelligence_service import FakeNewsLlm, _raw_item, build_session


def _entry(title: str, link: str, published_at: datetime) -> dict:
    return {
        "title": title,
        "link": link,
        "summary": "",
        "published": format_datetime(published_at),
    }


def _feed(entries):
    return feedparser.FeedParserDict(
        entries=[feedparser.FeedParserDict(item) for item in entries],
        feed=feedparser.FeedParserDict(title="Verified publisher"),
        bozo=False,
    )


def test_rss_merges_sources_by_publication_time_before_limit(monkeypatch):
    now = datetime.now(timezone.utc)
    feeds = {
        "old": _feed([_entry("Bitcoin ETF filing from last week", "https://example.org/old", now - timedelta(days=5))]),
        "new": _feed([_entry("Ethereum network upgrade today", "https://example.org/new", now - timedelta(minutes=20))]),
    }
    monkeypatch.setattr(rss, "RSS_FEEDS", ["old", "new"])
    monkeypatch.setattr(rss, "_read_rss_feed", feeds.__getitem__)

    items = rss.fetch_crypto_news(limit=1)
    assert [item["link"] for item in items] == ["https://example.org/new"]


def test_rss_source_failure_is_isolated_and_safely_counted(monkeypatch, caplog):
    now = datetime.now(timezone.utc)
    monkeypatch.setattr(rss, "RSS_FEEDS", ["failed", "available"])
    def reader(source):
        if source == "failed":
            raise TimeoutError("private provider response must not be logged")
        return _feed([_entry("Solana validator software upgrade", "https://example.org/sol", now)])
    monkeypatch.setattr(rss, "_read_rss_feed", reader)

    with caplog.at_level("INFO"):
        items = rss.fetch_crypto_news(limit=5)
    assert len(items) == 1
    assert "status=failed reason=TimeoutError" in caplog.text
    assert "status=ok entries=1 keyword_pass=1" in caplog.text
    assert "private provider response" not in caplog.text


@pytest.mark.asyncio
async def test_cached_high_priority_headline_does_not_consume_next_batch_slot():
    engine, session = await build_session()
    fake_llm = FakeNewsLlm()
    try:
        svc = NewsIntelligenceService(
            session, llm_client=fake_llm, model="test-model",
            max_items_per_run=1, max_llm_calls_per_run=1,
        )
        cached = _raw_item("Major Bitcoin exchange hack", "https://example.com/hack")
        newcomer = _raw_item("Ethereum network update", "https://example.com/new")
        await svc.analyze_items([cached])
        assert fake_llm.calls == 1

        await NewsIntelligenceService(
            session, llm_client=fake_llm, model="test-model",
            max_items_per_run=1, max_llm_calls_per_run=1,
        ).analyze_items([cached, newcomer])
        assert fake_llm.calls == 2
        rows = (await session.scalars(select(NewsItem))).all()
        assert {row.url for row in rows} == {
            "https://example.com/hack", "https://example.com/new"
        }
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_fresh_article_outranks_older_high_priority_in_new_work_cap():
    engine, session = await build_session()
    fake_llm = FakeNewsLlm()
    now = datetime.now(timezone.utc)
    old = _raw_item("Major Bitcoin exchange hack", "https://example.com/old")
    old["published"] = format_datetime(now - timedelta(days=3))
    fresh = _raw_item("Ethereum validator upgrade", "https://example.com/fresh")
    fresh["published"] = format_datetime(now - timedelta(minutes=15))
    try:
        svc = NewsIntelligenceService(
            session, llm_client=fake_llm, model="test-model",
            max_items_per_run=1, max_llm_calls_per_run=1,
        )
        await svc.analyze_items([old, fresh])
        rows = (await session.scalars(select(NewsItem))).all()
        assert [row.url for row in rows] == ["https://example.com/fresh"]
        assert fake_llm.calls == 1
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_scheduled_ingestion_persists_only_through_existing_intelligence(monkeypatch):
    analyzed = []
    fake_items = [{"title": "Bitcoin ETF approval", "link": "https://example.org/btc"}]
    class FakeSession:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return None
    class FakeIntelligence:
        def __init__(self, session):
            assert isinstance(session, FakeSession)
        async def analyze_items(self, items):
            analyzed.extend(items)

    monkeypatch.setattr(news, "DB_ENABLED", True)
    monkeypatch.setattr(news, "DB_SESSION_LOCAL", FakeSession)
    monkeypatch.setattr(news, "ENABLE_NEWS_INTELLIGENCE", True)
    monkeypatch.setattr(news, "fetch_crypto_news", lambda limit: fake_items)
    monkeypatch.setattr(news, "NewsIntelligenceService", FakeIntelligence)
    await news.ingest_news_job(None)
    assert analyzed == fake_items


def test_scheduled_ingestion_is_hourly_and_disabled_without_persistence(monkeypatch):
    jobs = []
    queue = SimpleNamespace(
        get_jobs_by_name=lambda name: [],
        run_repeating=lambda *args, **kwargs: jobs.append((args, kwargs)),
    )
    app = SimpleNamespace(job_queue=queue)
    monkeypatch.setattr(scheduler, "DB_ENABLED", True)
    monkeypatch.setattr(scheduler, "DB_SESSION_LOCAL", object())
    monkeypatch.setattr(scheduler, "ENABLE_NEWS_INTELLIGENCE", True)
    scheduler.schedule_news_ingestion(app)
    assert len(jobs) == 1
    assert jobs[0][1]["interval"] == 3600
    assert jobs[0][1]["job_kwargs"]["max_instances"] == 1

    jobs.clear()
    monkeypatch.setattr(scheduler, "ENABLE_NEWS_INTELLIGENCE", False)
    scheduler.schedule_news_ingestion(app)
    assert not jobs
