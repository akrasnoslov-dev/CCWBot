import os

from dotenv import load_dotenv


load_dotenv()

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
ALERT_COOLDOWN_MINUTES = int(os.getenv("ALERT_COOLDOWN_MINUTES", "2"))
