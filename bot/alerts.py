import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from hashlib import sha256
from time import perf_counter
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from telegram.constants import ParseMode
from telegram.ext import Application, ContextTypes

from bot.alerting.alert_rules import calculate_price_change_percent
from bot.alerting.alert_severity import (
    AlertDecision,
    AlertSeverity,
    AlertType,
    SeverityEvaluation,
    SeverityInput,
    alert_title_action,
    evaluate_alert_severity,
    thresholds_for_symbol,
)
from bot.alerting.notification_decision import (
    NotificationDecision,
    NotificationDirection,
    NotificationSeverity,
    NotificationType,
    SignalContext,
    TriggerSource,
    decide_notification,
)
from bot.config import (
    ENABLE_STRONG_SIGNAL_ALERTS,
    ENABLE_WEEKLY_REPORT,
    SEEN_NEWS_KEEP_LATEST,
    STRONG_SIGNAL_CHECK_INTERVAL_SECONDS,
    STRONG_SIGNAL_COOLDOWN_HOURS,
    TELEGRAM_CHAT_ID,
    WEEKLY_REPORT_DAY,
    WEEKLY_REPORT_HOUR,
)
from bot.db.database import (
    cleanup_seen_news,
    get_active_users_with_alert_preferences,
    get_event_ai_analysis,
    get_last_sent_alert,
    get_last_sent_alert_at,
    get_latest_success_event_ai_analysis,
    get_or_create_market_event,
    get_price_snapshots_since,
    get_price_state,
    get_reference_price_snapshot,
    get_user_symbol_alert_state,
    make_news_key,
    mark_user_bot_blocked,
    reserve_alert_delivery,
    save_alert,
    save_event_ai_analysis,
    save_price_snapshot,
    update_alert_delivery_status,
    update_price_state,
    upsert_user_symbol_alert_state,
)
from bot.domain.premium import (
    can_deliver_now,
    get_effective_frequency_seconds,
    is_coin_unlocked_for_user,
)
from bot.domain.supported_coins import SUPPORTED_COINS, SUPPORTED_SYMBOLS, normalize_symbol
from bot.news import fetch_news_context, remember_news_context
from bot.reports import send_scheduled_weekly_report
from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL, log
from bot.services.ai_agent_groq import (
    GROQ_MODEL,
    build_fallback_alert_message,
    classify_strong_signal,
    create_ai_alert_payload,
    sanitize_alert_message,
)
from bot.services.price_service import (
    DEFAULT_SYMBOL,
    CoinGeckoRateLimitError,
    get_btc_market_data,
    get_coin_market_data_batch,
)
from bot.settings import get_db_alert_settings, get_state_alert_settings
from bot.storage import load_state, save_state
from bot.telegram_errors import is_bot_blocked_error

logger = logging.getLogger(__name__)

PRODUCT_ALERT_TYPES = {
    NotificationType.MARKET_UPDATE.value,
    NotificationType.IMPORTANT_ALERT.value,
    NotificationType.CRITICAL_ALERT.value,
}
DELIVERABLE_ALERT_TYPES = {alert_type.value for alert_type in AlertType} | PRODUCT_ALERT_TYPES
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
    alert_frequency_seconds: int | None = field(default=None, compare=False)


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
MATERIAL_NEWS_TERMS = (
    "approval",
    "approved",
    "rejection",
    "rejected",
    "etf flow",
    "etf inflow",
    "etf outflow",
    "law passed",
    "bill passed",
    "regulation passed",
    "enforcement action",
    "lawsuit",
    "settlement",
    "major exchange",
    "outage",
    "hack",
    "bankruptcy",
    "exploit",
    "liquidation cascade",
    "central bank",
    "government statement",
    "institutional adoption",
    "institutional exit",
)
GENERIC_NEWS_TERMS = (
    "analysis",
    "analyst",
    "bear trap",
    "euphoria",
    "prediction",
    "price target",
    "could",
    "may",
    "might",
    "sentiment",
    "speculation",
    "commentary",
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
    event_type: str = "price_movement",
    previous_price: float,
    current_price: float,
    price_change_percent: float,
    event_bucket: str | None = None,
) -> str:
    """Build one key for one observed price movement.

    Prices are rounded to cents and movement to 4 decimals so retries for the
    same check reuse the event, while genuinely different movements do not
    collapse into a broad time bucket.
    """
    key_parts = {
        "symbol": symbol.upper(),
        "event_type": event_type,
        "previous_price": _stable_float(previous_price, 2),
        "price": _stable_float(current_price, 2),
        "price_change_percent": _stable_float(price_change_percent, 4),
        "event_bucket": event_bucket,
    }
    encoded = json.dumps(key_parts, sort_keys=True, separators=(",", ":"))
    normalized_symbol = normalize_symbol(symbol)
    return f"{normalized_symbol}:{event_type}:{sha256(encoded.encode('utf-8')).hexdigest()[:24]}"


def _build_strong_signal_event_key(
    *,
    price: float,
    change_24h: float,
    change_7d: float | None,
    news_items: list[dict],
) -> str:
    key_parts = {
        "symbol": "BTC",
        "event_type": "strong_signal",
        "price": _stable_float(price, 2),
        "change_24h": _stable_float(change_24h, 4),
        "change_7d": _stable_float(change_7d, 4),
        "news": [
            {
                "key": make_news_key(item),
                "title": str(item.get("title") or ""),
                "source": str(item.get("source") or ""),
                "link": _stable_news_link(str(item.get("link") or "")),
            }
            for item in news_items
        ],
    }
    encoded = json.dumps(key_parts, sort_keys=True, separators=(",", ":"))
    return f"btc:strong_signal:{sha256(encoded.encode('utf-8')).hexdigest()[:24]}"


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


def is_material_news_item(news_item: dict) -> bool:
    title = str(news_item.get("title") or "")
    summary = str(news_item.get("summary") or "")
    text = f" {title} {summary} ".lower()
    return any(term in text for term in MATERIAL_NEWS_TERMS)


def is_generic_news_item(news_item: dict) -> bool:
    title = str(news_item.get("title") or "")
    summary = str(news_item.get("summary") or "")
    text = f" {title} {summary} ".lower()
    return any(term in text for term in GENERIC_NEWS_TERMS)


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


