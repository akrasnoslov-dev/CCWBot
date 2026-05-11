from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from database import (
    Base,
    User,
    UserCoinSubscription,
    ensure_default_coin_subscriptions,
    grant_user_premium,
    revoke_user_premium,
    set_user_alert_frequency,
    set_user_coin_subscription,
)


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
