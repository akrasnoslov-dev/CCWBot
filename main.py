from datetime import datetime, time, timedelta, timezone

import httpx
from ai_agent_groq import (
    build_fallback_alert_message,
    classify_strong_signal,
    create_ai_alert_payload,
    create_daily_report,
    create_weekly_report,
)
from alert_rules import calculate_price_change_percent, should_send_alert
from config import (
    DATABASE_URL,
    AUTOMATIC_CHECK_INTERVAL_SECONDS,
    ENABLE_STRONG_SIGNAL_ALERTS,
    ENABLE_WEEKLY_REPORT,
    PRICE_MOVE_ALERT_PERCENT,
    STRONG_SIGNAL_CHECK_INTERVAL_SECONDS,
    STRONG_SIGNAL_COOLDOWN_HOURS,
    TELEGRAM_ADMIN_USER_ID,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    WEEKLY_REPORT_DAY,
    WEEKLY_REPORT_HOUR,
)
from database import (
    cleanup_seen_news,
    get_or_create_app_settings,
    get_or_create_user,
    get_price_state,
    get_user_role,
    init_db,
    make_news_key,
    mark_news_items_seen,
    save_alert,
    telegram_id_columns_are_bigint,
    update_app_settings,
    update_price_state,
    was_news_seen,
)
from news_service import fetch_crypto_news
from price_service import (
    COIN_SYMBOL_TO_ID,
    DEFAULT_SYMBOL,
    CoinGeckoRateLimitError,
    get_btc_market_data,
    get_coin_price,
)
from storage import load_state, save_state
from telegram import (
    BotCommand,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

# ---- Constants ----
MANUAL_RATE_LIMIT_MESSAGE_COOLDOWN_SECONDS = 120
AUTOMATIC_BTC_CHECK_JOB_NAME = "automatic_btc_check"
WEEKLY_REPORT_JOB_NAME = "weekly_report"
STRONG_SIGNAL_JOB_NAME = "strong_signal"
WEEKDAY_MAP = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

_MANUAL_RATE_LIMIT_LAST_SENT_AT_BY_CHAT: dict[int, float] = {}
DEFAULT_BTC_ALERT_THRESHOLD_PERCENT = 2.0
DEFAULT_AUTOMATIC_CHECK_INTERVAL_SECONDS = 300


# ---- Small utilities ----
def log(message: str) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{timestamp}] {message}")


# Optional DB bootstrap: PostgreSQL stores runtime state when configured.
DB_ENABLED = bool(DATABASE_URL)
DB_SESSION_LOCAL = None
if DB_ENABLED:
    log("Database configured. Using PostgreSQL state.")
    _, DB_SESSION_LOCAL = init_db(DATABASE_URL)
    if telegram_id_columns_are_bigint():
        log("Telegram ID columns are configured as PostgreSQL BIGINT.")
    else:
        log("Warning: Telegram ID columns are not all configured as PostgreSQL BIGINT.")
else:
    log("DATABASE_URL is not configured. Using local JSON state.")


def is_admin_user(user_id: int | str | None) -> bool:
    if user_id is None or TELEGRAM_ADMIN_USER_ID is None:
        return False
    if DB_ENABLED and DB_SESSION_LOCAL:
        with DB_SESSION_LOCAL() as session:
            return get_user_role(session, int(user_id)) == "admin"
    return str(user_id) == str(TELEGRAM_ADMIN_USER_ID)


def sync_user_from_update(update: Update) -> None:
    if not (DB_ENABLED and DB_SESSION_LOCAL):
        return
    if not update.effective_user or not update.effective_chat:
        return
    with DB_SESSION_LOCAL() as session:
        get_or_create_user(
            session,
            telegram_user_id=update.effective_user.id,
            telegram_chat_id=update.effective_chat.id,
            username=update.effective_user.username,
            first_name=update.effective_user.first_name,
            admin_user_id=TELEGRAM_ADMIN_USER_ID,
        )