def _build_strong_signal_ai_input_hash(
    *,
    price: float,
    change_24h: float,
    change_7d: float | None,
    news_items: list[dict],
) -> str:
    payload = {
        "symbol": "BTC",
        "event_type": "strong_signal",
        "price": _stable_float(price, 2),
        "change_24h": _stable_float(change_24h, 4),
        "change_7d": _stable_float(change_7d, 4),
        "news": [
            {
                "key": make_news_key(item),
                "title": str(item.get("title") or ""),
                "source": str(item.get("source") or ""),
                "link": _stable_news_link(str(item.get("link") or "")),
            }
            for item in news_items
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def _enabled_subscription_by_symbol(user) -> dict[str, bool]:
    return {
        normalize_symbol(row.symbol): bool(row.is_enabled)
        for row in getattr(user, "coin_subscriptions", [])
    }


async def resolve_symbols_to_check(now: datetime | None = None) -> list[str]:
    """Resolve globally needed symbols from active eligible watchlists."""
    now = now or datetime.now(timezone.utc)
    if not DB_ENABLED or not DB_SESSION_LOCAL:
        return [DEFAULT_SYMBOL] if TELEGRAM_CHAT_ID else []

    async with DB_SESSION_LOCAL() as session:
        users = await get_active_users_with_alert_preferences(session)
        enabled_symbols: set[str] = set()
        for user in users:
            enabled_by_symbol = _enabled_subscription_by_symbol(user)
            for symbol in SUPPORTED_SYMBOLS:
                if not enabled_by_symbol.get(symbol, False):
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
    bypass_frequency: bool = False,
) -> list[AlertRecipient]:
    """Resolve eligible recipients once for one market event."""
    normalized_symbol = normalize_symbol(symbol)
    if event_type not in DELIVERABLE_ALERT_TYPES or normalized_symbol not in SUPPORTED_COINS:
        return []
    if event_type == "strong_signal" and normalized_symbol != DEFAULT_SYMBOL:
        return []

    if DB_ENABLED and DB_SESSION_LOCAL:
        now = now or datetime.now(timezone.utc)
        recipients = []
        seen_chat_ids = set()
        async with DB_SESSION_LOCAL() as session:
            for user in await get_active_users_with_alert_preferences(session):
                if user.telegram_chat_id is None:
                    continue
                enabled_by_symbol = _enabled_subscription_by_symbol(user)
                if not enabled_by_symbol.get(normalized_symbol, False):
                    continue
                last_sent_at = await get_last_sent_alert_at(
                    session,
                    user_id=user.id,
                    symbol=normalized_symbol,
                )
                if not bypass_frequency and not can_deliver_now(
                    user, normalized_symbol, now, last_sent_at
                ):
                    continue
                chat_id = int(user.telegram_chat_id)
                if chat_id in seen_chat_ids:
                    continue
                seen_chat_ids.add(chat_id)
                recipients.append(
                    AlertRecipient(
                        chat_id=chat_id,
                        user_id=user.id,
                        alert_frequency_seconds=get_effective_frequency_seconds(user, now),
                    )
                )
        return recipients

    if normalized_symbol == DEFAULT_SYMBOL and TELEGRAM_CHAT_ID:
        return [AlertRecipient(chat_id=int(TELEGRAM_CHAT_ID))]
    return []


async def _get_or_create_strong_signal_market_event(
    *,
    price: float,
    change_24h: float,
    change_7d: float | None,
    news_items: list[dict],
) -> tuple[int | None, str | None]:
    if not DB_ENABLED or not DB_SESSION_LOCAL:
        return None, None

    event_key = _build_strong_signal_event_key(
        price=price,
        change_24h=change_24h,
        change_7d=change_7d,
        news_items=news_items,
    )
    async with DB_SESSION_LOCAL() as session:
        market_event = await get_or_create_market_event(
            session,
            symbol=DEFAULT_SYMBOL,
            event_type="strong_signal",
            event_key=event_key,
            price=price,
            previous_price=None,
            price_change_percent=change_24h,
            last_24h_change=change_24h,
            last_7d_change=change_7d,
            detected_at=datetime.now(timezone.utc),
        )
        return market_event.id, event_key


async def _get_or_create_strong_signal_ai_analysis(
    *,
    market_event_id: int | None,
    price: float,
    change_24h: float,
    change_7d: float | None,
    news_items: list[dict],
) -> tuple[dict | None, int | None, str | None, str | None]:
    input_hash = _build_strong_signal_ai_input_hash(
        price=price,
        change_24h=change_24h,
        change_7d=change_7d,
        news_items=news_items,
    )

    if DB_ENABLED and DB_SESSION_LOCAL and market_event_id:
        async with DB_SESSION_LOCAL() as session:
            saved_analysis = await get_latest_success_event_ai_analysis(
                session,
                market_event_id=market_event_id,
            )
            if saved_analysis and saved_analysis.plain_text:
                log("Reusing saved AI analysis for BTC strong-signal event.")
                return (
                    {
                        "plain_text": saved_analysis.plain_text,
                        "html_text": saved_analysis.html_text,
                    },
                    saved_analysis.id,
                    "medium",
                    "unclear",
                )
            existing_analysis = await get_event_ai_analysis(
                session,
                market_event_id=market_event_id,
                input_hash=input_hash,
            )
            if (
                existing_analysis
                and existing_analysis.status == "success"
                and existing_analysis.plain_text
            ):
                log("Reusing saved AI analysis for BTC strong-signal event.")
                return (
                    {
                        "plain_text": existing_analysis.plain_text,
                        "html_text": existing_analysis.html_text,
                    },
                    existing_analysis.id,
                    "medium",
                    "unclear",
                )

    result = await classify_strong_signal(price, change_24h, change_7d, news_items)
    if not result:
        return None, None, None, None

    strength = str(result.get("signal_strength", "")).lower()
    if result.get("should_alert") is not True or strength not in {"medium", "strong"}:
        return None, None, strength, str(result.get("direction", "unclear")).lower()

    message = sanitize_alert_message(str(result.get("telegram_message") or ""))
    if not message:
        return None, None, strength, str(result.get("direction", "unclear")).lower()

    event_ai_analysis_id = None
    if DB_ENABLED and DB_SESSION_LOCAL and market_event_id:
        async with DB_SESSION_LOCAL() as session:
            analysis = await save_event_ai_analysis(
                session,
                market_event_id=market_event_id,
                provider="groq",
                model=GROQ_MODEL,
                input_hash=input_hash,
                analysis_text=message,
                plain_text=message,
                html_text=None,
                status="success",
            )
            event_ai_analysis_id = analysis.id if analysis else None
    return (
        {"plain_text": message, "html_text": None},
        event_ai_analysis_id,
        strength,
        str(result.get("direction", "unclear")).lower(),
    )


async def _get_or_create_price_movement_market_event(
    *,
    symbol: str,
    event_type: str = "price_movement",
    previous_price: float,
    current_price: float,
    price_change_percent: float,
    change_24h: float,
    change_7d: float | None,
) -> tuple[int | None, str | None]:
    if not DB_ENABLED or not DB_SESSION_LOCAL:
        return None, None

    event_bucket = None
    if event_type in PRODUCT_ALERT_TYPES:
        event_bucket = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
    event_key = _build_price_movement_event_key(
        symbol=symbol,
        event_type=event_type,
        previous_price=previous_price,
        current_price=current_price,
        price_change_percent=price_change_percent,
        event_bucket=event_bucket,
    )
    async with DB_SESSION_LOCAL() as session:
        market_event = await get_or_create_market_event(
            session,
            symbol=normalize_symbol(symbol),
            event_type=event_type,
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
    event_type: str = "price_movement",
    market_event_id: int | None,
    previous_price: float,
    current_price: float,
    price_change_percent: float,
    change_24h: float,
    change_7d: float | None,
    news_items: list[dict],
    alert_settings: dict,
    alert_threshold_percent: float | None = None,
    window_seconds: int | None = None,
    peak_movement_percent: float | None = None,
    alert_type_label_text: str | None = None,
    force_fallback: bool = False,
) -> tuple[dict, int | None]:
    """Create or reuse the single AI analysis for one market event.

    The LLM call stays here, before recipient delivery, so one market event
    produces one analysis that can be sent to many active users.
    """
    input_hash = _build_alert_ai_input_hash(
        symbol=symbol,
        event_type=event_type,
        previous_price=previous_price,
        current_price=current_price,
        price_change_percent=price_change_percent,
        change_24h=change_24h,
        change_7d=change_7d,
        news_items=news_items,
        alert_threshold_percent=alert_threshold_percent
        or alert_settings["price_move_alert_percent"],
        check_interval_seconds=window_seconds
        or alert_settings["automatic_check_interval_seconds"],
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
            check_interval_seconds=window_seconds
            or alert_settings["automatic_check_interval_seconds"],
            symbol=normalize_symbol(symbol).upper(),
            coin_name=_coin_name(symbol),
            alert_type_label=alert_type_label_text or "basic price",
            window_seconds=window_seconds,
            peak_movement_percent=peak_movement_percent,
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
                alert_threshold_percent=alert_threshold_percent
                or alert_settings["price_move_alert_percent"],
                check_interval_seconds=window_seconds
                or alert_settings["automatic_check_interval_seconds"],
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
                check_interval_seconds=window_seconds
                or alert_settings["automatic_check_interval_seconds"],
                symbol=normalize_symbol(symbol).upper(),
                coin_name=_coin_name(symbol),
                alert_type_label=alert_type_label_text or "basic price",
                window_seconds=window_seconds,
                peak_movement_percent=peak_movement_percent,
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


async def _save_product_notification_analysis(
    *,
    market_event_id: int | None,
    alert_payload: dict,
    signal_context: SignalContext,
    decision: NotificationDecision,
) -> int | None:
    if not DB_ENABLED or not DB_SESSION_LOCAL or not market_event_id:
        return None
    input_payload = {
        "symbol": normalize_symbol(signal_context.symbol).upper(),
        "notification_type": decision.notification_type.value,
        "severity": decision.severity.value,
        "direction": decision.direction.value,
        "trigger_source": decision.trigger_source.value if decision.trigger_source else None,
        "current_price": _stable_float(signal_context.current_price, 2),
        "latest_5m_change_percent": _stable_float(
            signal_context.latest_5m_change_percent, 4
        ),
        "change_since_last_market_update_percent": _stable_float(
            signal_context.change_since_last_market_update_percent, 4
        ),
        "user_period_change_percent": _stable_float(
            signal_context.user_period_change_percent, 4
        ),
        "twenty_four_hour_change_percent": _stable_float(
            signal_context.twenty_four_hour_change_percent, 4
        ),
        "news": [make_news_key(item) for item in signal_context.relevant_news_items],
        "news_candidates": signal_context.news_candidates,
    }
    input_hash = sha256(
        json.dumps(input_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    async with DB_SESSION_LOCAL() as session:
        analysis = await save_event_ai_analysis(
            session,
            market_event_id=market_event_id,
            provider="deterministic",
            model="product-notification-v1",
            input_hash=input_hash,
            analysis_text=str(alert_payload.get("plain_text", "")),
            plain_text=str(alert_payload.get("plain_text", "")),
            html_text=None,
            status="success",
        )
        return analysis.id if analysis else None


def _classify_news_context(symbol: str, news_items: list[dict]) -> str:
    candidates = _build_news_candidates(symbol, news_items)
    if any(item["relevance"] == "strong" for item in candidates):
        return "strong"
    if any(item["relevance"] == "medium" for item in candidates):
        return "medium"
    if candidates:
        return "weak"
    return "none"


def _build_news_candidates(symbol: str, news_items: list[dict]) -> list[dict]:
    candidates: list[dict] = []
    normalized_symbol = normalize_symbol(symbol)
    for item in news_items:
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        source = str(item.get("source") or "").strip()
        url = str(item.get("url") or item.get("link") or "").strip()
        raw_relevance = classify_news_relevance(symbol, item)
        if raw_relevance == "irrelevant":
            continue
        material = is_material_news_item(item)
        generic = is_generic_news_item(item)
        if normalized_symbol == DEFAULT_SYMBOL:
            relevance = _classify_btc_news_candidate(item, raw_relevance, material, generic)
            reason = _news_relevance_reason(normalized_symbol, relevance, raw_relevance)
        elif _coin_is_secondary_context(normalized_symbol, item):
            relevance = "weak"
            reason = "Secondary coin mention in broader crypto context"
        elif raw_relevance == "direct" and material:
            relevance = "strong"
            reason = f"{normalized_symbol.upper()}-specific material market context"
        elif raw_relevance == "direct" and not generic:
            relevance = "medium"
            reason = f"{normalized_symbol.upper()}-specific market context"
        elif material:
            relevance = "medium"
            reason = "Market-wide material crypto context"
        else:
            relevance = "weak"
            reason = "Broad crypto market context"
        candidates.append(
            {
                "title": title,
                "url": url,
                "source": source,
                "relevance": relevance,
                "reason": reason,
            }
        )
    return candidates


def _classify_btc_news_candidate(
    item: dict,
    raw_relevance: str,
    material: bool,
    generic: bool,
) -> str:
    title = str(item.get("title") or "")
    summary = str(item.get("summary") or "")
    text = f" {title} {summary} ".lower()
    if _btc_is_secondary_context(text):
        return "weak"
    if raw_relevance == "market_wide" and not _btc_market_wide_is_material(text):
        return "weak"
    if _btc_has_strong_market_focus(text):
        return "strong" if material else "medium"
    if raw_relevance == "direct" and material and not generic:
        return "medium"
    return "weak"


def _btc_is_secondary_context(text: str) -> bool:
    secondary_patterns = (
        ("soluna", "revenue"),
        ("hosting business", "bitcoin mining"),
        ("xrp", "solana", "bitcoin outflow"),
        ("xrp", "solana", "bitcoin outflows"),
    )
    return any(all(term in text for term in pattern) for pattern in secondary_patterns)


def _btc_market_wide_is_material(text: str) -> bool:
    return any(
        term in text
        for term in (
            "bitcoin etf",
            "btc etf",
            "bitcoin fund flow",
            "bitcoin fund flows",
            "bitcoin inflow",
            "bitcoin inflows",
            "bitcoin outflow",
            "bitcoin outflows",
            "bitcoin regulation",
            "bitcoin policy",
            "bitcoin reserve",
            "bitcoin dominance",
        )
    )


def _btc_has_strong_market_focus(text: str) -> bool:
    if any(
        term in text
        for term in (
            "bitcoin price",
            "btc price",
            "bitcoin support",
            "bitcoin resistance",
            "bitcoin etf",
            "btc etf",
            "bitcoin fund",
            "bitcoin funds",
            "bitcoin outflow",
            "bitcoin outflows",
            "bitcoin inflow",
            "bitcoin inflows",
            "bitcoin regulation",
            "bitcoin policy",
            "bitcoin hashrate",
            "bitcoin hash rate",
        )
    ):
        return True
    return "bitcoin mining" in text and any(
        term in text for term in ("hashrate", "hash rate", "difficulty", "market impact")
    )


def _coin_is_secondary_context(symbol: str, item: dict) -> bool:
    title = str(item.get("title") or "")
    summary = str(item.get("summary") or "")
    text = f" {title} {summary} ".lower()
    if symbol == "sol" and "xrp" in text and "solana" in text and "bitcoin" in text:
        return False
    return False


def _news_relevance_reason(symbol: str, relevance: str, raw_relevance: str) -> str:
    if relevance == "strong":
        return f"{symbol.upper()}-specific material market context"
    if relevance == "medium":
        return f"{symbol.upper()}-specific market context"
    if raw_relevance == "direct":
        return f"Weak {symbol.upper()} mention without clear market catalyst"
    return "Broad crypto market context"


def _useful_news_candidates(candidates: list[dict] | None) -> list[dict]:
    return [
        item
        for item in candidates or []
        if str(item.get("relevance") or "").strip().lower() in {"medium", "strong"}
    ]


def _market_condition_can_alert(evaluation: SeverityEvaluation) -> bool:
    return evaluation.severity in {AlertSeverity.HIGH, AlertSeverity.EXTREME}


def _window_label(seconds: int) -> str:
    if seconds == 3600:
        return "1h"
    if seconds == 21600:
        return "6h"
    if seconds == 86400:
        return "24h"
    if seconds % 3600 == 0:
        return f"{seconds // 3600}h"
    if seconds % 60 == 0:
        return f"{seconds // 60}m"
    return f"{seconds}s"


def _severity_from_decision(decision: AlertDecision) -> SeverityEvaluation:
    severity = decision.backend_severity_ceiling
    alert_type = decision.alert_type or AlertType.PRICE_MOVEMENT
    return SeverityEvaluation(
        severity=severity,
        primary_alert_type=alert_type,
        signals=decision.signals,
    )


def _format_thresholds_for_storage(thresholds) -> str:
    return json.dumps(
        {
            "movement_percent": thresholds.movement_percent,
            "trend_24h_medium_percent": thresholds.trend_24h_medium_percent,
            "trend_24h_high_percent": thresholds.trend_24h_high_percent,
        },
        sort_keys=True,
    )


def _format_numeric_context_for_storage(
    *,
    current_price: float,
    previous_price: float,
    window_seconds: int,
    movement_percent: float,
    peak_movement_percent: float | None,
    change_24h: float,
) -> str:
    return json.dumps(
        {
            "current_price": current_price,
            "previous_price": previous_price,
            "window_seconds": window_seconds,
            "movement_percent": movement_percent,
            "peak_intrawindow_movement_percent": peak_movement_percent,
            "change_24h": change_24h,
        },
        sort_keys=True,
    )


def _format_signal_context_for_storage(
    context: SignalContext,
    decision: NotificationDecision,
) -> str:
    return json.dumps(
        {
            "symbol": normalize_symbol(context.symbol).upper(),
            "current_price": context.current_price,
            "latest_5m_change_percent": context.latest_5m_change_percent,
            "change_since_last_market_update_percent": (
                context.change_since_last_market_update_percent
            ),
            "user_period_change_percent": context.user_period_change_percent,
            "one_hour_change_percent": context.one_hour_change_percent,
            "four_hour_change_percent": context.four_hour_change_percent,
            "twenty_four_hour_change_percent": context.twenty_four_hour_change_percent,
            "news_relevance_score": context.news_relevance_score,
            "news_candidates": context.news_candidates,
            "last_notification_type": context.last_notification_type,
            "last_notification_severity": context.last_notification_severity,
            "last_notification_direction": context.last_notification_direction,
            "last_market_update_time": (
                context.last_market_update_time.isoformat()
                if context.last_market_update_time
                else None
            ),
            "previous_market_update_time": (
                context.last_market_update_time.isoformat()
                if context.last_market_update_time
                else None
            ),
            "new_market_update_time": (
                datetime.now(timezone.utc).isoformat()
                if decision.notification_type is NotificationType.MARKET_UPDATE
                else None
            ),
            "source_snapshot_time": datetime.now(timezone.utc).isoformat(),
            "baseline_snapshot_time": (
                context.last_market_update_time.isoformat()
                if context.last_market_update_time
                else None
            ),
            "user_alert_frequency_seconds": context.user_alert_frequency_seconds,
            "trigger_candidates": context.trigger_candidates,
            "suppression_context": context.suppression_context,
            "notification_type": decision.notification_type.value,
            "notification_severity": decision.severity.value,
            "notification_direction": decision.direction.value,
            "trigger_source": decision.trigger_source.value if decision.trigger_source else None,
        },
        sort_keys=True,
    )


async def _resolve_window_market_context(
    *,
    symbol: str,
    current_price: float,
    fallback_previous_price: float,
    window_seconds: int,
    now: datetime,
) -> tuple[float, float | None]:
    if not DB_ENABLED or not DB_SESSION_LOCAL:
        return fallback_previous_price, None
    since = now - timedelta(seconds=window_seconds)
    async with DB_SESSION_LOCAL() as session:
        reference = await get_reference_price_snapshot(
            session,
            symbol=symbol,
            at_or_before=since,
        )
        snapshots = await get_price_snapshots_since(session, symbol=symbol, since=since)
    previous_price = float(reference.price) if reference else fallback_previous_price
    peak = None
    if snapshots:
        moves = [
            abs(calculate_price_change_percent(previous_price, float(snapshot.price)))
            for snapshot in snapshots
            if previous_price
        ]
        if moves:
            peak = max(moves)
    if peak is None and previous_price:
        peak = abs(calculate_price_change_percent(previous_price, current_price))
    return previous_price, peak


def _strip_existing_alert_title(plain_text: str) -> str:
    lines = plain_text.strip().splitlines()
    if lines and any(term in lines[0].lower() for term in ("alert", "signal")):
        return "\n".join(lines[1:]).strip()
    return plain_text.strip()


def _coin_display_line(symbol: str) -> str:
    display_symbol = normalize_symbol(symbol).upper()
    try:
        coin_name = _coin_name(symbol)
    except KeyError:
        return f"Coin: {display_symbol}"
    if coin_name.lower() == display_symbol.lower():
        return f"Coin: {display_symbol}"
    return f"Coin: {display_symbol} / {coin_name}"


def _remove_user_facing_risk_level(plain_text: str) -> str:
    body = _strip_existing_alert_title(plain_text)
    cleaned_lines: list[str] = []
    risk_reason = ""
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("Risk level:"):
            continue
        if stripped.startswith("Risk reason:"):
            risk_reason = stripped.split(":", 1)[1].strip()
            continue
        if stripped.startswith("Coin:"):
            continue
        if stripped == "Not financial advice.":
            continue
        cleaned_lines.append(line)

    if risk_reason and not any(line.strip() == "Reason:" for line in cleaned_lines):
        section_index = next(
            (
                index
                for index, line in enumerate(cleaned_lines)
                if line.strip() in {"Context:", "Related news:", "Possible action:"}
            ),
            len(cleaned_lines),
        )
        reason_lines = ["", "Reason:", risk_reason, ""]
        cleaned_lines[section_index:section_index] = reason_lines

    cleaned = "\n".join(cleaned_lines).strip()
    return re.sub(r"\n{3,}", "\n\n", cleaned)


def _apply_severity_header(
    alert_payload: dict,
    *,
    symbol: str,
    severity: SeverityEvaluation | None,
) -> dict:
    if severity is None:
        return alert_payload

    plain_text = sanitize_alert_message(str(alert_payload.get("plain_text", "")))
    body = _remove_user_facing_risk_level(plain_text)
    display_symbol = normalize_symbol(symbol).upper()
    header = (
        f"{severity_icon_text(severity.severity)} {severity_label_text(severity.severity)} - "
        f"{display_symbol} {alert_title_action(severity.primary_alert_type)}\n\n"
        f"{_coin_display_line(symbol)}"
    )
    updated_plain_text = sanitize_alert_message(f"{header}\n{body}")
    return {"plain_text": updated_plain_text, "html_text": None}


def severity_label_text(severity: AlertSeverity) -> str:
    if severity is AlertSeverity.EXTREME:
        return "High"
    return {
        AlertSeverity.INFO: "Low",
        AlertSeverity.WATCH: "Medium",
        AlertSeverity.HIGH: "High",
    }[severity]


def severity_icon_text(severity: AlertSeverity) -> str:
    if severity is AlertSeverity.INFO:
        return "\U0001f7e2"
    if severity is AlertSeverity.WATCH:
        return "\U0001f7e1"
    return "\U0001f534"


def normalize_llm_severity(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    aliases = {
        "info": "low",
        "watch": "medium",
        "moderate": "medium",
        "critical": "extreme",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in {"low", "medium", "high", "extreme"}:
        return "low"
    return normalized


def _notification_type_label(notification_type: NotificationType | str) -> str:
    normalized = NotificationType(notification_type)
    return {
        NotificationType.MARKET_UPDATE: "Market Update",
        NotificationType.IMPORTANT_ALERT: "Important Alert",
        NotificationType.CRITICAL_ALERT: "Critical Alert",
        NotificationType.NO_ALERT: "Market Update",
    }[normalized]


def _format_percent(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:+.2f}%"


def _build_product_notification_payload(
    context: SignalContext,
    decision: NotificationDecision,
) -> dict:
    symbol = normalize_symbol(context.symbol).upper()
    period_label = _window_label(context.user_alert_frequency_seconds or 0)
    alert_move = _alert_move_percent(context, decision)
    summary = _summary_sentence(
        symbol,
        decision.direction,
        decision.notification_type,
        trigger_source=decision.trigger_source,
        alert_move_percent=alert_move,
        one_hour_change_percent=context.one_hour_change_percent,
        period_change_percent=context.user_period_change_percent,
        change_24h=context.twenty_four_hour_change_percent,
        period_label=period_label,
    )
    visible_news = _visible_news_candidates_for_message(context, decision)
    news_section = ""
    if visible_news and _is_user_visible_news(context.news_relevance_score):
        lines = []
        for item in visible_news[:2]:
            title = str(item.get("title") or "").strip()
            source = str(item.get("source") or "").strip()
            link = str(item.get("url") or item.get("link") or "").strip()
            if not title:
                continue
            detail = f" - {source}" if source else ""
            lines.append(f"- {title}{detail}")
            if link:
                lines.append(f"  {link}")
        if lines:
            news_section = "\nRelated news:\n" + "\n".join(lines) + "\n"
    elif decision.notification_type in {
        NotificationType.IMPORTANT_ALERT,
        NotificationType.CRITICAL_ALERT,
    }:
        if context.news_candidates:
            logger.info("weak_news_hidden_from_user_message")
        news_section = "\nNews context:\nNo clear news catalyst found.\n"

    if decision.notification_type is NotificationType.MARKET_UPDATE:
        movement_lines = (
            f"Move: {_format_percent(context.user_period_change_percent)} over the last "
            f"{period_label}\n"
            f"24h change: {_format_percent(context.twenty_four_hour_change_percent)}"
        )
    else:
        movement_lines = (
            f"Alert move: {_format_percent(alert_move)}\n"
            f"1h move: {_format_percent(context.one_hour_change_percent)}\n"
            f"24h change: {_format_percent(context.twenty_four_hour_change_percent)}"
        )

    message = (
        f"{decision.icon} {_notification_type_label(decision.notification_type)} - {symbol}\n\n"
        f"{summary}\n\n"
        f"Price: ${context.current_price:,.2f}\n"
        f"{movement_lines}\n\n"
        "Why this matters:\n"
        f"{decision.reasoning_summary}\n"
        f"{news_section}\n"
        "Possible action:\n"
        f"{decision.possible_action}\n\n"
        "Not financial advice."
    )
    return {"plain_text": sanitize_alert_message(message), "html_text": None}


def _alert_move_percent(context: SignalContext, decision: NotificationDecision) -> float | None:
    if decision.trigger_source is TriggerSource.FAST_MOVEMENT:
        return context.latest_5m_change_percent
    if decision.trigger_source is TriggerSource.CUMULATIVE_MOVEMENT:
        return context.change_since_last_market_update_percent
    if decision.trigger_source is TriggerSource.USER_PERIOD_MOVEMENT:
        return context.user_period_change_percent
    if decision.notification_type is NotificationType.CRITICAL_ALERT:
        values = [
            context.latest_5m_change_percent,
            context.change_since_last_market_update_percent,
            context.user_period_change_percent,
            context.one_hour_change_percent,
            context.four_hour_change_percent,
        ]
        return max(
            (value for value in values if value is not None),
            key=lambda value: abs(value),
            default=None,
        )
    return context.user_period_change_percent


def _visible_news_candidates_for_message(
    context: SignalContext,
    decision: NotificationDecision,
) -> list[dict]:
    candidates = _useful_news_candidates(context.news_candidates)
    if decision.notification_type is NotificationType.MARKET_UPDATE:
        return candidates
    return [
        item
        for item in candidates
        if str(item.get("relevance") or "").strip().lower() == "strong"
    ]


def _is_user_visible_news(news_relevance_score: str | None) -> bool:
    return (news_relevance_score or "").strip().lower() in {
        "relevant",
        "very_relevant",
        "medium",
        "strong",
        "high",
    }


def _summary_sentence(
    symbol: str,
    direction: NotificationDirection,
    notification_type: NotificationType,
    *,
    trigger_source: TriggerSource | None = None,
    alert_move_percent: float | None = None,
    one_hour_change_percent: float | None = None,
    period_change_percent: float | None = None,
    change_24h: float | None = None,
    period_label: str = "update window",
) -> str:
    period = period_change_percent or 0.0
    one_hour = one_hour_change_percent if one_hour_change_percent is not None else period
    alert_move = alert_move_percent if alert_move_percent is not None else period
    trend = change_24h or 0.0
    if notification_type is NotificationType.MARKET_UPDATE:
        summary = _market_update_timeframe_summary(
            symbol,
            period_change_percent=period,
            change_24h=trend,
            period_label=period_label,
        )
        logger.info(
            "market_update_timeframe_classification symbol=%s period=%.4f trend_24h=%.4f",
            symbol,
            period,
            trend,
        )
        return summary
    if trigger_source is TriggerSource.NEWS:
        if abs(one_hour) < 1.0 and abs(alert_move) < 1.0:
            return f"{symbol} has relevant market news, while price remains mostly stable."
        return f"{symbol} has relevant market news, but price has not reacted strongly yet."
    if notification_type is NotificationType.CRITICAL_ALERT:
        visible_move = one_hour if abs(one_hour) >= 0.3 else alert_move
        if visible_move > 0:
            action = "jumped sharply"
        elif visible_move < 0:
            action = "dropped sharply"
        elif direction is NotificationDirection.UP:
            action = "jumped sharply"
        else:
            action = "dropped sharply"
        return f"{symbol} {action}."
    visible_move = one_hour if abs(one_hour) >= 0.3 else alert_move
    if visible_move > 0:
        return f"{symbol} is gaining momentum."
    if visible_move < 0:
        return f"{symbol} is moving down faster than usual."
    return f"{symbol} market conditions changed."


def _market_update_timeframe_summary(
    symbol: str,
    *,
    period_change_percent: float,
    change_24h: float,
    period_label: str,
) -> str:
    period_abs = abs(period_change_percent)
    period_direction = _movement_direction(period_change_percent, calm_threshold=0.3)
    trend_direction = _movement_direction(change_24h, calm_threshold=1.0)
    trend_strength = _trend_strength(change_24h)

    if period_direction == "neutral":
        period_text = f"{symbol} is stable over the last {period_label}"
        if trend_direction == "neutral":
            return period_text + "."
        logger.info("mixed_timeframe_wording_selected symbol=%s", symbol)
        return f"{period_text}, but remains {trend_strength} on the 24h trend."

    if trend_direction != "neutral" and period_direction != trend_direction:
        logger.info("mixed_timeframe_wording_selected symbol=%s", symbol)
        if period_direction == "up":
            period_text = (
                f"{symbol} recovered slightly over the last {period_label}"
                if period_abs < 1.0
                else f"{symbol} strengthened over the last {period_label}"
            )
        else:
            period_text = (
                f"{symbol} is slightly lower over the last {period_label}"
                if period_abs < 1.0
                else f"{symbol} weakened over the last {period_label}"
            )
        return f"{period_text}, but the 24h trend remains {trend_strength}."

    if period_direction == "up":
        if period_abs >= 3.0 and trend_direction == "up":
            return (
                f"{symbol} strengthened meaningfully over the last {period_label} and remains "
                "positive on the 24h trend."
            )
        if period_abs < 1.0:
            return f"{symbol} recovered slightly over the last {period_label}."
        return f"{symbol} strengthened over the last {period_label}."

    if period_direction == "down":
        if period_abs >= 3.0 and trend_direction == "down":
            return (
                f"{symbol} weakened meaningfully over the last {period_label} and remains "
                f"{trend_strength} on the 24h trend."
            )
        if period_abs < 1.0:
            if trend_direction == "down":
                return (
                    f"{symbol} is slightly lower over the last {period_label}, while the 24h "
                    f"trend remains {trend_strength}."
                )
            return f"{symbol} is slightly lower over the last {period_label}."
        return f"{symbol} weakened over the last {period_label}."

    return f"{symbol} is relatively calm over the last {period_label}."


def _movement_direction(value: float, *, calm_threshold: float) -> str:
    if abs(value) < calm_threshold:
        return "neutral"
    return "up" if value > 0 else "down"


def _trend_strength(change_24h: float) -> str:
    if change_24h <= -5.0:
        return "weak"
    if change_24h < -2.0:
        return "mildly negative"
    if change_24h < -1.0:
        return "slightly negative"
    if change_24h >= 5.0:
        return "strong"
    if change_24h > 2.0:
        return "positive"
    if change_24h > 1.0:
        return "slightly positive"
    return "calm"


def _notification_severity_to_alert_severity(severity: NotificationSeverity) -> AlertSeverity:
    return {
        NotificationSeverity.LOW: AlertSeverity.INFO,
        NotificationSeverity.MEDIUM: AlertSeverity.WATCH,
        NotificationSeverity.HIGH: AlertSeverity.HIGH,
        NotificationSeverity.EXTREME: AlertSeverity.EXTREME,
    }[severity]


async def _send_alert_to_recipient(
    app: Application, recipient: AlertRecipient, alert_payload: dict
) -> tuple[bool, str | None]:
    logger.info("alert_delivery_path_used chat_id=%s", recipient.chat_id)
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
                if is_bot_blocked_error(error):
                    raise
                log(f"HTML alert send failed; falling back to plain text: {error}")
                await app.bot.send_message(chat_id=recipient.chat_id, text=plain_text)
        else:
            await app.bot.send_message(chat_id=recipient.chat_id, text=plain_text)
    except Exception as error:
        return False, str(error)
    return True, None


async def _disable_recipient_if_bot_blocked(
    recipient: AlertRecipient,
    error_message: str | None,
) -> None:
    if not is_bot_blocked_error(error_message):
        if error_message:
            logger.info(
                "delivery_failure_not_permanent user_id=%s telegram_chat_id=%s error=%r",
                recipient.user_id,
                recipient.chat_id,
                error_message,
            )
        return
    if not DB_ENABLED or not DB_SESSION_LOCAL:
        return
    async with DB_SESSION_LOCAL() as session:
        user, _ = await mark_user_bot_blocked(
            session,
            user_id=recipient.user_id,
            telegram_chat_id=recipient.chat_id,
        )
        if user is not None:
            logger.info(
                "user_deactivated_after_delivery_failure user_id=%s telegram_chat_id=%s error=%r",
                user.id,
                recipient.chat_id,
                error_message,
            )


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
    alert_type: str,
    recipient: AlertRecipient,
    plain_text: str,
    status: str,
    market_event_id: int | None,
    event_ai_analysis_id: int | None,
    error_message: str | None = None,
    trigger_reason: str | None = None,
    trigger_source: str | None = None,
    numeric_context: str | None = None,
    thresholds_used: str | None = None,
    llm_severity: str | None = None,
    llm_reasoning_summary: str | None = None,
    fallback_mode: bool = False,
) -> None:
    if not DB_ENABLED or not DB_SESSION_LOCAL:
        return

    async with DB_SESSION_LOCAL() as session:
        await save_alert(
            session,
            symbol=symbol,
            alert_type=alert_type,
            message=plain_text,
            sent_to_chat_id=recipient.chat_id,
            market_event_id=market_event_id,
            event_ai_analysis_id=event_ai_analysis_id,
            user_id=recipient.user_id,
            status=status,
            error_message=error_message,
            trigger_reason=trigger_reason,
            trigger_source=trigger_source,
            numeric_context=numeric_context,
            thresholds_used=thresholds_used,
            llm_severity=llm_severity,
            llm_reasoning_summary=llm_reasoning_summary,
            fallback_mode=fallback_mode,
        )


async def _save_price_state(
    *,
    symbol: str,
    state: dict,
    current_price: float,
    change_24h: float,
    change_7d: float | None = None,
    checked_at: str,
    last_alert_at: datetime | None = None,
) -> None:
    if DB_ENABLED and DB_SESSION_LOCAL:
        async with DB_SESSION_LOCAL() as session:
            checked_dt = datetime.fromisoformat(checked_at)
            if checked_dt.tzinfo is None:
                checked_dt = checked_dt.replace(tzinfo=timezone.utc)
            await save_price_snapshot(
                session,
                symbol=symbol,
                price=current_price,
                change_24h=change_24h,
                change_7d=change_7d,
                source="coingecko",
                checked_at=checked_dt,
            )
            await update_price_state(
                session,
                symbol=symbol,
                last_price=current_price,
                last_24h_change=change_24h,
                last_checked_at=checked_dt,
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
    event_type: str = "price_movement",
    severity: SeverityEvaluation | None = None,
    trigger_reason: str | None = None,
    trigger_source: str | None = None,
    numeric_context: str | None = None,
    thresholds_used: str | None = None,
) -> bool:
    """Send one sanitized event analysis to every resolved recipient."""
    if event_type not in PRODUCT_ALERT_TYPES:
        alert_payload = _apply_severity_header(alert_payload, symbol=symbol, severity=severity)
    alert_payload = _sanitize_alert_payload(alert_payload)
    normalized_symbol = normalize_symbol(symbol)
    if recipients is None:
        recipients = await get_alert_recipients(
            symbol=normalized_symbol,
            event_type=event_type,
        )
    if not recipients:
        log(f"No eligible recipients for {normalized_symbol.upper()} price movement alert.")
        return False

    plain_text = str(alert_payload.get("plain_text", ""))
    raw_stored_severity = (
        severity.severity.value
        if event_type in PRODUCT_ALERT_TYPES and severity
        else severity_label_text(severity.severity)
        if severity
        else None
    )
    stored_severity = normalize_llm_severity(raw_stored_severity)
    if raw_stored_severity != stored_severity:
        logger.info(
            "llm_severity_normalized original=%s normalized=%s",
            raw_stored_severity,
            stored_severity,
        )
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
                    alert_type=event_type,
                    sent_to_chat_id=recipient.chat_id,
                    market_event_id=market_event_id,
                    event_ai_analysis_id=event_ai_analysis_id,
                    message=plain_text,
                    trigger_reason=trigger_reason,
                    trigger_source=trigger_source,
                    numeric_context=numeric_context,
                    thresholds_used=thresholds_used,
                    llm_severity=stored_severity,
                    llm_reasoning_summary=trigger_reason,
                    fallback_mode="AI analysis is temporarily unavailable" in plain_text,
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
                alert_type=event_type,
                recipient=recipient,
                plain_text=plain_text,
                status="sent" if sent else "failed",
                market_event_id=market_event_id,
                event_ai_analysis_id=event_ai_analysis_id,
                error_message=error_message,
                trigger_reason=trigger_reason,
                trigger_source=trigger_source,
                numeric_context=numeric_context,
                thresholds_used=thresholds_used,
                llm_severity=stored_severity,
                llm_reasoning_summary=trigger_reason,
                fallback_mode="AI analysis is temporarily unavailable" in plain_text,
            )
        if sent:
            delivered = True
            sent_count += 1
            await _persist_successful_product_alert_state(
                recipient=recipient,
                symbol=normalized_symbol,
                event_type=event_type,
                severity=stored_severity,
                numeric_context=numeric_context,
            )
        else:
            await _disable_recipient_if_bot_blocked(recipient, error_message)
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
        job_kwargs={"max_instances": 1, "coalesce": True, "misfire_grace_time": 15},
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


def _last_alert_direction(alert_row) -> str | None:
    if not alert_row or not getattr(alert_row, "numeric_context", None):
        return None
    try:
        context = json.loads(str(alert_row.numeric_context))
    except json.JSONDecodeError:
        return None
    direction = context.get("notification_direction")
    return str(direction) if direction else None


def _numeric_context_value(numeric_context: str | None, key: str) -> float | None:
    if not numeric_context:
        return None
    try:
        payload = json.loads(numeric_context)
    except json.JSONDecodeError:
        return None
    value = payload.get(key)
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


async def _persist_successful_product_alert_state(
    *,
    recipient: AlertRecipient,
    symbol: str,
    event_type: str,
    severity: str | None,
    numeric_context: str | None,
) -> None:
    if not DB_ENABLED or not DB_SESSION_LOCAL or recipient.user_id is None:
        return
    now = datetime.now(timezone.utc)
    normalized_symbol = normalize_symbol(symbol)
    kwargs = {
        "user_id": recipient.user_id,
        "symbol": normalized_symbol,
        "last_notification_type": event_type,
        "last_notification_severity": severity,
        "last_notification_direction": _direction_from_numeric_context(numeric_context),
        "last_cumulative_movement_percent": _numeric_context_value(
            numeric_context,
            "change_since_last_market_update_percent",
        ),
    }
    if event_type == NotificationType.MARKET_UPDATE.value:
        kwargs["last_market_update_time"] = now
    elif event_type == NotificationType.IMPORTANT_ALERT.value:
        kwargs["last_important_alert_time"] = now
        kwargs["last_market_update_time"] = now
    elif event_type == NotificationType.CRITICAL_ALERT.value:
        kwargs["last_critical_alert_time"] = now
        kwargs["last_market_update_time"] = now
    else:
        return
    async with DB_SESSION_LOCAL() as session:
        await upsert_user_symbol_alert_state(session, **kwargs)
    if event_type == NotificationType.MARKET_UPDATE.value:
        logger.info(
            "last_market_update_time_persisted user_id=%s symbol=%s value=%s",
            recipient.user_id,
            normalized_symbol.upper(),
            now.isoformat(),
        )
    elif event_type in {
        NotificationType.IMPORTANT_ALERT.value,
        NotificationType.CRITICAL_ALERT.value,
    }:
        logger.debug(
            "alert_baseline_updated_after_send user_id=%s symbol=%s alert_type=%s value=%s",
            recipient.user_id,
            normalized_symbol.upper(),
            event_type,
            now.isoformat(),
        )


def _direction_from_numeric_context(numeric_context: str | None) -> str | None:
    if not numeric_context:
        return None
    try:
        payload = json.loads(numeric_context)
    except json.JSONDecodeError:
        return None
    direction = payload.get("notification_direction")
    return str(direction) if direction else None


def _numeric_context_payload(numeric_context: str | None) -> dict:
    if not numeric_context:
        return {}
    try:
        payload = json.loads(numeric_context)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _should_skip_market_update_after_recent_event_alert(
    *,
    notification_type: NotificationType,
    recent_event_alert,
    now: datetime,
    window_seconds: int = 3600,
) -> bool:
    if notification_type is not NotificationType.MARKET_UPDATE:
        return False
    if recent_event_alert is None:
        return False
    if getattr(recent_event_alert, "status", "sent") != "sent":
        return False
    if getattr(recent_event_alert, "alert_type", None) not in {
        NotificationType.IMPORTANT_ALERT.value,
        NotificationType.CRITICAL_ALERT.value,
    }:
        return False
    created_at = getattr(recent_event_alert, "created_at", None)
    if created_at is None:
        return False
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return (now - created_at).total_seconds() <= window_seconds


def _should_skip_near_duplicate_market_update(
    *,
    notification_type: NotificationType,
    previous_alert,
    context: SignalContext,
    decision: NotificationDecision,
    now: datetime,
    frequency_seconds: int,
) -> bool:
    if notification_type is not NotificationType.MARKET_UPDATE:
        return False
    if previous_alert is None or getattr(previous_alert, "status", "sent") != "sent":
        return False
    created_at = getattr(previous_alert, "created_at", None)
    if created_at is None:
        return False
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    max_quiet_seconds = max(int(frequency_seconds), 1) * 6
    if (now - created_at).total_seconds() > max_quiet_seconds:
        return False

    previous = _numeric_context_payload(getattr(previous_alert, "numeric_context", None))
    if previous.get("notification_type") != NotificationType.MARKET_UPDATE.value:
        return False
    if previous.get("notification_direction") != decision.direction.value:
        return False
    if previous.get("notification_severity") != decision.severity.value:
        return False
    previous_score = str(previous.get("news_relevance_score") or "none").lower()
    current_score = str(context.news_relevance_score or "none").lower()
    if _useful_news_candidates(context.news_candidates):
        return False
    if previous_score != current_score and current_score not in {"none", "weak"}:
        return False
    previous_period = previous.get("user_period_change_percent")
    try:
        previous_period_float = float(previous_period)
    except (TypeError, ValueError):
        return False
    current_period = float(context.user_period_change_percent or 0.0)
    if abs(current_period - previous_period_float) > 0.3:
        return False
    logger.debug(
        "near_duplicate_market_update reason=same_direction_severity_small_delta "
        "previous_period=%.4f current_period=%.4f news_score=%s",
        previous_period_float,
        current_period,
        current_score,
    )
    return True


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
                    change_7d=change_7d if isinstance(change_7d, float) else None,
                    checked_at=checked_at,
                    last_alert_at=last_alert_at,
                )
                log(f"Initial {symbol.upper()} price saved: ${current_price:,.2f}")
                continue

            candidate_recipients = await get_alert_recipients(
                symbol=symbol,
                event_type=AlertType.PRICE_MOVEMENT.value,
                now=now,
                bypass_frequency=True,
            )
            if not candidate_recipients:
                log(f"No subscribed recipients for {symbol.upper()} automatic alerts.")
                await _save_price_state(
                    symbol=symbol,
                    state=state,
                    current_price=current_price,
                    change_24h=change_24h,
                    change_7d=change_7d if isinstance(change_7d, float) else None,
                    checked_at=checked_at,
                    last_alert_at=None,
                )
                continue
            latest_5m_change_percent = calculate_price_change_percent(
                float(previous_price), current_price
            )
            one_hour_previous_price, _ = await _resolve_window_market_context(
                symbol=symbol,
                current_price=current_price,
                fallback_previous_price=previous_price,
                window_seconds=3600,
                now=now,
            )
            four_hour_previous_price, _ = await _resolve_window_market_context(
                symbol=symbol,
                current_price=current_price,
                fallback_previous_price=previous_price,
                window_seconds=14400,
                now=now,
            )
            one_hour_change_percent = calculate_price_change_percent(
                one_hour_previous_price, current_price
            )
            four_hour_change_percent = calculate_price_change_percent(
                four_hour_previous_price, current_price
            )
            logger.debug(
                "%s movement calculated: latest_5m=%.4f%% one_hour=%.4f%% "
                "four_hour=%.4f%% change24h=%.4f%% change7d=%s",
                symbol.upper(),
                latest_5m_change_percent,
                one_hour_change_percent,
                four_hour_change_percent,
                change_24h,
                change_7d,
            )

            delivered = False
            thresholds = thresholds_for_symbol(alert_settings, symbol)
            if raw_news_items is None:
                raw_news_items = await fetch_news_context(limit=12)
            news_items = filter_news_for_symbol(symbol, raw_news_items)
            news_candidates = _build_news_candidates(symbol, news_items)
            news_relevance = _classify_news_context(symbol, news_items)
            logger.debug(
                "news_candidates_selected symbol=%s count=%s useful_count=%s score=%s",
                symbol.upper(),
                len(news_candidates),
                len(_useful_news_candidates(news_candidates)),
                news_relevance,
            )

            grouped_notifications: dict[
                tuple[str, str, str, str | None, int],
                tuple[SignalContext, NotificationDecision, list[AlertRecipient]],
            ] = {}
            for recipient in candidate_recipients:
                frequency_seconds = recipient.alert_frequency_seconds or int(
                    alert_settings.get("automatic_check_interval_seconds", 300)
                )
                last_notification = None
                symbol_alert_state = None
                recent_event_alert = None
                last_market_update_alert = None
                important = None
                critical = None
                if DB_ENABLED and DB_SESSION_LOCAL and recipient.user_id is not None:
                    async with DB_SESSION_LOCAL() as session:
                        last_notification = await get_last_sent_alert(
                            session,
                            user_id=recipient.user_id,
                            symbol=symbol,
                        )
                        symbol_alert_state = await get_user_symbol_alert_state(
                            session,
                            user_id=recipient.user_id,
                            symbol=symbol,
                        )
                        important = await get_last_sent_alert(
                            session,
                            user_id=recipient.user_id,
                            symbol=symbol,
                            alert_type=NotificationType.IMPORTANT_ALERT.value,
                        )
                        critical = await get_last_sent_alert(
                            session,
                            user_id=recipient.user_id,
                            symbol=symbol,
                            alert_type=NotificationType.CRITICAL_ALERT.value,
                        )
                        recent_event_alert = max(
                            [alert for alert in (important, critical) if alert is not None],
                            key=lambda alert: alert.created_at,
                            default=None,
                        )
                        last_market_update_alert = await get_last_sent_alert(
                            session,
                            user_id=recipient.user_id,
                            symbol=symbol,
                            alert_type=NotificationType.MARKET_UPDATE.value,
                        )
                last_market_update_time = (
                    symbol_alert_state.last_market_update_time if symbol_alert_state else None
                )
                logger.info(
                    "last_market_update_time_loaded user_id=%s symbol=%s value=%s",
                    recipient.user_id,
                    symbol.upper(),
                    last_market_update_time.isoformat() if last_market_update_time else None,
                )
                if last_market_update_time is None:
                    logger.info(
                        "last_market_update_time_missing_safe_fallback user_id=%s symbol=%s",
                        recipient.user_id,
                        symbol.upper(),
                    )
                scheduled_due = (
                    last_market_update_time is None
                    or (now - last_market_update_time).total_seconds() >= frequency_seconds
                )
                period_previous_price, _ = await _resolve_window_market_context(
                    symbol=symbol,
                    current_price=current_price,
                    fallback_previous_price=previous_price,
                    window_seconds=frequency_seconds,
                    now=now,
                )
                user_period_change_percent = calculate_price_change_percent(
                    period_previous_price, current_price
                )
                if last_market_update_time is not None:
                    update_window_seconds = max(
                        int((now - last_market_update_time).total_seconds()),
                        int(alert_settings.get("automatic_check_interval_seconds", 300)),
                    )
                else:
                    update_window_seconds = frequency_seconds
                update_previous_price, _ = await _resolve_window_market_context(
                    symbol=symbol,
                    current_price=current_price,
                    fallback_previous_price=period_previous_price,
                    window_seconds=update_window_seconds,
                    now=now,
                )
                cumulative_change_percent = calculate_price_change_percent(
                    update_previous_price, current_price
                )
                if last_market_update_time is None:
                    cumulative_change_percent = user_period_change_percent
                logger.debug(
                    "important_alert_baseline_used user_id=%s symbol=%s baseline_time=%s "
                    "window_seconds=%s cumulative_change=%.4f",
                    recipient.user_id,
                    symbol.upper(),
                    last_market_update_time.isoformat() if last_market_update_time else None,
                    update_window_seconds,
                    cumulative_change_percent,
                )
                context_object = SignalContext(
                    symbol=symbol,
                    current_price=current_price,
                    latest_5m_change_percent=latest_5m_change_percent,
                    change_since_last_market_update_percent=cumulative_change_percent,
                    user_period_change_percent=user_period_change_percent,
                    one_hour_change_percent=one_hour_change_percent,
                    four_hour_change_percent=four_hour_change_percent,
                    twenty_four_hour_change_percent=change_24h,
                    relevant_news_items=news_items,
                    news_candidates=news_candidates,
                    news_relevance_score=news_relevance,
                    last_notification_time=(
                        recent_event_alert.created_at
                        if recent_event_alert is not None
                        else last_notification.created_at
                        if last_notification
                        else None
                    ),
                    last_notification_type=(
                        recent_event_alert.alert_type
                        if recent_event_alert is not None
                        else last_notification.alert_type
                        if last_notification
                        else None
                    ),
                    last_notification_severity=(
                        recent_event_alert.llm_severity
                        if recent_event_alert is not None
                        else last_notification.llm_severity
                        if last_notification
                        else None
                    ),
                    last_notification_direction=_last_alert_direction(
                        recent_event_alert if recent_event_alert is not None else last_notification
                    ),
                    last_market_update_time=last_market_update_time,
                    user_alert_frequency_seconds=frequency_seconds,
                    scheduled_market_update_due=scheduled_due,
                    fast_movement_threshold_percent=thresholds.movement_percent,
                    cumulative_movement_threshold_percent=thresholds.movement_percent,
                    extreme_movement_threshold_percent=max(
                        thresholds.movement_percent * 3.0,
                        thresholds.trend_24h_high_percent,
                    ),
                    suppression_context={
                        "previous_cumulative_movement_percent": (
                            symbol_alert_state.last_cumulative_movement_percent
                            if symbol_alert_state
                            else _numeric_context_value(
                                getattr(recent_event_alert, "numeric_context", None),
                                "change_since_last_market_update_percent",
                            )
                        ),
                        "last_event_alert_price": _numeric_context_value(
                            getattr(recent_event_alert, "numeric_context", None),
                            "current_price",
                        ),
                    },
                )
                notification_decision = decide_notification(context_object)
                logger.debug(
                    "cooldown_decision user_id=%s symbol=%s alert_type=%s direction=%s "
                    "severity=%s should_send=%s suppressed=%s last_event_at=%s",
                    recipient.user_id,
                    symbol.upper(),
                    notification_decision.notification_type.value,
                    notification_decision.direction.value,
                    notification_decision.severity.value,
                    notification_decision.should_send,
                    notification_decision.should_suppress,
                    recent_event_alert.created_at.isoformat() if recent_event_alert else None,
                )
                if notification_decision.notification_type is NotificationType.MARKET_UPDATE:
                    logger.info(
                        "market_update_severity_adjusted symbol=%s severity=%s "
                        "period=%.4f trend_24h=%.4f",
                        symbol.upper(),
                        notification_decision.severity.value,
                        user_period_change_percent,
                        change_24h,
                    )
                logger.info(
                    "%s notification decision: type=%s severity=%s direction=%s "
                    "send=%s suppress=%s trigger=%s reason=%s",
                    symbol.upper(),
                    notification_decision.notification_type.value,
                    notification_decision.severity.value,
                    notification_decision.direction.value,
                    notification_decision.should_send,
                    notification_decision.should_suppress,
                    (
                        notification_decision.trigger_source.value
                        if notification_decision.trigger_source
                        else None
                    ),
                    notification_decision.reasoning_summary,
                )
                logger.info(
                    "trigger_source_selected symbol=%s trigger_source=%s",
                    symbol.upper(),
                    (
                        notification_decision.trigger_source.value
                        if notification_decision.trigger_source
                        else None
                    ),
                )
                if notification_decision.notification_type.value in PRODUCT_ALERT_TYPES:
                    logger.info(
                        "alert_type_mapped_to_new_model symbol=%s alert_type=%s",
                        symbol.upper(),
                        notification_decision.notification_type.value,
                    )
                if (
                    _should_skip_market_update_after_recent_event_alert(
                        notification_type=notification_decision.notification_type,
                        recent_event_alert=recent_event_alert,
                        now=now,
                    )
                ):
                    logger.info(
                        "market_update_skipped_after_recent_event_alert "
                        "user_id=%s symbol=%s recent_alert_type=%s",
                        recipient.user_id,
                        symbol.upper(),
                        recent_event_alert.alert_type,
                    )
                    continue
                if _should_skip_near_duplicate_market_update(
                    notification_type=notification_decision.notification_type,
                    previous_alert=last_market_update_alert,
                    context=context_object,
                    decision=notification_decision,
                    now=now,
                    frequency_seconds=frequency_seconds,
                ):
                    logger.debug(
                        "market_update_near_duplicate_suppressed user_id=%s symbol=%s",
                        recipient.user_id,
                        symbol.upper(),
                    )
                    continue
                if not notification_decision.should_send:
                    logger.info(
                        "%s alert skipped: %s",
                        symbol.upper(),
                        notification_decision.reasoning_summary,
                    )
                    continue
                group_key = (
                    notification_decision.notification_type.value,
                    notification_decision.severity.value,
                    notification_decision.direction.value,
                    (
                        notification_decision.trigger_source.value
                        if notification_decision.trigger_source
                        else None
                    ),
                    frequency_seconds,
                )
                if group_key not in grouped_notifications:
                    grouped_notifications[group_key] = (
                        context_object,
                        notification_decision,
                        [],
                    )
                grouped_notifications[group_key][2].append(recipient)

            for signal_context, notification_decision, recipients in grouped_notifications.values():
                event_type = notification_decision.notification_type.value
                price_change_percent = (
                    signal_context.latest_5m_change_percent
                    if notification_decision.trigger_source is TriggerSource.FAST_MOVEMENT
                    else signal_context.change_since_last_market_update_percent
                    or signal_context.user_period_change_percent
                    or 0.0
                )
                previous_for_event = current_price / (1 + (price_change_percent / 100.0))
                used_news_items.extend(news_items)
                severity = SeverityEvaluation(
                    severity=_notification_severity_to_alert_severity(
                        notification_decision.severity
                    ),
                    primary_alert_type=AlertType.PRICE_MOVEMENT,
                    signals=(notification_decision.reasoning_summary,),
                )
                market_event_id, _ = await _get_or_create_price_movement_market_event(
                    symbol=symbol,
                    event_type=event_type,
                    previous_price=previous_for_event,
                    current_price=current_price,
                    price_change_percent=price_change_percent,
                    change_24h=change_24h,
                    change_7d=change_7d if isinstance(change_7d, float) else None,
                )
                if event_type == NotificationType.MARKET_UPDATE.value:
                    logger.info(
                        "market_update_created_per_symbol user_id_count=%s symbol=%s",
                        len(recipients),
                        symbol.upper(),
                    )
                ai_started_at = perf_counter()
                alert_payload = _build_product_notification_payload(
                    signal_context, notification_decision
                )
                event_ai_analysis_id = await _save_product_notification_analysis(
                    market_event_id=market_event_id,
                    alert_payload=alert_payload,
                    signal_context=signal_context,
                    decision=notification_decision,
                )
                logger.info(
                    "%s AI analysis resolved in %.2f seconds.",
                    symbol.upper(),
                    perf_counter() - ai_started_at,
                )
                delivered = await _deliver_market_event_alert(
                    app,
                    symbol=symbol,
                    alert_payload=alert_payload,
                    market_event_id=market_event_id,
                    event_ai_analysis_id=event_ai_analysis_id,
                    recipients=recipients,
                    event_type=event_type,
                    severity=severity,
                    trigger_reason=notification_decision.reasoning_summary,
                    trigger_source=(
                        notification_decision.trigger_source.value
                        if notification_decision.trigger_source
                        else None
                    ),
                    numeric_context=_format_signal_context_for_storage(
                        signal_context, notification_decision
                    ),
                    thresholds_used=_format_thresholds_for_storage(thresholds),
                )
                if delivered:
                    delivered_symbols += 1
            await _save_price_state(
                symbol=symbol,
                state=state,
                current_price=current_price,
                change_24h=change_24h,
                change_7d=change_7d if isinstance(change_7d, float) else None,
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
    recipients = await get_alert_recipients(
        symbol=DEFAULT_SYMBOL,
        event_type="strong_signal",
    )
    if not recipients:
        log("No eligible recipients for BTC strong-signal alert. Skipping AI analysis.")
        return

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
    market_event_id, _ = await _get_or_create_strong_signal_market_event(
        price=price,
        change_24h=change_24h,
        change_7d=change_7d,
        news_items=news_items,
    )
    alert_payload, event_ai_analysis_id, strength, direction = (
        await _get_or_create_strong_signal_ai_analysis(
            market_event_id=market_event_id,
            price=price,
            change_24h=change_24h,
            change_7d=change_7d,
            news_items=news_items,
        )
    )
    if not alert_payload:
        return

    severity = evaluate_alert_severity(
        SeverityInput(
            symbol=DEFAULT_SYMBOL,
            price_change_percent=0.0,
            change_24h=change_24h,
            change_7d=change_7d,
            news_relevance=_classify_news_context(DEFAULT_SYMBOL, news_items),
            strong_signal_strength=strength,
        )
    )
    delivered = await _deliver_market_event_alert(
        context.application,
        symbol=DEFAULT_SYMBOL,
        alert_payload=alert_payload,
        market_event_id=market_event_id,
        event_ai_analysis_id=event_ai_analysis_id,
        recipients=recipients,
        event_type="strong_signal",
        severity=severity,
    )
    if delivered:
        await remember_news_context(news_items)
        state["last_strong_signal_alert_at"] = now.isoformat()
        state["last_strong_signal_strength"] = strength
        state["last_strong_signal_direction"] = direction
        save_state(state)
