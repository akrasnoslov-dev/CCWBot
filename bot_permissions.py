from config import TELEGRAM_ADMIN_USER_ID
from database import get_or_create_user, get_user_role
from telegram import Update

from bot_runtime import DB_ENABLED, DB_SESSION_LOCAL


def is_admin_user(user_id: int | str | None) -> bool:
    if user_id is None or TELEGRAM_ADMIN_USER_ID is None:
        return False
    if DB_ENABLED and DB_SESSION_LOCAL:
        with DB_SESSION_LOCAL() as session:
            return get_user_role(session, int(user_id)) == "admin"
    return str(user_id) == str(TELEGRAM_ADMIN_USER_ID)


def is_admin_update(update: Update) -> bool:
    return is_admin_user(update.effective_user.id if update.effective_user else None)


def sync_user_from_update(update: Update) -> None:
    if not (DB_ENABLED and DB_SESSION_LOCAL):
        return
    if not update.effective_user or not update.effective_chat:
        return
    with DB_SESSION_LOCAL() as session:
        get_or_create_user(
            session,
            telegram_user_id=update.effective_user.id,
            telegram_chat_id=update.effective_chat.id,
            username=update.effective_user.username,
            first_name=update.effective_user.first_name,
            admin_user_id=TELEGRAM_ADMIN_USER_ID,
        )
