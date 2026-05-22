import logging

from telegram import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeChat
from telegram.ext import Application

from bot.config import TELEGRAM_ADMIN_USER_ID
from bot.runtime import log

logger = logging.getLogger(__name__)


async def setup_bot_commands(app: Application) -> None:
    default_commands = [
        BotCommand("start", "Open bot menu"),
        BotCommand("price", "Check crypto prices"),
        BotCommand("settings", "Manage alert settings"),
        BotCommand("reports", "Open market reports"),
        BotCommand("myplan", "Show subscription plan"),
        BotCommand("subscribe", "Subscribe with Telegram Stars"),
        BotCommand("status", "Show bot status"),
    ]
    await app.bot.set_my_commands(default_commands, scope=BotCommandScopeAllPrivateChats())

    if TELEGRAM_ADMIN_USER_ID:
        admin_commands = default_commands + [
            BotCommand("admin", "Open admin menu"),
        ]
        try:
            admin_chat_id = int(TELEGRAM_ADMIN_USER_ID)
            await app.bot.set_my_commands(
                admin_commands, scope=BotCommandScopeChat(chat_id=admin_chat_id)
            )
        except (TypeError, ValueError):
            log(
                "TELEGRAM_ADMIN_USER_ID is not a numeric ID. "
                "Skipping admin-only command scope setup."
            )

    logger.debug("Telegram command menu configured.")
