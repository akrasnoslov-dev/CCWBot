from telegram.ext import Application

from bot.config import TELEGRAM_BOT_TOKEN
from bot.handlers.registration import register_bot_handlers


def build_application() -> Application:
    return Application.builder().token(TELEGRAM_BOT_TOKEN).build()


def register_handlers(app: Application) -> None:
    register_bot_handlers(app)
