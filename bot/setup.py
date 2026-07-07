import logging

from telegram import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeChat
from telegram.ext import Application

from bot.config import TELEGRAM_ADMIN_USER_IDS
from bot.runtime import log

logger = logging.getLogger(__name__)


async def setup_bot_commands(app: Application) -> None:
    default_commands = [
        BotCommand("start", "Main bot menu"),
        BotCommand("price", "Check crypto prices"),
        BotCommand("settings", "Alert settings / watchlist"),
        BotCommand("reports", "Reports"),
        BotCommand("plan", "Plan & subscription"),
    ]
    await app.bot.set_my_commands(default_commands, scope=BotCommandScopeAllPrivateChats())

    if TELEGRAM_ADMIN_USER_IDS:
        admin_commands = default_commands + [
            BotCommand("admin", "Open admin menu"),
        ]
        for admin_chat_id in TELEGRAM_ADMIN_USER_IDS:
            await app.bot.set_my_commands(
                admin_commands, scope=BotCommandScopeChat(chat_id=admin_chat_id)
            )
    else:
        log("No numeric Telegram admin IDs configured. Skipping admin command scope setup.")

    logger.debug("Telegram command menu configured.")
