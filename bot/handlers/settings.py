"""User settings command handler."""

from telegram import Update
from telegram.ext import ContextTypes

from .common import handlers_module, log_request


@log_request("/settings")
async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handlers_module().settings_command(update)
