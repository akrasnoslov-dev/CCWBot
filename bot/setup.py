import logging

from telegram import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeChat
from telegram.ext import Application

from bot.config import TELEGRAM_ADMIN_USER_ID
from bot.runtime import log

logger = logging.getLogger(__name__)


async def setup_bot_commands(app: Application) -> None:
    default_commands = [
        BotCommand("start", "Show bot intro"),
        BotCommand("price", "Check crypto prices"),
        BotCommand("watchlist", "Manage alert watchlist"),
        BotCommand("settings", "Manage your alert settings"),
        BotCommand("myplan", "Show your plan"),
        BotCommand("subscribe", "Subscribe with Telegram Stars"),
        BotCommand("reports", "Open BTC reports menu"),
    ]
    await app.bot.set_my_commands(default_commands, scope=BotCommandScopeAllPrivateChats())

    if TELEGRAM_ADMIN_USER_ID:
        admin_commands = default_commands + [
            BotCommand("admin", "Open admin menu"),
            BotCommand("status", "Show bot status"),
            BotCommand("grantpremium", "Grant Premium manually"),
            BotCommand("revokepremium", "Revoke Premium manually"),
            BotCommand("error_logging_on", "Enable warning/error file logging"),
            BotCommand("error_logging_off", "Disable warning/error file logging"),
            BotCommand("error_logging_status", "Show warning/error logging status"),
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
