from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL
from config import AUTOMATIC_CHECK_INTERVAL_SECONDS, PRICE_MOVE_ALERT_PERCENT
from database import get_or_create_app_settings, update_app_settings
from storage import load_state, save_state

DEFAULT_BTC_ALERT_THRESHOLD_PERCENT = 2.0
DEFAULT_AUTOMATIC_CHECK_INTERVAL_SECONDS = 300


def get_state_alert_settings(state: dict) -> dict:
    return {
        "price_move_alert_percent": float(
            state.get(
                "btc_alert_threshold_percent",
                state.get("price_move_alert_percent", PRICE_MOVE_ALERT_PERCENT),
            )
        ),
        "automatic_check_interval_seconds": int(
            state.get("automatic_check_interval_seconds", AUTOMATIC_CHECK_INTERVAL_SECONDS)
        ),
    }


def get_db_alert_settings() -> dict:
    with DB_SESSION_LOCAL() as session:
        settings = get_or_create_app_settings(
            session,
            default_threshold=DEFAULT_BTC_ALERT_THRESHOLD_PERCENT,
            default_interval=DEFAULT_AUTOMATIC_CHECK_INTERVAL_SECONDS,
        )
    return {
        "price_move_alert_percent": settings["btc_alert_threshold_percent"],
        "automatic_check_interval_seconds": settings["automatic_check_interval_seconds"],
    }


def get_runtime_alert_settings() -> dict:
    if DB_ENABLED and DB_SESSION_LOCAL:
        return get_db_alert_settings()
    return get_state_alert_settings(load_state())


def save_threshold_setting(threshold: float) -> None:
    if DB_ENABLED and DB_SESSION_LOCAL:
        with DB_SESSION_LOCAL() as session:
            update_app_settings(
                session,
                threshold=threshold,
                default_threshold=DEFAULT_BTC_ALERT_THRESHOLD_PERCENT,
                default_interval=DEFAULT_AUTOMATIC_CHECK_INTERVAL_SECONDS,
            )
        return

    state = load_state()
    state["btc_alert_threshold_percent"] = threshold
    save_state(state)


def save_interval_setting(interval: int) -> None:
    if DB_ENABLED and DB_SESSION_LOCAL:
        with DB_SESSION_LOCAL() as session:
            update_app_settings(
                session,
                interval_seconds=interval,
                default_threshold=DEFAULT_BTC_ALERT_THRESHOLD_PERCENT,
                default_interval=DEFAULT_AUTOMATIC_CHECK_INTERVAL_SECONDS,
            )
        return

    state = load_state()
    state["automatic_check_interval_seconds"] = interval
    save_state(state)
