from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

from bot.config import TELEGRAM_BOT_TOKEN
from bot.handlers import (
    admin,
    button_router,
    chat_id,
    daily_report,
    error_logging_off,
    error_logging_on,
    error_logging_status,
    grant_premium,
    log_custom_emoji_ids,
    myplan,
    plan,
    price,
    reports,
    revoke_premium,
    set_interval,
    settings,
    start,
    subscribe,
    user_id,
    watchlist,
    weekly_report,
)
from bot.payments import pre_checkout_handler, successful_payment_handler


def build_application() -> Application:
    return Application.builder().token(TELEGRAM_BOT_TOKEN).build()


def register_handlers(app: Application) -> None:
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("plan", plan))
    app.add_handler(CommandHandler("watchlist", watchlist))
    app.add_handler(CommandHandler("myplan", myplan))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("userid", user_id))
    app.add_handler(CommandHandler("chatid", chat_id))
    app.add_handler(CommandHandler("settings", settings))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("reports", reports))
    app.add_handler(CommandHandler("dailyreport", daily_report))
    app.add_handler(CommandHandler("weeklyreport", weekly_report))
    app.add_handler(CommandHandler("setinterval", set_interval))
    app.add_handler(CommandHandler("grantpremium", grant_premium))
    app.add_handler(CommandHandler("revokepremium", revoke_premium))
    app.add_handler(CommandHandler("error_logging_on", error_logging_on))
    app.add_handler(CommandHandler("error_logging_off", error_logging_off))
    app.add_handler(CommandHandler("error_logging_status", error_logging_status))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, log_custom_emoji_ids))
    app.add_handler(CallbackQueryHandler(button_router))
