"""User settings command handler."""

from telegram import Update
from telegram.ext import ContextTypes

from bot.keyboards import build_admin_alert_settings_keyboard
from bot.settings import get_db_alert_settings, get_state_alert_settings
from bot.storage import load_state

from .admin import _format_admin_alert_settings
from .common import _mark_denied, handlers_module, log_request


@log_request("/settings")
async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await handlers_module().is_admin_update(update):
        _mark_denied(context)
        await update.message.reply_text(
            "Sorry, only the bot admin can access global settings. Use /watchlist for your alerts."
        )
        return
    root = handlers_module()
    alert_settings = (
        await get_db_alert_settings()
        if root.DB_ENABLED and root.DB_SESSION_LOCAL
        else get_state_alert_settings(load_state())
    )
    await update.message.reply_text(
        _format_admin_alert_settings(alert_settings),
        reply_markup=build_admin_alert_settings_keyboard(),
    )
