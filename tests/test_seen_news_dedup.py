import asyncio
from pathlib import Path

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.alerts import (
    AlertRecipient,
    _build_alert_ai_input_hash,
    _build_price_movement_event_key,
    get_alert_recipients,
)
from database import (
    Base,
    EventAiAnalysis,
    MarketEvent,
    SeenNews,
    User,
    count_market_events,
    get_active_users_with_chat_ids,
    get_event_ai_analysis,
    get_or_create_app_settings,
    get_or_create_market_event,
    get_recent_market_events,
    init_db,
    make_news_key,
    mark_news_items_seen,
    save_event_ai_analysis,
    update_app_settings,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


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


def test_link_key_normalizes_tracking_params():
    first = make_news_key(
        {
            "title": "BTC ETF inflows rise",
            "link": "https://example.com/article/?utm_source=rss&id=1",
            "source": "Example",
        }
    )
    second = make_news_key(
        {
            "title": "BTC ETF inflows rise",
            "link": "https://EXAMPLE.com/article?id=1",
            "source": "Example",
        }
    )

    assert first == second
    assert first.startswith("link:")


def test_missing_link_fallback_uses_source_and_title():
    first = make_news_key({"title": "Same headline", "source": "Source A"})
    second = make_news_key({"title": "Same headline", "source": "Source B"})

    assert first != second
    assert first.startswith("source_title:")


@pytest.mark.asyncio
async def test_seen_news_insert_skips_duplicate_keys():
    engine, session = await build_session()
    try:
        await mark_news_items_seen(
            session,
            [
                {
                    "title": "BTC ETF inflows rise",
                    "link": "https://example.com/article?id=1&utm_campaign=x",
                    "source": "Example",
                },
                {
                    "title": "Updated title should still dedupe by link",
                    "link": "https://example.com/article?id=1",
                    "source": "Example",
                },
            ],
        )

        assert await session.scalar(select(func.count()).select_from(SeenNews)) == 1
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_app_settings_defaults_and_updates_are_global():
    engine, session = await build_session()
    try:
        defaults = await get_or_create_app_settings(
            session,
            default_threshold=2,
            default_interval=300,
        )
        assert defaults == {
            "btc_alert_threshold_percent": 2.0,
            "automatic_check_interval_seconds": 300,
        }

        updated = await update_app_settings(
            session,
            default_threshold=2,
            default_interval=300,
            threshold=1.0,
            interval_seconds=600,
        )
        assert updated == {
            "btc_alert_threshold_percent": 1.0,
            "automatic_check_interval_seconds": 600,
        }

        reloaded = await get_or_create_app_settings(
            session,
            default_threshold=2,
            default_interval=300,
        )
        assert reloaded == updated
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_market_event_helpers_create_and_reuse_event_key():
    engine, session = await build_session()
    try:
        first = await get_or_create_market_event(
            session,
            symbol="btc",
            event_type="price_movement",
            event_key="btc:price_movement:2026-05-04T12:00:00Z",
            price=65000.0,
            previous_price=63000.0,
            price_change_percent=3.17,
            last_24h_change=2.4,
            last_7d_change=6.1,
        )
        second = await get_or_create_market_event(
            session,
            symbol="BTC",
            event_type="price_movement",
            event_key="btc:price_movement:2026-05-04T12:00:00Z",
            price=66000.0,
            price_change_percent=4.76,
        )

        assert first.id == second.id
        assert first.symbol == "BTC"
        assert await session.scalar(select(func.count()).select_from(MarketEvent)) == 1
        assert await count_market_events(session, symbol="btc") == 1
        assert await get_recent_market_events(session, symbol="BTC", limit=1) == [first]
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_event_ai_analysis_helpers_save_and_reuse_input_hash():
    engine, session = await build_session()
    try:
        market_event = await get_or_create_market_event(
            session,
            symbol="BTC",
            event_type="price_movement",
            event_key="btc:price_movement:2026-05-04T13:00:00Z",
            price=65000.0,
            price_change_percent=3.17,
        )

        first = await save_event_ai_analysis(
            session,
            market_event_id=market_event.id,
            provider="groq",
            model="llama-test",
            input_hash="abc123",
            analysis_text="BTC moved quickly.",
            plain_text="BTC moved quickly. Not financial advice.",
            status="completed",
        )
        second = await save_event_ai_analysis(
            session,
            market_event_id=market_event.id,
            provider="groq",
            model="llama-test",
            input_hash="abc123",
            analysis_text="Replacement text should not create another row.",
        )

        assert first.id == second.id
        assert await session.scalar(select(func.count()).select_from(EventAiAnalysis)) == 1
        assert (
            await get_event_ai_analysis(
                session, market_event_id=market_event.id, input_hash="abc123"
            )
            == first
        )
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_active_alert_recipients_use_active_users_with_chat_ids():
    engine, session = await build_session()
    try:
        session.add_all(
            [
                User(
                    telegram_user_id=1001,
                    telegram_chat_id=2001,
                    username="admin",
                    first_name="Admin",
                    role="admin",
                    is_active=True,
                ),
                User(
                    telegram_user_id=1002,
                    telegram_chat_id=2002,
                    username="normal",
                    first_name="Normal",
                    role="user",
                    is_active=True,
                ),
                User(
                    telegram_user_id=1003,
                    telegram_chat_id=2003,
                    username="inactive",
                    first_name="Inactive",
                    role="user",
                    is_active=False,
                ),
            ]
        )
        await session.commit()

        recipients = await get_active_users_with_chat_ids(session)

        assert [recipient.telegram_chat_id for recipient in recipients] == [2001, 2002]
        assert [recipient.role for recipient in recipients] == ["admin", "user"]
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_get_alert_recipients_deduplicates_active_user_chats(monkeypatch):
    class UserRow:
        def __init__(self, user_id, telegram_chat_id):
            self.id = user_id
            self.telegram_chat_id = telegram_chat_id
            self.premium_subscription = None

    class SessionContext:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc_value, traceback):
            return False

    async def fake_get_active_users_with_alert_preferences(session):
        return [
            UserRow(1, 2001),
            UserRow(2, 2002),
            UserRow(3, 2001),
        ]

    async def fake_ensure_default_coin_subscriptions(session, *, user_id):
        return [type("Subscription", (), {"symbol": "btc", "is_enabled": True})()]

    async def fake_get_last_sent_alert_at(session, *, user_id, symbol):
        return None

    monkeypatch.setattr("bot.alerts.DB_ENABLED", True)
    monkeypatch.setattr("bot.alerts.DB_SESSION_LOCAL", lambda: SessionContext())
    monkeypatch.setattr(
        "bot.alerts.get_active_users_with_alert_preferences",
        fake_get_active_users_with_alert_preferences,
    )
    monkeypatch.setattr(
        "bot.alerts.ensure_default_coin_subscriptions",
        fake_ensure_default_coin_subscriptions,
    )
    monkeypatch.setattr("bot.alerts.get_last_sent_alert_at", fake_get_last_sent_alert_at)

    recipients = await get_alert_recipients(symbol="BTC", event_type="price_movement")

    assert recipients == [
        AlertRecipient(chat_id=2001, user_id=1),
        AlertRecipient(chat_id=2002, user_id=2),
    ]
    assert await get_alert_recipients(symbol="ETH", event_type="price_movement") == []
    assert await get_alert_recipients(symbol="BTC", event_type="daily_report") == []


