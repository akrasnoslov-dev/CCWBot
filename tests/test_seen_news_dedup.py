from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from database import (
    Base,
    EventAiAnalysis,
    MarketEvent,
    SeenNews,
    count_market_events,
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


def build_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    return SessionLocal()


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


def test_seen_news_insert_skips_duplicate_keys():
    session = build_session()
    try:
        mark_news_items_seen(
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

        assert session.query(SeenNews).count() == 1
    finally:
        session.close()


def test_app_settings_defaults_and_updates_are_global():
    session = build_session()
    try:
        defaults = get_or_create_app_settings(
            session,
            default_threshold=2,
            default_interval=300,
        )
        assert defaults == {
            "btc_alert_threshold_percent": 2.0,
            "automatic_check_interval_seconds": 300,
        }

        updated = update_app_settings(
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

        reloaded = get_or_create_app_settings(
            session,
            default_threshold=2,
            default_interval=300,
        )
        assert reloaded == updated
    finally:
        session.close()


def test_market_event_helpers_create_and_reuse_event_key():
    session = build_session()
    try:
        first = get_or_create_market_event(
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
        second = get_or_create_market_event(
            session,
            symbol="BTC",
            event_type="price_movement",
            event_key="btc:price_movement:2026-05-04T12:00:00Z",
            price=66000.0,
            price_change_percent=4.76,
        )

        assert first.id == second.id
        assert first.symbol == "BTC"
        assert session.query(MarketEvent).count() == 1
        assert count_market_events(session, symbol="btc") == 1
        assert get_recent_market_events(session, symbol="BTC", limit=1) == [first]
    finally:
        session.close()


def test_event_ai_analysis_helpers_save_and_reuse_input_hash():
    session = build_session()
    try:
        market_event = get_or_create_market_event(
            session,
            symbol="BTC",
            event_type="price_movement",
            event_key="btc:price_movement:2026-05-04T13:00:00Z",
            price=65000.0,
            price_change_percent=3.17,
        )

        first = save_event_ai_analysis(
            session,
            market_event_id=market_event.id,
            provider="groq",
            model="llama-test",
            input_hash="abc123",
            analysis_text="BTC moved quickly.",
            plain_text="BTC moved quickly. Not financial advice.",
            status="completed",
        )
        second = save_event_ai_analysis(
            session,
            market_event_id=market_event.id,
            provider="groq",
            model="llama-test",
            input_hash="abc123",
            analysis_text="Replacement text should not create another row.",
        )

        assert first.id == second.id
        assert session.query(EventAiAnalysis).count() == 1
        assert (
            get_event_ai_analysis(
                session, market_event_id=market_event.id, input_hash="abc123"
            )
            == first
        )
    finally:
        session.close()


def test_legacy_app_settings_table_migrates_to_global_columns():
    db_path = PROJECT_ROOT / "legacy_app_settings_test.sqlite"
    if db_path.exists():
        db_path.unlink()
    try:
        database_url = f"sqlite:///{db_path.as_posix()}"
        engine = create_engine(database_url, future=True)
        with engine.begin() as connection:
            connection.execute(
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
            connection.execute(
                text(
                    "INSERT INTO app_settings "
                    "(setting_key, setting_value, created_at, updated_at) "
                    "VALUES "
                    "('btc_alert_threshold_percent', '1.5', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP), "
                    "('automatic_check_interval_seconds', '600', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                )
            )
        engine.dispose()

        migrated_engine, SessionLocal = init_db(database_url)
        session = SessionLocal()
        try:
            migrated = get_or_create_app_settings(
                session,
                default_threshold=2,
                default_interval=300,
            )
            assert migrated == {
                "btc_alert_threshold_percent": 1.5,
                "automatic_check_interval_seconds": 600,
            }
        finally:
            session.close()
            migrated_engine.dispose()
    finally:
        if db_path.exists():
            db_path.unlink()


if __name__ == "__main__":
    test_link_key_normalizes_tracking_params()
    test_missing_link_fallback_uses_source_and_title()
    test_seen_news_insert_skips_duplicate_keys()
    test_app_settings_defaults_and_updates_are_global()
    test_market_event_helpers_create_and_reuse_event_key()
    test_event_ai_analysis_helpers_save_and_reuse_input_hash()
    test_legacy_app_settings_table_migrates_to_global_columns()
    print("seen_news dedup tests passed")
