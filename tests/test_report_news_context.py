from unittest.mock import AsyncMock

import pytest

import bot.news as news


@pytest.mark.asyncio
async def test_report_news_context_selects_market_and_coin_news(monkeypatch):
    monkeypatch.setattr(
        news,
        "fetch_news_context",
        AsyncMock(
            return_value=[
                {
                    "title": "Crypto market rallies as liquidity improves",
                    "source": "CoinDesk",
                    "link": "https://example.com/market",
                    "published": "2026-06-25T08:00:00Z",
                },
                {
                    "title": "Ethereum ETF inflows accelerate",
                    "source": "Cointelegraph",
                    "link": "https://example.com/eth",
                    "published": "2026-06-25T07:00:00Z",
                    "primary_symbol": "eth",
                    "related_symbols": ["eth"],
                    "impact_score": 4,
                    "relevance_score": 5,
                },
                {
                    "title": "Solana network upgrade draws validator support",
                    "source": "CoinDesk",
                    "link": "https://example.com/sol",
                    "published": "2026-06-25T06:00:00Z",
                    "primary_symbol": "sol",
                    "related_symbols": ["sol"],
                },
            ]
        ),
    )

    payload, selected = await news.fetch_report_news_context(["btc", "eth", "ton", "sol"])

    assert [item["title"] for item in payload["market_news"]] == [
        "Crypto market rallies as liquidity improves"
    ]
    assert [item["title"] for item in payload["coin_news"]["ETH"]] == [
        "Ethereum ETF inflows accelerate"
    ]
    assert [item["title"] for item in payload["coin_news"]["SOL"]] == [
        "Solana network upgrade draws validator support"
    ]
    assert payload["coin_news"]["GRAM"] == []
    assert payload["fallback"] == ""
    assert all(item["title"] and item["source"] and item["link"] for item in selected)


@pytest.mark.asyncio
async def test_report_news_context_does_not_assign_btc_only_news_to_altcoins(monkeypatch):
    monkeypatch.setattr(
        news,
        "fetch_news_context",
        AsyncMock(
            return_value=[
                {
                    "title": "Bitcoin ETF flows rise again",
                    "source": "CoinDesk",
                    "link": "https://example.com/btc-etf",
                    "published": "2026-06-25T08:00:00Z",
                },
                {
                    "title": "GRAM token liquidity improves after TON rebrand",
                    "source": "CoinDesk",
                    "link": "https://example.com/gram",
                    "published": "2026-06-25T07:00:00Z",
                },
            ]
        ),
    )

    payload, _ = await news.fetch_report_news_context(["eth", "ton"])

    assert payload["coin_news"]["ETH"] == []
    assert [item["title"] for item in payload["coin_news"]["GRAM"]] == [
        "GRAM token liquidity improves after TON rebrand"
    ]
    assert payload["coin_news"]["GRAM"][0]["related_symbols"] == ["GRAM"]


@pytest.mark.asyncio
async def test_report_news_context_allows_direct_multi_coin_news_in_each_bucket(monkeypatch):
    monkeypatch.setattr(
        news,
        "fetch_news_context",
        AsyncMock(
            return_value=[
                {
                    "title": "Bitcoin and Ethereum ETF flows lift crypto markets",
                    "source": "CoinDesk",
                    "link": "https://example.com/btc-eth",
                    "published": "2026-06-25T08:00:00Z",
                    "primary_symbol": "btc",
                    "related_symbols": ["btc", "eth"],
                }
            ]
        ),
    )

    payload, selected = await news.fetch_report_news_context(["btc", "eth"])

    assert [item["title"] for item in payload["coin_news"]["BTC"]] == [
        "Bitcoin and Ethereum ETF flows lift crypto markets"
    ]
    assert [item["title"] for item in payload["coin_news"]["ETH"]] == [
        "Bitcoin and Ethereum ETF flows lift crypto markets"
    ]
    assert payload["market_news"] == []
    assert len(selected) == 1