def build_supported_symbols_message() -> str:
    return ", ".join(COIN_SYMBOL_TO_ID.keys())


def get_alert_settings(state: dict) -> dict:
    return {
        "price_move_alert_percent": float(
            state.get(
                "btc_alert_threshold_percent",
                state.get("price_move_alert_percent", PRICE_MOVE_ALERT_PERCENT),
            )
        ),
        "automatic_check_interval_seconds": int(
            state.get(
                "automatic_check_interval_seconds", AUTOMATIC_CHECK_INTERVAL_SECONDS
            )
        ),
    }


def get_db_alert_settings() -> dict:
    with DB_SESSION_LOCAL() as session:
        settings = get_or_create_app_settings(
            session,
            default_threshold=DEFAULT_BTC_ALERT_THRESHOLD_PERCENT,
            default_interval=DEFAULT_AUTOMATIC_CHECK_INTERVAL_SECONDS,
        )
    return {
        "price_move_alert_percent": settings["btc_alert_threshold_percent"],
        "automatic_check_interval_seconds": settings[
            "automatic_check_interval_seconds"
        ],
    }


def fetch_news_context(limit: int, *, prefer_unseen: bool = True) -> list[dict]:
    """Fetch RSS news and use seen_news for dedupe when PostgreSQL is active."""
    fetch_limit = max(limit * 3, limit)
    news_items = fetch_crypto_news(limit=fetch_limit)
    if not (DB_ENABLED and DB_SESSION_LOCAL):
        return news_items[:limit]

    with DB_SESSION_LOCAL() as session:
        unseen_items = [
            item for item in news_items if not was_news_seen(session, make_news_key(item))
        ]

    if unseen_items:
        return unseen_items[:limit]
    if prefer_unseen:
        log("No unseen RSS news found in PostgreSQL seen_news; reusing recent fetched news.")
    return news_items[:limit]


def remember_news_context(news_items: list[dict]) -> None:
    """Mark news items as seen in PostgreSQL after they were used by the bot."""
    if not (DB_ENABLED and DB_SESSION_LOCAL and news_items):
        return

    with DB_SESSION_LOCAL() as session:
        mark_news_items_seen(session, news_items)
        cleanup_seen_news(session, keep_latest=200)


# ---- Keyboards ----
def build_price_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("BTC", callback_data="price:btc"),
                InlineKeyboardButton("ETH", callback_data="price:eth"),
            ],
            [
                InlineKeyboardButton("TON", callback_data="price:ton"),
                InlineKeyboardButton("USDT", callback_data="price:usdt"),
            ],
        ]
    )


def build_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Current settings", callback_data="settings:current"
                )
            ],
            [
                InlineKeyboardButton(
                    "Set threshold", callback_data="settings:threshold_menu"
                )
            ],
            [
                InlineKeyboardButton(
                    "Set check interval", callback_data="settings:interval_menu"
                )
            ],
        ]
    )


def build_threshold_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("0.5%", callback_data="settings:set_threshold:0.5")],
            [InlineKeyboardButton("1.0%", callback_data="settings:set_threshold:1.0")],
            [InlineKeyboardButton("2.0%", callback_data="settings:set_threshold:2.0")],
        ]
    )


def build_interval_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("60 sec", callback_data="settings:set_interval:60")],
            [
                InlineKeyboardButton(
                    "300 sec", callback_data="settings:set_interval:300"
                )
            ],
            [
                InlineKeyboardButton(
                    "600 sec", callback_data="settings:set_interval:600"
                )
            ],
        ]
    )


def build_reports_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Daily report", callback_data="reports:daily")],
            [InlineKeyboardButton("Weekly report", callback_data="reports:weekly")],
        ]
    )


