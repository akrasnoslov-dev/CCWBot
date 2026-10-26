"""Real PostgreSQL regression for Event Alert cooldown delivery-time semantics.

Requires ALEMBIC_POSTGRES_TEST_DATABASE_URL pointing ONLY to an empty disposable
database. This test does not touch the bot's production/local main database.
"""
import os
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.db.database import (
    Alert,
    Base,
    get_latest_sent_event_alert_context_for_symbol,
    get_recent_sent_event_alert_contexts,
)


def postgres_url():
    url = (os.getenv("ALEMBIC_POSTGRES_TEST_DATABASE_URL")
           or os.getenv("OPS_AGENT_POSTGRES_TEST_DATABASE_URL"))
    if not url or not url.startswith("postgresql+asyncpg://"):
        pytest.skip("Requires a disposable PostgreSQL URL")
    return url


@pytest.mark.asyncio
async def test_real_postgres_cooldown_uses_delivery_time_with_legacy_fallback():
    engine = create_async_engine(postgres_url(), pool_size=3)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        now = datetime.now(timezone.utc)
        async with session_factory() as session:
            session.add_all([
                Alert(
                    symbol="BTC", alert_type="event_alert",
                    status="sent", user_id=7101, sent_to_chat_id=7101,
                    message="late delivery",
                    created_at=now - timedelta(hours=5),
                    sent_at=now - timedelta(minutes=12),
                ),
                Alert(
                    symbol="BTC", alert_type="event_alert",
                    status="sent", user_id=7102, sent_to_chat_id=7102,
                    message="old completion",
                    created_at=now - timedelta(minutes=7),
                    sent_at=now - timedelta(hours=5),
                ),
                Alert(
                    symbol="BTC", alert_type="event_alert",
                    status="sent", user_id=7103, sent_to_chat_id=7103,
                    message="legacy delivery",
                    created_at=now - timedelta(hours=2),
                    sent_at=None,
                ),
            ])
            # Keep test rows in an uncommitted transaction; no CI DB pollution.
            await session.flush()
            rows = await get_recent_sent_event_alert_contexts(
                session, user_ids=[7101, 7102, 7103],
                symbol="BTC", alert_type="event_alert",
                since=now - timedelta(hours=4),
            )
            assert {alert.user_id for alert, _, _ in rows} == {7101, 7103}
            assert rows[0][0].user_id == 7101
            latest = await get_latest_sent_event_alert_context_for_symbol(
                session, symbol="BTC", alert_type="event_alert",
            )
            assert latest is not None
            # Latest delivered, not latest reserved; user context is global.
            assert latest[0].user_id == 7101
    finally:
        await engine.dispose()
