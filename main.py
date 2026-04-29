from datetime import datetime, timezone

import httpx
from ai_agent_groq import create_ai_alert_message
from alert_rules import calculate_price_change_percent, should_send_alert
from config import (
    ALERT_COOLDOWN_MINUTES,
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
    get_btc_price,
    get_coin_price,
)
from storage import load_state, save_state
from telegram import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeChat, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes


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
        [InlineKeyboardButton("Set cooldown", callback_data="settings:cooldown_menu")],
    ])


def build_threshold_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("0.5%", callback_data="settings:set_threshold:0.5")],
        [InlineKeyboardButton("1.0%", callback_data="settings:set_threshold:1.0")],
        [InlineKeyboardButton("2.0%", callback_data="settings:set_threshold:2.0")],
    ])


def build_cooldown_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("10 min", callback_data="settings:set_cooldown:10")],
        [InlineKeyboardButton("30 min", callback_data="settings:set_cooldown:30")],
        [InlineKeyboardButton("60 min", callback_data="settings:set_cooldown:60")],
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


async def set_cooldown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin_user(update.effective_user.id if update.effective_user else None):
        await update.message.reply_text("Sorry, only the bot admin can change settings.")
        return
    if not context.args:
        await update.message.reply_text("Please provide cooldown in minutes.\n\nExample:\n/setcooldown 30")
        return
    try:
        cooldown = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Cooldown must be a whole number.\n\nExample:\n/setcooldown 30")
        return
    if cooldown < 0:
        await update.message.reply_text("Cooldown cannot be negative.")
        return
    state = load_state()
    state["alert_cooldown_minutes"] = cooldown
    save_state(state)
    await update.message.reply_text(f"Alert cooldown updated to {cooldown} minutes ✅")


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
        await update.message.reply_text("CoinGecko rate limit reached. Please wait a bit and try again.")
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
                f"Alert cooldown: {alert_settings['alert_cooldown_minutes']} minutes"
            )
            return
        if data == "settings:threshold_menu":
            await query.message.reply_text("Choose a new threshold:", reply_markup=build_threshold_keyboard())
            return
        if data == "settings:cooldown_menu":
            await query.message.reply_text("Choose a new cooldown:", reply_markup=build_cooldown_keyboard())
            return
        if data.startswith("settings:set_threshold:"):
            threshold = float(data.rsplit(":", maxsplit=1)[1])
            state = load_state()
            state["price_move_alert_percent"] = threshold
            save_state(state)
            await query.message.reply_text(f"Price movement threshold updated to {threshold}% ✅")
            return
        if data.startswith("settings:set_cooldown:"):
            cooldown = int(data.rsplit(":", maxsplit=1)[1])
            state = load_state()
            state["alert_cooldown_minutes"] = cooldown
            save_state(state)
            await query.message.reply_text(f"Alert cooldown updated to {cooldown} minutes ✅")
            return

    except CoinGeckoRateLimitError:
        await query.message.reply_text("CoinGecko rate limit reached. Please wait a bit and try again.")
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
        current_price, change_24h = await get_btc_price()
        checked_at = datetime.now(timezone.utc).isoformat()
        if previous_price is None:
            state.update({"last_price": current_price, "last_24h_change": change_24h, "last_checked_at": checked_at, "last_alert_at": state.get("last_alert_at")})
            save_state(state)
            print(f"Initial BTC price saved: ${current_price:,.2f}")
            return
        price_change_percent = calculate_price_change_percent(previous_price, current_price)
        state.update({"last_price": current_price, "last_24h_change": change_24h, "last_checked_at": checked_at})
        alert_settings = get_alert_settings(state)
        movement_is_big_enough, cooldown_is_active, should_alert = should_send_alert(
            price_change_percent=price_change_percent,
            threshold_percent=alert_settings["price_move_alert_percent"],
            last_alert_at=state.get("last_alert_at"),
            cooldown_minutes=alert_settings["alert_cooldown_minutes"],
        )
        if should_alert:
            try:
                news_items = fetch_crypto_news(limit=5)
                message = await create_ai_alert_message(previous_price, current_price, price_change_percent, change_24h, news_items)
            except Exception as error:
                log(f"AI alert generation failed: {error}")
                direction = "up" if price_change_percent > 0 else "down"
                message = (
                    "🚨 BTC price alert\n\n"
                    f"BTC moved {direction} by {price_change_percent:.2f}% since last check.\n\n"
                    f"Previous price: ${previous_price:,.2f}\nCurrent price: ${current_price:,.2f}\n"
                    f"24h change: {change_24h:.2f}%\n\nAI summary was unavailable, so this is a basic alert."
                )
            await app.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
            state["last_alert_at"] = checked_at
            log("Alert sent.")
        elif movement_is_big_enough and cooldown_is_active:
            log("Alert skipped because cooldown is active.")
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
        "alert_cooldown_minutes": int(state.get("alert_cooldown_minutes", ALERT_COOLDOWN_MINUTES)),
    }


async def setup_bot_commands(app: Application) -> None:
    default_commands = [BotCommand("start", "Show bot intro"), BotCommand("price", "Check crypto prices")]
    await app.bot.set_my_commands(default_commands, scope=BotCommandScopeAllPrivateChats())
    if TELEGRAM_ADMIN_USER_ID:
        admin_commands = default_commands + [BotCommand("settings", "Open settings menu"), BotCommand("status", "Show bot status")]
        await app.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=int(TELEGRAM_ADMIN_USER_ID)))
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
    app.add_handler(CommandHandler("setcooldown", set_cooldown))
    app.add_handler(CallbackQueryHandler(button_router))
    app.job_queue.run_repeating(automatic_price_check, interval=60, first=5)
    log("Bot is running. Automatic BTC checks are enabled.")
    app.post_init = setup_bot_commands
    app.run_polling()


if __name__ == "__main__":
    main()
