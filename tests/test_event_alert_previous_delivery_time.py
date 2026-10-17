"""The global previous-alert hint reflects confirmed delivery, never reservation age."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.alerts import _previous_event_alert_context
from bot.db.database import Alert, Base, get_latest_sent_event_alert_context_for_symbol


def test_previous_market_alert_context_uses_latest_successful_delivery_time():
    now = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)
    stored = SimpleNamespace(
        created_at=now - timedelta(hours=5),
        sent_at=now - timedelta(minutes=12),
        numeric_context=None,
        trigger_reason=None,
    )
    result = _previous_event_alert_context(
        stored, canonical_event_key="btc_price_uptrend",
        semantic_family="price_uptrend",
    )
    assert result["created_at"] == stored.sent_at.isoformat()


def test_previous_market_alert_context_supports_legacy_deliveries():
    now = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)
    stored = SimpleNamespace(
        created_at=now - timedelta(minutes=25),
        sent_at=None,
        numeric_context=None,
        trigger_reason=None,
    )
    result = _previous_event_alert_context(
        stored, canonical_event_key="btc_price_uptrend",
        semantic_family="price_uptrend",
    )
    assert result["created_at"] == stored.created_at.isoformat()



@pytest.mark.asyncio
async def test_latest_sent_event_uses_completed_delivery_order_not_reservation():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        now = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as session:
            session.add_all([
                Alert(
                    symbol="BTC", alert_type="event_alert", status="sent",
                    user_id=13, sent_to_chat_id=13, message="newly delivered",
                    created_at=now - timedelta(hours=5),
                    sent_at=now - timedelta(minutes=12),
                ),
                Alert(
                    symbol="BTC", alert_type="event_alert", status="sent",
                    user_id=14, sent_to_chat_id=14, message="new reservation",
                    created_at=now - timedelta(minutes=7),
                    sent_at=now - timedelta(hours=4),
                ),
                Alert(
                    symbol="BTC", alert_type="event_alert", status="failed",
                    user_id=15, sent_to_chat_id=15, message="never delivered",
                    created_at=now - timedelta(minutes=1),
                ),
            ])
            await session.commit()
            latest = await get_latest_sent_event_alert_context_for_symbol(
                session, symbol="BTC", alert_type="event_alert",
            )
            assert latest is not None
            assert latest[0].user_id == 13
    finally:
        await engine.dispose()
