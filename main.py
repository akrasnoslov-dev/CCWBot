import asyncio
import logging
import signal
import sys
import time

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

from bot.alerts import (
    schedule_automatic_btc_check,
    schedule_seen_news_cleanup,
    schedule_strong_signal_job,
    schedule_weekly_report,
)
from bot.handlers import (
    button_router,
    chat_id,
    daily_report,
    grant_premium,
    myplan,
    price,
    reports,
    revoke_premium,
    set_interval,
    set_threshold,
    settings,
    start,
    status,
    subscribe,
    user_id,
    watchlist,
    weekly_report,
)
from bot.payments import pre_checkout_handler, successful_payment_handler
from bot.runtime import close_database, initialize_database, log
from bot.settings import get_runtime_alert_settings
from bot.setup import setup_bot_commands
from config import HEALTH_PORT, TELEGRAM_ADMIN_USER_ID, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from health import start_health_server, stop_health_server
from price_service import warm_up_price_cache


def create_event_loop() -> asyncio.AbstractEventLoop:
    if sys.platform == "win32":
        return asyncio.SelectorEventLoop()
    return asyncio.new_event_loop()


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("alembic").setLevel(logging.WARNING)
    logging.getLogger("alembic.runtime.migration").setLevel(logging.WARNING)
    logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_stop_signals() -> tuple[signal.Signals, ...] | None:
    if sys.platform == "win32":
        return None
    return (signal.SIGINT, signal.SIGTERM)


def register_handlers(app: Application) -> None:
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("watchlist", watchlist))
    app.add_handler(CommandHandler("myplan", myplan))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("userid", user_id))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("chatid", chat_id))
    app.add_handler(CommandHandler("settings", settings))
    app.add_handler(CommandHandler("reports", reports))
    app.add_handler(CommandHandler("dailyreport", daily_report))
    app.add_handler(CommandHandler("weeklyreport", weekly_report))
    app.add_handler(CommandHandler("setthreshold", set_threshold))
    app.add_handler(CommandHandler("setcooldown", set_interval))
    app.add_handler(CommandHandler("setinterval", set_interval))
    app.add_handler(CommandHandler("grantpremium", grant_premium))
    app.add_handler(CommandHandler("revokepremium", revoke_premium))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    app.add_handler(CallbackQueryHandler(button_router))


def main():
    configure_logging()

    started_at = time.monotonic()
    health_runner = None
    loop = create_event_loop()
    asyncio.set_event_loop(loop)
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is missing. Check your .env file.")
    if not TELEGRAM_CHAT_ID:
        raise ValueError("TELEGRAM_CHAT_ID is missing. Check your .env file.")
    if not TELEGRAM_ADMIN_USER_ID:
        raise ValueError("TELEGRAM_ADMIN_USER_ID is missing. Check your .env file.")

    loop.run_until_complete(initialize_database())
    loop.run_until_complete(warm_up_price_cache())

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    register_handlers(app)

    runtime_settings = loop.run_until_complete(get_runtime_alert_settings())
    schedule_automatic_btc_check(app, runtime_settings["automatic_check_interval_seconds"])
    schedule_weekly_report(app)
    schedule_strong_signal_job(app)
    schedule_seen_news_cleanup(app)

    health_runner = loop.run_until_complete(
        start_health_server(HEALTH_PORT, started_at=started_at)
    )
    log(f"Health server is running on port {HEALTH_PORT}.")
    log("Bot is running. Automatic BTC checks are enabled.")
    app.post_init = setup_bot_commands
    try:
        app.run_polling(close_loop=False, stop_signals=get_stop_signals())
    finally:
        log("Shutting down bot.")
        if not loop.is_closed():
            loop.run_until_complete(stop_health_server(health_runner))
        if not loop.is_closed():
            loop.run_until_complete(close_database())
        if not loop.is_closed():
            loop.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Bot stopped by user.")
