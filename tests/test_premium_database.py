from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.db.database import (
    Base,
    ProductEvent,
    User,
    UserCoinSubscription,
    UserPremiumTrial,
    ensure_default_coin_subscriptions,
    get_user_by_telegram_user_id,
    grant_user_premium,
    revoke_user_premium,
    set_user_alert_frequency,
    set_user_coin_subscription,
)
from bot.db.premium import expire_due_premium_trials, start_user_premium_trial
from bot.domain.premium import (
    get_effective_market_heartbeat_frequency_seconds,
    has_premium_entitlement,
    is_coin_unlocked_for_user,
    is_user_premium_active,
)
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


@pytest.mark.asyncio
async def test_trial_is_one_time_unlocks_premium_and_expires_once():
    engine, session = await build_session()
    try:
        user = await create_user(session)
        now = datetime(2026, 5, 11, tzinfo=timezone.utc)

        trial, created = await start_user_premium_trial(
            session,
            telegram_user_id=user.telegram_user_id,
            now=now,
        )
        duplicate, duplicate_created = await start_user_premium_trial(
            session,
            telegram_user_id=user.telegram_user_id,
            now=now + timedelta(days=1),
        )

        assert created is True
        assert duplicate_created is False
        assert duplicate.id == trial.id
        assert trial.active_until == as_naive_utc(now + timedelta(days=7))
        reloaded = await get_user_by_telegram_user_id(
            session, user.telegram_user_id, include_plan=True
        )
        assert has_premium_entitlement(reloaded, now + timedelta(days=6, hours=23))
        assert is_coin_unlocked_for_user(reloaded, "eth", now + timedelta(days=6, hours=23))
        assert not has_premium_entitlement(reloaded, now + timedelta(days=7))

        expired = await expire_due_premium_trials(session, now=now + timedelta(days=7))
        repeated = await expire_due_premium_trials(session, now=now + timedelta(days=8))

        assert [row.id for row in expired] == [trial.id]
        assert repeated == []
        stored = await session.scalar(
            select(UserPremiumTrial).where(UserPremiumTrial.id == trial.id)
        )
        assert stored.expired_at.replace(tzinfo=timezone.utc) == now + timedelta(days=7)
        assert await session.scalar(
            select(func.count()).select_from(ProductEvent).where(
                ProductEvent.event_name == "trial_started"
            )
        ) == 1
        assert await session.scalar(
            select(func.count()).select_from(ProductEvent).where(
                ProductEvent.event_name == "trial_expired"
            )
        ) == 1
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_trial_rejects_any_historical_or_current_paid_premium():
    engine, session = await build_session()
    now = datetime(2026, 5, 11, tzinfo=timezone.utc)
    try:
        expired_user = await create_user(session, telegram_user_id=1002)
        await grant_user_premium(
            session, telegram_user_id=expired_user.telegram_user_id, days=1, now=now
        )
        expired_trial, expired_created = await start_user_premium_trial(
            session,
            telegram_user_id=expired_user.telegram_user_id,
            now=now + timedelta(days=2),
        )

        revoked_user = await create_user(session, telegram_user_id=1003)
        await grant_user_premium(
            session, telegram_user_id=revoked_user.telegram_user_id, days=10, now=now
        )
        await revoke_user_premium(
            session, telegram_user_id=revoked_user.telegram_user_id, now=now + timedelta(days=1)
        )
        revoked_trial, revoked_created = await start_user_premium_trial(
            session,
            telegram_user_id=revoked_user.telegram_user_id,
            now=now + timedelta(days=2),
        )

        current_user = await create_user(session, telegram_user_id=1004)
        await grant_user_premium(
            session, telegram_user_id=current_user.telegram_user_id, days=10, now=now
        )
        current_trial, current_created = await start_user_premium_trial(
            session, telegram_user_id=current_user.telegram_user_id, now=now + timedelta(days=1)
        )

        never_user = await create_user(session, telegram_user_id=1005)
        never_trial, never_created = await start_user_premium_trial(
            session, telegram_user_id=never_user.telegram_user_id, now=now
        )
        repeated_trial, repeated_created = await start_user_premium_trial(
            session, telegram_user_id=never_user.telegram_user_id, now=now + timedelta(days=1)
        )

        assert (expired_trial, expired_created) == (None, False)
        assert (revoked_trial, revoked_created) == (None, False)
        assert (current_trial, current_created) == (None, False)
        assert never_created is True
        assert repeated_created is False
        assert repeated_trial.id == never_trial.id
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_revoke_terminates_active_trial_and_preserves_consumed_history():
    engine, session = await build_session()
    now = datetime(2026, 5, 11, tzinfo=timezone.utc)
    try:
        user = await create_user(session)
        trial, created = await start_user_premium_trial(
            session, telegram_user_id=user.telegram_user_id, now=now
        )
        assert created is True
        await grant_user_premium(
            session,
            telegram_user_id=user.telegram_user_id,
            days=10,
            now=now + timedelta(days=1),
        )

        await revoke_user_premium(
            session, telegram_user_id=user.telegram_user_id, now=now + timedelta(days=2)
        )

        reloaded = await get_user_by_telegram_user_id(
            session, user.telegram_user_id, include_plan=True
        )
        assert not has_premium_entitlement(reloaded, now + timedelta(days=2, seconds=1))
        assert not is_coin_unlocked_for_user(reloaded, "eth", now + timedelta(days=2, seconds=1))
        assert get_effective_market_heartbeat_frequency_seconds(
            reloaded, now + timedelta(days=2, seconds=1)
        ) == 21600
        assert reloaded.premium_trial.id == trial.id
        assert reloaded.premium_trial.expired_at.replace(tzinfo=timezone.utc) == now + timedelta(
            days=2
        )
        retried_trial, retried_created = await start_user_premium_trial(
            session, telegram_user_id=user.telegram_user_id, now=now + timedelta(days=3)
        )
        assert (retried_trial, retried_created) == (None, False)
        assert await session.scalar(
            select(func.count()).select_from(ProductEvent).where(
                ProductEvent.event_name == "trial_expired"
            )
        ) == 1
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_trial_survives_database_restart_and_cannot_restart(tmp_path):
    database_path = tmp_path / "premium_trial_restart.sqlite"
    database_url = f"sqlite+aiosqlite:///{database_path.as_posix()}"
    now = datetime(2026, 5, 11, tzinfo=timezone.utc)
    first_engine = create_async_engine(database_url, future=True)
    try:
        async with first_engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        first_session_factory = async_sessionmaker(bind=first_engine, expire_on_commit=False)
        async with first_session_factory() as session:
            user = await create_user(session)
            trial, created = await start_user_premium_trial(
                session,
                telegram_user_id=user.telegram_user_id,
                now=now,
            )
            trial_id = trial.id
            assert created is True
    finally:
        await first_engine.dispose()

    second_engine = create_async_engine(database_url, future=True)
    try:
        second_session_factory = async_sessionmaker(bind=second_engine, expire_on_commit=False)
        async with second_session_factory() as session:
            reloaded = await get_user_by_telegram_user_id(session, 1001, include_plan=True)
            duplicate, created = await start_user_premium_trial(
                session,
                telegram_user_id=reloaded.telegram_user_id,
                now=now + timedelta(days=1),
            )

            assert created is False
            assert duplicate.id == trial_id
            assert has_premium_entitlement(reloaded, now + timedelta(days=1))
    finally:
        await second_engine.dispose()
