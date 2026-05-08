import time

from telegram import Update
from telegram.ext import ContextTypes

from bot.alerts import schedule_automatic_btc_check
from bot.keyboards import (
    build_interval_keyboard,
    build_price_keyboard,
    build_reports_keyboard,
    build_settings_keyboard,
    build_threshold_keyboard,
)
from bot.permissions import is_admin_update, is_admin_user, sync_user_from_update
from bot.prices import (
    build_supported_symbols_message,
    send_manual_rate_limit_message,
    send_price_message,
)
from bot.reports import send_daily_report_message, send_weekly_report_message
from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL, log
from bot.settings import (
    get_db_alert_settings,
    get_state_alert_settings,
    save_interval_setting,
    save_threshold_setting,
)
from database import get_price_state
from price_service import COIN_SYMBOL_TO_ID, DEFAULT_SYMBOL, CoinGeckoRateLimitError
from storage import load_state

PRICE_RATE_LIMIT_SECONDS = 10
_user_last_price_call: dict[int, float] = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sync_user_from_update(update)
    is_admin = is_admin_update(update)
    message = (
        "Hi! I’m CCWBot 🚀\n\n"
        "I monitor crypto prices and send automatic BTC alerts.\n\n"
        "Use:\n"
        "/price - check crypto prices"
        "\n/reports - BTC reports menu"
    )
    if is_admin:
        message += "\n/settings - open settings menu\n/status - show bot status"
    await update.message.reply_text(message)


async def user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sync_user_from_update(update)
    user_id_value = update.effective_user.id if update.effective_user else "unknown"
    await update.message.reply_text(f"Your Telegram user ID is: {user_id_value}")


async def daily_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sync_user_from_update(update)
    await send_daily_report_message(update.message)


async def weekly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sync_user_from_update(update)
    await send_weekly_report_message(update.message)


async def reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sync_user_from_update(update)
    await update.message.reply_text("Reports menu 📊", reply_markup=build_reports_keyboard())


async def chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sync_user_from_update(update)
    if not is_admin_update(update):
        await update.message.reply_text("Sorry, only the bot admin can view chat ID.")
        return
    await update.message.reply_text(f"Your chat ID is: {update.effective_chat.id}")


async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sync_user_from_update(update)
    if not is_admin_update(update):
        await update.message.reply_text("Sorry, only the bot admin can access settings.")
        return
    await update.message.reply_text("Settings menu ⚙️", reply_markup=build_settings_keyboard())


async def set_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sync_user_from_update(update)
    if not is_admin_update(update):
        await update.message.reply_text("Sorry, only the bot admin can change settings.")
        return
    if not context.args:
        await update.message.reply_text(
            "Please provide a threshold value.\n\nExample:\n/setthreshold 1.0"
        )
        return
    try:
        threshold = float(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "Threshold must be a number.\n\nExample:\n/setthreshold 1.0"
        )
        return
    if threshold <= 0:
        await update.message.reply_text("Threshold must be greater than 0.")
        return

    save_threshold_setting(threshold)
    await update.message.reply_text(f"Price movement threshold updated to {threshold}% ✅")


