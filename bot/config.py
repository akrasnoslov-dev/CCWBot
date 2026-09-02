"""Centralized configuration loaded from environment variables.

Notes about key IDs:
- TELEGRAM_CHAT_ID: fallback destination chat for automatic bot alerts when database storage is off.
- TELEGRAM_ADMIN_USER_ID / TELEGRAM_ADMIN_USER_IDS: Telegram users allowed to run
  admin-only commands.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _get_environment() -> str:
    value = os.getenv("ENVIRONMENT", "development").strip().lower()
    if value in {"development", "production"}:
        return value
    return "custom" if value else "development"


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


def parse_telegram_user_id(value: int | str | None) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(str(value).strip())
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def parse_telegram_user_ids(value: int | str | None) -> tuple[int, ...]:
    if value is None:
        return ()
    ids: list[int] = []
    for item in str(value).split(","):
        parsed = parse_telegram_user_id(item)
        if parsed is not None:
            ids.append(parsed)
    return tuple(ids)


def combine_telegram_admin_user_ids(
    single_admin_user_id: int | str | None,
    admin_user_ids: int | str | None,
) -> tuple[int, ...]:
    combined: list[int] = []
    for parsed in (
        parse_telegram_user_id(single_admin_user_id),
        *parse_telegram_user_ids(admin_user_ids),
    ):
        if parsed is not None and parsed not in combined:
            combined.append(parsed)
    return tuple(combined)


ENVIRONMENT = _get_environment()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# Public bot username, without the @ prefix, used to build operator-facing deep links.
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "").strip()
# Fallback chat ID for automatic BTC alerts when database storage is off.
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# User ID allowed to run admin-only commands (/settings, /admin, etc.).
TELEGRAM_ADMIN_USER_ID = parse_telegram_user_id(os.getenv("TELEGRAM_ADMIN_USER_ID"))
TELEGRAM_ADMIN_USER_IDS = combine_telegram_admin_user_ids(
    TELEGRAM_ADMIN_USER_ID,
    os.getenv("TELEGRAM_ADMIN_USER_IDS"),
)

ALERT_COOLDOWN_MINUTES = _get_int_env("ALERT_COOLDOWN_MINUTES", 30, minimum=0)
EVENT_ALERT_SEMANTIC_COOLDOWN_SECONDS = _get_int_env(
    "EVENT_ALERT_SEMANTIC_COOLDOWN_SECONDS", 4 * 60 * 60, minimum=0
)
SEEN_NEWS_KEEP_LATEST = _get_int_env("SEEN_NEWS_KEEP_LATEST", 500, minimum=1)

# Budget-aware RSS news intelligence. Persistent cache must be checked before LLM calls.
ENABLE_NEWS_INTELLIGENCE = _get_bool_env("ENABLE_NEWS_INTELLIGENCE", True)
ENABLE_NEWS_DRIVEN_ALERTS = _get_bool_env("ENABLE_NEWS_DRIVEN_ALERTS", False)
NEWS_INTELLIGENCE_MAX_ITEMS_PER_RUN = _get_int_env(
    "NEWS_INTELLIGENCE_MAX_ITEMS_PER_RUN", 5, minimum=0
)
NEWS_INTELLIGENCE_MAX_LLM_CALLS_PER_RUN = _get_int_env(
    "NEWS_INTELLIGENCE_MAX_LLM_CALLS_PER_RUN", 3, minimum=0
)
NEWS_INTELLIGENCE_MAX_LLM_CALLS_PER_HOUR = _get_int_env(
    "NEWS_INTELLIGENCE_MAX_LLM_CALLS_PER_HOUR", 20, minimum=0
)
NEWS_LLM_TIMEOUT_SECONDS = _get_int_env("NEWS_LLM_TIMEOUT_SECONDS", 20, minimum=1)

# In-memory CoinGecko cache TTL to reduce API calls and reduce 429 risk.
PRICE_CACHE_TTL_SECONDS = _get_int_env("PRICE_CACHE_TTL_SECONDS", 300, minimum=1)
# Event Alert LLM analysis cadence in seconds.
AUTOMATIC_CHECK_INTERVAL_SECONDS = _get_int_env("AUTOMATIC_CHECK_INTERVAL_SECONDS", 1800, minimum=1)
# Lightweight HTTP health endpoint port.
HEALTH_PORT = _get_int_env("HEALTH_PORT", 8080, minimum=1)

# Optional PostgreSQL connection string. If missing, JSON state remains active.
DATABASE_URL = os.getenv("DATABASE_URL")

# Telegram Stars price for monthly Premium subscriptions.
PREMIUM_MONTHLY_STARS = _get_int_env("PREMIUM_MONTHLY_STARS", 199, minimum=1)

# Optional warning/error file logging target. Runtime toggle is stored separately.
ERROR_LOG_FILE = Path(os.getenv("ERROR_LOG_FILE", "logs/ccwbot-warnings-errors.log"))
