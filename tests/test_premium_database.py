from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.db.database import (
    Base,
    User,
    UserCoinSubscription,
    ensure_default_coin_subscriptions,
    get_user_by_telegram_user_id,
    grant_user_premium,
    revoke_user_premium,
    set_user_alert_frequency,
    set_user_coin_subscription,
)
from bot.domain.premium import is_user_premium_active
from bot.watchlist import build_plan_message, build_watchlist_message


async def build_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    return engine, SessionLocal()


async def create_user(session, telegram_user_id=1001):
    user = User(
        telegram_user_id=telegram_user_id,
        telegram_chat_id=2001,
        username="user",
        first_name="User",
        role="user",
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


def as_naive_utc(value):
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_default_coin_subscriptions_enable_only_btc():
    engine, session = await build_session()
    try:
        user = await create_user(session)

        subscriptions = await ensure_default_coin_subscriptions(session, user_id=user.id)

        enabled = {row.symbol: row.is_enabled for row in subscriptions}
        assert enabled["btc"] is True
        assert all(not enabled[symbol] for symbol in enabled if symbol != "btc")
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_coin_subscription_write_is_idempotent_and_preserves_choices():
    engine, session = await build_session()
    try:
        user = await create_user(session)

        await set_user_coin_subscription(session, user_id=user.id, symbol="ETH", is_enabled=True)
        await set_user_coin_subscription(session, user_id=user.id, symbol="eth", is_enabled=True)

        rows = list(
            (
                await session.scalars(
                    select(UserCoinSubscription).where(
                        UserCoinSubscription.user_id == user.id,
                        UserCoinSubscription.symbol == "eth",
                    )
                )
            ).all()
        )
        assert len(rows) == 1
        assert rows[0].is_enabled is True

        await revoke_user_premium(session, telegram_user_id=user.telegram_user_id)
        rows = list(
            (
                await session.scalars(
                    select(UserCoinSubscription).where(
                        UserCoinSubscription.user_id == user.id,
                        UserCoinSubscription.symbol == "eth",
                    )
                )
            ).all()
        )
        assert rows[0].is_enabled is True
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_grant_extends_from_max_now_or_existing_active_until():
    engine, session = await build_session()
    try:
        user = await create_user(session)
        now = datetime(2026, 5, 11, tzinfo=timezone.utc)

        first = await grant_user_premium(
            session,
            telegram_user_id=user.telegram_user_id,
            days=10,
            now=now,
        )
        assert first.active_until == as_naive_utc(now + timedelta(days=10))

        second = await grant_user_premium(
            session,
            telegram_user_id=user.telegram_user_id,
            days=5,
            now=now + timedelta(days=1),
        )
        assert second.id == first.id
        assert second.active_until == as_naive_utc(now + timedelta(days=15))
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_grant_uses_telegram_user_id_not_internal_user_id():
    engine, session = await build_session()
    try:
        first_user = await create_user(session, telegram_user_id=1)
        target_user = await create_user(session, telegram_user_id=7287293904)
        now = datetime(2026, 5, 11, tzinfo=timezone.utc)

        subscription = await grant_user_premium(
            session,
            telegram_user_id=7287293904,
            days=30,
            now=now,
        )

        assert subscription.user_id == target_user.id
        assert subscription.user_id != first_user.id
        reloaded = await get_user_by_telegram_user_id(
            session,
            7287293904,
            include_plan=True,
        )
        assert is_user_premium_active(reloaded.premium_subscription, now)
        plan_message = build_plan_message(reloaded, now)
        assert "Plan: Premium" in plan_message
        assert "Paid access until:" in plan_message
        assert "Recurring subscription: not tracked by CCWBot" in plan_message
        subscriptions = await ensure_default_coin_subscriptions(session, user_id=target_user.id)
        _, rows = build_watchlist_message(reloaded, subscriptions, now)
        assert ("eth", False, True) in rows
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_grant_unknown_telegram_user_id_does_not_create_user():
    engine, session = await build_session()
    try:
        with pytest.raises(ValueError, match="User not found"):
            await grant_user_premium(
                session,
                telegram_user_id=7287293904,
                days=30,
                now=datetime(2026, 5, 11, tzinfo=timezone.utc),
            )

        assert await session.scalar(select(User).where(User.telegram_user_id == 7287293904)) is None
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_revoke_unknown_telegram_user_id_does_not_create_user():
    engine, session = await build_session()
    try:
        with pytest.raises(ValueError, match="User not found"):
            await revoke_user_premium(
                session,
                telegram_user_id=7287293904,
                now=datetime(2026, 5, 11, tzinfo=timezone.utc),
            )

        assert await session.scalar(select(User).where(User.telegram_user_id == 7287293904)) is None
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_revoke_makes_premium_inactive_without_disabling_btc():
    engine, session = await build_session()
    try:
        user = await create_user(session)
        now = datetime(2026, 5, 11, tzinfo=timezone.utc)
        await ensure_default_coin_subscriptions(session, user_id=user.id)
        await set_user_coin_subscription(session, user_id=user.id, symbol="btc", is_enabled=True)
        await grant_user_premium(
            session,
            telegram_user_id=user.telegram_user_id,
            days=10,
            now=now,
        )

        revoked = await revoke_user_premium(
            session,
            telegram_user_id=user.telegram_user_id,
            now=now + timedelta(days=1),
        )

        assert revoked.status == "revoked"
        assert revoked.active_until == as_naive_utc(now + timedelta(days=1))
        btc_row = await session.scalar(
            select(UserCoinSubscription).where(
                UserCoinSubscription.user_id == user.id,
                UserCoinSubscription.symbol == "btc",
            )
        )
        assert btc_row.is_enabled is True
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_frequency_preference_accepts_only_premium_presets():
    engine, session = await build_session()
    try:
        user = await create_user(session)

        updated = await set_user_alert_frequency(session, user_id=user.id, frequency_seconds=3600)
        assert updated.alert_frequency_seconds == 3600
        with pytest.raises(ValueError, match="Unsupported alert frequency"):
            await set_user_alert_frequency(session, user_id=user.id, frequency_seconds=123)
    finally:
        await session.close()
        await engine.dispose()