# ---- Shared message helpers ----
async def send_daily_report_message(target) -> None:
    try:
        price, change_24h, change_7d = await get_btc_market_data()
        news_items = fetch_news_context(limit=5, prefer_unseen=True)
        report = await create_daily_report(price, change_24h, news_items)
        if report and report.get("telegram_message"):
            message = str(report["telegram_message"])
            await target.reply_text(message)
            remember_news_context(news_items)
            if DB_ENABLED and DB_SESSION_LOCAL and TELEGRAM_CHAT_ID:
                with DB_SESSION_LOCAL() as session:
                    save_alert(
                        session,
                        symbol="BTC",
                        alert_type="daily_report",
                        message=message,
                        sent_to_chat_id=int(TELEGRAM_CHAT_ID),
                    )
            return
        await target.reply_text(
            build_fallback_alert_message(price, price, 0.0, change_24h, change_7d)
        )
    except Exception as error:
        log(f"Daily report generation failed: {error}")
        await target.reply_text(
            "Daily report unavailable. Monitor risk and avoid impulsive action.\nNot financial advice."
        )


async def send_weekly_report_message(target) -> None:
    try:
        price, change_24h, change_7d = await get_btc_market_data()
        news_items = fetch_news_context(limit=6, prefer_unseen=True)
        report = await create_weekly_report(price, change_24h, change_7d, news_items)
        if report and report.get("telegram_message"):
            message = str(report["telegram_message"])
            await target.reply_text(message)
            remember_news_context(news_items)
            if DB_ENABLED and DB_SESSION_LOCAL and TELEGRAM_CHAT_ID:
                with DB_SESSION_LOCAL() as session:
                    save_alert(
                        session,
                        symbol="BTC",
                        alert_type="weekly_report",
                        message=message,
                        sent_to_chat_id=int(TELEGRAM_CHAT_ID),
                    )
            return
        trend_text = "unknown" if change_7d is None else f"{change_7d:+.2f}%"
        await target.reply_text(
            f"📊 BTC weekly report\n\nPrice: ${price:,.2f}\n24h change: {change_24h:+.2f}%\n7d trend: {trend_text}\n"
            "Risk level: Medium\nPossible action: consider waiting for clearer confirmation.\nNot financial advice."
        )
    except Exception as error:
        log(f"Weekly report generation failed: {error}")


async def send_price_message(target, symbol: str) -> None:
    coin_price, change_24h, resolved_symbol = await get_coin_price(symbol)
    checked_at = datetime.now(timezone.utc).isoformat()

    if resolved_symbol == DEFAULT_SYMBOL and DB_ENABLED and DB_SESSION_LOCAL:
        with DB_SESSION_LOCAL() as session:
            existing = get_price_state(session, DEFAULT_SYMBOL)
            update_price_state(
                session,
                symbol=DEFAULT_SYMBOL,
                last_price=coin_price,
                last_24h_change=change_24h,
                last_checked_at=datetime.now(timezone.utc),
                last_alert_at=existing.last_alert_at if existing else None,
            )
    else:
        state = load_state()
        if resolved_symbol == DEFAULT_SYMBOL:
            state["last_price"] = coin_price
            state["last_24h_change"] = change_24h
            state["last_checked_at"] = checked_at
            if "last_alert_at" not in state:
                state["last_alert_at"] = None
            save_state(state)

    await target.reply_text(
        f"{resolved_symbol.upper()} price\n\nCurrent USD price: ${coin_price:,.2f}\n24h change: {change_24h:.2f}%"
    )


async def send_manual_rate_limit_message(target, chat_id: int | None) -> None:
    log("CoinGecko rate limit reached during manual price request.")
    if chat_id is None:
        await target.reply_text(
            "CoinGecko rate limit reached. Please wait a bit and try again."
        )
        return

    now_ts = datetime.now(timezone.utc).timestamp()
    last_sent_ts = _MANUAL_RATE_LIMIT_LAST_SENT_AT_BY_CHAT.get(chat_id)
    if (
        last_sent_ts is not None
        and (now_ts - last_sent_ts) < MANUAL_RATE_LIMIT_MESSAGE_COOLDOWN_SECONDS
    ):
        return

    _MANUAL_RATE_LIMIT_LAST_SENT_AT_BY_CHAT[chat_id] = now_ts
    await target.reply_text(
        "CoinGecko rate limit reached. Please wait a bit and try again."
    )


