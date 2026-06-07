"""Market report command handlers."""

from telegram import Update
from telegram.ext import ContextTypes

from bot.keyboards import build_reports_keyboard
from bot.reports import send_daily_report_message, send_weekly_report_message

from .common import log_request


@log_request("/dailyreport")
async def daily_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_daily_report_message(update.message)


@log_request("/weeklyreport")
async def weekly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_weekly_report_message(update.message)


@log_request("/reports")
async def reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Reports menu 📊", reply_markup=build_reports_keyboard())
