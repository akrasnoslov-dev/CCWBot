from datetime import datetime, timezone

from ai_agent_groq import create_ai_alert_message
from alert_rules import calculate_price_change_percent, should_send_alert
from config import (
    ALERT_COOLDOWN_MINUTES,
    PRICE_MOVE_ALERT_PERCENT,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)
from news_service import fetch_crypto_news
from price_service import get_btc_price
from storage import load_state, save_state
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


def log(message: str) -> None:
    """Print message with UTC timestamp."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{timestamp}] {message}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! I am your BTC Watcher Bot. 🚀\n\n"
        "Available commands:\n"
        "/price - get current BTC price\n"
        "/status - show last saved BTC data\n"
        "/chatid - show your Telegram chat ID"
    )


async def chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Your chat ID is: {update.effective_chat.id}")


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        btc_price, change_24h = await get_btc_price()

        checked_at = datetime.now(timezone.utc).isoformat()

        state = load_state()
        state["last_price"] = btc_price
        state["last_24h_change"] = change_24h
        state["last_checked_at"] = checked_at

        if "last_alert_at" not in state:
            state["last_alert_at"] = None

        save_state(state)

        message = (
            "BTC price\n\n"
            f"Current price: ${btc_price:,.2f}\n"
            f"24h change: {change_24h:.2f}%"
        )

        await update.message.reply_text(message)

    except Exception as error:
        await update.message.reply_text(
            "Sorry, I could not get the BTC price right now."
        )
        print(f"Price error: {error}")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()

    last_price = state.get("last_price")
    last_24h_change = state.get("last_24h_change")
    last_checked_at = state.get("last_checked_at")
    last_alert_at = state.get("last_alert_at")

    if last_price is None:
        await update.message.reply_text(
            "Status: running ✅\n\n"
            "No BTC price has been saved yet.\n"
            "Send /price first."
        )
        return

    message = (
        "Status: running ✅\n\n"
        f"Last saved BTC price: ${last_price:,.2f}\n"
        f"Last 24h change: {last_24h_change:.2f}%\n"
        f"Last checked at: {last_checked_at}\n"
        f"Last alert at: {last_alert_at}"
    )

    await update.message.reply_text(message)


async def automatic_price_check(context: ContextTypes.DEFAULT_TYPE):
    """Check BTC price in the background and send alert if movement is big enough."""
    app = context.application

    log("Running automatic BTC check...")

    try:
        state = load_state()

        previous_price = state.get("last_price")
        current_price, change_24h = await get_btc_price()
        checked_at = datetime.now(timezone.utc).isoformat()

        # First automatic check: save price, but do not alert yet.
        if previous_price is None:
            state["last_price"] = current_price
            state["last_24h_change"] = change_24h
            state["last_checked_at"] = checked_at
            state["last_alert_at"] = state.get("last_alert_at")
            save_state(state)

            print(f"Initial BTC price saved: ${current_price:,.2f}")
            return

        price_change_percent = calculate_price_change_percent(
            previous_price,
            current_price,
        )

        state["last_price"] = current_price
        state["last_24h_change"] = change_24h
        state["last_checked_at"] = checked_at

        movement_is_big_enough, cooldown_is_active, should_alert = should_send_alert(
            price_change_percent=price_change_percent,
            threshold_percent=PRICE_MOVE_ALERT_PERCENT,
            last_alert_at=state.get("last_alert_at"),
            cooldown_minutes=ALERT_COOLDOWN_MINUTES,
        )
        print(
            f"Raw change: {price_change_percent:.6f}%, "
            f"threshold: {PRICE_MOVE_ALERT_PERCENT}%, "
            f"movement_is_big_enough: {movement_is_big_enough}, "
            f"cooldown_is_active: {cooldown_is_active}, "
            f"should_alert: {should_alert}"
        )

        if should_alert:
            try:
                news_items = fetch_crypto_news(limit=5)

                log(f"Fetched {len(news_items)} news items for AI context.")

                message = await create_ai_alert_message(
                    previous_price=previous_price,
                    current_price=current_price,
                    price_change_percent=price_change_percent,
                    change_24h=change_24h,
                    news_items=news_items,
                )
            except Exception as error:
                log(f"AI alert generation failed: {error}")

                direction = "up" if price_change_percent > 0 else "down"

                message = (
                    "🚨 BTC price alert\n\n"
                    f"BTC moved {direction} by {price_change_percent:.2f}% since last check.\n\n"
                    f"Previous price: ${previous_price:,.2f}\n"
                    f"Current price: ${current_price:,.2f}\n"
                    f"24h change: {change_24h:.2f}%\n\n"
                    "AI summary was unavailable, so this is a basic alert."
                )

            await app.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=message,
            )

            state["last_alert_at"] = checked_at
            log("Alert sent.")
        elif movement_is_big_enough and cooldown_is_active:
            log("Alert skipped because cooldown is active.")
        save_state(state)

        log(
            f"Checked BTC: ${current_price:,.2f}, "
            f"change since last check: {price_change_percent:.2f}%"
        )

    except Exception as error:
        print(f"Automatic check error: {error}")


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is missing. Check your .env file.")

    if not TELEGRAM_CHAT_ID:
        raise ValueError("TELEGRAM_CHAT_ID is missing. Check your .env file.")

    # if not OPENAI_API_KEY:
    # raise ValueError("OPENAI_API_KEY is missing. Check your .env file.")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("chatid", chat_id))

    app.job_queue.run_repeating(
        automatic_price_check,
        interval=60,
        first=5,
    )

    log("Bot is running. Automatic BTC checks are enabled.")
    log("Open Telegram and send /start, /price, or /status.")

    app.run_polling()


if __name__ == "__main__":
    main()
