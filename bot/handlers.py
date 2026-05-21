import logging
import time
from functools import wraps

from telegram import MessageEntity, Update
from telegram.ext import ContextTypes

from bot.alerting.event_analysis import (
    EVENT_ANALYSIS_FAILURE_STATUSES,
    EVENT_ANALYSIS_SUCCESS_STATUSES,
)
from bot.alerts import schedule_automatic_market_check
from bot.db.database import (
    get_latest_event_analysis_attempt,
    get_latest_event_analysis_by_statuses,
    get_price_state,
)
from bot.error_logging import (
    disable_error_file_logging,
    enable_error_file_logging,
    is_error_file_logging_enabled,
)
from bot.keyboards import (
    build_admin_alert_settings_keyboard,
    build_admin_keyboard,
    build_interval_keyboard,
    build_price_keyboard,
    build_reports_keyboard,
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
    get_runtime_error_file_logging_enabled,
    get_state_alert_settings,
    save_alert_threshold_setting,
    save_error_file_logging_enabled,
    save_interval_setting,
    save_threshold_setting,
)
from bot.storage import load_state
from bot.watchlist import (
    grant_premium_command,
    handle_watchlist_callback,
    myplan_command,
    revoke_premium_command,
    settings_command,
    watchlist_command,
)

PRICE_RATE_LIMIT_SECONDS = 10
PRICE_RATE_LIMIT_PRUNE_AFTER_SECONDS = 3600
_user_last_price_call: dict[int, float] = {}
logger = logging.getLogger(__name__)


def _format_admin_alert_settings(alert_settings: dict) -> str:
    return (
        "Current alert settings\n\n"
        f"Check interval: {alert_settings['automatic_check_interval_seconds']} seconds\n"
        "Event decision: Groq LLM JSON analysis\n"
        "Movement thresholds: disabled for automatic event alerts"
    )


async def _build_admin_system_status_text() -> str:
    ai_status = "NOT OK"
    last_success = "not available"
    last_failed = "not available"
    last_error_reason = "not available"
    if DB_ENABLED and DB_SESSION_LOCAL:
        async with DB_SESSION_LOCAL() as session:
            btc_state = await get_price_state(session, DEFAULT_SYMBOL)
            latest_ai = await get_latest_event_analysis_attempt(session)
            latest_success = await get_latest_event_analysis_by_statuses(
                session,
                EVENT_ANALYSIS_SUCCESS_STATUSES,
            )
            latest_failure = await get_latest_event_analysis_by_statuses(
                session,
                EVENT_ANALYSIS_FAILURE_STATUSES,
            )
        last_check = btc_state.last_checked_at if btc_state else "not checked yet"
        database_status = "OK"
        if latest_ai and latest_ai.status in EVENT_ANALYSIS_SUCCESS_STATUSES:
            ai_status = "OK"
        elif latest_ai is None:
            ai_status = "NOT OK"
            last_error_reason = "no AI analysis yet"
        if latest_success:
            last_success = latest_success.created_at
        if latest_failure:
            last_failed = latest_failure.created_at
            last_error_reason = latest_failure.error_reason or latest_failure.status
    else:
        state = load_state()
        last_check = state.get("last_checked_at", "not checked yet")
        database_status = "disabled"
        ai_status = "NOT OK"
        last_error_reason = "database disabled"
    return (
        "System status\n\n"
        "Bot status: OK\n"
        f"Database status: {database_status}\n"
        "CoinGecko status: OK\n"
        f"Groq AI status: {ai_status}\n"
        f"Last successful AI analysis time: {last_success}\n"
        f"Last failed AI analysis time: {last_failed}\n"
        f"Last AI error reason: {last_error_reason}\n"
        "RSS/news status: OK\n"
        f"Last check time: {last_check}\n"
        "Rate limit status: no active rate limit recorded"
    )


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
                    exc_info=True,
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
        "CCWBot\n\n"
        "I monitor crypto prices and alert settings.\n\n"
        "Use:\n"
        "/price - check crypto prices"
        "\n/settings - manage alert settings"
        "\n/myplan - show subscription plan"
        "\n/subscribe - subscribe with Telegram Stars"
        "\n/status - show bot status"
    )
    if is_admin:
        message += "\n/admin - open admin menu"
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


@log_request("/error_logging_on")
async def error_logging_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_update(update):
        _mark_denied(context)
        await update.message.reply_text("Sorry, only the bot admin can change error logging.")
        return

    await save_error_file_logging_enabled(True)
    log_file = enable_error_file_logging()
    await update.message.reply_text(f"Warning/error file logging enabled.\nPath: {log_file}")


@log_request("/error_logging_off")
async def error_logging_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_update(update):
        _mark_denied(context)
        await update.message.reply_text("Sorry, only the bot admin can change error logging.")
        return

    await save_error_file_logging_enabled(False)
    disable_error_file_logging()
    await update.message.reply_text("Warning/error file logging disabled.")


