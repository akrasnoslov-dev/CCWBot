import json
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from hashlib import sha256
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from telegram.constants import ParseMode
from telegram.ext import Application, ContextTypes

from ai_agent_groq import (
    GROQ_MODEL,
    build_fallback_alert_message,
    classify_strong_signal,
    create_ai_alert_payload,
)
from alert_rules import (
    calculate_price_change_percent,
    is_cooldown_active,
    should_send_alert,
)
from bot.news import fetch_news_context, remember_news_context
from bot.reports import send_scheduled_weekly_report
from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL, log
from bot.settings import get_db_alert_settings, get_state_alert_settings
from config import (
    ALERT_COOLDOWN_MINUTES,
    ENABLE_STRONG_SIGNAL_ALERTS,
    ENABLE_WEEKLY_REPORT,
    SEEN_NEWS_KEEP_LATEST,
    STRONG_SIGNAL_CHECK_INTERVAL_SECONDS,
    STRONG_SIGNAL_COOLDOWN_HOURS,
    TELEGRAM_CHAT_ID,
    WEEKLY_REPORT_DAY,
    WEEKLY_REPORT_HOUR,
)
from database import (
    cleanup_seen_news,
    get_active_users_with_chat_ids,
    get_event_ai_analysis,
    get_or_create_market_event,
    get_price_state,
    make_news_key,
    save_alert,
    save_event_ai_analysis,
    update_price_state,
)
from price_service import (
    DEFAULT_SYMBOL,
    CoinGeckoRateLimitError,
    get_btc_market_data,
)
from storage import load_state, save_state

AUTOMATIC_BTC_CHECK_JOB_NAME = "automatic_btc_check"
WEEKLY_REPORT_JOB_NAME = "weekly_report"
STRONG_SIGNAL_JOB_NAME = "strong_signal"
SEEN_NEWS_CLEANUP_JOB_NAME = "seen_news_cleanup"
WEEKDAY_MAP = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


@dataclass(frozen=True)
class AlertRecipient:
    chat_id: int
    user_id: int | None = None


def _stable_float(value: float | None, digits: int) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def _stable_news_link(link: str) -> str:
    parsed = urlsplit(link.strip())
    query_params = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
    ]
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/") or parsed.path,
            urlencode(sorted(query_params)),
            "",
        )
    )


def _build_price_movement_event_key(
    *,
    symbol: str,
    previous_price: float,
    current_price: float,
    price_change_percent: float,
) -> str:
    """Build one key for one observed BTC price movement.

    Prices are rounded to cents and movement to 4 decimals so retries for the
    same check reuse the event, while genuinely different movements do not
    collapse into a broad time bucket.
    """
    key_parts = {
        "symbol": symbol.upper(),
        "event_type": "price_movement",
        "previous_price": _stable_float(previous_price, 2),
        "price": _stable_float(current_price, 2),
        "price_change_percent": _stable_float(price_change_percent, 4),
    }
    encoded = json.dumps(key_parts, sort_keys=True, separators=(",", ":"))
    return f"btc:price_movement:{sha256(encoded.encode('utf-8')).hexdigest()[:24]}"