@pytest.mark.asyncio
async def test_report_news_context_requires_title_source_and_link(monkeypatch):
    monkeypatch.setattr(
        news,
        "fetch_news_context",
        AsyncMock(
            return_value=[
                {
                    "title": "Ethereum ETF inflows accelerate",
                    "source": "",
                    "link": "https://example.com/eth",
                },
                {
                    "title": "Solana network upgrade draws support",
                    "source": "CoinDesk",
                    "link": "",
                },
            ]
        ),
    )

    payload, selected = await news.fetch_report_news_context(["eth", "sol"])

    assert payload["market_news"] == []
    assert payload["coin_news"] == {"ETH": [], "SOL": []}
    assert payload["fallback"] == "No clearly relevant fresh news found for tracked coins"
    assert selected == []



@pytest.mark.asyncio
async def test_weekly_news_reads_verified_seven_day_history_not_just_rss_page(monkeypatch):
    from datetime import datetime, timedelta, timezone

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from bot.db.database import Base, NewsItem

    now = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    articles = [
        ("verified", "Bitcoin ETF flows affect BTC", 3, "success", False),
        ("stale", "Bitcoin ETF from old week", 9, "success", False),
        ("noise", "Bitcoin prediction article", 2, "success", True),
        ("pending", "Bitcoin fake claim", 1, "pending", False),
    ]
    try:
        async with sessions() as session:
            session.add_all([
                NewsItem(
                    news_key=key,
                    title=title,
                    source="Verified Publisher",
                    url=f"https://example.org/{key}",
                    published_at=now - timedelta(days=days),
                    fetched_at=now - timedelta(days=days),
                    primary_symbol="btc",
                    related_symbols=["btc"],
                    llm_status=status,
                    is_noise=noise,
                    is_duplicate=False,
                    impact_score=65,
                    relevance_score=75,
                )
                for key, title, days, status, noise in articles
            ])
            await session.commit()
        monkeypatch.setattr(news, "DB_ENABLED", True)
        monkeypatch.setattr(news, "DB_SESSION_LOCAL", sessions)
        fetch = AsyncMock(return_value=[])
        monkeypatch.setattr(news, "fetch_news_context", fetch)

        weekly, selected = await news.fetch_report_news_context(
            ["btc", "eth"], max_age_hours=168, now=now,
        )
        assert [item["title"] for item in weekly["coin_news"]["BTC"]] == [
            "Bitcoin ETF flows affect BTC"
        ]
        assert len(selected) == 1
        daily, _ = await news.fetch_report_news_context(
            ["btc", "eth"], max_age_hours=24, now=now,
        )
        assert daily["coin_news"]["BTC"] == []
        assert fetch.await_count == 2  # existing RSS call, not a new provider
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_weekly_news_filters_expired_rss_and_unknown_dates(monkeypatch):
    from datetime import datetime, timedelta, timezone

    now = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)
    monkeypatch.setattr(news, "DB_ENABLED", False)
    rss = [
        {
            "title": "Ethereum upgrade update",
            "source": "CoinDesk",
            "link": "https://example.org/recent",
            "published": (now - timedelta(days=3)).isoformat(),
        },
        {
            "title": "Ethereum upgrade months ago",
            "source": "CoinDesk",
            "link": "https://example.org/stale",
            "published": (now - timedelta(days=20)).isoformat(),
        },
        {
            "title": "Ethereum headline without publication date",
            "source": "CoinDesk",
            "link": "https://example.org/undated",
        },
    ]
    monkeypatch.setattr(news, "fetch_news_context", AsyncMock(return_value=rss))
    weekly, selected = await news.fetch_report_news_context(
        ["eth"], max_age_hours=168, now=now,
    )
    assert [item["title"] for item in selected] == ["Ethereum upgrade update"]
    assert len(weekly["coin_news"]["ETH"]) == 1
