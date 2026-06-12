"""Central Telegram handler registration.

Belongs here: mapping commands, callbacks, payments, and passive text handlers
to python-telegram-bot handlers. Command implementation belongs in sibling
domain modules.
"""

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

from bot.payments import pre_checkout_handler, successful_payment_handler

from .admin import (
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
from .plans import myplan, plan, subscribe, watchlist
from .price import log_custom_emoji_ids, price
from .reports import daily_report, reports, weekly_report
from .settings import settings
from .user import start, user_id

COMMAND_HANDLERS = (
    ("start", start),
    ("price", price),
    ("plan", plan),
    ("watchlist", watchlist),
    ("myplan", myplan),
    ("subscribe", subscribe),
    ("userid", user_id),
    ("chatid", chat_id),
    ("settings", settings),
    ("admin", admin),
    ("reports", reports),
    ("dailyreport", daily_report),
    ("weeklyreport", weekly_report),
    ("setinterval", set_interval),
    ("grantpremium", grant_premium),
    ("revokepremium", revoke_premium),
    ("error_logging_on", error_logging_on),
    ("error_logging_off", error_logging_off),
    ("error_logging_status", error_logging_status),
)


def register_bot_handlers(app: Application) -> None:
    for command, handler in COMMAND_HANDLERS:
        app.add_handler(CommandHandler(command, handler))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, log_custom_emoji_ids))
    app.add_handler(CallbackQueryHandler(button_router))
