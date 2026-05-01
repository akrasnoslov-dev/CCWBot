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
    if value < minimum:
        return default
    return value

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

_admin_user_id_raw = os.getenv("TELEGRAM_ADMIN_USER_ID")
if _admin_user_id_raw and _admin_user_id_raw.strip():
    _admin_user_id_raw = _admin_user_id_raw.strip()
    TELEGRAM_ADMIN_USER_ID = (
        int(_admin_user_id_raw)
        if _admin_user_id_raw.lstrip("-").isdigit()
        else _admin_user_id_raw
    )
else:
    TELEGRAM_ADMIN_USER_ID = None

PRICE_MOVE_ALERT_PERCENT = float(os.getenv("PRICE_MOVE_ALERT_PERCENT", "0.01"))
ALERT_COOLDOWN_MINUTES = _get_int_env("ALERT_COOLDOWN_MINUTES", 2, minimum=0)
# Legacy setting kept for backward compatibility. Not used by MVP alert logic.
PRICE_CACHE_TTL_SECONDS = _get_int_env("PRICE_CACHE_TTL_SECONDS", 300, minimum=1)
AUTOMATIC_CHECK_INTERVAL_SECONDS = _get_int_env("AUTOMATIC_CHECK_INTERVAL_SECONDS", 300, minimum=1)
