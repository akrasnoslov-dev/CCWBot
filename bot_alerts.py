from datetime import datetime, time, timedelta, timezone

import httpx
from ai_agent_groq import (
    build_fallback_alert_message,
    classify_strong_signal,
    create_ai_alert_payload,
)
from alert_rules import calculate_price_change_percent, should_send_alert
from config import (
    ENABLE_STRONG_SIGNAL_ALERTS,
    ENABLE_WEEKLY_REPORT,
    STRONG_SIGNAL_CHECK_INTERVAL_SECONDS,
    STRONG_SIGNAL_COOLDOWN_HOURS,
    TELEGRAM_CHAT_ID,
    WEEKLY_REPORT_DAY,
    WEEKLY_REPORT_HOUR,
)
from database import get_price_state, save_alert, update_price_state
from price_service import (
    DEFAULT_SYMBOL,
    CoinGeckoRateLimitError,
    get_btc_market_data,
)
from storage import load_state, save_state
from telegram.constants import ParseMode
from telegram.ext import Application, ContextTypes

from bot_news import fetch_news_context, remember_news_context
from bot_reports import send_scheduled_weekly_report
from bot_runtime import DB_ENABLED, DB_SESSION_LOCAL, log
from bot_settings import get_db_alert_settings, get_state_alert_settings

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
            alert_settings = get_state_alert_settings(state)

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
