"""Telegram handler package with compatibility exports for existing imports."""

from bot.error_logging import (
    build_sanitized_log_exports,
    disable_error_file_logging,
    enable_error_file_logging,
    is_error_file_logging_enabled,
)
from bot.onboarding import handle_onboarding_callback
from bot.payments import send_subscribe_invoice
from bot.permissions import is_admin_update, is_admin_user, sync_user_from_update
from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL
from bot.settings import get_runtime_error_file_logging_enabled, save_error_file_logging_enabled
from bot.watchlist import (
    edit_myplan_message,
    grant_premium_command,
    handle_watchlist_callback,
    myplan_command,
    revoke_premium_command,
    settings_command,
    watchlist_command,
)

from .admin import (
    _build_admin_system_status_text,
    _build_error_logging_status_text,
    _format_admin_alert_settings,
    _premium_grant_usage_text,
    _premium_revoke_usage_text,
    _send_log_exports,
    _set_error_logging_enabled,
    _toggle_error_logging,
    admin,
    chat_id,
    error_logging_off,
    error_logging_on,
    error_logging_status,
    grant_premium,
    revoke_premium,
    set_interval,
)
from .callbacks import button_router
from .common import (
    _callback_command_update,
    _mark_denied,
    _pop_denied,
    _role_label,
    _telegram_user_id,
    log_request,
)
from .plans import myplan, plan, subscribe, watchlist
from .price import (
    PRICE_RATE_LIMIT_PRUNE_AFTER_SECONDS,
    PRICE_RATE_LIMIT_SECONDS,
    log_custom_emoji_ids,
    price,
)
from .reports import daily_report, reports, weekly_report
from .settings import settings
from .user import start, user_id

__all__ = [
    "DB_ENABLED",
    "DB_SESSION_LOCAL",
    "PRICE_RATE_LIMIT_PRUNE_AFTER_SECONDS",
    "PRICE_RATE_LIMIT_SECONDS",
    "_build_admin_system_status_text",
    "_build_error_logging_status_text",
    "_callback_command_update",
    "_format_admin_alert_settings",
    "_mark_denied",
    "_pop_denied",
    "_premium_grant_usage_text",
    "_premium_revoke_usage_text",
    "_role_label",
    "_send_log_exports",
    "_set_error_logging_enabled",
    "_telegram_user_id",
    "_toggle_error_logging",
    "admin",
    "build_sanitized_log_exports",
    "button_router",
    "chat_id",
    "daily_report",
    "disable_error_file_logging",
    "enable_error_file_logging",
    "error_logging_off",
    "error_logging_on",
    "error_logging_status",
    "edit_myplan_message",
    "get_runtime_error_file_logging_enabled",
    "grant_premium",
    "grant_premium_command",
    "handle_watchlist_callback",
    "handle_onboarding_callback",
    "is_admin_update",
    "is_admin_user",
    "is_error_file_logging_enabled",
    "log_custom_emoji_ids",
    "log_request",
    "myplan",
    "myplan_command",
    "plan",
    "price",
    "reports",
    "revoke_premium",
    "revoke_premium_command",
    "save_error_file_logging_enabled",
    "send_subscribe_invoice",
    "set_interval",
    "settings",
    "settings_command",
    "start",
    "subscribe",
    "sync_user_from_update",
    "user_id",
    "watchlist",
    "watchlist_command",
    "weekly_report",
]
