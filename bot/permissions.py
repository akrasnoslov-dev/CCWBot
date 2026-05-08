from telegram import Update

from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL
from config import TELEGRAM_ADMIN_USER_ID, parse_telegram_user_id
from database import get_or_create_user, get_user_role


async def is_admin_user(user_id: int | str | None) -> bool:
    if user_id is None or TELEGRAM_ADMIN_USER_ID is None:
        return False
    if DB_ENABLED and DB_SESSION_LOCAL:
        async with DB_SESSION_LOCAL() as session:
            return await get_user_role(session, int(user_id)) == "admin"
    return parse_telegram_user_id(user_id) == parse_telegram_user_id(TELEGRAM_ADMIN_USER_ID)


async def is_admin_update(update: Update) -> bool:
    return await is_admin_user(update.effective_user.id if update.effective_user else None)


async def sync_user_from_update(update: Update) -> None:
    if not (DB_ENABLED and DB_SESSION_LOCAL):
        return
    if not update.effective_user or not update.effective_chat:
        return
    async with DB_SESSION_LOCAL() as session:
        await get_or_create_user(
            session,
            telegram_user_id=update.effective_user.id,
            telegram_chat_id=update.effective_chat.id,
            username=update.effective_user.username,
            first_name=update.effective_user.first_name,
            admin_user_id=TELEGRAM_ADMIN_USER_ID,
        )
