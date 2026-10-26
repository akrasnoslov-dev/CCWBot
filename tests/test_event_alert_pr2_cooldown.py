"""PR 2 regressions for confirmed semantic cooldown boundary defects.

No provider, Telegram, or production access.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot import alerts
from bot.db.database import (
    Alert,
    Base,
    get_or_create_market_event,
    get_recent_sent_event_alert_contexts,
)


async def _db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


@pytest.mark.asyncio
async def test_late_delivery_remains_in_semantic_cooldown_query():
    engine, factory = await _db()
    now = datetime.now(timezone.utc)
    try:
        async with factory() as session:
            session.add(
                Alert(
                    symbol="BTC",
                    alert_type="event_alert",
                    status="sent",
                    user_id=42,
                    sent_to_chat_id=42,
                    message="test",
                    created_at=now - timedelta(hours=5),
                    sent_at=now - timedelta(minutes=12),
                )
            )
            await session.commit()
            recent = await get_recent_sent_event_alert_contexts(
                session,
                user_ids=[42],
                symbol="BTC",
                alert_type="event_alert",
                since=now - timedelta(hours=4),
            )
            assert len(recent) == 1, "A completed retry must remain visible for four hours"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "previous_key,previous_family,numeric_context,current_family,blocked",
    [
        (None, None, '{"analysed_window_change_percent":-1.5}', "price_downtrend", True),
        (None, None, '{"analysed_window_change_percent":-1.5}', "price_uptrend", False),
        (
            "btc_down_1_5",
            "price_downtrend",
            '{"analysed_window_change_percent":-1.5}',
            "price_downtrend",
            True,
        ),
    ],
)
async def test_incomplete_persisted_identity_uses_own_verified_market_move(
    monkeypatch,
    previous_key,
    previous_family,
    numeric_context,
    current_family,
    blocked,
):
    engine, factory = await _db()
    now = datetime.now(timezone.utc)
    try:
        previous = SimpleNamespace(
            id=12,
            user_id=7,
            created_at=now - timedelta(hours=5),
            sent_at=now - timedelta(minutes=10),
            numeric_context=numeric_context,
        )
        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", factory)
        monkeypatch.setattr(
            alerts,
            "get_recent_sent_event_alert_contexts",
            AsyncMock(return_value=[(previous, previous_key, previous_family)]),
        )
        result = await alerts._filter_event_recipients_for_cooldown(
            [alerts.AlertRecipient(chat_id=777, user_id=7)],
            symbol="btc",
            urgency="normal",
            cooldown_seconds=300,
            canonical_event_key="btc_" + current_family,
            semantic_family=current_family,
            now=now,
            return_summary=True,
        )
        assert bool(result.suppressed) is blocked
        assert bool(result.recipients) is not blocked
    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("second_family", "expected_sends"),
    [("price_uptrend", 1), ("price_downtrend", 2)],
)
async def test_stale_prefilter_cannot_bypass_in_lock_cooldown(
    monkeypatch,
    second_family,
    expected_sends,
):
    """Two distinct event rows can pass prefilter before the first send finishes."""
    engine, factory = await _db()
    try:
        async with factory() as session:
            first = await get_or_create_market_event(
                session,
                symbol="btc",
                event_type="price_movement",
                event_key="btc:recheck:one",
                price=101,
                previous_price=100,
                price_change_percent=1,
            )
            second = await get_or_create_market_event(
                session,
                symbol="btc",
                event_type="price_movement",
                event_key="btc:recheck:two",
                price=102,
                previous_price=100,
                price_change_percent=2,
            )
        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", factory)
        monkeypatch.setattr(alerts, "_prepare_event_alert_chart", AsyncMock())
        send = AsyncMock(return_value=(True, None, None))
        monkeypatch.setattr(alerts, "_send_alert_to_recipient_with_retry", send)
        recipient = alerts.AlertRecipient(chat_id=777, user_id=77)
        for index, market_event in enumerate((first, second)):
            family = "price_uptrend" if index == 0 else second_family
            await alerts._deliver_market_event_alert(
                SimpleNamespace(bot=SimpleNamespace()),
                symbol="btc",
                alert_payload={"plain_text": "BTC moves\nNot financial advice."},
                market_event_id=market_event.id,
                event_ai_analysis_id=None,
                recipients=[recipient],
                event_type=alerts.EVENT_ALERT_TYPE,
                canonical_event_key="btc_" + family,
                semantic_family=family,
                numeric_context=(
                    '{"analysed_window_change_percent":1.0,"current_price":101}'
                    if family == "price_uptrend"
                    else '{"analysed_window_change_percent":-1.0,"current_price":101}'
                ),
            )
        assert send.await_count == expected_sends, (
            "Same-family overlap must suppress; distinct price directions remain eligible"
        )
    finally:
        await engine.dispose()