async def update_interval_and_reschedule(
    context: ContextTypes.DEFAULT_TYPE,
    interval: int,
) -> None:
    if DB_ENABLED and DB_SESSION_LOCAL:
        with DB_SESSION_LOCAL() as session:
            update_app_settings(
                session,
                interval_seconds=interval,
                default_threshold=DEFAULT_BTC_ALERT_THRESHOLD_PERCENT,
                default_interval=DEFAULT_AUTOMATIC_CHECK_INTERVAL_SECONDS,
            )
        schedule_automatic_btc_check(context.application, interval)
        return
    state = load_state()
    state["automatic_check_interval_seconds"] = interval
    save_state(state)
    schedule_automatic_btc_check(context.application, interval)


def _is_admin_update(update: Update) -> bool:
    return is_admin_user(update.effective_user.id if update.effective_user else None)


# ---- Command handlers ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sync_user_from_update(update)
    is_admin = _is_admin_update(update)
    message = (
        "Hi! I’m CCWBot 🚀\n\n"
        "I monitor crypto prices and send automatic BTC alerts.\n\n"
        "Use:\n"
        "/price - check crypto prices"
        "\n/reports - BTC reports menu"
    )
    if is_admin:
        message += "\n/settings - open settings menu\n/status - show bot status"
    await update.message.reply_text(message)


async def user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sync_user_from_update(update)
    user_id_value = update.effective_user.id if update.effective_user else "unknown"
    await update.message.reply_text(f"Your Telegram user ID is: {user_id_value}")


async def daily_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sync_user_from_update(update)
    await send_daily_report_message(update.message)


async def weekly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sync_user_from_update(update)
    await send_weekly_report_message(update.message)


async def reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sync_user_from_update(update)
    await update.message.reply_text(
        "Reports menu 📊", reply_markup=build_reports_keyboard()
    )


async def chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sync_user_from_update(update)
    if not _is_admin_update(update):
        await update.message.reply_text("Sorry, only the bot admin can view chat ID.")
        return
    await update.message.reply_text(f"Your chat ID is: {update.effective_chat.id}")


async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sync_user_from_update(update)
    if not _is_admin_update(update):
        await update.message.reply_text(
            "Sorry, only the bot admin can access settings."
        )
        return
    await update.message.reply_text(
        "Settings menu ⚙️", reply_markup=build_settings_keyboard()
    )


async def set_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sync_user_from_update(update)
    if not _is_admin_update(update):
        await update.message.reply_text(
            "Sorry, only the bot admin can change settings."
        )
        return
    if not context.args:
        await update.message.reply_text(
            "Please provide a threshold value.\n\nExample:\n/setthreshold 1.0"
        )
        return
    try:
        threshold = float(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "Threshold must be a number.\n\nExample:\n/setthreshold 1.0"
        )
        return
    if threshold <= 0:
        await update.message.reply_text("Threshold must be greater than 0.")
        return

    if DB_ENABLED and DB_SESSION_LOCAL:
        with DB_SESSION_LOCAL() as session:
            update_app_settings(
                session,
                threshold=threshold,
                default_threshold=DEFAULT_BTC_ALERT_THRESHOLD_PERCENT,
                default_interval=DEFAULT_AUTOMATIC_CHECK_INTERVAL_SECONDS,
            )
    else:
        state = load_state()
        state["btc_alert_threshold_percent"] = threshold
        save_state(state)
    await update.message.reply_text(
        f"Price movement threshold updated to {threshold}% ✅"
    )


