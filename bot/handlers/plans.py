"""Plan, subscription, and watchlist command handlers."""

from telegram import Update
from telegram.ext import ContextTypes

from bot.keyboards import build_plan_keyboard

from .common import handlers_module, log_request


@log_request("/plan")
async def plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Plan & subscription", reply_markup=build_plan_keyboard())


@log_request("/watchlist")
async def watchlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handlers_module().watchlist_command(update)


@log_request("/myplan")
async def myplan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handlers_module().myplan_command(update)


@log_request("/subscribe")
async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handlers_module().send_subscribe_invoice(update, context)
