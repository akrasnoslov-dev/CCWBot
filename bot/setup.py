from telegram import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeChat
from telegram.ext import Application

from bot.runtime import log
from config import TELEGRAM_ADMIN_USER_ID


async def setup_bot_commands(app: Application) -> None:
    default_commands = [
        BotCommand("start", "Show bot intro"),
        BotCommand("price", "Check crypto prices"),
        BotCommand("reports", "Open BTC reports menu"),
    ]
    await app.bot.set_my_commands(default_commands, scope=BotCommandScopeAllPrivateChats())

    if TELEGRAM_ADMIN_USER_ID:
        admin_commands = default_commands + [
            BotCommand("settings", "Open settings menu"),
            BotCommand("status", "Show bot status"),
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

    log("Telegram command menu has been updated.")