async def set_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sync_user_from_update(update)
    if not _is_admin_update(update):
        await update.message.reply_text(
            "Sorry, only the bot admin can change settings."
        )
        return
    if not context.args:
        await update.message.reply_text(
            "Please provide interval in seconds.\n\nExample:\n/setinterval 300"
        )
        return
    try:
        interval = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "Interval must be a whole number.\n\nExample:\n/setinterval 300"
        )
        return
    if interval <= 0:
        await update.message.reply_text("Interval must be greater than 0.")
        return

    await update_interval_and_reschedule(
        context,
        interval,
    )
    await update.message.reply_text(
        f"Automatic BTC check interval updated to {interval} seconds ✅ Applied immediately."
    )


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sync_user_from_update(update)
    try:
        if not context.args:
            await update.message.reply_text(
                "Choose a coin symbol:", reply_markup=build_price_keyboard()
            )
            return
        requested_symbol = context.args[0].lower()
        if requested_symbol not in COIN_SYMBOL_TO_ID:
            await update.message.reply_text(
                f"Unsupported symbol '{requested_symbol}'.\nSupported symbols: {build_supported_symbols_message()}"
            )
            return
        await send_price_message(update.message, requested_symbol)
    except CoinGeckoRateLimitError:
        await send_manual_rate_limit_message(
            update.message, update.effective_chat.id if update.effective_chat else None
        )
    except ValueError as error:
        await update.message.reply_text(
            f"Price data is temporarily unavailable: {error}"
        )
    except Exception as error:
        await update.message.reply_text("Sorry, I could not get the price right now.")
        print(f"Price error: {error}")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sync_user_from_update(update)
    if not _is_admin_update(update):
        await update.message.reply_text("Sorry, only the bot admin can view status.")
        return
    if DB_ENABLED and DB_SESSION_LOCAL:
        with DB_SESSION_LOCAL() as session:
            btc_state = get_price_state(session, DEFAULT_SYMBOL)
        if btc_state is None:
            await update.message.reply_text("Status: running ✅\n\nNo BTC price has been saved yet.")
            return
        await update.message.reply_text(
            "Status: running ✅\n\n"
            f"Last saved BTC price: ${btc_state.last_price:,.2f}\n"
            f"Last 24h change: {btc_state.last_24h_change:.2f}%\n"
            f"Last checked at: {btc_state.last_checked_at}\n"
            f"Last alert at: {btc_state.last_alert_at}"
        )
        return
    state = load_state()
    last_price = state.get("last_price")
    if last_price is None:
        await update.message.reply_text(
            "Status: running ✅\n\nNo BTC price has been saved yet.\nSend /price first."
        )
        return
    await update.message.reply_text(
        "Status: running ✅\n\n"
        f"Last saved BTC price: ${last_price:,.2f}\n"
        f"Last 24h change: {state.get('last_24h_change'):.2f}%\n"
        f"Last checked at: {state.get('last_checked_at')}\n"
        f"Last alert at: {state.get('last_alert_at')}"
    )


