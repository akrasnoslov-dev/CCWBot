import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from hashlib import sha256
from time import perf_counter
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from telegram.constants import ParseMode
from telegram.ext import Application, ContextTypes

from ai_agent_groq import (
    GROQ_MODEL,
    build_fallback_alert_message,
    classify_strong_signal,
    create_ai_alert_payload,
    sanitize_alert_message,
)
from alert_rules import (
    calculate_price_change_percent,
    should_send_alert,
)
from bot.news import fetch_news_context, remember_news_context
from bot.reports import send_scheduled_weekly_report
from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL, log
from bot.settings import get_db_alert_settings, get_state_alert_settings
from config import (
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
    ensure_default_coin_subscriptions,
    get_active_users_with_alert_preferences,
    get_event_ai_analysis,
    get_last_sent_alert_at,
    get_latest_success_event_ai_analysis,
    get_or_create_market_event,
    get_price_state,
    make_news_key,
    reserve_alert_delivery,
    save_alert,
    save_event_ai_analysis,
    update_alert_delivery_status,
    update_price_state,
)
from premium import can_deliver_now, is_coin_unlocked_for_user
from price_service import (
    DEFAULT_SYMBOL,
    CoinGeckoRateLimitError,
    get_btc_market_data,
    get_coin_market_data_batch,
)
from storage import load_state, save_state
from supported_coins import SUPPORTED_COINS, SUPPORTED_SYMBOLS, normalize_symbol

logger = logging.getLogger(__name__)

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


