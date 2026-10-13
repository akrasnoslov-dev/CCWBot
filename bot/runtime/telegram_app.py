from telegram.ext import Application

from bot.config import TELEGRAM_BOT_TOKEN
from bot.handlers.registration import register_bot_handlers
from bot.handlers.transient import TransientBot


def build_application() -> Application:
    return Application.builder().bot(TransientBot(token=TELEGRAM_BOT_TOKEN)).build()


def register_handlers(app: Application) -> None:
    register_bot_handlers(app)