@log_request("/error_logging_status")
async def error_logging_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_update(update):
        _mark_denied(context)
        await update.message.reply_text("Sorry, only the bot admin can view error logging status.")
        return

    persisted_enabled = await get_runtime_error_file_logging_enabled()
    active_enabled = is_error_file_logging_enabled()
    state = "enabled" if persisted_enabled else "disabled"
    active = "active" if active_enabled else "inactive"
    await update.message.reply_text(f"Warning/error file logging: {state} ({active}).")


@log_request("/chatid")
async def chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_update(update):
        _mark_denied(context)
        await update.message.reply_text("Sorry, only the bot admin can view chat ID.")
        return
    await update.message.reply_text(f"Your chat ID is: {update.effective_chat.id}")


@log_request("/settings")
async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await settings_command(update)


@log_request("/admin")
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_update(update):
        _mark_denied(context)
        await update.message.reply_text("Sorry, only the bot admin can access admin settings.")
        return
    await update.message.reply_text("Admin menu", reply_markup=build_admin_keyboard())


@log_request("/setthreshold")
async def set_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_update(update):
        _mark_denied(context)
        await update.message.reply_text("Sorry, only the bot admin can change settings.")
        return
    await update.message.reply_text(
        "Price movement thresholds are disabled for automatic Event Alerts. "
        "Use /setinterval to change the check interval."
    )
    return


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
    schedule_automatic_market_check(context.application, interval)
    await update.message.reply_text(
        f"Automatic market check interval updated to {interval} seconds ✅ Applied immediately."
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
        logger.exception("Price command failed: %s", error)


@log_request("/status")
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
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


async def log_custom_emoji_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_update(update):
        return
    message = update.effective_message
    if message is None:
        return
    text = message.text or message.caption or ""
    entities = list(message.entities or ()) + list(message.caption_entities or ())
    for entity in entities:
        if entity.type != MessageEntity.CUSTOM_EMOJI:
            continue
        custom_emoji_id = getattr(entity, "custom_emoji_id", None)
        if not custom_emoji_id:
            continue
        nearby_start = max(int(entity.offset) - 8, 0)
        nearby_end = min(int(entity.offset) + int(entity.length) + 8, len(text))
        logger.info(
            "custom_emoji_entity type=%s offset=%s length=%s custom_emoji_id=%s nearby_text=%r",
            entity.type,
            entity.offset,
            entity.length,
            custom_emoji_id,
            text[nearby_start:nearby_end],
        )


@log_request("callback")
async def button_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data or ""

    try:
        if (data.startswith("settings:") or data.startswith("admin:")) and not await is_admin_user(
            query.from_user.id if query.from_user else None
        ):
            _mark_denied(context)
            await query.answer("Sorry, only the bot admin can change settings.")
            await query.message.reply_text("Sorry, only the bot admin can change settings.")
            return

        if data.startswith("admin:"):
            await query.answer()
            if data == "admin:alert_settings":
                await query.message.reply_text(
                    "Alert settings", reply_markup=build_admin_alert_settings_keyboard()
                )
                return
            if data == "admin:system_status":
                await query.message.reply_text(await _build_admin_system_status_text())
                return
            if data == "admin:export_logs":
                await query.message.reply_text(
                    "Log export is available from the server logs directory."
                )
                return
            if data == "admin:current":
                alert_settings = (
                    await get_db_alert_settings()
                    if DB_ENABLED and DB_SESSION_LOCAL
                    else get_state_alert_settings(load_state())
                )
                await query.message.reply_text(_format_admin_alert_settings(alert_settings))
                return
            if data == "admin:interval_menu":
                await query.message.reply_text(
                    "Choose a new check interval:", reply_markup=build_interval_keyboard()
                )
                return
            if data.startswith("admin:threshold_menu:"):
                setting_key = data.rsplit(":", maxsplit=1)[1]
                await query.message.reply_text(
                    "Choose a new threshold:",
                    reply_markup=build_threshold_keyboard(setting_key),
                )
                return
            if data.startswith("admin:set_threshold:"):
                _, _, setting_key, raw_value = data.split(":", maxsplit=3)
                threshold = float(raw_value)
                await save_alert_threshold_setting(setting_key, threshold)
                await query.message.reply_text(f"Threshold updated to {threshold}%.")
                return
            if data.startswith("admin:set_interval:"):
                interval = int(data.rsplit(":", maxsplit=1)[1])
                await save_interval_setting(interval)
                schedule_automatic_market_check(context.application, interval)
                await query.message.reply_text(
                    f"Automatic check interval updated to {interval} seconds. Applied immediately."
                )
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
                "Automatic market check interval: "
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
            schedule_automatic_market_check(context.application, interval)
            await query.message.reply_text(
                f"Automatic market check interval updated to {interval} seconds ✅ "
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
        logger.exception("Callback handling failed: %s", error)
        await query.message.reply_text("Sorry, something went wrong.")