def test_price_movement_event_key_is_stable_for_same_movement():
    first = _build_price_movement_event_key(
        symbol="btc",
        previous_price=65000.001,
        current_price=67000.004,
        price_change_percent=3.0769234,
    )
    second = _build_price_movement_event_key(
        symbol="BTC",
        previous_price=65000.002,
        current_price=67000.003,
        price_change_percent=3.0769235,
    )
    different_move = _build_price_movement_event_key(
        symbol="BTC",
        previous_price=65000.0,
        current_price=67100.0,
        price_change_percent=3.2308,
    )

    assert first == second
    assert first != different_move
    assert first.startswith("btc:price_movement:")


def test_alert_ai_input_hash_uses_stable_news_identity():
    base_news = [
        {
            "title": "BTC ETF inflows rise",
            "link": "https://example.com/article?id=1&utm_source=rss",
            "source": "Example",
            "ignored": "not part of hash",
        }
    ]
    same_news_identity = [
        {
            "title": "BTC ETF inflows rise",
            "link": "https://EXAMPLE.com/article?id=1",
            "source": "Example",
        }
    ]

    first = _build_alert_ai_input_hash(
        symbol="btc",
        event_type="price_movement",
        previous_price=65000.0,
        current_price=67000.0,
        price_change_percent=3.0769,
        change_24h=2.5,
        change_7d=6.25,
        news_items=base_news,
        alert_threshold_percent=2.0,
        check_interval_seconds=300,
    )
    second = _build_alert_ai_input_hash(
        symbol="BTC",
        event_type="price_movement",
        previous_price=65000.0,
        current_price=67000.0,
        price_change_percent=3.0769,
        change_24h=2.5,
        change_7d=6.25,
        news_items=same_news_identity,
        alert_threshold_percent=2.0,
        check_interval_seconds=300,
    )
    changed_price = _build_alert_ai_input_hash(
        symbol="BTC",
        event_type="price_movement",
        previous_price=65000.0,
        current_price=67100.0,
        price_change_percent=3.2308,
        change_24h=2.5,
        change_7d=6.25,
        news_items=same_news_identity,
        alert_threshold_percent=2.0,
        check_interval_seconds=300,
    )

    assert first == second
    assert first != changed_price
    assert len(first) == 64