# ---- Callback handlers ----
async def button_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data or ""
    sync_user_from_update(update)

    try:
        if data.startswith("settings:") and not is_admin_user(
            query.from_user.id if query.from_user else None
        ):
            await query.answer("Sorry, only the bot admin can change settings.")
            await query.message.reply_text(
                "Sorry, only the bot admin can change settings."
            )
            return

        await query.answer()

        if data.startswith("price:"):
            await send_price_message(query.message, data.split(":", maxsplit=1)[1])
            return
        if data == "reports:daily":
            await send_daily_report_message(query.message)
            return
        if data == "reports:weekly":
            await send_weekly_report_message(query.message)
            return
        if data == "settings:current":
            if DB_ENABLED and DB_SESSION_LOCAL:
                alert_settings = get_db_alert_settings()
            else:
                state = load_state()
                alert_settings = get_alert_settings(state)
            await query.message.reply_text(
                "Current alert settings ⚙️\n\n"
                f"Price movement threshold: {alert_settings['price_move_alert_percent']}%\n"
                f"Automatic BTC check interval: {alert_settings['automatic_check_interval_seconds']} seconds"
            )
            return
        if data == "settings:threshold_menu":
            await query.message.reply_text(
                "Choose a new threshold:", reply_markup=build_threshold_keyboard()
            )
            return
        if data == "settings:interval_menu":
            await query.message.reply_text(
                "Choose a new check interval:", reply_markup=build_interval_keyboard()
            )
            return
        if data.startswith("settings:set_threshold:"):
            threshold = float(data.rsplit(":", maxsplit=1)[1])
            if DB_ENABLED and DB_SESSION_LOCAL:
                with DB_SESSION_LOCAL() as session:
                    update_app_settings(
                        session,
                        threshold=threshold,
                        default_threshold=DEFAULT_BTC_ALERT_THRESHOLD_PERCENT,
                        default_interval=DEFAULT_AUTOMATIC_CHECK_INTERVAL_SECONDS,
                    )
            else:
                state = load_state()
                state["btc_alert_threshold_percent"] = threshold
                save_state(state)
            await query.message.reply_text(
                f"Price movement threshold updated to {threshold}% ✅"
            )
            return
        if data.startswith("settings:set_interval:"):
            interval = int(data.rsplit(":", maxsplit=1)[1])
            await update_interval_and_reschedule(
                context,
                interval,
            )
            await query.message.reply_text(
                f"Automatic BTC check interval updated to {interval} seconds ✅ Applied immediately."
            )
            return
    except CoinGeckoRateLimitError:
        await send_manual_rate_limit_message(
            query.message, query.message.chat_id if query.message else None
        )
    except ValueError as error:
        await query.message.reply_text(
            f"Price data is temporarily unavailable: {error}"
        )
    except Exception as error:
        log(f"Callback handling error: {error}")
        await query.message.reply_text("Sorry, something went wrong.")


# ---- Scheduled jobs ----
def schedule_automatic_btc_check(app: Application, interval_seconds: int) -> None:
    for job in app.job_queue.get_jobs_by_name(AUTOMATIC_BTC_CHECK_JOB_NAME):
        job.schedule_removal()
    app.job_queue.run_repeating(
        automatic_price_check,
        interval=interval_seconds,
        first=5,
        name=AUTOMATIC_BTC_CHECK_JOB_NAME,
    )
    log(f"Automatic BTC check interval: {interval_seconds} seconds")


def schedule_weekly_report(app: Application) -> None:
    for job in app.job_queue.get_jobs_by_name(WEEKLY_REPORT_JOB_NAME):
        job.schedule_removal()
    if not ENABLE_WEEKLY_REPORT:
        log("Weekly report scheduling is disabled.")
        return

    weekday = WEEKDAY_MAP.get(WEEKLY_REPORT_DAY, WEEKDAY_MAP["sunday"])
    app.job_queue.run_daily(
        send_scheduled_weekly_report,
        time=time(hour=WEEKLY_REPORT_HOUR, minute=0, second=0),
        days=(weekday,),
        name=WEEKLY_REPORT_JOB_NAME,
    )
    log(
        f"Weekly report scheduling enabled: {WEEKLY_REPORT_DAY} at {WEEKLY_REPORT_HOUR:02d}:00 UTC"
    )


def schedule_strong_signal_job(app: Application) -> None:
    for job in app.job_queue.get_jobs_by_name(STRONG_SIGNAL_JOB_NAME):
        job.schedule_removal()
    if not ENABLE_STRONG_SIGNAL_ALERTS:
        log("Strong-signal alerting is disabled.")
        return

    app.job_queue.run_repeating(
        strong_signal_check,
        interval=STRONG_SIGNAL_CHECK_INTERVAL_SECONDS,
        first=15,
        name=STRONG_SIGNAL_JOB_NAME,
    )
    log(
        f"Strong-signal check enabled every {STRONG_SIGNAL_CHECK_INTERVAL_SECONDS} seconds."
    )


