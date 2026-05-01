from datetime import datetime, timezone

import httpx
from ai_agent_groq import build_fallback_alert_message, create_ai_alert_message
from alert_rules import calculate_price_change_percent, should_send_alert
from config import (
    AUTOMATIC_CHECK_INTERVAL_SECONDS,
    PRICE_MOVE_ALERT_PERCENT,
    TELEGRAM_ADMIN_USER_ID,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
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
from telegram import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeChat, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

MANUAL_RATE_LIMIT_MESSAGE_COOLDOWN_SECONDS = 120
AUTOMATIC_BTC_CHECK_JOB_NAME = "automatic_btc_check"
_MANUAL_RATE_LIMIT_LAST_SENT_AT_BY_CHAT: dict[int, float] = {}


def log(message: str) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{timestamp}] {message}")


def is_admin_user(user_id: int | str | None) -> bool:
    if user_id is None or TELEGRAM_ADMIN_USER_ID is None:
        return False
    return str(user_id) == str(TELEGRAM_ADMIN_USER_ID)


def build_supported_symbols_message() -> str:
    return ", ".join(COIN_SYMBOL_TO_ID.keys())


def build_price_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("BTC", callback_data="price:btc"), InlineKeyboardButton("ETH", callback_data="price:eth")],
        [InlineKeyboardButton("TON", callback_data="price:ton"), InlineKeyboardButton("USDT", callback_data="price:usdt")],
    ])


def build_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Current settings", callback_data="settings:current")],
        [InlineKeyboardButton("Set threshold", callback_data="settings:threshold_menu")],
        [InlineKeyboardButton("Set check interval", callback_data="settings:interval_menu")],
    ])


def build_threshold_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("0.5%", callback_data="settings:set_threshold:0.5")],
        [InlineKeyboardButton("1.0%", callback_data="settings:set_threshold:1.0")],
        [InlineKeyboardButton("2.0%", callback_data="settings:set_threshold:2.0")],
    ])


def build_interval_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("60 sec", callback_data="settings:set_interval:60")],
        [InlineKeyboardButton("300 sec", callback_data="settings:set_interval:300")],
        [InlineKeyboardButton("600 sec", callback_data="settings:set_interval:600")],
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_admin = is_admin_user(update.effective_user.id if update.effective_user else None)
    message = (
        "Hi! I’m CCWBot 🚀\n\n"
        "I monitor crypto prices and send automatic BTC alerts.\n\n"
        "Use:\n"
        "/price - check crypto prices"
    )
    if is_admin:
        message += "\n/settings - open settings menu\n/status - show bot status"
    await update.message.reply_text(message)


async def user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_value = update.effective_user.id if update.effective_user else "unknown"
    await update.message.reply_text(f"Your Telegram user ID is: {user_id_value}")


async def chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin_user(update.effective_user.id if update.effective_user else None):
        await update.message.reply_text("Sorry, only the bot admin can view chat ID.")
        return
    await update.message.reply_text(f"Your chat ID is: {update.effective_chat.id}")


async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin_user(update.effective_user.id if update.effective_user else None):
        await update.message.reply_text("Sorry, only the bot admin can access settings.")
        return
    await update.message.reply_text("Settings menu ⚙️", reply_markup=build_settings_keyboard())


async def set_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin_user(update.effective_user.id if update.effective_user else None):
        await update.message.reply_text("Sorry, only the bot admin can change settings.")
        return
    if not context.args:
        await update.message.reply_text("Please provide a threshold value.\n\nExample:\n/setthreshold 1.0")
        return
    try:
        threshold = float(context.args[0])
    except ValueError:
        await update.message.reply_text("Threshold must be a number.\n\nExample:\n/setthreshold 1.0")
        return
    if threshold <= 0:
        await update.message.reply_text("Threshold must be greater than 0.")
        return
    state = load_state()
    state["price_move_alert_percent"] = threshold
    save_state(state)
    await update.message.reply_text(f"Price movement threshold updated to {threshold}% ✅")


async def set_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin_user(update.effective_user.id if update.effective_user else None):
        await update.message.reply_text("Sorry, only the bot admin can change settings.")
        return
    if not context.args:
        await update.message.reply_text("Please provide interval in seconds.\n\nExample:\n/setinterval 300")
        return
    try:
        interval = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Interval must be a whole number.\n\nExample:\n/setinterval 300")
        return
    if interval <= 0:
        await update.message.reply_text("Interval must be greater than 0.")
        return
    await update_interval_and_reschedule(context, interval)
    await update.message.reply_text(
        f"Automatic BTC check interval updated to {interval} seconds ✅ Applied immediately."
    )