@pytest.mark.asyncio
async def test_legacy_app_settings_table_migrates_to_global_columns():
    db_path = PROJECT_ROOT / "legacy_app_settings_test.sqlite"
    if db_path.exists():
        db_path.unlink()
    try:
        database_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
        engine = create_async_engine(database_url, future=True)
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "CREATE TABLE app_settings ("
                    "id INTEGER PRIMARY KEY, "
                    "setting_key VARCHAR(255) NOT NULL UNIQUE, "
                    "setting_value VARCHAR(255) NOT NULL, "
                    "created_at DATETIME, "
                    "updated_at DATETIME"
                    ")"
                )
            )
            await connection.execute(
                text(
                    "INSERT INTO app_settings "
                    "(setting_key, setting_value, created_at, updated_at) "
                    "VALUES "
                    "('btc_alert_threshold_percent', '1.5', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP), "
                    "('automatic_check_interval_seconds', '600', "
                    "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                )
            )
        await engine.dispose()

        migrated_engine, SessionLocal = await init_db(database_url)
        session = SessionLocal()
        try:
            migrated = await get_or_create_app_settings(
                session,
                default_threshold=2,
                default_interval=300,
            )
            assert migrated == {
                "btc_alert_threshold_percent": 1.5,
                "automatic_check_interval_seconds": 600,
            }
        finally:
            await session.close()
            await migrated_engine.dispose()
    finally:
        if db_path.exists():
            db_path.unlink()


if __name__ == "__main__":
    test_link_key_normalizes_tracking_params()
    test_missing_link_fallback_uses_source_and_title()
    asyncio.run(test_seen_news_insert_skips_duplicate_keys())
    asyncio.run(test_app_settings_defaults_and_updates_are_global())
    asyncio.run(test_market_event_helpers_create_and_reuse_event_key())
    asyncio.run(test_event_ai_analysis_helpers_save_and_reuse_input_hash())
    test_price_movement_event_key_is_stable_for_same_movement()
    test_alert_ai_input_hash_uses_stable_news_identity()
    asyncio.run(test_legacy_app_settings_table_migrates_to_global_columns())
    print("seen_news dedup tests passed")
