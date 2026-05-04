"""Centralized configuration loaded from environment variables.

Notes about key IDs:
- TELEGRAM_CHAT_ID: destination chat for automatic bot alerts/jobs.
- TELEGRAM_ADMIN_USER_ID: Telegram user allowed to run admin-only commands.
"""

import os

from dotenv import load_dotenv

load_dotenv()


def _get_int_env(name: str, default: int, minimum: int = 0) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value >= minimum else default


def _get_float_env(name: str, default: float, minimum: float | None = None) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    if minimum is not None and value < minimum:
        return default
    return value


def _get_bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# Chat ID that receives automatic BTC alerts and scheduled reports.
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

_admin_user_id_raw = os.getenv("TELEGRAM_ADMIN_USER_ID")
if _admin_user_id_raw and _admin_user_id_raw.strip():
    _admin_user_id_raw = _admin_user_id_raw.strip()
    # User ID allowed to run admin-only commands (/settings, /status, etc.).
    TELEGRAM_ADMIN_USER_ID = (
        int(_admin_user_id_raw)
        if _admin_user_id_raw.lstrip("-").isdigit()
        else _admin_user_id_raw
    )
else:
    TELEGRAM_ADMIN_USER_ID = None

# Movement threshold (in percentage points) required to send an automatic BTC alert.
PRICE_MOVE_ALERT_PERCENT = _get_float_env("PRICE_MOVE_ALERT_PERCENT", 2, minimum=0)
ALERT_COOLDOWN_MINUTES = _get_int_env("ALERT_COOLDOWN_MINUTES", 2, minimum=0)

# In-memory CoinGecko cache TTL to reduce API calls and reduce 429 risk.
PRICE_CACHE_TTL_SECONDS = _get_int_env("PRICE_CACHE_TTL_SECONDS", 300, minimum=1)
# Automatic BTC check cadence in seconds.
AUTOMATIC_CHECK_INTERVAL_SECONDS = _get_int_env(
    "AUTOMATIC_CHECK_INTERVAL_SECONDS", 300, minimum=1
)

ENABLE_WEEKLY_REPORT = _get_bool_env("ENABLE_WEEKLY_REPORT", default=False)
WEEKLY_REPORT_DAY = os.getenv("WEEKLY_REPORT_DAY", "sunday").strip().lower()
WEEKLY_REPORT_HOUR = _get_int_env("WEEKLY_REPORT_HOUR", 9, minimum=0)
if WEEKLY_REPORT_HOUR > 23:
    WEEKLY_REPORT_HOUR = 9

ENABLE_STRONG_SIGNAL_ALERTS = _get_bool_env(
    "ENABLE_STRONG_SIGNAL_ALERTS", default=False
)
STRONG_SIGNAL_CHECK_INTERVAL_SECONDS = _get_int_env(
    "STRONG_SIGNAL_CHECK_INTERVAL_SECONDS", 1800, minimum=60
)
STRONG_SIGNAL_COOLDOWN_HOURS = _get_int_env(
    "STRONG_SIGNAL_COOLDOWN_HOURS", 6, minimum=1
)


# Optional PostgreSQL connection string. If missing, JSON state remains active.
DATABASE_URL = os.getenv("DATABASE_URL")