def schedule_automatic_btc_check(app: Application, interval_seconds: int) -> None:
    existing_jobs = app.job_queue.get_jobs_by_name(AUTOMATIC_BTC_CHECK_JOB_NAME)
    for job in existing_jobs:
        job.schedule_removal()
    app.job_queue.run_repeating(
        automatic_price_check,
        interval=interval_seconds,
        first=5,
        name=AUTOMATIC_BTC_CHECK_JOB_NAME,
    )
    log(f"Automatic BTC check interval: {interval_seconds} seconds")


async def update_interval_and_reschedule(context: ContextTypes.DEFAULT_TYPE, interval: int) -> None:
    state = load_state()
    state["automatic_check_interval_seconds"] = interval
    save_state(state)
    schedule_automatic_btc_check(context.application, interval)

async def send_price_message(target, symbol: str) -> None:
    coin_price, change_24h, resolved_symbol = await get_coin_price(symbol)
    checked_at = datetime.now(timezone.utc).isoformat()
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
        await target.reply_text("CoinGecko rate limit reached. Please wait a bit and try again.")
        return
    now_ts = datetime.now(timezone.utc).timestamp()
    last_sent_ts = _MANUAL_RATE_LIMIT_LAST_SENT_AT_BY_CHAT.get(chat_id)
    if last_sent_ts is not None and (now_ts - last_sent_ts) < MANUAL_RATE_LIMIT_MESSAGE_COOLDOWN_SECONDS:
        return
    _MANUAL_RATE_LIMIT_LAST_SENT_AT_BY_CHAT[chat_id] = now_ts
    await target.reply_text("CoinGecko rate limit reached. Please wait a bit and try again.")


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("Choose a coin symbol:", reply_markup=build_price_keyboard())
            return
        requested_symbol = context.args[0].lower()
        if requested_symbol not in COIN_SYMBOL_TO_ID:
            await update.message.reply_text(
                f"Unsupported symbol '{requested_symbol}'.\nSupported symbols: {build_supported_symbols_message()}"
            )
            return
        await send_price_message(update.message, requested_symbol)
    except CoinGeckoRateLimitError:
        await send_manual_rate_limit_message(update.message, update.effective_chat.id if update.effective_chat else None)
    except ValueError as error:
        await update.message.reply_text(f"Price data is temporarily unavailable: {error}")
    except Exception as error:
        await update.message.reply_text("Sorry, I could not get the price right now.")
        print(f"Price error: {error}")


async def button_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data or ""

    try:
        if data.startswith("settings:") and not is_admin_user(query.from_user.id if query.from_user else None):
            await query.answer("Sorry, only the bot admin can change settings.")
            await query.message.reply_text("Sorry, only the bot admin can change settings.")
            return

        await query.answer()

        if data.startswith("price:"):
            await send_price_message(query.message, data.split(":", maxsplit=1)[1])
            return
        if data == "settings:current":
            state = load_state()
            alert_settings = get_alert_settings(state)
            await query.message.reply_text(
                "Current alert settings ⚙️\n\n"
                f"Price movement threshold: {alert_settings['price_move_alert_percent']}%\n"
                f"Automatic BTC check interval: {alert_settings['automatic_check_interval_seconds']} seconds"
            )
            return
        if data == "settings:threshold_menu":
            await query.message.reply_text("Choose a new threshold:", reply_markup=build_threshold_keyboard())
            return
        if data == "settings:interval_menu":
            await query.message.reply_text("Choose a new check interval:", reply_markup=build_interval_keyboard())
            return
        if data.startswith("settings:set_threshold:"):
            threshold = float(data.rsplit(":", maxsplit=1)[1])
            state = load_state()
            state["price_move_alert_percent"] = threshold
            save_state(state)
            await query.message.reply_text(f"Price movement threshold updated to {threshold}% ✅")
            return
        if data.startswith("settings:set_interval:"):
            interval = int(data.rsplit(":", maxsplit=1)[1])
            await update_interval_and_reschedule(context, interval)
            await query.message.reply_text(
                f"Automatic BTC check interval updated to {interval} seconds ✅ Applied immediately."
            )
            return

    except CoinGeckoRateLimitError:
        await send_manual_rate_limit_message(query.message, query.message.chat_id if query.message else None)
    except ValueError as error:
        await query.message.reply_text(f"Price data is temporarily unavailable: {error}")
    except Exception as error:
        log(f"Callback handling error: {error}")
        await query.message.reply_text("Sorry, something went wrong.")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin_user(update.effective_user.id if update.effective_user else None):
        await update.message.reply_text("Sorry, only the bot admin can view status.")
        return
    state = load_state()
    last_price = state.get("last_price")
    if last_price is None:
        await update.message.reply_text("Status: running ✅\n\nNo BTC price has been saved yet.\nSend /price first.")
        return
    await update.message.reply_text(
        "Status: running ✅\n\n"
        f"Last saved BTC price: ${last_price:,.2f}\n"
        f"Last 24h change: {state.get('last_24h_change'):.2f}%\n"
        f"Last checked at: {state.get('last_checked_at')}\n"
        f"Last alert at: {state.get('last_alert_at')}"
    )


