"""General user command handlers."""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.db.analytics import record_bot_started, resolve_start_attribution
from bot.db.users import get_user_by_telegram_user_id
from bot.domain.attribution import parse_start_attribution
from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL

from .common import handlers_module, log_request

logger = logging.getLogger(__name__)


def _start_payload(context: ContextTypes.DEFAULT_TYPE) -> str | None:
    args = getattr(context, "args", None) or []
    if len(args) != 1:
        return None
    value = args[0]
    return value if isinstance(value, str) else None


async def _record_start_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Best-effort product measurement that never exposes deep-link data to users."""
    if (
        not (DB_ENABLED and DB_SESSION_LOCAL)
        or not update.effective_user
        or getattr(getattr(update, "effective_chat", None), "type", None) != "private"
    ):
        return
    token = parse_start_attribution(_start_payload(context))
    try:
        async with DB_SESSION_LOCAL() as session:
            user = await get_user_by_telegram_user_id(session, update.effective_user.id)
            if user is None:
                return
            attribution = await resolve_start_attribution(session, token=token)
            await record_bot_started(session, user_id=user.id, attribution=attribution)
    except Exception as error:  # pragma: no cover - defensive analytics isolation
        logger.warning("Product start analytics failed: %s", type(error).__name__)


@log_request("/start")
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _record_start_analytics(update, context)
    is_admin = await handlers_module().is_admin_update(update)
    message = (
        "CCWBot\n\n"
        "I monitor crypto prices and alert settings.\n\n"
        "Use:\n"
        "/price - check crypto prices"
        "\n/watchlist - manage alert watchlist"
        "\n/reports - open market reports"
        "\n/plan - plan and subscription"
    )
    if is_admin:
        message += "\n/admin - open admin menu"
    await update.message.reply_text(message)


@log_request("/userid")
async def user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_value = update.effective_user.id if update.effective_user else "unknown"
    await update.message.reply_text(f"Your Telegram user ID is: {user_id_value}")