async def automatic_price_check(context: ContextTypes.DEFAULT_TYPE):
    app = context.application
    log("Running automatic BTC check...")
    try:
        state = load_state() if not DB_ENABLED else {}
        previous_price = None
        db_row = None
        if DB_ENABLED and DB_SESSION_LOCAL:
            with DB_SESSION_LOCAL() as session:
                db_row = get_price_state(session, DEFAULT_SYMBOL)
                previous_price = db_row.last_price if db_row else None
        else:
            previous_price = state.get("last_price")
        current_price, change_24h, change_7d = await get_btc_market_data()
        checked_at = datetime.now(timezone.utc).isoformat()

        if previous_price is None:
            if DB_ENABLED and DB_SESSION_LOCAL:
                with DB_SESSION_LOCAL() as session:
                    update_price_state(
                        session,
                        symbol=DEFAULT_SYMBOL,
                        last_price=current_price,
                        last_24h_change=change_24h,
                        last_checked_at=datetime.now(timezone.utc),
                        last_alert_at=db_row.last_alert_at if db_row else None,
                    )
            else:
                state.update(
                    {
                        "last_price": current_price,
                        "last_24h_change": change_24h,
                        "last_checked_at": checked_at,
                        "last_alert_at": state.get("last_alert_at"),
                    }
                )
                save_state(state)
            print(f"Initial BTC price saved: ${current_price:,.2f}")
            return

        price_change_percent = calculate_price_change_percent(
            previous_price, current_price
        )
        if DB_ENABLED and DB_SESSION_LOCAL:
            alert_settings = get_db_alert_settings()
        else:
            state.update(
                {
                    "last_price": current_price,
                    "last_24h_change": change_24h,
                    "last_checked_at": checked_at,
                }
            )
            alert_settings = get_alert_settings(state)

        if should_send_alert(
            price_change_percent=price_change_percent,
            threshold_percent=alert_settings["price_move_alert_percent"],
        ):
            news_items = []
            try:
                news_items = fetch_news_context(limit=5)
                alert_payload = await create_ai_alert_payload(
                    previous_price,
                    current_price,
                    price_change_percent,
                    change_24h,
                    change_7d,
                    news_items,
                    alert_threshold_percent=alert_settings["price_move_alert_percent"],
                    check_interval_seconds=alert_settings[
                        "automatic_check_interval_seconds"
                    ],
                )
            except Exception as error:
                log(f"AI alert generation failed: {error}")
                plain_message = build_fallback_alert_message(
                    previous_price=previous_price,
                    current_price=current_price,
                    price_change_percent=price_change_percent,
                    change_24h=change_24h,
                    change_7d=change_7d,
                    alert_threshold_percent=alert_settings["price_move_alert_percent"],
                    check_interval_seconds=alert_settings[
                        "automatic_check_interval_seconds"
                    ],
                )
                alert_payload = {"plain_text": plain_message, "html_text": None}

            html_text = alert_payload.get("html_text")
            plain_text = str(alert_payload.get("plain_text", ""))
            if html_text:
                try:
                    await app.bot.send_message(
                        chat_id=TELEGRAM_CHAT_ID,
                        text=str(html_text),
                        parse_mode=ParseMode.HTML,
                    )
                except Exception as error:
                    log(f"HTML alert send failed; falling back to plain text: {error}")
                    await app.bot.send_message(
                        chat_id=TELEGRAM_CHAT_ID, text=plain_text
                    )
            else:
                await app.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=plain_text)
            remember_news_context(news_items)
            if DB_ENABLED and DB_SESSION_LOCAL:
                with DB_SESSION_LOCAL() as session:
                    update_price_state(
                        session,
                        symbol=DEFAULT_SYMBOL,
                        last_price=current_price,
                        last_24h_change=change_24h,
                        last_checked_at=datetime.now(timezone.utc),
                        last_alert_at=datetime.now(timezone.utc),
                    )
                    save_alert(
                        session,
                        symbol="BTC",
                        alert_type="price_movement",
                        message=plain_text,
                        sent_to_chat_id=int(TELEGRAM_CHAT_ID),
                    )
            else:
                state["last_alert_at"] = checked_at
            log("Alert sent.")
        if not DB_ENABLED:
            save_state(state)
    except CoinGeckoRateLimitError:
        log("CoinGecko returned 429 during automatic BTC check. Skipping this cycle.")
    except httpx.HTTPStatusError as error:
        log(f"Automatic check HTTP error: {error}")
    except Exception as error:
        print(f"Automatic check error: {error}")


