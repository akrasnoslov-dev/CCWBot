from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import bot.alerts as alerts
from bot.db.database import (
    Alert,
    Base,
    User,
    backfill_blocked_users_from_alerts,
    ensure_default_coin_subscriptions,
    get_or_create_market_event,
    save_alert,
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


async def create_user(session, telegram_user_id, chat_id, *, is_active=True, bot_blocked=False):
    user = User(
        telegram_user_id=telegram_user_id,
        telegram_chat_id=chat_id,
        username=f"user{telegram_user_id}",
        first_name="User",
        role="user",
        is_active=is_active,
        bot_blocked=bot_blocked,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    await ensure_default_coin_subscriptions(session, user_id=user.id)
    return user


async def create_market_event(session, event_key):
    return await get_or_create_market_event(
        session,
        symbol="btc",
        event_type="price_movement",
        event_key=event_key,
        price=100000,
        previous_price=99000,
        price_change_percent=1.01,
    )


@pytest.mark.asyncio
async def test_blocked_telegram_error_disables_user_and_keeps_failed_alert(monkeypatch):
    class FakeBot:
        async def send_message(self, chat_id, text, parse_mode=None):
            raise RuntimeError("Telegram API failed: Forbidden: bot was blocked by the user")

    engine, SessionLocal = await build_session_factory()
    try:
        async with SessionLocal() as session:
            user = await create_user(session, 1001, 2001)
            market_event = await create_market_event(session, "btc:blocked-live")

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", SessionLocal)

        delivered = await alerts._deliver_market_event_alert(
            SimpleNamespace(bot=FakeBot()),
            symbol="btc",
            alert_payload={"plain_text": "BTC alert\n\nNot financial advice."},
            market_event_id=market_event.id,
            event_ai_analysis_id=123,
            recipients=[alerts.AlertRecipient(chat_id=2001, user_id=user.id)],
        )

        assert delivered is False
        async with SessionLocal() as session:
            reloaded = await session.get(User, user.id)
            alert = await session.scalar(select(Alert).where(Alert.user_id == user.id))
            assert reloaded.is_active is False
            assert reloaded.bot_blocked is True
            assert reloaded.blocked_at is not None
            assert alert.status == "failed"
            assert "Forbidden: bot was blocked by the user" in alert.error_message
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_blocked_user_is_skipped_in_future_alert_delivery(monkeypatch):
    sent_messages = []

    class FakeBot:
        async def send_message(self, chat_id, text, parse_mode=None):
            sent_messages.append((chat_id, text))

    engine, SessionLocal = await build_session_factory()
    try:
        async with SessionLocal() as session:
            await create_user(session, 1001, 2001, is_active=False, bot_blocked=True)
            market_event = await create_market_event(session, "btc:blocked-skip")

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", SessionLocal)

        delivered = await alerts._deliver_market_event_alert(
            SimpleNamespace(bot=FakeBot()),
            symbol="btc",
            alert_payload={"plain_text": "BTC alert\n\nNot financial advice."},
            market_event_id=market_event.id,
            event_ai_analysis_id=123,
        )

        assert delivered is False
        assert sent_messages == []
        async with SessionLocal() as session:
            assert await session.scalar(select(func.count()).select_from(Alert)) == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_transient_delivery_error_does_not_disable_user(monkeypatch):
    class FakeBot:
        async def send_message(self, chat_id, text, parse_mode=None):
            raise RuntimeError("Timed out while sending Telegram message")

    engine, SessionLocal = await build_session_factory()
    try:
        async with SessionLocal() as session:
            user = await create_user(session, 1001, 2001)
            market_event = await create_market_event(session, "btc:transient-failure")

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", SessionLocal)

        delivered = await alerts._deliver_market_event_alert(
            SimpleNamespace(bot=FakeBot()),
            symbol="btc",
            alert_payload={"plain_text": "BTC alert\n\nNot financial advice."},
            market_event_id=market_event.id,
            event_ai_analysis_id=123,
            recipients=[alerts.AlertRecipient(chat_id=2001, user_id=user.id)],
        )

        assert delivered is False
        async with SessionLocal() as session:
            reloaded = await session.get(User, user.id)
            alert = await session.scalar(select(Alert).where(Alert.user_id == user.id))
            assert reloaded.is_active is True
            assert reloaded.bot_blocked is False
            assert reloaded.blocked_at is None
            assert alert.status == "failed"
            assert alert.error_message == "Timed out while sending Telegram message"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_backfill_marks_historical_blocked_users_and_is_idempotent():
    blocked_at = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)
    engine, SessionLocal = await build_session_factory()
    try:
        async with SessionLocal() as session:
            blocked_user = await create_user(session, 1001, 2001)
            chat_only_user = await create_user(session, 1002, 2002)
            active_user = await create_user(session, 1003, 2003)
            await save_alert(
                session,
                symbol="BTC",
                alert_type="price_movement",
                message="failed",
                sent_to_chat_id=2001,
                user_id=blocked_user.id,
                status="failed",
                error_message="Forbidden: bot was blocked by the user",
            )
            alert = await session.scalar(select(Alert).where(Alert.user_id == blocked_user.id))
            alert.created_at = blocked_at
            await save_alert(
                session,
                symbol="BTC",
                alert_type="price_movement",
                message="failed",
                sent_to_chat_id=2002,
                status="failed",
                error_message="Wrapped error: Forbidden: bot was blocked by the user",
            )
            await save_alert(
                session,
                symbol="BTC",
                alert_type="price_movement",
                message="failed",
                sent_to_chat_id=2003,
                user_id=active_user.id,
                status="failed",
                error_message="Timed out while sending Telegram message",
            )
            await session.commit()

            matched_alerts, updated_users = await backfill_blocked_users_from_alerts(session)
            second_matched_alerts, second_updated_users = await backfill_blocked_users_from_alerts(
                session
            )

            assert matched_alerts == 2
            assert updated_users == 2
            assert second_matched_alerts == 2
            assert second_updated_users == 0

            blocked_reloaded = await session.get(User, blocked_user.id)
            chat_only_reloaded = await session.get(User, chat_only_user.id)
            active_reloaded = await session.get(User, active_user.id)
            assert blocked_reloaded.is_active is False
            assert blocked_reloaded.bot_blocked is True
            assert blocked_reloaded.blocked_at.replace(tzinfo=timezone.utc) == blocked_at
            assert chat_only_reloaded.is_active is False
            assert chat_only_reloaded.bot_blocked is True
            assert chat_only_reloaded.blocked_at is not None
            assert active_reloaded.is_active is True
            assert active_reloaded.bot_blocked is False
            assert active_reloaded.blocked_at is None
            assert await session.scalar(select(func.count()).select_from(Alert)) == 3
    finally:
        await engine.dispose()
