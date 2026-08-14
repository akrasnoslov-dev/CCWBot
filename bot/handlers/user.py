"""General user command handlers."""

from telegram import Update
from telegram.ext import ContextTypes

from .common import handlers_module, log_request


@log_request("/start")
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_admin = await handlers_module().is_admin_update(update)
    message = (
        "CCWBot\n\n"
        "I monitor crypto prices and alert settings.\n\n"
        "Use:\n"
        "/price - check crypto prices"
        "\n/watchlist - manage alert watchlist"
        "\n/reports - open market reports"
        "\n/plan - plan and subscription"
    )
    if is_admin:
        message += "\n/admin - open admin menu"
    await update.message.reply_text(message)


@log_request("/userid")
async def user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_value = update.effective_user.id if update.effective_user else "unknown"
    await update.message.reply_text(f"Your Telegram user ID is: {user_id_value}")
