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
