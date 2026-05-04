from config import TELEGRAM_ADMIN_USER_ID, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from bot_alerts import (
    schedule_automatic_btc_check,
    schedule_strong_signal_job,
    schedule_weekly_report,
)
from bot_handlers import (
    button_router,
    chat_id,
    daily_report,
    price,
    reports,
    set_interval,
    set_threshold,
    settings,
    start,
    status,
    user_id,
    weekly_report,
)
from bot_runtime import log
from bot_setup import setup_bot_commands
from bot_settings import get_runtime_alert_settings


def register_handlers(app: Application) -> None:
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price))
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
    app.add_handler(CallbackQueryHandler(button_router))


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is missing. Check your .env file.")
    if not TELEGRAM_CHAT_ID:
        raise ValueError("TELEGRAM_CHAT_ID is missing. Check your .env file.")
    if not TELEGRAM_ADMIN_USER_ID:
        raise ValueError("TELEGRAM_ADMIN_USER_ID is missing. Check your .env file.")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    register_handlers(app)

    runtime_settings = get_runtime_alert_settings()
    schedule_automatic_btc_check(
        app, runtime_settings["automatic_check_interval_seconds"]
    )
    schedule_weekly_report(app)
    schedule_strong_signal_job(app)

    log("Bot is running. Automatic BTC checks are enabled.")
    app.post_init = setup_bot_commands
    app.run_polling()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Bot stopped by user.")
