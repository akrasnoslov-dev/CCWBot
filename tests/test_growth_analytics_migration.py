from datetime import datetime, timezone

from alembic.config import Config
from sqlalchemy import create_engine, text

from alembic import command


def _alembic_config(database_url: str) -> Config:
    config = Config("alembic.ini")
    config.attributes["database_url"] = database_url
    config.attributes["configure_logger"] = False
    return config


def test_growth_analytics_upgrade_backfills_existing_users(tmp_path):
    database_path = tmp_path / "growth_analytics.sqlite"
    async_url = f"sqlite+aiosqlite:///{database_path.as_posix()}"
    config = _alembic_config(async_url)
    command.upgrade(config, "0025_llm_operation_correlation")

    created_at = datetime(2026, 8, 31, 12, tzinfo=timezone.utc)
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO users (telegram_user_id, telegram_chat_id, username, first_name, "
                    "role, is_active, bot_blocked, alert_frequency_seconds, created_at, "
                    "updated_at) "
                    "VALUES (:telegram_user_id, :telegram_chat_id, :username, :first_name, :role, "
                    ":is_active, :bot_blocked, :alert_frequency_seconds, :created_at, :updated_at)"
                ),
                {
                    "telegram_user_id": 123456,
                    "telegram_chat_id": 123456,
                    "username": "legacy",
                    "first_name": "Legacy",
                    "role": "user",
                    "is_active": True,
                    "bot_blocked": False,
                    "alert_frequency_seconds": 14400,
                    "created_at": created_at,
                    "updated_at": created_at,
                },
            )

        command.upgrade(config, "0026_growth_analytics")

        with engine.connect() as connection:
            migrated = connection.execute(
                text(
                    "SELECT onboarding_completed_at = created_at AS onboarding_backfilled "
                    "FROM users WHERE telegram_user_id = :telegram_user_id"
                ),
                {"telegram_user_id": 123456},
            ).scalar_one()
            attribution_count = connection.execute(
                text("SELECT COUNT(*) FROM user_acquisition_attributions")
            ).scalar_one()
        assert migrated == 1
        assert attribution_count == 0
    finally:
        engine.dispose()
