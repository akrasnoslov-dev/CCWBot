from telegram.ext import ContextTypes

from ai_agent_groq import (
    build_fallback_alert_message,
    create_daily_report,
    create_weekly_report,
)
from bot.news import fetch_news_context, remember_news_context
from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL, log
from config import TELEGRAM_CHAT_ID
from database import save_alert
from price_service import get_btc_market_data


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
            "Daily report unavailable. Monitor risk and avoid impulsive action.\n"
            "Not financial advice."
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
            f"📊 BTC weekly report\n\nPrice: ${price:,.2f}\n"
            f"24h change: {change_24h:+.2f}%\n7d trend: {trend_text}\n"
            "Risk level: Medium\n"
            "Possible action: consider waiting for clearer confirmation.\n"
            "Not financial advice."
        )
    except Exception as error:
        log(f"Weekly report generation failed: {error}")


async def send_scheduled_weekly_report(context: ContextTypes.DEFAULT_TYPE):
    try:
        price, change_24h, change_7d = await get_btc_market_data()
        news_items = fetch_news_context(limit=6, prefer_unseen=True)
        report = await create_weekly_report(price, change_24h, change_7d, news_items)
        message = report.get("telegram_message") if report else None
        if not message:
            trend_text = "unknown" if change_7d is None else f"{change_7d:+.2f}%"
            message = (
                f"📊 BTC weekly report\n\nPrice: ${price:,.2f}\n"
                f"24h change: {change_24h:+.2f}%\n7d trend: {trend_text}\n"
                "Risk level: Medium\n"
                "Possible action: monitor risk and avoid impulsive action.\n"
                "Not financial advice."
            )
        await context.application.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        remember_news_context(news_items)
    except Exception as error:
        log(f"Scheduled weekly report failed: {error}")
