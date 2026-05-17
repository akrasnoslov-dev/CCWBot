from bot.config import AUTOMATIC_CHECK_INTERVAL_SECONDS
from bot.db.database import get_or_create_app_settings, update_app_settings
from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL
from bot.storage import load_state, save_state

DEFAULT_BTC_ALERT_THRESHOLD_PERCENT = 2.0
DEFAULT_AUTOMATIC_CHECK_INTERVAL_SECONDS = 300
DEFAULT_MAJOR_MOVEMENT_THRESHOLD_PERCENT = 1.0
DEFAULT_ALT_MOVEMENT_THRESHOLD_PERCENT = 2.0
DEFAULT_MAJOR_24H_MEDIUM_THRESHOLD_PERCENT = 3.0
DEFAULT_MAJOR_24H_HIGH_THRESHOLD_PERCENT = 5.0
DEFAULT_ALT_24H_MEDIUM_THRESHOLD_PERCENT = 5.0
DEFAULT_ALT_24H_HIGH_THRESHOLD_PERCENT = 8.0


def _threshold_defaults() -> dict:
    return {
        "major_movement_threshold_percent": DEFAULT_MAJOR_MOVEMENT_THRESHOLD_PERCENT,
        "alt_movement_threshold_percent": DEFAULT_ALT_MOVEMENT_THRESHOLD_PERCENT,
        "major_24h_medium_threshold_percent": DEFAULT_MAJOR_24H_MEDIUM_THRESHOLD_PERCENT,
        "major_24h_high_threshold_percent": DEFAULT_MAJOR_24H_HIGH_THRESHOLD_PERCENT,
        "alt_24h_medium_threshold_percent": DEFAULT_ALT_24H_MEDIUM_THRESHOLD_PERCENT,
        "alt_24h_high_threshold_percent": DEFAULT_ALT_24H_HIGH_THRESHOLD_PERCENT,
    }


def get_state_alert_settings(state: dict) -> dict:
    settings = {
        "price_move_alert_percent": float(
            state.get(
                "btc_alert_threshold_percent",
                state.get("price_move_alert_percent", DEFAULT_MAJOR_MOVEMENT_THRESHOLD_PERCENT),
            )
        ),
        "automatic_check_interval_seconds": int(
            state.get("automatic_check_interval_seconds", AUTOMATIC_CHECK_INTERVAL_SECONDS)
        ),
    }
    for key, default in _threshold_defaults().items():
        settings[key] = float(state.get(key, default))
    return settings


def get_state_error_file_logging_enabled(state: dict) -> bool:
    return bool(state.get("error_file_logging_enabled", False))


async def get_db_alert_settings() -> dict:
    async with DB_SESSION_LOCAL() as session:
        settings = await get_or_create_app_settings(
            session,
            default_threshold=DEFAULT_BTC_ALERT_THRESHOLD_PERCENT,
            default_interval=DEFAULT_AUTOMATIC_CHECK_INTERVAL_SECONDS,
        )
    return {
        "price_move_alert_percent": settings["btc_alert_threshold_percent"],
        "automatic_check_interval_seconds": settings["automatic_check_interval_seconds"],
        **{key: settings[key] for key in _threshold_defaults()},
    }


async def get_db_error_file_logging_enabled() -> bool:
    async with DB_SESSION_LOCAL() as session:
        settings = await get_or_create_app_settings(
            session,
            default_threshold=DEFAULT_BTC_ALERT_THRESHOLD_PERCENT,
            default_interval=DEFAULT_AUTOMATIC_CHECK_INTERVAL_SECONDS,
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
                default_threshold=DEFAULT_BTC_ALERT_THRESHOLD_PERCENT,
                default_interval=DEFAULT_AUTOMATIC_CHECK_INTERVAL_SECONDS,
            )
        return

    state = load_state()
    state["error_file_logging_enabled"] = enabled
    save_state(state)


async def save_threshold_setting(threshold: float) -> None:
    if DB_ENABLED and DB_SESSION_LOCAL:
        async with DB_SESSION_LOCAL() as session:
            await update_app_settings(
                session,
                threshold=threshold,
                default_threshold=DEFAULT_BTC_ALERT_THRESHOLD_PERCENT,
                default_interval=DEFAULT_AUTOMATIC_CHECK_INTERVAL_SECONDS,
            )
        return

    state = load_state()
    state["btc_alert_threshold_percent"] = threshold
    save_state(state)


async def save_alert_threshold_setting(key: str, value: float) -> None:
    if key not in _threshold_defaults():
        raise ValueError("Unsupported threshold setting.")
    if DB_ENABLED and DB_SESSION_LOCAL:
        async with DB_SESSION_LOCAL() as session:
            await update_app_settings(
                session,
                threshold_updates={key: value},
                default_threshold=DEFAULT_BTC_ALERT_THRESHOLD_PERCENT,
                default_interval=DEFAULT_AUTOMATIC_CHECK_INTERVAL_SECONDS,
            )
        return

    state = load_state()
    state[key] = value
    save_state(state)


async def save_interval_setting(interval: int) -> None:
    if DB_ENABLED and DB_SESSION_LOCAL:
        async with DB_SESSION_LOCAL() as session:
            await update_app_settings(
                session,
                interval_seconds=interval,
                default_threshold=DEFAULT_BTC_ALERT_THRESHOLD_PERCENT,
                default_interval=DEFAULT_AUTOMATIC_CHECK_INTERVAL_SECONDS,
            )
        return

    state = load_state()
    state["automatic_check_interval_seconds"] = interval
    save_state(state)
