# The DB-backed tests exercise reservation time separately from successful send time.
import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import bot.alerts as alerts
from bot.db.alerts import get_last_sent_alert_at, save_alert, update_alert_delivery_status
from bot.db.database import Base, MarketEvent, User, UserCoinSubscription, UserPremiumSubscription
from bot.domain.premium import can_deliver_market_heartbeat_now

NOW = datetime(2026, 10, 13, 12, tzinfo=timezone.utc)


def user(*, activated=NOW, frequency=3600, premium=True):
    return SimpleNamespace(
        created_at=activated,
        alert_frequency_seconds=frequency,
        coin_subscriptions=[
            SimpleNamespace(symbol=s, is_enabled=True, updated_at=activated)
            for s in ("btc", "eth", "gram", "sol")
        ],
        premium_subscription=SimpleNamespace(
            active_until=NOW + timedelta(days=7), updated_at=activated
        )
        if premium
        else None,
        premium_trial=None,
    )


@pytest.mark.parametrize("symbol", ["btc", "eth", "gram", "sol"])
@pytest.mark.parametrize("frequency", [3600, 21600, 86400, 123])
def test_full_24_hours_required_regardless_of_stored_frequency(symbol, frequency):
    recipient = user(activated=NOW - timedelta(days=3), frequency=frequency)
    assert not can_deliver_market_heartbeat_now(
        recipient, symbol, NOW, NOW - timedelta(hours=23, minutes=59)
    )
    assert can_deliver_market_heartbeat_now(recipient, symbol, NOW, NOW - timedelta(hours=24))


def test_first_delivery_waits_from_activation():
    recipient = user()
    assert not can_deliver_market_heartbeat_now(recipient, "btc", NOW, None)
    assert not can_deliver_market_heartbeat_now(
        recipient, "eth", NOW + timedelta(hours=23, minutes=59), None
    )
    assert can_deliver_market_heartbeat_now(recipient, "eth", NOW + timedelta(hours=24), None)


def test_newly_enabled_and_newly_unlocked_coins_wait_independently():
    recipient = user(activated=NOW - timedelta(days=3))
    recipient.coin_subscriptions[1].updated_at = NOW
    assert can_deliver_market_heartbeat_now(recipient, "btc", NOW, None)
    assert not can_deliver_market_heartbeat_now(recipient, "eth", NOW, None)
    recipient.premium_subscription.updated_at = NOW
    assert not can_deliver_market_heartbeat_now(recipient, "sol", NOW, None)
    assert can_deliver_market_heartbeat_now(recipient, "btc", NOW, None)


def test_missing_activation_evidence_fails_closed():
    assert not can_deliver_market_heartbeat_now(SimpleNamespace(), "btc", NOW, None)


