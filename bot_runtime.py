from datetime import datetime, timezone

from config import DATABASE_URL
from database import init_db, telegram_id_columns_are_bigint


def log(message: str) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{timestamp}] {message}")


# Optional DB bootstrap: PostgreSQL stores runtime state when configured.
DB_ENABLED = bool(DATABASE_URL)
DB_SESSION_LOCAL = None

if DB_ENABLED:
    log("Database configured. Using PostgreSQL state.")
    _, DB_SESSION_LOCAL = init_db(DATABASE_URL)
    if telegram_id_columns_are_bigint():
        log("Telegram ID columns are configured as PostgreSQL BIGINT.")
    else:
        log("Warning: Telegram ID columns are not all configured as PostgreSQL BIGINT.")
else:
    log("DATABASE_URL is not configured. Using local JSON state.")