async def set_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sync_user_from_update(update)
    if not is_admin_update(update):
        await update.message.reply_text("Sorry, only the bot admin can change settings.")
        return
    if not context.args:
        await update.message.reply_text(
            "Please provide interval in seconds.\n\nExample:\n/setinterval 300"
        )
        return
    try:
        interval = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "Interval must be a whole number.\n\nExample:\n/setinterval 300"
        )
        return
    if interval <= 0:
        await update.message.reply_text("Interval must be greater than 0.")
        return

    save_interval_setting(interval)
    schedule_automatic_btc_check(context.application, interval)
    await update.message.reply_text(
        f"Automatic BTC check interval updated to {interval} seconds ✅ Applied immediately."
    )


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sync_user_from_update(update)
    try:
        user_id_value = update.effective_user.id if update.effective_user else None
        now = time.monotonic()
        if user_id_value is not None:
            last_call_at = _user_last_price_call.get(user_id_value)
            if last_call_at is not None and now - last_call_at < PRICE_RATE_LIMIT_SECONDS:
                await update.message.reply_text(
                    "⏳ Please wait a few seconds before requesting again."
                )
                return
            _user_last_price_call[user_id_value] = now

        if not context.args:
            await update.message.reply_text(
                "Choose a coin symbol:", reply_markup=build_price_keyboard()
            )
            return
        requested_symbol = context.args[0].lower()
        if requested_symbol not in COIN_SYMBOL_TO_ID:
            supported_symbols = build_supported_symbols_message()
            await update.message.reply_text(
                f"Unsupported symbol '{requested_symbol}'.\nSupported symbols: {supported_symbols}"
            )
            return
        await send_price_message(update.message, requested_symbol)
    except CoinGeckoRateLimitError:
        await send_manual_rate_limit_message(
            update.message, update.effective_chat.id if update.effective_chat else None
        )
    except ValueError as error:
        await update.message.reply_text(f"Price data is temporarily unavailable: {error}")
    except Exception as error:
        await update.message.reply_text("Sorry, I could not get the price right now.")
        log(f"Price error: {error}")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sync_user_from_update(update)
    if not is_admin_update(update):
        await update.message.reply_text("Sorry, only the bot admin can view status.")
        return
    if DB_ENABLED and DB_SESSION_LOCAL:
        with DB_SESSION_LOCAL() as session:
            btc_state = get_price_state(session, DEFAULT_SYMBOL)
        if btc_state is None:
            await update.message.reply_text(
                "Status: running ✅\n\nNo BTC price has been saved yet."
            )
            return
        await update.message.reply_text(
            "Status: running ✅\n\n"
            f"Last saved BTC price: ${btc_state.last_price:,.2f}\n"
            f"Last 24h change: {btc_state.last_24h_change:.2f}%\n"
            f"Last checked at: {btc_state.last_checked_at}\n"
            f"Last alert at: {btc_state.last_alert_at}"
        )
        return
    state = load_state()
    last_price = state.get("last_price")
    if last_price is None:
        await update.message.reply_text(
            "Status: running ✅\n\nNo BTC price has been saved yet.\nSend /price first."
        )
        return
    await update.message.reply_text(
        "Status: running ✅\n\n"
        f"Last saved BTC price: ${last_price:,.2f}\n"
        f"Last 24h change: {state.get('last_24h_change'):.2f}%\n"
        f"Last checked at: {state.get('last_checked_at')}\n"
        f"Last alert at: {state.get('last_alert_at')}"
    )


async def button_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data or ""
    sync_user_from_update(update)

    try:
        if data.startswith("settings:") and not is_admin_user(
            query.from_user.id if query.from_user else None
        ):
            await query.answer("Sorry, only the bot admin can change settings.")
            await query.message.reply_text("Sorry, only the bot admin can change settings.")
            return

        await query.answer()

        if data.startswith("price:"):
            await send_price_message(query.message, data.split(":", maxsplit=1)[1])
            return
        if data == "reports:daily":
            await send_daily_report_message(query.message)
            return
        if data == "reports:weekly":
            await send_weekly_report_message(query.message)
            return
        if data == "settings:current":
            if DB_ENABLED and DB_SESSION_LOCAL:
                alert_settings = get_db_alert_settings()
            else:
                state = load_state()
                alert_settings = get_state_alert_settings(state)
            await query.message.reply_text(
                "Current alert settings ⚙️\n\n"
                f"Price movement threshold: {alert_settings['price_move_alert_percent']}%\n"
                "Automatic BTC check interval: "
                f"{alert_settings['automatic_check_interval_seconds']} seconds"
            )
            return
        if data == "settings:threshold_menu":
            await query.message.reply_text(
                "Choose a new threshold:", reply_markup=build_threshold_keyboard()
            )
            return
        if data == "settings:interval_menu":
            await query.message.reply_text(
                "Choose a new check interval:", reply_markup=build_interval_keyboard()
            )
            return
        if data.startswith("settings:set_threshold:"):
            threshold = float(data.rsplit(":", maxsplit=1)[1])
            save_threshold_setting(threshold)
            await query.message.reply_text(f"Price movement threshold updated to {threshold}% ✅")
            return
        if data.startswith("settings:set_interval:"):
            interval = int(data.rsplit(":", maxsplit=1)[1])
            save_interval_setting(interval)
            schedule_automatic_btc_check(context.application, interval)
            await query.message.reply_text(
                f"Automatic BTC check interval updated to {interval} seconds ✅ "
                "Applied immediately."
            )
            return
    except CoinGeckoRateLimitError:
        await send_manual_rate_limit_message(
            query.message, query.message.chat_id if query.message else None
        )
    except ValueError as error:
        await query.message.reply_text(f"Price data is temporarily unavailable: {error}")
    except Exception as error:
        log(f"Callback handling error: {error}")
        await query.message.reply_text("Sorry, something went wrong.")
