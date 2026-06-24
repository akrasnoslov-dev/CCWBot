import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import bot.alerts as alerts
from bot.alerting.event_analysis import EventAnalysisDecision
from bot.db.database import (
    Alert,
    Base,
    MarketEvent,
    User,
    ensure_default_coin_subscriptions,
    grant_user_premium,
    save_price_snapshot,
    set_user_coin_subscription,
    upsert_news_item,
)

FORBIDDEN_EVENT_PLACEHOLDERS = ("n/a", "null", "unknown", "unavailable")


def assert_no_event_placeholders(message: str):
    lowered = message.lower()
    assert all(value not in lowered for value in FORBIDDEN_EVENT_PLACEHOLDERS)


async def build_session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_local = async_sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    return engine, session_local


async def create_user(session, telegram_user_id, chat_id):
    user = User(
        telegram_user_id=telegram_user_id,
        telegram_chat_id=chat_id,
        username=f"user{telegram_user_id}",
        first_name="User",
        role="user",
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    await ensure_default_coin_subscriptions(session, user_id=user.id)
    return user


async def store_news(
    session,
    *,
    news_key="link:https://example.test/btc-etf",
    title="Bitcoin ETF approval sends flows higher",
    source="Example News",
    url="https://example.test/btc-etf",
    published_at,
    primary_symbol="btc",
    related_symbols=None,
    category="etf",
    impact_level="high",
    impact_score=0,
    relevance_score=0,
    dedup_group_id="btc-etf-approval",
    is_noise=False,
):
    return await upsert_news_item(
        session,
        news_key=news_key,
        title=title,
        source=source,
        url=url,
        published_at=published_at,
        fetched_at=published_at,
        raw_summary="Possible market context for crypto sentiment.",
        llm_summary="High-impact news to watch for sentiment.",
        related_symbols=related_symbols if related_symbols is not None else [primary_symbol],
        primary_symbol=primary_symbol,
        category=category,
        impact_score=impact_score,
        impact_level=impact_level,
        relevance_score=relevance_score,
        dedup_group_id=dedup_group_id,
        is_duplicate=False,
        is_noise=is_noise,
        is_alert_worthy=False,
        llm_provider="groq",
        llm_model="test-model",
        llm_input_hash=f"hash-{news_key}",
        llm_status="success",
    )


def no_alert_decision(symbol="BTC"):
    return EventAnalysisDecision(
        symbol=symbol,
        should_alert=False,
        event_key=None,
        title=None,
        message_body=None,
        related_news_ids=[],
        possible_action=None,
        urgency=None,
        confidence=None,
        reason_for_no_alert="No meaningful market event detected.",
    )


def fake_app(sent_messages):
    class FakeBot:
        async def send_message(self, chat_id, text, parse_mode=None, entities=None):
            sent_messages.append((chat_id, text, parse_mode, entities))

    return SimpleNamespace(bot=FakeBot())


async def run_news_cycle(monkeypatch, session_local, *, symbols, sent_messages, flag=True):
    monkeypatch.setattr(alerts, "DB_ENABLED", True)
    monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
    monkeypatch.setattr(alerts, "ENABLE_NEWS_DRIVEN_ALERTS", flag)
    monkeypatch.setattr(alerts, "resolve_symbols_to_check", AsyncMock(return_value=symbols))
    monkeypatch.setattr(
        alerts,
        "get_coin_market_data_batch",
        AsyncMock(
            return_value={
                symbol: {"price": 100.0 + index, "change_24h": 0.5, "change_7d": None}
                for index, symbol in enumerate(symbols)
            }
        ),
    )
    monkeypatch.setattr(
        alerts,
        "get_db_alert_settings",
        AsyncMock(return_value={"automatic_check_interval_seconds": 600}),
    )
    monkeypatch.setattr(
        alerts,
        "_select_related_news_context",
        AsyncMock(return_value=([], None, True)),
    )
    monkeypatch.setattr(
        alerts,
        "_create_event_analysis_decision",
        AsyncMock(side_effect=[(no_alert_decision(symbol.upper()), 1) for symbol in symbols]),
    )
    monkeypatch.setattr(alerts, "_deliver_market_heartbeat", AsyncMock(return_value=False))
    monkeypatch.setattr(alerts, "remember_news_context", AsyncMock())

    await alerts.automatic_price_check(SimpleNamespace(application=fake_app(sent_messages)))


@pytest.mark.asyncio
async def test_feature_flag_off_means_no_news_driven_alert(monkeypatch):
    engine, session_local = await build_session_factory()
    sent_messages = []
    now = datetime.now(timezone.utc)
    try:
        async with session_local() as session:
            await create_user(session, 1001, 2001)
            await store_news(session, published_at=now)

        await run_news_cycle(
            monkeypatch,
            session_local,
            symbols=["btc"],
            sent_messages=sent_messages,
            flag=False,
        )

        assert sent_messages == []
        async with session_local() as session:
            assert await session.scalar(select(func.count()).select_from(Alert)) == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_high_impact_btc_news_does_not_produce_standalone_event_alert(monkeypatch):
    engine, session_local = await build_session_factory()
    sent_messages = []
    now = datetime.now(timezone.utc)
    try:
        async with session_local() as session:
            await create_user(session, 1001, 2001)
            await store_news(session, published_at=now, impact_score=0, relevance_score=0)

        await run_news_cycle(
            monkeypatch,
            session_local,
            symbols=["btc"],
            sent_messages=sent_messages,
        )

        assert sent_messages == []
        async with session_local() as session:
            assert await session.scalar(select(func.count()).select_from(MarketEvent)) == 0
            assert await session.scalar(select(func.count()).select_from(Alert)) == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_low_noisy_old_and_undated_news_do_not_alert(monkeypatch):
    engine, session_local = await build_session_factory()
    sent_messages = []
    now = datetime.now(timezone.utc)
    try:
        async with session_local() as session:
            await create_user(session, 1001, 2001)
            await store_news(
                session,
                news_key="low",
                title="Bitcoin analyst commentary may affect sentiment",
                published_at=now,
                impact_level="low",
                category="market",
                dedup_group_id="low",
            )
            await store_news(
                session,
                news_key="noise",
                title="Bitcoin ETF approval update",
                published_at=now,
                is_noise=True,
                dedup_group_id="noise",
            )
            await store_news(
                session,
                news_key="old",
                title="Bitcoin ETF approval update from last week",
                published_at=now - timedelta(days=2),
                dedup_group_id="old",
            )

        await run_news_cycle(
            monkeypatch,
            session_local,
            symbols=["btc"],
            sent_messages=sent_messages,
        )

        assert sent_messages == []
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_news_driven_flag_cannot_bypass_product_policy(monkeypatch):
    monkeypatch.setattr(alerts, "ENABLE_NEWS_DRIVEN_ALERTS", True)
    monkeypatch.setattr(alerts, "DB_ENABLED", True)
    monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", object())

    candidates = await alerts._load_news_driven_alert_candidates(
        ["btc"],
        now=datetime.now(timezone.utc),
    )

    assert candidates == {}


@pytest.mark.asyncio
async def test_free_users_receive_no_news_only_event_alerts(monkeypatch):
    engine, session_local = await build_session_factory()
    sent_messages = []
    now = datetime.now(timezone.utc)
    try:
        async with session_local() as session:
            free_user = await create_user(session, 1001, 2001)
            await set_user_coin_subscription(
                session, user_id=free_user.id, symbol="eth", is_enabled=True
            )
            await store_news(session, published_at=now)
            await store_news(
                session,
                news_key="eth-news",
                title="Ethereum ETF approval draws major exchange flows",
                url="https://example.test/eth",
                published_at=now,
                primary_symbol="eth",
                related_symbols=["eth"],
                dedup_group_id="eth-etf",
            )

        await run_news_cycle(
            monkeypatch,
            session_local,
            symbols=["btc", "eth"],
            sent_messages=sent_messages,
        )

        assert sent_messages == []
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_premium_users_receive_no_news_only_event_alerts(monkeypatch):
    engine, session_local = await build_session_factory()
    sent_messages = []
    now = datetime.now(timezone.utc)
    try:
        async with session_local() as session:
            premium_user = await create_user(session, 1002, 2002)
            await grant_user_premium(session, telegram_user_id=1002, days=30, now=now)
            await set_user_coin_subscription(
                session, user_id=premium_user.id, symbol="eth", is_enabled=True
            )
            await set_user_coin_subscription(
                session, user_id=premium_user.id, symbol="sol", is_enabled=False
            )
            await store_news(
                session,
                news_key="eth-news",
                title="Ethereum ETF approval draws major exchange flows",
                url="https://example.test/eth",
                published_at=now,
                primary_symbol="eth",
                related_symbols=["eth"],
                dedup_group_id="eth-etf",
            )
            await store_news(
                session,
                news_key="sol-news",
                title="Solana outage hits a major exchange",
                url="https://example.test/sol",
                published_at=now,
                primary_symbol="sol",
                related_symbols=["sol"],
                category="exchange",
                dedup_group_id="sol-outage",
            )

        await run_news_cycle(
            monkeypatch,
            session_local,
            symbols=["eth", "sol"],
            sent_messages=sent_messages,
        )

        assert sent_messages == []
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_duplicate_dedup_group_and_repeated_cycles_are_idempotent(monkeypatch):
    engine, session_local = await build_session_factory()
    sent_messages = []
    now = datetime.now(timezone.utc)
    try:
        async with session_local() as session:
            await create_user(session, 1001, 2001)
            await store_news(session, news_key="first", published_at=now)
            await store_news(
                session,
                news_key="second",
                title="Bitcoin ETF approved as major exchange flows rise",
                url="https://example.test/second",
                published_at=now + timedelta(minutes=2),
                dedup_group_id="btc-etf-approval",
            )

        await run_news_cycle(
            monkeypatch,
            session_local,
            symbols=["btc"],
            sent_messages=sent_messages,
        )
        await run_news_cycle(
            monkeypatch,
            session_local,
            symbols=["btc"],
            sent_messages=sent_messages,
        )

        assert sent_messages == []
        async with session_local() as session:
            assert await session.scalar(select(func.count()).select_from(MarketEvent)) == 0
            assert await session.scalar(select(func.count()).select_from(Alert)) == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_news_driven_alert_uses_shared_market_context_when_available(monkeypatch):
    engine, session_local = await build_session_factory()
    now = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)
    news_item = {
        "news_item_id": 1,
        "news_key": "btc",
        "dedup_group_id": "btc-etf",
        "title": "Bitcoin ETF approval draws major exchange flows",
        "source": "Example News",
        "url": "https://example.test/btc",
        "published_at": now,
        "summary": "High-impact news to watch.",
        "primary_symbol": "btc",
        "related_symbols": ["btc"],
        "matched_symbols": ["btc"],
        "category": "etf",
        "impact_level": "high",
    }
    try:
        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        async with session_local() as session:
            user = await create_user(session, 1001, 2001)
            session.add(
                Alert(
                    symbol="BTC",
                    alert_type=alerts.EVENT_ALERT_TYPE,
                    message="previous BTC event alert",
                    sent_to_chat_id=2001,
                    user_id=user.id,
                    status="sent",
                    created_at=now - timedelta(hours=2),
                    numeric_context=alerts._json_dumps({"current_price": 95.0}),
                )
            )
            await save_price_snapshot(
                session,
                symbol="btc",
                price=90.0,
                change_24h=1.0,
                checked_at=now - timedelta(minutes=60),
            )
            await save_price_snapshot(
                session,
                symbol="btc",
                price=98.0,
                change_24h=1.0,
                checked_at=now - timedelta(minutes=20),
            )
            await session.commit()

        event_input = await alerts._build_event_analysis_input(
            analysis_id="event_analysis_btc_shared_context",
            symbol="btc",
            current_price=100.0,
            change_24h=1.0,
            now=now,
            state={},
            candidate_news=[],
            event_analysis_interval_seconds=600,
        )
        news_input = alerts._build_news_driven_event_input(
            analysis_id="news_driven_alert_btc_shared_context",
            symbol="btc",
            news_item=news_item,
            current_price=100.0,
            change_24h=1.0,
            now=now,
            market_context=event_input["market"],
        )
        decision = alerts._build_news_driven_event_decision(
            symbol="btc",
            news_item=news_item,
            event_key=alerts._build_news_driven_event_key(symbol="btc", news_item=news_item),
        )
        payload = alerts._build_event_alert_payload(
            decision=decision,
            input_payload=news_input,
            related_news=news_input["news"],
        )

        assert news_input["market"]["analysed_window_minutes"] == 60
        assert news_input["market"]["chg_window"] == event_input["market"]["chg_window"]
        assert news_input["market"]["chg_since_msg"] == event_input["market"]["chg_since_msg"]
        assert "Price: $100.00" in payload["plain_text"]
        assert "Since last alert/message: +5.26%" in payload["plain_text"]
        assert "Since last BTC alert" not in payload["plain_text"]
        assert "1h market move: +11.11%" in payload["plain_text"]
        assert_no_event_placeholders(payload["plain_text"])
    finally:
        await engine.dispose()


