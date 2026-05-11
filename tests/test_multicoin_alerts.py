from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import bot.alerts as alerts
from database import (
    Alert,
    Base,
    User,
    ensure_default_coin_subscriptions,
    get_or_create_market_event,
    grant_user_premium,
    reserve_alert_delivery,
    save_alert,
    set_user_coin_subscription,
    update_alert_delivery_status,
)


async def build_session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    return engine, SessionLocal


async def create_user(session, telegram_user_id, chat_id, *, is_active=True):
    user = User(
        telegram_user_id=telegram_user_id,
        telegram_chat_id=chat_id,
        username=f"user{telegram_user_id}",
        first_name="User",
        role="user",
        is_active=is_active,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    await ensure_default_coin_subscriptions(session, user_id=user.id)
    return user


@pytest.mark.asyncio
async def test_resolve_symbols_to_check_uses_enabled_active_eligible_users(monkeypatch):
    engine, SessionLocal = await build_session_factory()
    now = datetime(2026, 5, 11, tzinfo=timezone.utc)
    try:
        async with SessionLocal() as session:
            free_user = await create_user(session, 1001, 2001)
            premium_user = await create_user(session, 1002, 2002)
            expired_user = await create_user(session, 1003, 2003)
            inactive_user = await create_user(session, 1004, 2004, is_active=False)

            await set_user_coin_subscription(
                session, user_id=free_user.id, symbol="btc", is_enabled=False
            )
            await set_user_coin_subscription(
                session, user_id=free_user.id, symbol="eth", is_enabled=True
            )
            await grant_user_premium(
                session,
                telegram_user_id=premium_user.telegram_user_id,
                days=10,
                now=now,
            )
            await set_user_coin_subscription(
                session, user_id=premium_user.id, symbol="btc", is_enabled=False
            )
            await set_user_coin_subscription(
                session, user_id=premium_user.id, symbol="sol", is_enabled=True
            )
            await grant_user_premium(
                session,
                telegram_user_id=expired_user.telegram_user_id,
                days=1,
                now=now - timedelta(days=2),
            )
            await set_user_coin_subscription(
                session, user_id=expired_user.id, symbol="btc", is_enabled=False
            )
            await set_user_coin_subscription(
                session, user_id=expired_user.id, symbol="xrp", is_enabled=True
            )
            await set_user_coin_subscription(
                session, user_id=inactive_user.id, symbol="btc", is_enabled=True
            )

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", SessionLocal)

        assert await alerts.resolve_symbols_to_check(now) == ["sol"]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_resolve_symbols_includes_btc_when_active_user_enabled(monkeypatch):
    engine, SessionLocal = await build_session_factory()
    now = datetime(2026, 5, 11, tzinfo=timezone.utc)
    try:
        async with SessionLocal() as session:
            await create_user(session, 1001, 2001)

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", SessionLocal)

        assert await alerts.resolve_symbols_to_check(now) == ["btc"]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_get_alert_recipients_applies_premium_and_frequency(monkeypatch):
    engine, SessionLocal = await build_session_factory()
    now = datetime(2026, 5, 11, tzinfo=timezone.utc)
    try:
        async with SessionLocal() as session:
            free_user = await create_user(session, 1001, 2001)
            premium_user = await create_user(session, 1002, 2002)
            expired_user = await create_user(session, 1003, 2003)

            await set_user_coin_subscription(
                session, user_id=free_user.id, symbol="eth", is_enabled=True
            )
            await grant_user_premium(
                session,
                telegram_user_id=premium_user.telegram_user_id,
                days=10,
                now=now,
            )
            await set_user_coin_subscription(
                session, user_id=premium_user.id, symbol="eth", is_enabled=True
            )
            await grant_user_premium(
                session,
                telegram_user_id=expired_user.telegram_user_id,
                days=1,
                now=now - timedelta(days=2),
            )
            await set_user_coin_subscription(
                session, user_id=expired_user.id, symbol="eth", is_enabled=True
            )
            await save_alert(
                session,
                symbol="ETH",
                alert_type="price_movement",
                message="previous sent",
                sent_to_chat_id=2002,
                user_id=premium_user.id,
                status="failed",
            )

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", SessionLocal)

        recipients = await alerts.get_alert_recipients("eth", "price_movement", now=now)

        assert recipients == [alerts.AlertRecipient(chat_id=2002, user_id=premium_user.id)]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_get_alert_recipients_sent_status_blocks_frequency(monkeypatch):
    engine, SessionLocal = await build_session_factory()
    now = datetime(2026, 5, 11, tzinfo=timezone.utc)
    try:
        async with SessionLocal() as session:
            premium_user = await create_user(session, 1002, 2002)
            await grant_user_premium(
                session,
                telegram_user_id=premium_user.telegram_user_id,
                days=10,
                now=now,
            )
            await set_user_coin_subscription(
                session, user_id=premium_user.id, symbol="eth", is_enabled=True
            )
            await save_alert(
                session,
                symbol="ETH",
                alert_type="price_movement",
                message="previous sent",
                sent_to_chat_id=2002,
                user_id=premium_user.id,
                status="sent",
            )

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", SessionLocal)

        assert await alerts.get_alert_recipients("eth", "price_movement", now=now) == []
    finally:
        await engine.dispose()


def test_filter_news_for_symbol_excludes_btc_only_news_for_eth():
    news = [
        {"title": "Bitcoin miners see BTC fees rise", "source": "A", "link": "https://a.test"},
        {"title": "Ethereum staking demand rises", "source": "B", "link": "https://b.test"},
        {"title": "Fed rate decision moves crypto market", "source": "C", "link": "https://c.test"},
        {"title": "Unrelated equity earnings", "source": "D", "link": "https://d.test"},
    ]

    filtered = alerts.filter_news_for_symbol("eth", news)

    assert [item["title"] for item in filtered] == [
        "Ethereum staking demand rises",
        "Fed rate decision moves crypto market",
    ]
    assert all(item["link"].startswith("https://") for item in filtered)


@pytest.mark.asyncio
async def test_delivery_reservation_is_idempotent_and_retryable():
    engine, SessionLocal = await build_session_factory()
    try:
        async with SessionLocal() as session:
            user = await create_user(session, 1001, 2001)
            market_event = await get_or_create_market_event(
                session,
                symbol="eth",
                event_type="price_movement",
                event_key="eth:price_movement:test",
                price=3000,
                previous_price=2900,
                price_change_percent=3.4,
            )
            first, should_send_first = await reserve_alert_delivery(
                session,
                user_id=user.id,
                symbol="eth",
                alert_type="price_movement",
                sent_to_chat_id=2001,
                market_event_id=market_event.id,
                event_ai_analysis_id=None,
                message="ETH alert",
            )
            second, should_send_second = await reserve_alert_delivery(
                session,
                user_id=user.id,
                symbol="ETH",
                alert_type="price_movement",
                sent_to_chat_id=2001,
                market_event_id=market_event.id,
                event_ai_analysis_id=None,
                message="ETH alert",
            )
            await update_alert_delivery_status(session, alert_id=first.id, status="failed")
            third, should_send_third = await reserve_alert_delivery(
                session,
                user_id=user.id,
                symbol="eth",
                alert_type="price_movement",
                sent_to_chat_id=2001,
                market_event_id=market_event.id,
                event_ai_analysis_id=None,
                message="ETH alert retry",
            )

            assert first.id == second.id == third.id
            assert should_send_first is True
            assert should_send_second is False
            assert should_send_third is True
            assert await session.scalar(select(func.count()).select_from(Alert)) == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_one_analysis_payload_is_delivered_to_multiple_recipients(monkeypatch):
    sent_messages = []

    class FakeBot:
        async def send_message(self, chat_id, text, parse_mode=None):
            sent_messages.append((chat_id, text, parse_mode))

    engine, SessionLocal = await build_session_factory()
    now = datetime(2026, 5, 11, tzinfo=timezone.utc)
    try:
        async with SessionLocal() as session:
            first = await create_user(session, 1001, 2001)
            second = await create_user(session, 1002, 2002)
            await grant_user_premium(session, telegram_user_id=1001, days=10, now=now)
            await grant_user_premium(session, telegram_user_id=1002, days=10, now=now)
            await set_user_coin_subscription(
                session, user_id=first.id, symbol="eth", is_enabled=True
            )
            await set_user_coin_subscription(
                session, user_id=second.id, symbol="eth", is_enabled=True
            )
            market_event = await get_or_create_market_event(
                session,
                symbol="eth",
                event_type="price_movement",
                event_key="eth:price_movement:delivery",
                price=3000,
                previous_price=2900,
                price_change_percent=3.4,
            )

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", SessionLocal)

        delivered = await alerts._deliver_market_event_alert(
            SimpleNamespace(bot=FakeBot()),
            symbol="eth",
            alert_payload={"plain_text": "ETH movement alert\n\nNot financial advice."},
            market_event_id=market_event.id,
            event_ai_analysis_id=123,
        )

        assert delivered is True
        assert sent_messages == [
            (2001, "ETH movement alert\n\nNot financial advice.", None),
            (2002, "ETH movement alert\n\nNot financial advice.", None),
        ]
        async with SessionLocal() as session:
            assert await session.scalar(select(func.count()).select_from(Alert)) == 2
    finally:
        await engine.dispose()
