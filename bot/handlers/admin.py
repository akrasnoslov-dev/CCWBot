"""Admin and operational Telegram command handlers.

Belongs here: admin-only commands, system status, interval changes, premium
grant/revoke entrypoints, and warning/error log export controls. User-facing
non-admin commands belong in their domain modules.
"""

from io import BytesIO

from telegram import Update
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
from bot.keyboards import (
    build_admin_alert_settings_keyboard,
    build_admin_keyboard,
    build_admin_logs_keyboard,
    build_admin_premium_keyboard,
    build_interval_keyboard,
)
from bot.services.price_service import DEFAULT_SYMBOL
from bot.settings import (
    get_db_alert_settings,
    get_state_alert_settings,
    normalize_automatic_check_interval_seconds,
    save_interval_setting,
)
from bot.storage import load_state

from .common import _mark_denied, handlers_module, log_request


def _format_admin_alert_settings(alert_settings: dict) -> str:
    return (
        "Current alert settings\n\n"
        "Event Alert analysis interval: "
        f"{alert_settings['automatic_check_interval_seconds']} seconds\n"
        "Event decision: Groq LLM JSON analysis\n"
        "Movement thresholds: disabled for automatic event alerts"
    )


async def _build_admin_system_status_text() -> str:
    root = handlers_module()
    ai_status = "NOT OK"
    last_success = "not available"
    last_failed = "not available"
    last_error_reason = "not available"
    if root.DB_ENABLED and root.DB_SESSION_LOCAL:
        async with root.DB_SESSION_LOCAL() as session:
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


def _premium_grant_usage_text() -> str:
    return (
        "Grant premium\n\n"
        "Usage:\n"
        "/grantpremium <telegram_user_id|me> <days>\n\n"
        "Examples:\n"
        "/grantpremium 123456789 30\n"
        "/grantpremium me 7"
    )


def _premium_revoke_usage_text() -> str:
    return (
        "Revoke premium\n\n"
        "Usage:\n"
        "/revokepremium <telegram_user_id|me>\n\n"
        "Examples:\n"
        "/revokepremium 123456789\n"
        "/revokepremium me"
    )


async def _set_error_logging_enabled(enabled: bool) -> str:
    root = handlers_module()
    await root.save_error_file_logging_enabled(enabled)
    if enabled:
        log_file = root.enable_error_file_logging()
        return f"Warning/error file logging enabled.\nPath: {log_file}"
    root.disable_error_file_logging()
    return "Warning/error file logging disabled."


async def _build_error_logging_status_text() -> str:
    root = handlers_module()
    persisted_enabled = await root.get_runtime_error_file_logging_enabled()
    active_enabled = root.is_error_file_logging_enabled()
    state = "enabled" if persisted_enabled else "disabled"
    active = "active" if active_enabled else "inactive"
    return f"Warning/error file logging: {state} ({active})."


async def _toggle_error_logging() -> str:
    persisted_enabled = await handlers_module().get_runtime_error_file_logging_enabled()
    return await _set_error_logging_enabled(not persisted_enabled)


async def _send_log_exports(message) -> None:
    exports = handlers_module().build_sanitized_log_exports()
    if not exports:
        await message.reply_text(
            "No log files are available. Enable warning/error file logging and try again "
            "after a warning or error is recorded."
        )
        return

    for export in exports:
        document = BytesIO(export.content)
        document.name = export.file_name
        await message.reply_document(
            document=document,
            filename=export.file_name,
            caption=f"Log export: {export.file_name}",
        )


@log_request("/grantpremium")
async def grant_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await handlers_module().is_admin_update(update):
        _mark_denied(context)
    await handlers_module().grant_premium_command(update, context.args)


@log_request("/revokepremium")
async def revoke_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await handlers_module().is_admin_update(update):
        _mark_denied(context)
    await handlers_module().revoke_premium_command(update, context.args)


@log_request("/error_logging_on")
async def error_logging_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await handlers_module().is_admin_update(update):
        _mark_denied(context)
        await update.message.reply_text("Sorry, only the bot admin can change error logging.")
        return

    await update.message.reply_text(await _set_error_logging_enabled(True))