COIN_ALIASES = {
    "btc": ("btc", "bitcoin"),
    "eth": ("eth", "ethereum", "ether"),
    "sol": ("sol", "solana"),
    "xrp": ("xrp", "ripple"),
    "bnb": ("bnb", "binance coin", "binancecoin"),
    "doge": ("doge", "dogecoin"),
    "ada": ("ada", "cardano"),
    "ton": ("ton", "toncoin", "the open network"),
    "link": ("link", "chainlink"),
    "trx": ("trx", "tron"),
}
MARKET_WIDE_NEWS_TERMS = (
    "crypto market",
    "cryptocurrency market",
    "digital asset",
    "digital assets",
    "market-wide",
    "regulation",
    "regulatory",
    "sec",
    "fed",
    "federal reserve",
    "interest rate",
    "rates",
    "macro",
    "inflation",
    "exchange",
    "hack",
    "etf",
    "dominance",
)


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
    """Build one key for one observed price movement.

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
    normalized_symbol = normalize_symbol(symbol)
    return f"{normalized_symbol}:price_movement:{sha256(encoded.encode('utf-8')).hexdigest()[:24]}"


def _coin_name(symbol: str) -> str:
    return str(SUPPORTED_COINS[normalize_symbol(symbol)]["name"])


def classify_news_relevance(symbol: str, news_item: dict) -> str:
    """Classify RSS item relevance before it reaches the LLM."""
    normalized_symbol = normalize_symbol(symbol)
    title = str(news_item.get("title") or "")
    summary = str(news_item.get("summary") or "")
    text = f" {title} {summary} ".lower()
    aliases = COIN_ALIASES.get(normalized_symbol, (normalized_symbol,))
    for alias in aliases:
        if re_search_word(alias.lower(), text):
            return "direct"
    if any(term in text for term in MARKET_WIDE_NEWS_TERMS):
        if normalized_symbol != "btc" and re_search_word("bitcoin", text):
            broader_terms = ("crypto", "market", "dominance", "etf", "macro", "regulation")
            if not any(term in text for term in broader_terms):
                return "irrelevant"
        return "market_wide"
    return "irrelevant"


def re_search_word(term: str, text: str) -> bool:
    escaped = re.escape(term)
    if re.fullmatch(r"[a-z0-9]+", term):
        return re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", text) is not None
    return term in text


def filter_news_for_symbol(
    symbol: str,
    news_items: list[dict],
    *,
    max_direct: int = 3,
    max_market_wide: int = 2,
) -> list[dict]:
    direct: list[dict] = []
    market_wide: list[dict] = []
    for item in news_items:
        relevance = classify_news_relevance(symbol, item)
        if relevance == "direct" and len(direct) < max_direct:
            direct.append(item)
        elif relevance == "market_wide" and len(market_wide) < max_market_wide:
            market_wide.append(item)
    return direct + market_wide


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


async def resolve_symbols_to_check(now: datetime | None = None) -> list[str]:
    """Resolve globally needed symbols from active eligible watchlists."""
    now = now or datetime.now(timezone.utc)
    if not DB_ENABLED or not DB_SESSION_LOCAL:
        return [DEFAULT_SYMBOL] if TELEGRAM_CHAT_ID else []

    async with DB_SESSION_LOCAL() as session:
        users = await get_active_users_with_alert_preferences(session)
        enabled_symbols: set[str] = set()
        for user in users:
            subscriptions = await ensure_default_coin_subscriptions(session, user_id=user.id)
            subscription_by_symbol = {row.symbol: row for row in subscriptions}
            for symbol in SUPPORTED_SYMBOLS:
                row = subscription_by_symbol.get(symbol)
                if row is None or not row.is_enabled:
                    continue
                if not is_coin_unlocked_for_user(user, symbol, now):
                    continue
                enabled_symbols.add(symbol)
    return [symbol for symbol in SUPPORTED_SYMBOLS if symbol in enabled_symbols]


async def get_alert_recipients(
    symbol: str,
    event_type: str,
    *,
    now: datetime | None = None,
) -> list[AlertRecipient]:
    """Resolve eligible recipients once for one market event."""
    normalized_symbol = normalize_symbol(symbol)
    if event_type != "price_movement" or normalized_symbol not in SUPPORTED_COINS:
        return []

    if DB_ENABLED and DB_SESSION_LOCAL:
        now = now or datetime.now(timezone.utc)
        recipients = []
        seen_chat_ids = set()
        async with DB_SESSION_LOCAL() as session:
            for user in await get_active_users_with_alert_preferences(session):
                if user.telegram_chat_id is None:
                    continue
                subscriptions = await ensure_default_coin_subscriptions(session, user_id=user.id)
                subscription_by_symbol = {row.symbol: row for row in subscriptions}
                subscription = subscription_by_symbol.get(normalized_symbol)
                if subscription is None or not subscription.is_enabled:
                    continue
                last_sent_at = await get_last_sent_alert_at(
                    session,
                    user_id=user.id,
                    symbol=normalized_symbol,
                )
                if not can_deliver_now(user, normalized_symbol, now, last_sent_at):
                    continue
                chat_id = int(user.telegram_chat_id)
                if chat_id in seen_chat_ids:
                    continue
                seen_chat_ids.add(chat_id)
                recipients.append(AlertRecipient(chat_id=chat_id, user_id=user.id))
        return recipients

    if normalized_symbol == DEFAULT_SYMBOL and TELEGRAM_CHAT_ID:
        return [AlertRecipient(chat_id=int(TELEGRAM_CHAT_ID))]
    return []


async def _get_or_create_price_movement_market_event(
    *,
    symbol: str,
    previous_price: float,
    current_price: float,
    price_change_percent: float,
    change_24h: float,
    change_7d: float | None,
) -> tuple[int | None, str | None]:
    if not DB_ENABLED or not DB_SESSION_LOCAL:
        return None, None

    event_key = _build_price_movement_event_key(
        symbol=symbol,
        previous_price=previous_price,
        current_price=current_price,
        price_change_percent=price_change_percent,
    )
    async with DB_SESSION_LOCAL() as session:
        market_event = await get_or_create_market_event(
            session,
            symbol=normalize_symbol(symbol),
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
    symbol: str,
    market_event_id: int | None,
    previous_price: float,
    current_price: float,
    price_change_percent: float,
    change_24h: float,
    change_7d: float | None,
    news_items: list[dict],
    alert_settings: dict,
    force_fallback: bool = False,
) -> tuple[dict, int | None]:
    """Create or reuse the single AI analysis for one market event.

    The LLM call stays here, before recipient delivery, so one market event
    produces one analysis that can be sent to many active users.
    """
    input_hash = _build_alert_ai_input_hash(
        symbol=symbol,
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
            saved_analysis = await get_latest_success_event_ai_analysis(
                session,
                market_event_id=market_event_id,
            )
            if saved_analysis and saved_analysis.plain_text:
                display_symbol = normalize_symbol(symbol).upper()
                log(f"Reusing saved AI analysis for {display_symbol} market event.")
                return (
                    {
                        "plain_text": saved_analysis.plain_text,
                        "html_text": saved_analysis.html_text,
                    },
                    saved_analysis.id,
                )
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
                display_symbol = normalize_symbol(symbol).upper()
                log(f"Reusing saved AI analysis for {display_symbol} market event.")
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
    if force_fallback:
        provider = "fallback"
        model = "deterministic"
        error_message = "AI disabled for this automatic check cycle."
        plain_message = build_fallback_alert_message(
            previous_price=previous_price,
            current_price=current_price,
            price_change_percent=price_change_percent,
            change_24h=change_24h,
            change_7d=change_7d,
            alert_threshold_percent=alert_settings["price_move_alert_percent"],
            check_interval_seconds=alert_settings["automatic_check_interval_seconds"],
            symbol=normalize_symbol(symbol).upper(),
            coin_name=_coin_name(symbol),
        )
        alert_payload = {"plain_text": plain_message, "html_text": None}
    else:
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
                symbol=normalize_symbol(symbol).upper(),
                coin_name=_coin_name(symbol),
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
                symbol=normalize_symbol(symbol).upper(),
                coin_name=_coin_name(symbol),
            )
            alert_payload = {"plain_text": plain_message, "html_text": None}
    if alert_payload.get("rate_limited"):
        provider = "fallback"
        model = "deterministic"
        error_message = "Groq rate limit reached."

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


def _sanitize_alert_payload(alert_payload: dict) -> dict:
    plain_text = str(alert_payload.get("plain_text", ""))
    sanitized_plain_text = sanitize_alert_message(plain_text)
    html_text = alert_payload.get("html_text")
    if sanitized_plain_text != plain_text:
        html_text = None
    return {"plain_text": sanitized_plain_text, "html_text": html_text}


async def _record_alert_delivery(
    *,
    symbol: str,
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
            symbol=symbol,
            alert_type="price_movement",
            message=plain_text,
            sent_to_chat_id=recipient.chat_id,
            market_event_id=market_event_id,
            event_ai_analysis_id=event_ai_analysis_id,
            user_id=recipient.user_id,
            status=status,
            error_message=error_message,
        )


async def _save_price_state(
    *,
    symbol: str,
    state: dict,
    current_price: float,
    change_24h: float,
    checked_at: str,
    last_alert_at: datetime | None = None,
) -> None:
    if DB_ENABLED and DB_SESSION_LOCAL:
        async with DB_SESSION_LOCAL() as session:
            await update_price_state(
                session,
                symbol=symbol,
                last_price=current_price,
                last_24h_change=change_24h,
                last_checked_at=datetime.now(timezone.utc),
                last_alert_at=last_alert_at,
            )
        return

    state.update(
        {
            "last_price": current_price,
            "last_24h_change": change_24h,
            "last_checked_at": checked_at,
        }
    )
    if last_alert_at is not None:
        state["last_alert_at"] = checked_at
    save_state(state)


async def _deliver_market_event_alert(
    app: Application,
    *,
    symbol: str,
    alert_payload: dict,
    market_event_id: int | None,
    event_ai_analysis_id: int | None,
    recipients: list[AlertRecipient] | None = None,
) -> bool:
    """Send one sanitized event analysis to every resolved recipient."""
    alert_payload = _sanitize_alert_payload(alert_payload)
    normalized_symbol = normalize_symbol(symbol)
    if recipients is None:
        recipients = await get_alert_recipients(
            symbol=normalized_symbol,
            event_type="price_movement",
        )
    if not recipients:
        log(f"No eligible recipients for {normalized_symbol.upper()} price movement alert.")
        return False

    plain_text = str(alert_payload.get("plain_text", ""))
    delivered = False
    sent_count = 0
    skipped_count = 0
    for recipient in recipients:
        if DB_ENABLED and DB_SESSION_LOCAL and recipient.user_id is not None and market_event_id:
            async with DB_SESSION_LOCAL() as session:
                alert_row, should_send = await reserve_alert_delivery(
                    session,
                    user_id=recipient.user_id,
                    symbol=normalized_symbol,
                    alert_type="price_movement",
                    sent_to_chat_id=recipient.chat_id,
                    market_event_id=market_event_id,
                    event_ai_analysis_id=event_ai_analysis_id,
                    message=plain_text,
                )
                alert_id = alert_row.id
            if not should_send:
                skipped_count += 1
                continue
        else:
            alert_id = None
        sent, error_message = await _send_alert_to_recipient(app, recipient, alert_payload)
        if DB_ENABLED and DB_SESSION_LOCAL and alert_id is not None:
            async with DB_SESSION_LOCAL() as session:
                await update_alert_delivery_status(
                    session,
                    alert_id=alert_id,
                    status="sent" if sent else "failed",
                    error_message=error_message,
                )
        else:
            await _record_alert_delivery(
                symbol=normalized_symbol,
                recipient=recipient,
                plain_text=plain_text,
                status="sent" if sent else "failed",
                market_event_id=market_event_id,
                event_ai_analysis_id=event_ai_analysis_id,
                error_message=error_message,
            )
        if sent:
            delivered = True
            sent_count += 1
        else:
            log(f"Alert delivery failed for chat {recipient.chat_id}: {error_message}")
    log(
        f"{normalized_symbol.upper()} alert sent to {sent_count}/{len(recipients)} "
        f"eligible recipients; skipped duplicates={skipped_count}."
    )
    return delivered


def schedule_automatic_btc_check(app: Application, interval_seconds: int) -> None:
    for job in app.job_queue.get_jobs_by_name(AUTOMATIC_BTC_CHECK_JOB_NAME):
        job.schedule_removal()
    app.job_queue.run_repeating(
        automatic_price_check,
        interval=interval_seconds,
        first=5,
        name=AUTOMATIC_BTC_CHECK_JOB_NAME,
        job_kwargs={"max_instances": 1, "coalesce": True, "misfire_grace_time": 15},
    )
    log(f"Automatic price check interval: {interval_seconds} seconds")


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
    cycle_started_at = perf_counter()
    logger.debug("Running automatic price check.")
    try:
        db_active = DB_ENABLED and DB_SESSION_LOCAL
        now = datetime.now(timezone.utc)
        symbols_to_check = await resolve_symbols_to_check(now)
        if not symbols_to_check:
            logger.debug("Automatic price check skipped because no eligible symbols are enabled.")
            return

        state = load_state() if not db_active else {}
        market_data = await get_coin_market_data_batch(symbols_to_check)
        if not market_data:
            log("Automatic price check skipped because CoinGecko returned no usable symbol data.")
            return
        checked_at = datetime.now(timezone.utc).isoformat()

        if DB_ENABLED and DB_SESSION_LOCAL:
            alert_settings = await get_db_alert_settings()
        else:
            alert_settings = get_state_alert_settings(state)

        raw_news_items: list[dict] | None = None
        used_news_items: list[dict] = []
        delivered_symbols = 0
        ai_disabled_for_cycle = False
        for symbol in symbols_to_check:
            symbol_data = market_data.get(symbol)
            if not symbol_data:
                continue
            current_price = float(symbol_data["price"])
            change_24h = float(symbol_data.get("change_24h") or 0.0)
            change_7d = symbol_data.get("change_7d")
            previous_price = None
            last_alert_at = None
            db_row = None
            if DB_ENABLED and DB_SESSION_LOCAL:
                async with DB_SESSION_LOCAL() as session:
                    db_row = await get_price_state(session, symbol)
                    previous_price = db_row.last_price if db_row else None
                    last_alert_at = db_row.last_alert_at if db_row else None
            else:
                previous_price = state.get("last_price") if symbol == DEFAULT_SYMBOL else None
                last_alert_at = _parse_state_alert_at(state.get("last_alert_at"))

            if previous_price is None:
                await _save_price_state(
                    symbol=symbol,
                    state=state,
                    current_price=current_price,
                    change_24h=change_24h,
                    checked_at=checked_at,
                    last_alert_at=last_alert_at,
                )
                log(f"Initial {symbol.upper()} price saved: ${current_price:,.2f}")
                continue

            price_change_percent = calculate_price_change_percent(previous_price, current_price)
            logger.debug(
                "%s movement calculated: previous=%.2f current=%.2f move=%.4f%% "
                "change24h=%.4f%% change7d=%s",
                symbol.upper(),
                previous_price,
                current_price,
                price_change_percent,
                change_24h,
                change_7d,
            )

            delivered = False
            if should_send_alert(
                price_change_percent=price_change_percent,
                threshold_percent=alert_settings["price_move_alert_percent"],
            ):
                recipients = await get_alert_recipients(
                    symbol=symbol,
                    event_type="price_movement",
                    now=now,
                )
                if not recipients:
                    log(
                        f"No eligible recipients for {symbol.upper()} price movement alert. "
                        "Skipping AI analysis."
                    )
                    await _save_price_state(
                        symbol=symbol,
                        state=state,
                        current_price=current_price,
                        change_24h=change_24h,
                        checked_at=checked_at,
                        last_alert_at=None,
                    )
                    continue
                if raw_news_items is None:
                    raw_news_items = await fetch_news_context(limit=12)
                news_items = filter_news_for_symbol(symbol, raw_news_items)
                used_news_items.extend(news_items)
                market_event_id, _ = await _get_or_create_price_movement_market_event(
                    symbol=symbol,
                    previous_price=previous_price,
                    current_price=current_price,
                    price_change_percent=price_change_percent,
                    change_24h=change_24h,
                    change_7d=change_7d if isinstance(change_7d, float) else None,
                )
                ai_started_at = perf_counter()
                alert_payload, event_ai_analysis_id = await _get_or_create_event_ai_analysis(
                    symbol=symbol,
                    market_event_id=market_event_id,
                    previous_price=previous_price,
                    current_price=current_price,
                    price_change_percent=price_change_percent,
                    change_24h=change_24h,
                    change_7d=change_7d if isinstance(change_7d, float) else None,
                    news_items=news_items,
                    alert_settings=alert_settings,
                    force_fallback=ai_disabled_for_cycle,
                )
                logger.info(
                    "%s AI analysis resolved in %.2f seconds.",
                    symbol.upper(),
                    perf_counter() - ai_started_at,
                )
                if alert_payload.get("rate_limited") and not ai_disabled_for_cycle:
                    ai_disabled_for_cycle = True
                    log("AI disabled for this cycle because Groq rate limit was reached.")
                delivered = await _deliver_market_event_alert(
                    app,
                    symbol=symbol,
                    alert_payload=alert_payload,
                    market_event_id=market_event_id,
                    event_ai_analysis_id=event_ai_analysis_id,
                    recipients=recipients,
                )
                if delivered:
                    delivered_symbols += 1
            await _save_price_state(
                symbol=symbol,
                state=state,
                current_price=current_price,
                change_24h=change_24h,
                checked_at=checked_at,
                last_alert_at=(datetime.now(timezone.utc) if delivered else None),
            )
        if used_news_items:
            deduped_news = list({make_news_key(item): item for item in used_news_items}.values())
            await remember_news_context(deduped_news)
        if not db_active:
            save_state(state)
        checked_symbols_text = ", ".join(symbol.upper() for symbol in symbols_to_check)
        log(
            f"Automatic price check completed for symbols: {checked_symbols_text}; "
            f"delivered alerts for {delivered_symbols} symbol(s)."
        )
    except CoinGeckoRateLimitError:
        log("CoinGecko returned 429 during automatic price check. Skipping this cycle.")
    except httpx.HTTPStatusError as error:
        log(f"Automatic check HTTP error: {error}")
    except Exception as error:
        log(f"Automatic check error: {error}")
    finally:
        logger.info(
            "Automatic price check cycle completed in %.2f seconds.",
            perf_counter() - cycle_started_at,
        )


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
        message = sanitize_alert_message(str(result.get("telegram_message") or ""))
        if not message:
            return
        await context.application.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID, text=message
        )
        await remember_news_context(news_items)
        state["last_strong_signal_alert_at"] = now.isoformat()
        state["last_strong_signal_strength"] = strength
        state["last_strong_signal_direction"] = str(result.get("direction", "unclear")).lower()
        save_state(state)