async def automatic_price_check(context: ContextTypes.DEFAULT_TYPE):
    app = context.application
    log("Running automatic BTC check...")
    try:
        state = load_state()
        previous_price = state.get("last_price")
        current_price, change_24h, change_7d = await get_btc_market_data()
        checked_at = datetime.now(timezone.utc).isoformat()
        if previous_price is None:
            state.update({"last_price": current_price, "last_24h_change": change_24h, "last_checked_at": checked_at, "last_alert_at": state.get("last_alert_at")})
            save_state(state)
            print(f"Initial BTC price saved: ${current_price:,.2f}")
            return
        price_change_percent = calculate_price_change_percent(previous_price, current_price)
        state.update({"last_price": current_price, "last_24h_change": change_24h, "last_checked_at": checked_at})
        alert_settings = get_alert_settings(state)
        should_alert = should_send_alert(
            price_change_percent=price_change_percent,
            threshold_percent=alert_settings["price_move_alert_percent"],
        )
        if should_alert:
            try:
                news_items = fetch_crypto_news(limit=5)
                message = await create_ai_alert_message(
                    previous_price,
                    current_price,
                    price_change_percent,
                    change_24h,
                    change_7d,
                    news_items,
                )
            except Exception as error:
                log(f"AI alert generation failed: {error}")
                message = build_fallback_alert_message(
                    previous_price=previous_price,
                    current_price=current_price,
                    price_change_percent=price_change_percent,
                    change_24h=change_24h,
                    change_7d=change_7d,
                )
            await app.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
            state["last_alert_at"] = checked_at
            log("Alert sent.")
        save_state(state)
    except CoinGeckoRateLimitError:
        log("CoinGecko returned 429 during automatic BTC check. Skipping this cycle.")
    except httpx.HTTPStatusError as error:
        log(f"Automatic check HTTP error: {error}")
    except Exception as error:
        print(f"Automatic check error: {error}")


def get_alert_settings(state: dict) -> dict:
    return {
        "price_move_alert_percent": float(state.get("price_move_alert_percent", PRICE_MOVE_ALERT_PERCENT)),
        "automatic_check_interval_seconds": int(state.get("automatic_check_interval_seconds", AUTOMATIC_CHECK_INTERVAL_SECONDS)),
    }


async def setup_bot_commands(app: Application) -> None:
    default_commands = [BotCommand("start", "Show bot intro"), BotCommand("price", "Check crypto prices")]
    await app.bot.set_my_commands(default_commands, scope=BotCommandScopeAllPrivateChats())
    if TELEGRAM_ADMIN_USER_ID:
        admin_commands = default_commands + [BotCommand("settings", "Open settings menu"), BotCommand("status", "Show bot status")]
        try:
            admin_chat_id = int(TELEGRAM_ADMIN_USER_ID)
            await app.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_chat_id))
        except (TypeError, ValueError):
            log("TELEGRAM_ADMIN_USER_ID is not a numeric ID. Skipping admin-only command scope setup.")
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
    app.add_handler(CommandHandler("setthreshold", set_threshold))
    app.add_handler(CommandHandler("setcooldown", set_interval))
    app.add_handler(CommandHandler("setinterval", set_interval))
    app.add_handler(CallbackQueryHandler(button_router))
    runtime_state = load_state()
    runtime_settings = get_alert_settings(runtime_state)
    schedule_automatic_btc_check(app, runtime_settings["automatic_check_interval_seconds"])
    log("Bot is running. Automatic BTC checks are enabled.")
    app.post_init = setup_bot_commands
    app.run_polling()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Bot stopped by user.")