@log_request("/error_logging_off")
async def error_logging_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await handlers_module().is_admin_update(update):
        _mark_denied(context)
        await update.message.reply_text("Sorry, only the bot admin can change error logging.")
        return

    await update.message.reply_text(await _set_error_logging_enabled(False))


@log_request("/error_logging_status")
async def error_logging_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await handlers_module().is_admin_update(update):
        _mark_denied(context)
        await update.message.reply_text("Sorry, only the bot admin can view error logging status.")
        return

    await update.message.reply_text(await _build_error_logging_status_text())


@log_request("/chatid")
async def chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await handlers_module().is_admin_update(update):
        _mark_denied(context)
        await update.message.reply_text("Sorry, only the bot admin can view chat ID.")
        return
    await update.message.reply_text(f"Your chat ID is: {update.effective_chat.id}")


@log_request("/admin")
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await handlers_module().is_admin_update(update):
        _mark_denied(context)
        await update.message.reply_text("Sorry, only the bot admin can access admin settings.")
        return
    await update.message.reply_text("Admin menu", reply_markup=build_admin_keyboard())


@log_request("/setinterval")
async def set_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await handlers_module().is_admin_update(update):
        _mark_denied(context)
        await update.message.reply_text("Sorry, only the bot admin can change settings.")
        return
    if not context.args:
        await update.message.reply_text(
            "Please provide interval in seconds.\n\nExample:\n/setinterval 1800"
        )
        return
    try:
        interval = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "Interval must be a whole number.\n\nExample:\n/setinterval 1800"
        )
        return
    if interval <= 0:
        await update.message.reply_text("Interval must be greater than 0.")
        return

    applied_interval = normalize_automatic_check_interval_seconds(interval)
    await save_interval_setting(applied_interval)
    schedule_automatic_market_check(context.application, applied_interval)
    interval = applied_interval
    await update.message.reply_text(
        f"Event Alert analysis interval updated to {interval} seconds ✅ Applied immediately."
    )


async def send_admin_callback_response(data: str, message, application) -> bool:
    if data == "admin:alert_settings":
        await message.reply_text(
            "Alert settings",
            reply_markup=build_admin_alert_settings_keyboard(),
        )
        return True
    if data == "admin:back":
        await message.reply_text("Admin menu", reply_markup=build_admin_keyboard())
        return True
    if data == "admin:system_status":
        await message.reply_text(await _build_admin_system_status_text())
        return True
    if data == "admin:premium_menu":
        await message.reply_text("Premium management", reply_markup=build_admin_premium_keyboard())
        return True
    if data == "admin:premium_grant":
        await message.reply_text(_premium_grant_usage_text())
        return True
    if data == "admin:premium_revoke":
        await message.reply_text(_premium_revoke_usage_text())
        return True
    if data == "admin:logs_menu":
        await message.reply_text("Logs", reply_markup=build_admin_logs_keyboard())
        return True
    if data == "admin:logs_toggle":
        await message.reply_text(await _toggle_error_logging())
        return True
    if data == "admin:logs_status":
        await message.reply_text(await _build_error_logging_status_text())
        return True
    if data == "admin:logs_export":
        await _send_log_exports(message)
        return True
    if data == "admin:current":
        root = handlers_module()
        alert_settings = (
            await get_db_alert_settings()
            if root.DB_ENABLED and root.DB_SESSION_LOCAL
            else get_state_alert_settings(load_state())
        )
        await message.reply_text(_format_admin_alert_settings(alert_settings))
        return True
    if data == "admin:interval_menu":
        await message.reply_text(
            "Choose a new Event Alert analysis interval:",
            reply_markup=build_interval_keyboard(),
        )
        return True
    if data.startswith("admin:set_interval:"):
        interval = int(data.rsplit(":", maxsplit=1)[1])
        applied_interval = normalize_automatic_check_interval_seconds(interval)
        await save_interval_setting(applied_interval)
        schedule_automatic_market_check(application, applied_interval)
        interval = applied_interval
        await message.reply_text(
            f"Automatic check interval updated to {interval} seconds. Applied immediately."
        )
        return True
    return False
