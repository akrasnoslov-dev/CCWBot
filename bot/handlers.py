import logging
import time
from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes

from bot.alerts import schedule_automatic_btc_check
from bot.db.database import get_price_state
from bot.keyboards import (
    build_interval_keyboard,
    build_price_keyboard,
    build_reports_keyboard,
    build_settings_keyboard,
    build_threshold_keyboard,
)
from bot.payments import send_subscribe_invoice
from bot.permissions import is_admin_update, is_admin_user, sync_user_from_update
from bot.prices import (
    build_supported_symbols_message,
    send_manual_rate_limit_message,
    send_price_message,
)
from bot.reports import send_daily_report_message, send_weekly_report_message
from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL, log
from bot.services.price_service import COIN_SYMBOL_TO_ID, DEFAULT_SYMBOL, CoinGeckoRateLimitError
from bot.settings import (
    get_db_alert_settings,
    get_state_alert_settings,
    save_interval_setting,
    save_threshold_setting,
)
from bot.storage import load_state
from bot.watchlist import (
    grant_premium_command,
    handle_watchlist_callback,
    myplan_command,
    revoke_premium_command,
    watchlist_command,
)

PRICE_RATE_LIMIT_SECONDS = 10
PRICE_RATE_LIMIT_PRUNE_AFTER_SECONDS = 3600
_user_last_price_call: dict[int, float] = {}
logger = logging.getLogger(__name__)


def _telegram_user_id(update: Update) -> int | str:
    return update.effective_user.id if update.effective_user else "unknown"


async def _role_label(update: Update) -> str:
    user_id = update.effective_user.id if update.effective_user else None
    return "admin" if await is_admin_user(user_id) else "user"


def _mark_denied(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["_ccwbot_command_denied"] = True


def _pop_denied(context: ContextTypes.DEFAULT_TYPE) -> bool:
    return bool(context.user_data.pop("_ccwbot_command_denied", False))


def log_request(action_name: str):
    def decorator(handler):
        @wraps(handler)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            started_at = time.perf_counter()
            try:
                await sync_user_from_update(update)
                result = await handler(update, context)
            except Exception:
                duration_ms = int((time.perf_counter() - started_at) * 1000)
                role = await _role_label(update)
                logger.warning(
                    "Failed %s for user_id=%s role=%s in %sms",
                    action_name,
                    _telegram_user_id(update),
                    role,
                    duration_ms,
                )
                raise

            duration_ms = int((time.perf_counter() - started_at) * 1000)
            role = await _role_label(update)
            outcome = "Denied" if _pop_denied(context) else "Handled"
            log(
                f"{outcome} {action_name} for user_id={_telegram_user_id(update)} "
                f"role={role} in {duration_ms}ms"
            )
            return result

        return wrapper

    return decorator


@log_request("/start")
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_admin = await is_admin_update(update)
    message = (
        "Hi! I’m CCWBot 🚀\n\n"
        "I monitor crypto prices and send automatic BTC alerts.\n\n"
        "Use:\n"
        "/price - check crypto prices"
        "\n/watchlist - manage alert coins"
        "\n/myplan - show your plan"
        "\n/reports - BTC reports menu"
    )
    if is_admin:
        message += "\n/settings - open settings menu\n/status - show bot status"
    await update.message.reply_text(message)


@log_request("/userid")
async def user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_value = update.effective_user.id if update.effective_user else "unknown"
    await update.message.reply_text(f"Your Telegram user ID is: {user_id_value}")


@log_request("/dailyreport")
async def daily_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_daily_report_message(update.message)


@log_request("/weeklyreport")
async def weekly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_weekly_report_message(update.message)


@log_request("/reports")
async def reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Reports menu 📊", reply_markup=build_reports_keyboard())


@log_request("/watchlist")
async def watchlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await watchlist_command(update)


@log_request("/myplan")
async def myplan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await myplan_command(update)


@log_request("/subscribe")
async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_subscribe_invoice(update, context)


@log_request("/grantpremium")
async def grant_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_update(update):
        _mark_denied(context)
    await grant_premium_command(update, context.args)


@log_request("/revokepremium")
async def revoke_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_update(update):
        _mark_denied(context)
    await revoke_premium_command(update, context.args)


@log_request("/chatid")
async def chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_update(update):
        _mark_denied(context)
        await update.message.reply_text("Sorry, only the bot admin can view chat ID.")
        return
    await update.message.reply_text(f"Your chat ID is: {update.effective_chat.id}")


@log_request("/settings")
async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_update(update):
        _mark_denied(context)
        await update.message.reply_text("Sorry, only the bot admin can access settings.")
        return
    await update.message.reply_text("Settings menu ⚙️", reply_markup=build_settings_keyboard())


@log_request("/setthreshold")
async def set_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_update(update):
        _mark_denied(context)
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

    await save_threshold_setting(threshold)
    await update.message.reply_text(f"Price movement threshold updated to {threshold}% ✅")


@log_request("/setinterval")
async def set_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_update(update):
        _mark_denied(context)
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

    await save_interval_setting(interval)
    schedule_automatic_btc_check(context.application, interval)
    await update.message.reply_text(
        f"Automatic BTC check interval updated to {interval} seconds ✅ Applied immediately."
    )


@log_request("/price")
async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id_value = update.effective_user.id if update.effective_user else None
        now = time.monotonic()
        if user_id_value is not None:
            stale_before = now - PRICE_RATE_LIMIT_PRUNE_AFTER_SECONDS
            for cached_user_id, last_seen_at in list(_user_last_price_call.items()):
                if last_seen_at < stale_before:
                    _user_last_price_call.pop(cached_user_id, None)
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
        logger.warning("Manual price lookup failed: %s", error)
        await update.message.reply_text("Price data is temporarily unavailable.")
    except Exception as error:
        await update.message.reply_text("Sorry, I could not get the price right now.")
        log(f"Price error: {error}")


@log_request("/status")
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_update(update):
        _mark_denied(context)
        await update.message.reply_text("Sorry, only the bot admin can view status.")
        return
    if DB_ENABLED and DB_SESSION_LOCAL:
        async with DB_SESSION_LOCAL() as session:
            btc_state = await get_price_state(session, DEFAULT_SYMBOL)
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


@log_request("callback")
async def button_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data or ""

    try:
        if data.startswith("settings:") and not await is_admin_user(
            query.from_user.id if query.from_user else None
        ):
            _mark_denied(context)
            await query.answer("Sorry, only the bot admin can change settings.")
            await query.message.reply_text("Sorry, only the bot admin can change settings.")
            return

        if data.startswith("watchlist:"):
            handled = await handle_watchlist_callback(update, data)
            if handled:
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
                alert_settings = await get_db_alert_settings()
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
            await save_threshold_setting(threshold)
            await query.message.reply_text(f"Price movement threshold updated to {threshold}% ✅")
            return
        if data.startswith("settings:set_interval:"):
            interval = int(data.rsplit(":", maxsplit=1)[1])
            await save_interval_setting(interval)
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
        logger.warning("Callback price lookup failed: %s", error)
        await query.message.reply_text("Price data is temporarily unavailable.")
    except Exception as error:
        log(f"Callback handling error: {error}")
        await query.message.reply_text("Sorry, something went wrong.")