async def send_scheduled_weekly_report(context: ContextTypes.DEFAULT_TYPE):
    try:
        price, change_24h, change_7d = await get_btc_market_data()
        news_items = fetch_news_context(limit=6, prefer_unseen=True)
        report = await create_weekly_report(price, change_24h, change_7d, news_items)
        message = report.get("telegram_message") if report else None
        if not message:
            trend_text = "unknown" if change_7d is None else f"{change_7d:+.2f}%"
            message = (
                f"📊 BTC weekly report\n\nPrice: ${price:,.2f}\n24h change: {change_24h:+.2f}%\n7d trend: {trend_text}\n"
                "Risk level: Medium\nPossible action: monitor risk and avoid impulsive action.\nNot financial advice."
            )
        await context.application.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID, text=message
        )
        remember_news_context(news_items)
    except Exception as error:
        log(f"Scheduled weekly report failed: {error}")


async def strong_signal_check(context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    now = datetime.now(timezone.utc)
    last_alert_at = state.get("last_strong_signal_alert_at")
    if last_alert_at:
        try:
            if now - datetime.fromisoformat(last_alert_at) < timedelta(
                hours=STRONG_SIGNAL_COOLDOWN_HOURS
            ):
                return
        except ValueError:
            pass

    price, change_24h, change_7d = await get_btc_market_data()
    news_items = fetch_news_context(limit=6)
    result = await classify_strong_signal(price, change_24h, change_7d, news_items)
    if not result:
        return

    strength = str(result.get("signal_strength", "")).lower()
    if result.get("should_alert") is True and strength in {"medium", "strong"}:
        await context.application.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID, text=str(result.get("telegram_message"))
        )
        remember_news_context(news_items)
        state["last_strong_signal_alert_at"] = now.isoformat()
        state["last_strong_signal_strength"] = strength
        state["last_strong_signal_direction"] = str(
            result.get("direction", "unclear")
        ).lower()
        save_state(state)


# ---- Setup/startup ----
async def setup_bot_commands(app: Application) -> None:
    default_commands = [
        BotCommand("start", "Show bot intro"),
        BotCommand("price", "Check crypto prices"),
        BotCommand("reports", "Open BTC reports menu"),
    ]
    await app.bot.set_my_commands(
        default_commands, scope=BotCommandScopeAllPrivateChats()
    )

    if TELEGRAM_ADMIN_USER_ID:
        admin_commands = default_commands + [
            BotCommand("settings", "Open settings menu"),
            BotCommand("status", "Show bot status"),
        ]
        try:
            admin_chat_id = int(TELEGRAM_ADMIN_USER_ID)
            await app.bot.set_my_commands(
                admin_commands, scope=BotCommandScopeChat(chat_id=admin_chat_id)
            )
        except (TypeError, ValueError):
            log(
                "TELEGRAM_ADMIN_USER_ID is not a numeric ID. Skipping admin-only command scope setup."
            )

    log("Telegram command menu has been updated.")


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is missing. Check your .env file.")
    if not TELEGRAM_CHAT_ID:
        raise ValueError("TELEGRAM_CHAT_ID is missing. Check your .env file.")
    if not TELEGRAM_ADMIN_USER_ID:
        raise ValueError("TELEGRAM_ADMIN_USER_ID is missing. Check your .env file.")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

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

    if DB_ENABLED and DB_SESSION_LOCAL:
        runtime_settings = get_db_alert_settings()
    else:
        runtime_state = load_state()
        runtime_settings = get_alert_settings(runtime_state)
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
