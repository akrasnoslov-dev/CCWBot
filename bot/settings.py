from bot.config import AUTOMATIC_CHECK_INTERVAL_SECONDS
from bot.db.database import get_or_create_app_settings, update_app_settings
from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL
from bot.storage import load_state, save_state

DEFAULT_AUTOMATIC_CHECK_INTERVAL_SECONDS = 1800
AUTOMATIC_CHECK_SCHEDULER_GRACE_SECONDS = 120


def normalize_automatic_check_interval_seconds(interval_seconds: int | None) -> int:
    _ = interval_seconds
    return DEFAULT_AUTOMATIC_CHECK_INTERVAL_SECONDS


def get_state_alert_settings(state: dict) -> dict:
    return {
        "automatic_check_interval_seconds": normalize_automatic_check_interval_seconds(
            state.get("automatic_check_interval_seconds", AUTOMATIC_CHECK_INTERVAL_SECONDS)
        ),
    }


def get_state_error_file_logging_enabled(state: dict) -> bool:
    return bool(state.get("error_file_logging_enabled", False))


async def get_db_alert_settings() -> dict:
    async with DB_SESSION_LOCAL() as session:
        settings = await get_or_create_app_settings(
            session, default_interval=DEFAULT_AUTOMATIC_CHECK_INTERVAL_SECONDS
        )
    return {
        "automatic_check_interval_seconds": normalize_automatic_check_interval_seconds(
            settings["automatic_check_interval_seconds"]
        ),
    }


async def get_db_error_file_logging_enabled() -> bool:
    async with DB_SESSION_LOCAL() as session:
        settings = await get_or_create_app_settings(
            session, default_interval=DEFAULT_AUTOMATIC_CHECK_INTERVAL_SECONDS
        )
    return bool(settings["error_file_logging_enabled"])


async def get_runtime_alert_settings() -> dict:
    if DB_ENABLED and DB_SESSION_LOCAL:
        return await get_db_alert_settings()
    return get_state_alert_settings(load_state())


async def get_runtime_error_file_logging_enabled() -> bool:
    if DB_ENABLED and DB_SESSION_LOCAL:
        return await get_db_error_file_logging_enabled()
    return get_state_error_file_logging_enabled(load_state())


async def save_error_file_logging_enabled(enabled: bool) -> None:
    if DB_ENABLED and DB_SESSION_LOCAL:
        async with DB_SESSION_LOCAL() as session:
            await update_app_settings(
                session,
                error_file_logging_enabled=enabled,
                default_interval=DEFAULT_AUTOMATIC_CHECK_INTERVAL_SECONDS,
            )
        return

    state = load_state()
    state["error_file_logging_enabled"] = enabled
    save_state(state)


async def save_interval_setting(interval: int) -> None:
    interval = normalize_automatic_check_interval_seconds(interval)
    if DB_ENABLED and DB_SESSION_LOCAL:
        async with DB_SESSION_LOCAL() as session:
            await update_app_settings(
                session,
                interval_seconds=interval,
                default_interval=DEFAULT_AUTOMATIC_CHECK_INTERVAL_SECONDS,
            )
        return

    state = load_state()
    state["automatic_check_interval_seconds"] = interval
    save_state(state)
