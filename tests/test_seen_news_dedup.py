import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from alembic.config import Config
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from alembic import command
from bot.alerts import (
    _build_alert_ai_input_hash,
    _build_price_movement_event_key,
)
from bot.db.database import (
    Base,
    EventAiAnalysis,
    MarketEvent,
    SeenNews,
    User,
    attach_analysis_to_market_event,
    count_market_events,
    get_active_users_with_chat_ids,
    get_event_ai_analysis,
    get_latest_success_event_ai_analysis,
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
            default_interval=600,
        )
        assert defaults.items() >= {
            "btc_alert_threshold_percent": 2.0,
            "automatic_check_interval_seconds": 600,
            "error_file_logging_enabled": False,
        }.items()
        assert defaults["major_movement_threshold_percent"] == 1.0
        assert defaults["alt_movement_threshold_percent"] == 2.0

        updated = await update_app_settings(
            session,
            default_threshold=2,
            default_interval=600,
            threshold=1.0,
            interval_seconds=600,
            error_file_logging_enabled=True,
        )
        assert updated.items() >= {
            "btc_alert_threshold_percent": 1.0,
            "automatic_check_interval_seconds": 600,
            "error_file_logging_enabled": True,
        }.items()

        reloaded = await get_or_create_app_settings(
            session,
            default_threshold=2,
            default_interval=600,
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
async def test_market_event_helpers_use_event_instance_key_for_concrete_occurrence():
    engine, session = await build_session()
    try:
        first = await get_or_create_market_event(
            session,
            symbol="btc",
            event_type="event_alert",
            event_key="btc_price_volatility",
            event_instance_key="instance-a",
            price=65000.0,
            previous_price=64000.0,
            price_change_percent=1.56,
        )
        same_instance = await get_or_create_market_event(
            session,
            symbol="btc",
            event_type="event_alert",
            event_key="btc_price_volatility",
            event_instance_key="instance-a",
            price=65100.0,
            previous_price=64000.0,
            price_change_percent=1.72,
        )
        next_instance = await get_or_create_market_event(
            session,
            symbol="btc",
            event_type="event_alert",
            event_key="btc_price_volatility",
            event_instance_key="instance-b",
            price=65200.0,
            previous_price=64000.0,
            price_change_percent=1.88,
        )

        assert first.id == same_instance.id
        assert next_instance.id != first.id
        assert first.event_key == next_instance.event_key == "btc_price_volatility"
        assert await session.scalar(select(func.count()).select_from(MarketEvent)) == 2
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
async def test_attach_analysis_reuses_existing_success_for_market_event():
    engine, session = await build_session()
    try:
        market_event = await get_or_create_market_event(
            session,
            symbol="BTC",
            event_type="event_alert",
            event_key="btc_volatility",
            event_instance_key="btc:volatility:instance",
            price=65000.0,
            price_change_percent=1.5,
        )
        canonical = EventAiAnalysis(
            market_event_id=market_event.id,
            analysis_id="event_analysis_btc_canonical",
            symbol="BTC",
            analysis_type="event_analysis",
            provider="groq",
            model="llama-test",
            input_hash="canonical-hash",
            status="success",
            should_alert=True,
            plain_text="Canonical text. Not financial advice.",
        )
        fresh_attempt = EventAiAnalysis(
            market_event_id=None,
            analysis_id="event_analysis_btc_fresh",
            symbol="BTC",
            analysis_type="event_analysis",
            provider="groq",
            model="llama-test",
            input_hash="fresh-hash",
            status="success",
            should_alert=True,
            plain_text="Fresh text. Not financial advice.",
        )
        session.add_all([canonical, fresh_attempt])
        await session.commit()

        attached = await attach_analysis_to_market_event(
            session,
            analysis_id="event_analysis_btc_fresh",
            market_event_id=market_event.id,
            plain_text="Fresh text. Not financial advice.",
        )

        assert attached.id == canonical.id
        refreshed_fresh = await session.scalar(
            select(EventAiAnalysis).where(EventAiAnalysis.analysis_id == "event_analysis_btc_fresh")
        )
        assert refreshed_fresh.market_event_id is None
        assert (
            await get_latest_success_event_ai_analysis(
                session,
                market_event_id=market_event.id,
            )
        ).id == canonical.id
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_save_event_llm_analysis_integrity_race_returns_existing_success(monkeypatch):
    from bot.db import alerts as alert_db

    engine, session = await build_session()
    try:
        market_event = await get_or_create_market_event(
            session,
            symbol="BTC",
            event_type="event_alert",
            event_key="btc_volatility_race",
            event_instance_key="btc:volatility:race",
            price=65000.0,
            price_change_percent=1.5,
        )
        canonical = EventAiAnalysis(
            market_event_id=market_event.id,
            analysis_id="event_analysis_btc_race_canonical",
            symbol="BTC",
            analysis_type="event_analysis",
            provider="groq",
            model="llama-test",
            input_hash="canonical-race-hash",
            status="success",
            should_alert=True,
            plain_text="Canonical text. Not financial advice.",
        )
        session.add(canonical)
        await session.commit()
        await session.refresh(canonical)
        canonical_id = canonical.id
        market_event_id = market_event.id

        integrity_error = IntegrityError("insert", {}, Exception("duplicate attached analysis"))
        monkeypatch.setattr(session, "commit", AsyncMock(side_effect=integrity_error))

        lookup_count = 0

        async def lookup_existing_success(session_arg, *, market_event_id):
            nonlocal lookup_count
            lookup_count += 1
            if lookup_count == 1:
                return None
            return await session_arg.scalar(
                select(EventAiAnalysis)
                .where(EventAiAnalysis.market_event_id == market_event_id)
                .where(EventAiAnalysis.analysis_type == "event_analysis")
                .where(EventAiAnalysis.status == "success")
                .where(EventAiAnalysis.should_alert.is_(True))
                .limit(1)
            )

        lookup = AsyncMock(side_effect=lookup_existing_success)
        monkeypatch.setattr(alert_db, "get_latest_success_event_ai_analysis", lookup)

        result = await alert_db.save_event_llm_analysis(
            session,
            analysis_id="event_analysis_btc_race_fresh",
            symbol="BTC",
            input_hash="fresh-race-hash",
            raw_input_json="{}",
            raw_output_json="{}",
            status="success",
            provider="groq",
            model="llama-test",
            analysis_type="event_analysis",
            market_event_id=market_event_id,
            should_alert=True,
            plain_text="Fresh text. Not financial advice.",
        )

        assert result.id == canonical_id
        assert lookup.await_count == 2
        fresh = await session.scalar(
            select(EventAiAnalysis).where(
                EventAiAnalysis.analysis_id == "event_analysis_btc_race_fresh"
            )
        )
        attached_count = await session.scalar(
            select(func.count())
            .select_from(EventAiAnalysis)
            .where(EventAiAnalysis.market_event_id == market_event_id)
            .where(EventAiAnalysis.analysis_type == "event_analysis")
            .where(EventAiAnalysis.status.in_(["success", "completed"]))
            .where(EventAiAnalysis.should_alert.is_(True))
        )
        assert fresh is None
        assert attached_count == 1
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_duplicate_attached_success_event_analysis_is_rejected():
    engine, session = await build_session()
    try:
        market_event = await get_or_create_market_event(
            session,
            symbol="BTC",
            event_type="event_alert",
            event_key="btc_reversal",
            event_instance_key="btc:reversal:instance",
            price=65000.0,
            price_change_percent=1.5,
        )
        session.add(
            EventAiAnalysis(
                market_event_id=market_event.id,
                analysis_id="event_analysis_btc_one",
                symbol="BTC",
                analysis_type="event_analysis",
                provider="groq",
                model="llama-test",
                input_hash="one",
                status="success",
                should_alert=True,
            )
        )
        await session.commit()
        session.add(
            EventAiAnalysis(
                market_event_id=market_event.id,
                analysis_id="event_analysis_btc_two",
                symbol="BTC",
                analysis_type="event_analysis",
                provider="groq",
                model="llama-test",
                input_hash="two",
                status="success",
                should_alert=True,
            )
        )

        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

        session.add_all(
            [
                EventAiAnalysis(
                    market_event_id=None,
                    analysis_id="event_analysis_btc_failed",
                    symbol="BTC",
                    analysis_type="event_analysis",
                    provider="groq",
                    model="llama-test",
                    input_hash="failed",
                    status="llm_error",
                ),
                EventAiAnalysis(
                    market_event_id=None,
                    analysis_id="event_analysis_btc_no_alert",
                    symbol="BTC",
                    analysis_type="event_analysis",
                    provider="groq",
                    model="llama-test",
                    input_hash="no-alert",
                    status="no_alert",
                    should_alert=False,
                ),
            ]
        )
        await session.commit()
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_event_analysis_invariant_migration_detaches_duplicates():
    tmp_dir = PROJECT_ROOT / ".tmp"
    tmp_dir.mkdir(exist_ok=True)
    db_path = tmp_dir / "event_analysis_invariant_migration_test.sqlite"
    if db_path.exists():
        db_path.unlink()
    database_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    alembic_config = Config(str(PROJECT_ROOT / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    alembic_config.set_main_option("sqlalchemy.url", database_url)
    alembic_config.attributes["database_url"] = database_url
    alembic_config.attributes["configure_logger"] = False
    await asyncio.to_thread(command.upgrade, alembic_config, "0021_alert_delivery_outcomes")

    engine = create_async_engine(database_url, future=True)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                INSERT INTO market_events (
                    id, symbol, event_type, event_key, event_instance_key, price,
                    previous_price, price_change_percent, detected_at, created_at
                )
                VALUES (
                    1, 'BTC', 'event_alert', 'btc_volatility', 'instance-migration',
                    65000.0, 64000.0, 1.5, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """
            )
        )
        await connection.execute(
            text(
                """
                INSERT INTO event_ai_analyses (
                    id, market_event_id, analysis_id, symbol, analysis_type, provider, model,
                    input_hash, should_alert, status, plain_text, created_at
                )
                VALUES
                    (
                        1, 1, 'event_analysis_canonical', 'BTC', 'event_analysis',
                        'groq', 'llama-test', 'canonical', 1, 'success',
                        'Canonical text. Not financial advice.', CURRENT_TIMESTAMP
                    ),
                    (
                        2, 1, 'event_analysis_duplicate', 'BTC', 'event_analysis',
                        'groq', 'llama-test', 'duplicate', 1, 'success',
                        'Duplicate text. Not financial advice.', CURRENT_TIMESTAMP
                    ),
                    (
                        3, 1, 'event_analysis_no_alert', 'BTC', 'event_analysis',
                        'groq', 'llama-test', 'no-alert', 0, 'no_alert',
                        NULL, CURRENT_TIMESTAMP
                    )
                """
            )
        )
        await connection.execute(
            text(
                """
                INSERT INTO alerts (
                    id, symbol, alert_type, message, sent_to_chat_id, market_event_id,
                    event_ai_analysis_id, user_id, status, retry_count, created_at
                )
                VALUES (
                    1, 'BTC', 'event_alert', 'Canonical text. Not financial advice.',
                    2001, 1, 1, NULL, 'sent', 0, CURRENT_TIMESTAMP
                )
                """
            )
        )
    await engine.dispose()

    migrated_engine, SessionLocal = await init_db(database_url)
    try:
        async with SessionLocal() as session:
            attached_ids = list(
                (
                    await session.scalars(
                        select(EventAiAnalysis.id)
                        .where(EventAiAnalysis.market_event_id == 1)
                        .where(EventAiAnalysis.analysis_type == "event_analysis")
                        .order_by(EventAiAnalysis.id)
                    )
                ).all()
            )
            detached_ids = list(
                (
                    await session.scalars(
                        select(EventAiAnalysis.id)
                        .where(EventAiAnalysis.market_event_id.is_(None))
                        .order_by(EventAiAnalysis.id)
                    )
                ).all()
            )

        assert attached_ids == [1]
        assert detached_ids == [2, 3]
    finally:
        await migrated_engine.dispose()
        if db_path.exists():
            db_path.unlink()


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
                default_interval=600,
            )
            assert migrated.items() >= {
                "btc_alert_threshold_percent": 1.5,
                "automatic_check_interval_seconds": 600,
                "error_file_logging_enabled": False,
            }.items()
        finally:
            await session.close()
            await migrated_engine.dispose()
    finally:
        if db_path.exists():
            db_path.unlink()


@pytest.mark.asyncio
async def test_unique_telegram_user_migration_refuses_existing_duplicates():
    db_path = PROJECT_ROOT / "duplicate_users_migration_test.sqlite"
    if db_path.exists():
        db_path.unlink()
    try:
        database_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
        engine = create_async_engine(database_url, future=True)
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "CREATE TABLE alembic_version ("
                    "version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
                )
            )
            await connection.execute(
                text(
                    "INSERT INTO alembic_version (version_num) "
                    "VALUES ('0006_payment_recurring_metadata')"
                )
            )
            await connection.execute(
                text(
                    "CREATE TABLE users ("
                    "id INTEGER PRIMARY KEY, "
                    "telegram_user_id BIGINT NOT NULL, "
                    "telegram_chat_id BIGINT NOT NULL, "
                    "username VARCHAR(255), "
                    "first_name VARCHAR(255), "
                    "role VARCHAR(64) NOT NULL, "
                    "is_active BOOLEAN NOT NULL, "
                    "alert_frequency_seconds INTEGER NOT NULL DEFAULT 14400, "
                    "created_at DATETIME, "
                    "updated_at DATETIME)"
                )
            )
            await connection.execute(
                text(
                    "INSERT INTO users "
                    "(id, telegram_user_id, telegram_chat_id, role, is_active) "
                    "VALUES "
                    "(1, 1001, 2001, 'user', 1), "
                    "(2, 1001, 2002, 'admin', 1)"
                )
            )
        await engine.dispose()

        with pytest.raises(RuntimeError, match="duplicate users exist"):
            await init_db(database_url)
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
