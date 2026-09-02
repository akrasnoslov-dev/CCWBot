"""Admin and operational Telegram command handlers.

Belongs here: admin-only commands, system status, interval changes, premium
grant/revoke entrypoints, and warning/error log export controls. User-facing
non-admin commands belong in their domain modules.
"""

from io import BytesIO

from telegram import Update
from telegram.ext import ContextTypes

from bot.alerts import schedule_automatic_market_check
from bot.config import TELEGRAM_BOT_USERNAME
from bot.db.analytics import create_acquisition_link, list_active_acquisition_links
from bot.domain.attribution import (
    build_acquisition_telegram_url,
    validate_acquisition_link_metadata,
)
from bot.keyboards import (
    build_admin_alert_settings_keyboard,
    build_admin_back_keyboard,
    build_admin_keyboard,
    build_admin_logs_keyboard,
    build_admin_premium_keyboard,
    build_interval_keyboard,
)
from bot.observability.system_status import (
    build_admin_llm_diagnostics_text,
    build_admin_system_status_text,
)
from bot.settings import (
    get_db_alert_settings,
    get_state_alert_settings,
    normalize_automatic_check_interval_seconds,
    save_interval_setting,
)
from bot.storage import load_state

from .common import _mark_denied, handlers_module, log_request, safe_edit_callback_message

ACQUISITION_LINK_LIST_LIMIT = 100
TELEGRAM_REPLY_TEXT_LIMIT = 3500
ACQUISITION_LINK_PRIVATE_CHAT_MESSAGE = (
    "Acquisition links may only be managed in a private admin chat."
)


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
    return await build_admin_system_status_text(
        db_enabled=root.DB_ENABLED,
        session_factory=root.DB_SESSION_LOCAL,
    )


