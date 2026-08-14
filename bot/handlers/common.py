"""Shared Telegram handler helpers.

Belongs here: cross-command logging, permission-denied bookkeeping, and callback
update adapters. Domain command logic belongs in the sibling handler modules.
"""

import logging
import time
from functools import wraps
from importlib import import_module
from types import SimpleNamespace

from telegram import Update
from telegram.error import BadRequest, TelegramError
from telegram.ext import ContextTypes

from bot.runtime import log

logger = logging.getLogger("bot.handlers")


def handlers_module():
    return import_module("bot.handlers")


def _callback_command_update(update: Update) -> SimpleNamespace:
    query = update.callback_query
    return SimpleNamespace(
        message=query.message if query else None,
        effective_user=query.from_user if query else None,
        effective_chat=getattr(query.message, "chat", None) if query and query.message else None,
    )


def _telegram_user_id(update: Update) -> int | str:
    return update.effective_user.id if update.effective_user else "unknown"


async def _role_label(update: Update) -> str:
    user_id = update.effective_user.id if update.effective_user else None
    return "admin" if await handlers_module().is_admin_user(user_id) else "user"


def _mark_denied(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["_ccwbot_command_denied"] = True


async def safe_edit_callback_message(query, text: str, **kwargs) -> bool:
    """Edit a transient callback screen without exposing Telegram failures."""
    try:
        await query.edit_message_text(text=text, **kwargs)
    except BadRequest as error:
        if "message is not modified" in str(error).lower():
            return True
        logger.debug("Transient callback edit failed: %s", type(error).__name__)
        return False
    except TelegramError as error:
        logger.debug("Transient callback edit failed: %s", type(error).__name__)
        return False
    return True


async def safe_delete_command_invocation(update: Update) -> bool:
    """Best-effort deletion of a user's slash command in a private chat."""
    message = getattr(update, "message", None)
    chat = getattr(update, "effective_chat", None)
    if message is None or str(getattr(chat, "type", "")).lower() != "private":
        return False
    try:
        await message.delete()
    except Exception as error:
        logger.debug("Command invocation deletion failed: %s", type(error).__name__)
        return False
    return True


def _pop_denied(context: ContextTypes.DEFAULT_TYPE) -> bool:
    return bool(context.user_data.pop("_ccwbot_command_denied", False))


def log_request(action_name: str):
    def decorator(handler):
        @wraps(handler)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            started_at = time.perf_counter()
            try:
                await handlers_module().sync_user_from_update(update)
                result = await handler(update, context)
            except Exception:
                duration_ms = int((time.perf_counter() - started_at) * 1000)
                role = await _role_label(update)
                logger.warning(
                    "ops_event=command_failed command=%s role=%s duration_ms=%s",
                    action_name,
                    role,
                    duration_ms,
                    exc_info=True,
                )
                raise

            if action_name.startswith("/"):
                await safe_delete_command_invocation(update)

            duration_ms = int((time.perf_counter() - started_at) * 1000)
            role = await _role_label(update)
            outcome = "Denied" if _pop_denied(context) else "Handled"
            log(
                "ops_event=command_handled "
                f"command={action_name} outcome={outcome.lower()} role={role} "
                f"duration_ms={duration_ms}"
            )
            return result

        return wrapper

    return decorator