def _build_alert_ai_input_hash(
    *,
    symbol: str,
    event_type: str,
    previous_price: float,
    current_price: float,
    price_change_percent: float,
    change_24h: float,
    change_7d: float | None,
    news_items: list[dict],
    alert_threshold_percent: float,
    check_interval_seconds: int,
) -> str:
    news_context = [
        {
            "key": make_news_key(item),
            "title": str(item.get("title") or ""),
            "source": str(item.get("source") or ""),
            "link": _stable_news_link(str(item.get("link") or "")),
        }
        for item in news_items
    ]
    payload = {
        "symbol": symbol.upper(),
        "event_type": event_type,
        "previous_price": _stable_float(previous_price, 2),
        "price": _stable_float(current_price, 2),
        "price_change_percent": _stable_float(price_change_percent, 4),
        "change_24h": _stable_float(change_24h, 4),
        "change_7d": _stable_float(change_7d, 4),
        "alert_threshold_percent": _stable_float(alert_threshold_percent, 4),
        "check_interval_seconds": int(check_interval_seconds),
        "news": news_context,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


async def get_alert_recipients(symbol: str, event_type: str) -> list[AlertRecipient]:
    """Resolve recipients for automatic alerts.

    Automatic alerts are still BTC-only. This boundary exists so future
    subscription logic can expand recipients without changing event analysis.
    """
    if symbol.upper() != "BTC" or event_type != "price_movement":
        return []

    if DB_ENABLED and DB_SESSION_LOCAL:
        recipients = []
        seen_chat_ids = set()
        async with DB_SESSION_LOCAL() as session:
            for user in await get_active_users_with_chat_ids(session):
                if user.telegram_chat_id is None:
                    continue
                chat_id = int(user.telegram_chat_id)
                if chat_id in seen_chat_ids:
                    continue
                seen_chat_ids.add(chat_id)
                recipients.append(AlertRecipient(chat_id=chat_id, user_id=user.id))
        return recipients

    if TELEGRAM_CHAT_ID:
        return [AlertRecipient(chat_id=int(TELEGRAM_CHAT_ID))]
    return []


async def _get_or_create_btc_market_event(
    *,
    previous_price: float,
    current_price: float,
    price_change_percent: float,
    change_24h: float,
    change_7d: float | None,
) -> tuple[int | None, str | None]:
    if not DB_ENABLED or not DB_SESSION_LOCAL:
        return None, None

    event_key = _build_price_movement_event_key(
        symbol=DEFAULT_SYMBOL,
        previous_price=previous_price,
        current_price=current_price,
        price_change_percent=price_change_percent,
    )
    async with DB_SESSION_LOCAL() as session:
        market_event = await get_or_create_market_event(
            session,
            symbol=DEFAULT_SYMBOL,
            event_type="price_movement",
            event_key=event_key,
            price=current_price,
            previous_price=previous_price,
            price_change_percent=price_change_percent,
            last_24h_change=change_24h,
            last_7d_change=change_7d,
            detected_at=datetime.now(timezone.utc),
        )
        return market_event.id, event_key


async def _get_or_create_event_ai_analysis(
    *,
    market_event_id: int | None,
    previous_price: float,
    current_price: float,
    price_change_percent: float,
    change_24h: float,
    change_7d: float | None,
    news_items: list[dict],
    alert_settings: dict,
) -> tuple[dict, int | None]:
    input_hash = _build_alert_ai_input_hash(
        symbol=DEFAULT_SYMBOL,
        event_type="price_movement",
        previous_price=previous_price,
        current_price=current_price,
        price_change_percent=price_change_percent,
        change_24h=change_24h,
        change_7d=change_7d,
        news_items=news_items,
        alert_threshold_percent=alert_settings["price_move_alert_percent"],
        check_interval_seconds=alert_settings["automatic_check_interval_seconds"],
    )

    if DB_ENABLED and DB_SESSION_LOCAL and market_event_id:
        async with DB_SESSION_LOCAL() as session:
            existing_analysis = await get_event_ai_analysis(
                session,
                market_event_id=market_event_id,
                input_hash=input_hash,
            )
            if (
                existing_analysis
                and existing_analysis.status in {"success", "completed"}
                and existing_analysis.plain_text
            ):
                log("Reusing saved AI analysis for BTC market event.")
                return (
                    {
                        "plain_text": existing_analysis.plain_text,
                        "html_text": existing_analysis.html_text,
                    },
                    existing_analysis.id,
                )

    provider = "groq"
    model = GROQ_MODEL
    error_message = None
    try:
        alert_payload = await create_ai_alert_payload(
            previous_price,
            current_price,
            price_change_percent,
            change_24h,
            change_7d,
            news_items,
            alert_threshold_percent=alert_settings["price_move_alert_percent"],
            check_interval_seconds=alert_settings["automatic_check_interval_seconds"],
        )
    except Exception as error:
        log(f"AI alert generation failed: {error}")
        provider = "fallback"
        model = "deterministic"
        error_message = str(error)
        plain_message = build_fallback_alert_message(
            previous_price=previous_price,
            current_price=current_price,
            price_change_percent=price_change_percent,
            change_24h=change_24h,
            change_7d=change_7d,
            alert_threshold_percent=alert_settings["price_move_alert_percent"],
            check_interval_seconds=alert_settings["automatic_check_interval_seconds"],
        )
        alert_payload = {"plain_text": plain_message, "html_text": None}

    event_ai_analysis_id = None
    if DB_ENABLED and DB_SESSION_LOCAL and market_event_id:
        async with DB_SESSION_LOCAL() as session:
            analysis = await save_event_ai_analysis(
                session,
                market_event_id=market_event_id,
                provider=provider,
                model=model,
                input_hash=input_hash,
                analysis_text=str(alert_payload.get("plain_text", "")),
                plain_text=str(alert_payload.get("plain_text", "")),
                html_text=alert_payload.get("html_text"),
                status="success",
                error_message=error_message,
            )
            event_ai_analysis_id = analysis.id if analysis else None
    return alert_payload, event_ai_analysis_id


async def _send_alert_to_recipient(
    app: Application, recipient: AlertRecipient, alert_payload: dict
) -> tuple[bool, str | None]:
    html_text = alert_payload.get("html_text")
    plain_text = str(alert_payload.get("plain_text", ""))
    try:
        if html_text:
            try:
                await app.bot.send_message(
                    chat_id=recipient.chat_id,
                    text=str(html_text),
                    parse_mode=ParseMode.HTML,
                )
            except Exception as error:
                log(f"HTML alert send failed; falling back to plain text: {error}")
                await app.bot.send_message(chat_id=recipient.chat_id, text=plain_text)
        else:
            await app.bot.send_message(chat_id=recipient.chat_id, text=plain_text)
    except Exception as error:
        return False, str(error)
    return True, None


async def _record_alert_delivery(
    *,
    recipient: AlertRecipient,
    plain_text: str,
    status: str,
    market_event_id: int | None,
    event_ai_analysis_id: int | None,
    error_message: str | None = None,
) -> None:
    if not DB_ENABLED or not DB_SESSION_LOCAL:
        return

    async with DB_SESSION_LOCAL() as session:
        await save_alert(
            session,
            symbol="BTC",
            alert_type="price_movement",
            message=plain_text,
            sent_to_chat_id=recipient.chat_id,
            market_event_id=market_event_id,
            event_ai_analysis_id=event_ai_analysis_id,
            user_id=recipient.user_id,
            status=status,
            error_message=error_message,
        )


async def _deliver_btc_market_event_alert(
    app: Application,
    *,
    alert_payload: dict,
    market_event_id: int | None,
    event_ai_analysis_id: int | None,
) -> bool:
    recipients = await get_alert_recipients(symbol="BTC", event_type="price_movement")
    if not recipients:
        log("No configured recipients for BTC price movement alert.")
        return False

    plain_text = str(alert_payload.get("plain_text", ""))
    delivered = False
    for recipient in recipients:
        sent, error_message = await _send_alert_to_recipient(app, recipient, alert_payload)
        await _record_alert_delivery(
            recipient=recipient,
            plain_text=plain_text,
            status="sent" if sent else "failed",
            market_event_id=market_event_id,
            event_ai_analysis_id=event_ai_analysis_id,
            error_message=error_message,
        )
        if sent:
            delivered = True
        else:
            log(f"Alert delivery failed for chat {recipient.chat_id}: {error_message}")
    return delivered


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
    log(f"Weekly report scheduling enabled: {WEEKLY_REPORT_DAY} at {WEEKLY_REPORT_HOUR:02d}:00 UTC")


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
    log(f"Strong-signal check enabled every {STRONG_SIGNAL_CHECK_INTERVAL_SECONDS} seconds.")


def schedule_seen_news_cleanup(app: Application) -> None:
    for job in app.job_queue.get_jobs_by_name(SEEN_NEWS_CLEANUP_JOB_NAME):
        job.schedule_removal()
    if not DB_ENABLED or not DB_SESSION_LOCAL:
        log("Seen news cleanup scheduling is disabled because database storage is off.")
        return

    app.job_queue.run_daily(
        cleanup_seen_news_job,
        time=time(hour=3, minute=0, second=0),
        name=SEEN_NEWS_CLEANUP_JOB_NAME,
    )
    log(f"Seen news cleanup scheduled daily; keeping latest {SEEN_NEWS_KEEP_LATEST}.")


async def cleanup_seen_news_job(context: ContextTypes.DEFAULT_TYPE):
    if not DB_ENABLED or not DB_SESSION_LOCAL:
        return
    try:
        async with DB_SESSION_LOCAL() as session:
            deleted_count = await cleanup_seen_news(session, keep_latest=SEEN_NEWS_KEEP_LATEST)
        log(f"Seen news cleanup removed {deleted_count} rows.")
    except Exception as error:
        log(f"Seen news cleanup error: {error}")


def _parse_state_alert_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


async def automatic_price_check(context: ContextTypes.DEFAULT_TYPE):
    app = context.application
    log("Running automatic BTC check...")
    try:
        db_active = DB_ENABLED and DB_SESSION_LOCAL
        state = load_state() if not db_active else {}
        previous_price = None
        last_alert_at = None
        db_row = None
        if DB_ENABLED and DB_SESSION_LOCAL:
            async with DB_SESSION_LOCAL() as session:
                db_row = await get_price_state(session, DEFAULT_SYMBOL)
                previous_price = db_row.last_price if db_row else None
                last_alert_at = db_row.last_alert_at if db_row else None
        else:
            previous_price = state.get("last_price")
            last_alert_at = _parse_state_alert_at(state.get("last_alert_at"))
        current_price, change_24h, change_7d = await get_btc_market_data()
        checked_at = datetime.now(timezone.utc).isoformat()

        if previous_price is None:
            if DB_ENABLED and DB_SESSION_LOCAL:
                async with DB_SESSION_LOCAL() as session:
                    await update_price_state(
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
            log(f"Initial BTC price saved: ${current_price:,.2f}")
            return

        price_change_percent = calculate_price_change_percent(previous_price, current_price)
        if DB_ENABLED and DB_SESSION_LOCAL:
            alert_settings = await get_db_alert_settings()
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
            if is_cooldown_active(last_alert_at, ALERT_COOLDOWN_MINUTES):
                log("BTC movement alert skipped because cooldown is active.")
                if DB_ENABLED and DB_SESSION_LOCAL:
                    async with DB_SESSION_LOCAL() as session:
                        await update_price_state(
                            session,
                            symbol=DEFAULT_SYMBOL,
                            last_price=current_price,
                            last_24h_change=change_24h,
                            last_checked_at=datetime.now(timezone.utc),
                            last_alert_at=last_alert_at,
                        )
                else:
                    save_state(state)
                return

            news_items = await fetch_news_context(limit=5)
            market_event_id, _ = await _get_or_create_btc_market_event(
                previous_price=previous_price,
                current_price=current_price,
                price_change_percent=price_change_percent,
                change_24h=change_24h,
                change_7d=change_7d,
            )
            alert_payload, event_ai_analysis_id = await _get_or_create_event_ai_analysis(
                market_event_id=market_event_id,
                previous_price=previous_price,
                current_price=current_price,
                price_change_percent=price_change_percent,
                change_24h=change_24h,
                change_7d=change_7d,
                news_items=news_items,
                alert_settings=alert_settings,
            )
            delivered = await _deliver_btc_market_event_alert(
                app,
                alert_payload=alert_payload,
                market_event_id=market_event_id,
                event_ai_analysis_id=event_ai_analysis_id,
            )
            if delivered:
                await remember_news_context(news_items)
            if DB_ENABLED and DB_SESSION_LOCAL:
                async with DB_SESSION_LOCAL() as session:
                    await update_price_state(
                        session,
                        symbol=DEFAULT_SYMBOL,
                        last_price=current_price,
                        last_24h_change=change_24h,
                        last_checked_at=datetime.now(timezone.utc),
                        last_alert_at=(datetime.now(timezone.utc) if delivered else None),
                    )
            else:
                if delivered:
                    state["last_alert_at"] = checked_at
            log("Alert sent." if delivered else "Alert was not delivered.")
        if not db_active:
            save_state(state)
    except CoinGeckoRateLimitError:
        log("CoinGecko returned 429 during automatic BTC check. Skipping this cycle.")
    except httpx.HTTPStatusError as error:
        log(f"Automatic check HTTP error: {error}")
    except Exception as error:
        log(f"Automatic check error: {error}")


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
    news_items = await fetch_news_context(limit=6)
    result = await classify_strong_signal(price, change_24h, change_7d, news_items)
    if not result:
        return

    strength = str(result.get("signal_strength", "")).lower()
    if result.get("should_alert") is True and strength in {"medium", "strong"}:
        await context.application.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID, text=str(result.get("telegram_message"))
        )
        await remember_news_context(news_items)
        state["last_strong_signal_alert_at"] = now.isoformat()
        state["last_strong_signal_strength"] = strength
        state["last_strong_signal_direction"] = str(result.get("direction", "unclear")).lower()
        save_state(state)