async def _build_admin_llm_diagnostics_text() -> str:
    root = handlers_module()
    return await build_admin_llm_diagnostics_text(
        db_enabled=root.DB_ENABLED,
        session_factory=root.DB_SESSION_LOCAL,
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


def _acquisition_link_usage_text() -> str:
    return (
        "Create acquisition link\n\n"
        "Usage:\n"
        "/acquisitionlink source=<source> [campaign=<code>] [creative=<code>] "
        "[referrer_code=<code>]\n\n"
        "Sources: reddit, telegramads, telegramdir, product-hunt\n\n"
        "Examples:\n"
        "/acquisitionlink source=reddit campaign=cryptotelegrambots\n"
        "/acquisitionlink source=telegramads campaign=general-crypto creative=ad01\n"
        "/acquisitionlink source=telegramdir\n"
        "/acquisitionlink source=product-hunt"
    )


def _parse_acquisition_link_arguments(args: list[str]) -> dict[str, str | None]:
    allowed = {"source", "campaign", "creative", "referrer_code"}
    values: dict[str, str | None] = {}
    for argument in args:
        key, separator, value = argument.partition("=")
        if not separator or key not in allowed or key in values or not value:
            raise ValueError("Use named source, campaign, creative, and referrer_code values.")
        values[key] = value
    if "source" not in values:
        raise ValueError("source is required.")
    metadata = validate_acquisition_link_metadata(**values)
    return {
        "source": metadata.source,
        "campaign": metadata.campaign,
        "creative": metadata.creative,
        "referrer_code": metadata.referrer_code,
    }


def _format_acquisition_link(link) -> str:
    url = build_acquisition_telegram_url(
        bot_username=TELEGRAM_BOT_USERNAME,
        link_code=link.link_code,
    )
    fields = [f"source={link.source}"]
    if link.campaign:
        fields.append(f"campaign={link.campaign}")
    if link.creative:
        fields.append(f"creative={link.creative}")
    return f"{' '.join(fields)}\n{url}"


async def _reply_acquisition_link_list(message, links) -> None:
    heading = "Active acquisition links:\n\n"
    current = heading
    for link in links:
        entry = _format_acquisition_link(link)
        separator = "" if current == heading else "\n\n"
        if len(current) + len(separator) + len(entry) > TELEGRAM_REPLY_TEXT_LIMIT:
            await message.reply_text(current)
            current = "Active acquisition links (continued):\n\n" + entry
        else:
            current += separator + entry
    await message.reply_text(current)


def _is_private_chat(update: Update) -> bool:
    return str(getattr(getattr(update, "effective_chat", None), "type", "")).lower() == "private"


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


@log_request("/acquisitionlink")
async def acquisition_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await handlers_module().is_admin_update(update):
        _mark_denied(context)
        await update.message.reply_text("Sorry, only the bot admin can manage acquisition links.")
        return
    if not _is_private_chat(update):
        _mark_denied(context)
        await update.message.reply_text(ACQUISITION_LINK_PRIVATE_CHAT_MESSAGE)
        return
    root = handlers_module()
    if not root.DB_ENABLED or not root.DB_SESSION_LOCAL:
        await update.message.reply_text(
            "Acquisition links require the configured PostgreSQL database."
        )
        return
    try:
        metadata = _parse_acquisition_link_arguments(context.args)
    except ValueError:
        await update.message.reply_text(_acquisition_link_usage_text())
        return
    try:
        build_acquisition_telegram_url(
            bot_username=TELEGRAM_BOT_USERNAME,
            link_code="sample-code",
        )
    except ValueError:
        await update.message.reply_text("Telegram bot username is not configured correctly.")
        return
    try:
        async with root.DB_SESSION_LOCAL() as session:
            link = await create_acquisition_link(session, **metadata)
    except RuntimeError:
        await update.message.reply_text("Could not create an acquisition link. Please try again.")
        return
    await update.message.reply_text(f"Acquisition link created:\n{_format_acquisition_link(link)}")


@log_request("/acquisitionlinks")
async def acquisition_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await handlers_module().is_admin_update(update):
        _mark_denied(context)
        await update.message.reply_text("Sorry, only the bot admin can manage acquisition links.")
        return
    if not _is_private_chat(update):
        _mark_denied(context)
        await update.message.reply_text(ACQUISITION_LINK_PRIVATE_CHAT_MESSAGE)
        return
    root = handlers_module()
    if not root.DB_ENABLED or not root.DB_SESSION_LOCAL:
        await update.message.reply_text(
            "Acquisition links require the configured PostgreSQL database."
        )
        return
    try:
        build_acquisition_telegram_url(
            bot_username=TELEGRAM_BOT_USERNAME,
            link_code="sample-code",
        )
    except ValueError:
        await update.message.reply_text("Telegram bot username is not configured correctly.")
        return
    async with root.DB_SESSION_LOCAL() as session:
        links = await list_active_acquisition_links(
            session,
            limit=ACQUISITION_LINK_LIST_LIMIT,
        )
    if not links:
        await update.message.reply_text("No active acquisition links.")
        return
    await _reply_acquisition_link_list(update.message, links)


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


async def send_admin_callback_response(data: str, query, application) -> bool:
    if data == "admin:alert_settings":
        await safe_edit_callback_message(
            query,
            "Alert settings",
            reply_markup=build_admin_alert_settings_keyboard(),
        )
        return True
    if data == "admin:back":
        await safe_edit_callback_message(query, "Admin menu", reply_markup=build_admin_keyboard())
        return True
    if data == "admin:system_status":
        await safe_edit_callback_message(
            query,
            await _build_admin_system_status_text(),
            reply_markup=build_admin_back_keyboard(),
        )
        return True
    if data == "admin:llm_diagnostics":
        await safe_edit_callback_message(
            query,
            await _build_admin_llm_diagnostics_text(),
            reply_markup=build_admin_back_keyboard(),
        )
        return True
    if data == "admin:premium_menu":
        await safe_edit_callback_message(
            query, "Premium management", reply_markup=build_admin_premium_keyboard()
        )
        return True
    if data == "admin:premium_grant":
        await safe_edit_callback_message(
            query, _premium_grant_usage_text(), reply_markup=build_admin_back_keyboard()
        )
        return True
    if data == "admin:premium_revoke":
        await safe_edit_callback_message(
            query, _premium_revoke_usage_text(), reply_markup=build_admin_back_keyboard()
        )
        return True
    if data == "admin:logs_menu":
        await safe_edit_callback_message(query, "Logs", reply_markup=build_admin_logs_keyboard())
        return True
    if data == "admin:logs_toggle":
        await safe_edit_callback_message(
            query, await _toggle_error_logging(), reply_markup=build_admin_logs_keyboard()
        )
        return True
    if data == "admin:logs_status":
        await safe_edit_callback_message(
            query,
            await _build_error_logging_status_text(),
            reply_markup=build_admin_logs_keyboard(),
        )
        return True
    if data == "admin:logs_export":
        await _send_log_exports(query.message)
        return True
    if data == "admin:current":
        root = handlers_module()
        alert_settings = (
            await get_db_alert_settings()
            if root.DB_ENABLED and root.DB_SESSION_LOCAL
            else get_state_alert_settings(load_state())
        )
        await safe_edit_callback_message(
            query,
            _format_admin_alert_settings(alert_settings),
            reply_markup=build_admin_alert_settings_keyboard(),
        )
        return True
    if data == "admin:interval_menu":
        await safe_edit_callback_message(
            query,
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
        await safe_edit_callback_message(
            query,
            f"Automatic check interval updated to {interval} seconds. Applied immediately.",
            reply_markup=build_admin_alert_settings_keyboard(),
        )
        return True
    return False
