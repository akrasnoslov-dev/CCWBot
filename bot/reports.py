import time

from telegram.ext import ContextTypes

from bot.config import TELEGRAM_CHAT_ID
from bot.db.database import save_alert
from bot.news import fetch_news_context, remember_news_context
from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL, log
from bot.services.ai_agent_groq import (
    build_fallback_alert_message,
    create_daily_report,
    create_weekly_report,
    sanitize_alert_message,
)
from bot.services.price_service import get_btc_market_data

REPORT_COOLDOWN_SECONDS = 60
REPORT_RATE_LIMIT_PRUNE_AFTER_SECONDS = 3600
_last_report_call: dict[tuple[int, str], float] = {}


def _target_chat_id(target) -> int | None:
    chat_id = getattr(target, "chat_id", None)
    if chat_id is not None:
        return int(chat_id)
    chat = getattr(target, "chat", None)
    chat_id = getattr(chat, "id", None)
    return int(chat_id) if chat_id is not None else None


def _is_report_rate_limited(chat_id: int | None, report_type: str) -> bool:
    if chat_id is None:
        return False
    now = time.monotonic()
    stale_before = now - REPORT_RATE_LIMIT_PRUNE_AFTER_SECONDS
    for key, last_seen_at in list(_last_report_call.items()):
        if last_seen_at < stale_before:
            _last_report_call.pop(key, None)
    key = (chat_id, report_type)
    last_call_at = _last_report_call.get(key)
    if last_call_at is not None and now - last_call_at < REPORT_COOLDOWN_SECONDS:
        return True
    _last_report_call[key] = now
    return False


async def send_daily_report_message(target) -> None:
    chat_id = _target_chat_id(target)
    if _is_report_rate_limited(chat_id, "daily"):
        await target.reply_text("Please wait a minute before requesting another daily report.")
        return
    try:
        price, change_24h, change_7d = await get_btc_market_data()
        news_items = await fetch_news_context(limit=5, prefer_unseen=True)
        report = await create_daily_report(price, change_24h, news_items)
        if report and report.get("telegram_message"):
            message = sanitize_alert_message(str(report["telegram_message"]))
            await target.reply_text(message)
            await remember_news_context(news_items)
            if DB_ENABLED and DB_SESSION_LOCAL and chat_id is not None:
                async with DB_SESSION_LOCAL() as session:
                    await save_alert(
                        session,
                        symbol="BTC",
                        alert_type="daily_report",
                        message=message,
                        sent_to_chat_id=chat_id,
                    )
            return
        await target.reply_text(
            sanitize_alert_message(
                build_fallback_alert_message(price, price, 0.0, change_24h, change_7d)
            )
        )
    except Exception as error:
        log(f"Daily report generation failed: {error}")
        await target.reply_text(
            "Daily report unavailable. Monitor risk and avoid impulsive action.\n"
            "Not financial advice."
        )


async def send_weekly_report_message(target) -> None:
    chat_id = _target_chat_id(target)
    if _is_report_rate_limited(chat_id, "weekly"):
        await target.reply_text("Please wait a minute before requesting another weekly report.")
        return
    try:
        price, change_24h, change_7d = await get_btc_market_data()
        news_items = await fetch_news_context(limit=6, prefer_unseen=True)
        report = await create_weekly_report(price, change_24h, change_7d, news_items)
        if report and report.get("telegram_message"):
            message = sanitize_alert_message(str(report["telegram_message"]))
            await target.reply_text(message)
            await remember_news_context(news_items)
            if DB_ENABLED and DB_SESSION_LOCAL and chat_id is not None:
                async with DB_SESSION_LOCAL() as session:
                    await save_alert(
                        session,
                        symbol="BTC",
                        alert_type="weekly_report",
                        message=message,
                        sent_to_chat_id=chat_id,
                    )
            return
        trend_text = "unknown" if change_7d is None else f"{change_7d:+.2f}%"
        message = (
            f"BTC weekly report\n\nPrice: ${price:,.2f}\n"
            f"24h change: {change_24h:+.2f}%\n7d trend: {trend_text}\n"
            "Risk level: Medium\n"
            "Possible action: consider waiting for clearer confirmation.\n"
            "Not financial advice."
        )
        await target.reply_text(sanitize_alert_message(message))
    except Exception as error:
        log(f"Weekly report generation failed: {error}")


async def send_scheduled_weekly_report(context: ContextTypes.DEFAULT_TYPE):
    try:
        price, change_24h, change_7d = await get_btc_market_data()
        news_items = await fetch_news_context(limit=6, prefer_unseen=True)
        report = await create_weekly_report(price, change_24h, change_7d, news_items)
        message = report.get("telegram_message") if report else None
        if not message:
            trend_text = "unknown" if change_7d is None else f"{change_7d:+.2f}%"
            message = (
                f"BTC weekly report\n\nPrice: ${price:,.2f}\n"
                f"24h change: {change_24h:+.2f}%\n7d trend: {trend_text}\n"
                "Risk level: Medium\n"
                "Possible action: monitor risk and avoid impulsive action.\n"
                "Not financial advice."
            )
        message = sanitize_alert_message(str(message))
        await context.application.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        await remember_news_context(news_items)
    except Exception as error:
        log(f"Scheduled weekly report failed: {error}")