def test_unsupported_runtime_symbols_are_not_selected():
    now = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)
    news_items = [
        {
            "news_item_id": 1,
            "news_key": "xrp",
            "dedup_group_id": "xrp-etf",
            "title": "XRP ETF approval draws major exchange flows",
            "source": "Example News",
            "url": "https://example.test/xrp",
            "published_at": now,
            "summary": "High-impact news to watch.",
            "primary_symbol": "xrp",
            "related_symbols": ["xrp"],
            "matched_symbols": ["xrp"],
            "category": "etf",
            "impact_level": "high",
        }
    ]

    assert alerts._select_news_driven_alert_candidates(news_items, ["xrp"]) == {}


def test_news_driven_wording_avoids_false_causality():
    now = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)
    news_item = {
        "news_item_id": 1,
        "news_key": "btc",
        "dedup_group_id": "btc",
        "title": "Bitcoin ETF approval draws major exchange flows",
        "source": "Example News",
        "url": "https://example.test/btc",
        "published_at": now,
        "summary": "High-impact news to watch.",
        "primary_symbol": "btc",
        "related_symbols": ["btc"],
        "matched_symbols": ["btc"],
        "category": "etf",
        "impact_level": "high",
    }
    event_key = alerts._build_news_driven_event_key(symbol="btc", news_item=news_item)
    input_payload = alerts._build_news_driven_event_input(
        analysis_id="news_driven_alert_btc_test",
        symbol="btc",
        news_item=news_item,
        current_price=100000,
        change_24h=1.0,
        now=now,
    )
    decision = alerts._build_news_driven_event_decision(
        symbol="btc",
        news_item=news_item,
        event_key=event_key,
    )
    payload = alerts._build_event_alert_payload(
        decision=decision,
        input_payload=input_payload,
        related_news=input_payload["news"],
    )

    text = payload["plain_text"].lower()
    forbidden = [
        "because of this",
        "dropped because",
        "caused",
        "guaranteed",
        "buy now",
        "sell now",
    ]
    assert all(term not in text for term in forbidden)
    assert "could be related" in text
    assert "not financial advice." in text


def test_news_driven_numeric_context_persists_stable_news_identity():
    now = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)
    news_item = {
        "news_item_id": 1,
        "news_key": "btc",
        "dedup_group_id": "btc",
        "title": "Bitcoin ETF approval draws major exchange flows",
        "source": "Example News",
        "url": "https://example.test/btc",
        "published_at": now,
        "primary_symbol": "btc",
        "category": "etf",
        "impact_level": "high",
    }
    input_payload = alerts._build_news_driven_event_input(
        analysis_id="news_driven_alert_btc_test",
        symbol="btc",
        news_item=news_item,
        current_price=100000,
        change_24h=1.0,
        now=now,
    )

    context = json.loads(alerts._news_driven_numeric_context(input_payload, news_item))

    assert context["semantic_family"] == "news_catalyst"
    assert context["stable_related_news_ids"] == [alerts._news_driven_identity(news_item)]