@pytest_asyncio.fixture
async def delivery_db(monkeypatch, tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'delivery.sqlite'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(timezone.utc)
    async with factory() as session:
        for identifier in (1, 2):
            recipient = User(
                id=identifier,
                telegram_user_id=identifier,
                telegram_chat_id=identifier,
                is_active=True,
                created_at=now - timedelta(days=3),
            )
            session.add(recipient)
            session.add(
                UserPremiumSubscription(
                    user_id=identifier,
                    active_until=now + timedelta(days=7),
                    updated_at=now - timedelta(days=3),
                )
            )
            for symbol in ("btc", "eth", "gram", "sol"):
                session.add(
                    UserCoinSubscription(
                        user_id=identifier,
                        symbol=symbol,
                        is_enabled=True,
                        updated_at=now - timedelta(days=3),
                    )
                )
        session.add(
            MarketEvent(
                id=1,
                symbol="BTC",
                event_type="event_alert",
                event_key="btc_test",
                event_instance_key="btc_test_1",
                price=Decimal("100"),
                price_change_percent=1,
                detected_at=now,
            )
        )
        await session.commit()
    monkeypatch.setattr(alerts, "DB_ENABLED", True)
    monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", factory)
    yield factory, now
    await engine.dispose()


async def add_delivery(
    factory,
    *,
    user_id=1,
    symbol="BTC",
    status="sent",
    sent_at=None,
    created_at=None,
    alert_type="event_alert",
):
    async with factory() as session:
        row = await save_alert(
            session,
            user_id=user_id,
            symbol=symbol,
            alert_type=alert_type,
            message="prior",
            sent_to_chat_id=user_id,
            status=status,
        )
        if sent_at is not None:
            row.sent_at = sent_at
        if created_at is not None:
            row.created_at = created_at
        await session.commit()
        return row.id


@pytest.mark.asyncio
async def test_success_clock_ignores_failed_pending_and_suppressed(delivery_db):
    factory, now = delivery_db
    await add_delivery(factory, sent_at=now - timedelta(hours=24))
    for status in ("failed", "pending", "retry_pending", "suppressed"):
        await add_delivery(factory, status=status)
    due = await alerts._get_due_market_heartbeat_recipients(symbol="btc", now=now)
    assert {r.user_id for r, _ in due} == {1, 2}
    await add_delivery(factory, sent_at=now)
    due = await alerts._get_due_market_heartbeat_recipients(symbol="btc", now=now)
    assert {r.user_id for r, _ in due} == {2}
    due = await alerts._get_due_market_heartbeat_recipients(symbol="eth", now=now)
    assert {r.user_id for r, _ in due} == {1, 2}


@pytest.mark.asyncio
async def test_delayed_success_uses_completion_not_reservation(delivery_db):
    factory, now = delivery_db
    identifier = await add_delivery(factory, status="pending", created_at=now - timedelta(days=2))
    async with factory() as session:
        assert await get_last_sent_alert_at(session, user_id=1, symbol="btc") is None
        await update_alert_delivery_status(session, alert_id=identifier, status="sent")
        completed = await get_last_sent_alert_at(session, user_id=1, symbol="btc")
        assert completed.replace(tzinfo=timezone.utc) >= now
    assert not await alerts._get_due_market_heartbeat_recipients(symbol="btc", now=now, user_id=1)


@pytest.mark.asyncio
async def test_latest_success_is_ordered_by_delivery_not_reservation(delivery_db):
    factory, now = delivery_db
    await add_delivery(
        factory, created_at=now - timedelta(hours=25), sent_at=now - timedelta(hours=25)
    )
    await add_delivery(factory, created_at=now - timedelta(days=3), sent_at=now)
    assert not await alerts._get_due_market_heartbeat_recipients(symbol="btc", now=now, user_id=1)


@pytest.mark.asyncio
async def test_concurrent_checks_send_one_heartbeat_and_reset_timer(delivery_db, monkeypatch):
    from test_market_heartbeat import create_heartbeat, fake_app

    factory, now = delivery_db
    async with factory() as session:
        await create_heartbeat(session, generated_at=now)
    app = fake_app()
    kwargs = dict(symbol="btc", current_price=Decimal("100"), change_24h=0, now=now)
    results = await asyncio.gather(
        *(alerts._deliver_market_heartbeat(app, **kwargs) for _ in range(3))
    )
    assert any(results)
    assert app.bot.send_message.await_count == 2  # Exactly once for each independent user.
    assert not await alerts._get_due_market_heartbeat_recipients(symbol="btc", now=now)


@pytest.mark.asyncio
async def test_event_success_while_heartbeat_waits_cancels_stale_preflight(
    delivery_db, monkeypatch
):
    from test_market_heartbeat import create_heartbeat, fake_app

    factory, now = delivery_db
    async with factory() as session:
        await create_heartbeat(session, generated_at=now)
    app = fake_app()
    started, release = asyncio.Event(), asyncio.Event()

    real_send = alerts._send_alert_to_recipient_with_retry

    async def send_event(app, recipient, payload, **kwargs):
        if payload.get("plain_text") != "Event alert":
            return await real_send(app, recipient, payload, **kwargs)
        started.set()
        await release.wait()
        return True, None, None

    monkeypatch.setattr(alerts, "_send_alert_to_recipient_with_retry", send_event)
    event_task = asyncio.create_task(
        alerts._deliver_market_event_alert(
            app,
            symbol="btc",
            alert_payload={"plain_text": "Event alert"},
            market_event_id=1,
            event_ai_analysis_id=None,
            event_type="event_alert",
            recipients=[alerts.AlertRecipient(chat_id=1, user_id=1)],
        )
    )
    await started.wait()
    # Force the heartbeat to complete its preflight while the Event Alert owns the lock.
    preflight = asyncio.Event()
    real_due = alerts._get_due_market_heartbeat_recipients

    async def due(**kwargs):
        result = await real_due(**kwargs)
        if kwargs.get("user_id") is None:
            preflight.set()
        return result

    monkeypatch.setattr(alerts, "_get_due_market_heartbeat_recipients", due)
    heartbeat_task = asyncio.create_task(
        alerts._deliver_market_heartbeat(
            app,
            symbol="btc",
            current_price=100,
            change_24h=0,
            now=now,
        )
    )
    await preflight.wait()
    release.set()
    assert await event_task
    monkeypatch.setattr(alerts, "_send_alert_to_recipient_with_retry", real_send)
    assert await heartbeat_task  # User 2 remains due.
    assert [call.kwargs["chat_id"] for call in app.bot.send_message.await_args_list] == [2]


@pytest.mark.asyncio
async def test_no_due_recipients_skips_all_generation_providers(delivery_db, monkeypatch):
    factory, now = delivery_db
    for identifier in (1, 2):
        for symbol in ("BTC", "ETH", "GRAM", "SOL"):
            await add_delivery(factory, user_id=identifier, symbol=symbol, sent_at=now)
    market = AsyncMock()
    llm = AsyncMock()
    monkeypatch.setattr(alerts, "get_coin_market_data_batch", market)
    monkeypatch.setattr(alerts, "_create_market_heartbeat", llm)
    await alerts.generate_market_heartbeats(SimpleNamespace())
    market.assert_not_awaited()
    llm.assert_not_awaited()


@pytest.mark.parametrize("symbol", ["btc", "eth", "gram", "sol"])
def test_one_microsecond_before_boundary_is_still_silent(symbol):
    recipient = user(activated=NOW - timedelta(days=3))
    last = NOW - timedelta(hours=24) + timedelta(microseconds=1)
    assert not can_deliver_market_heartbeat_now(recipient, symbol, NOW, last)
    assert can_deliver_market_heartbeat_now(
        recipient, symbol, NOW + timedelta(microseconds=1), last
    )


def test_trial_only_and_overlapping_entitlements_use_persisted_baseline():
    recipient = user(activated=NOW - timedelta(days=3), premium=False)
    recipient.premium_trial = SimpleNamespace(active_until=NOW + timedelta(days=7), started_at=NOW)
    assert not can_deliver_market_heartbeat_now(recipient, "eth", NOW, None)
    assert can_deliver_market_heartbeat_now(recipient, "eth", NOW + timedelta(hours=24), None)
    recipient.premium_subscription = SimpleNamespace(
        active_until=NOW + timedelta(days=7), updated_at=NOW - timedelta(days=2)
    )
    assert can_deliver_market_heartbeat_now(recipient, "eth", NOW, None)


@pytest.mark.asyncio
async def test_failed_telegram_send_does_not_reset_clock(delivery_db):
    from sqlalchemy import select
    from telegram.error import BadRequest
    from test_market_heartbeat import create_heartbeat, fake_app

    from bot.db.database import Alert

    factory, now = delivery_db
    async with factory() as session:
        await create_heartbeat(session, generated_at=now)
    app = fake_app()
    app.bot.send_message.side_effect = BadRequest("invalid destination")
    assert not await alerts._deliver_market_heartbeat(
        app,
        symbol="btc",
        current_price=100,
        change_24h=0,
        now=now,
    )
    async with factory() as session:
        rows = list((await session.scalars(select(Alert))).all())
        assert len(rows) == 2
        assert all(row.status == "failed" and row.sent_at is None for row in rows)
    assert len(await alerts._get_due_market_heartbeat_recipients(symbol="btc", now=now)) == 2


@pytest.mark.asyncio
async def test_unchanged_choice_preserves_activation_and_reenable_advances(delivery_db):
    from bot.db.database import set_user_coin_subscription

    factory, now = delivery_db
    async with factory() as session:
        row = await set_user_coin_subscription(session, user_id=1, symbol="eth", is_enabled=True)
        original = row.updated_at
        await set_user_coin_subscription(session, user_id=1, symbol="eth", is_enabled=True)
        assert row.updated_at == original
        await set_user_coin_subscription(session, user_id=1, symbol="eth", is_enabled=False)
        await set_user_coin_subscription(session, user_id=1, symbol="eth", is_enabled=True)
        assert row.updated_at.replace(tzinfo=timezone.utc) >= now
    assert not await alerts._get_due_market_heartbeat_recipients(symbol="eth", now=now, user_id=1)


@pytest.mark.asyncio
async def test_event_resets_timer_during_generation_market_fetch(delivery_db, monkeypatch):
    factory, now = delivery_db

    async def market(symbols):
        for identifier in (1, 2):
            for symbol in symbols:
                await add_delivery(factory, user_id=identifier, symbol=symbol, sent_at=now)
        return {symbol: {"price": 100, "change_24h": 0} for symbol in symbols}

    llm = AsyncMock()
    monkeypatch.setattr(alerts, "get_coin_market_data_batch", market)
    monkeypatch.setattr(alerts, "_create_market_heartbeat", llm)
    await alerts.generate_market_heartbeats(SimpleNamespace())
    llm.assert_not_awaited()


@pytest.mark.asyncio
async def test_fresh_cache_avoids_generation_market_fetch(delivery_db, monkeypatch):
    from test_market_heartbeat import create_heartbeat

    factory, now = delivery_db
    async with factory() as session:
        await create_heartbeat(session, generated_at=now)
    market = AsyncMock()
    monkeypatch.setattr(alerts, "SUPPORTED_SYMBOLS", ("btc",))
    monkeypatch.setattr(alerts, "get_coin_market_data_batch", market)
    await alerts.generate_market_heartbeats(SimpleNamespace())
    market.assert_not_awaited()


@pytest.mark.asyncio
async def test_cache_expiring_before_lock_acquisition_is_not_sent(delivery_db, monkeypatch):
    from test_market_heartbeat import create_heartbeat, fake_app

    factory, now = delivery_db
    async with factory() as session:
        await create_heartbeat(session, generated_at=now)
    real_due = alerts._get_due_market_heartbeat_recipients

    async def due(**kwargs):
        result = await real_due(**kwargs)
        if kwargs.get("user_id") is not None:
            # After preflight, emulate a cache becoming stale while waiting.
            monkeypatch.setattr(alerts, "_is_fresh_heartbeat", lambda *args, **kwargs: False)
        return result

    monkeypatch.setattr(alerts, "_get_due_market_heartbeat_recipients", due)
    app = fake_app()
    assert not await alerts._deliver_market_heartbeat(
        app,
        symbol="btc",
        current_price=100,
        change_24h=0,
        now=now,
    )
    app.bot.send_message.assert_not_awaited()
