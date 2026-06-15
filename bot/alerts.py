import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from hashlib import sha256
from html import escape
from time import perf_counter
from urllib.parse import urlsplit

import httpx
from telegram import MessageEntity
from telegram.constants import ParseMode
from telegram.error import BadRequest, Forbidden, NetworkError, RetryAfter, TimedOut
from telegram.ext import Application, ContextTypes

from bot.alerting import event_identity as _event_identity
from bot.alerting import news_context as _news_context
from bot.alerting.alert_rules import calculate_price_change_percent
from bot.alerting.alert_severity import (
    AlertDecision,
    AlertSeverity,
    AlertType,
    SeverityEvaluation,
    alert_title_action,
)
from bot.alerting.event_analysis import (
    EVENT_ALERT_TYPE,
    EVENT_ANALYSIS_TYPE,
    EventAnalysisDecision,
    EventAnalysisValidationError,
    validate_event_analysis_output,
    with_canonical_event_key,
)
from bot.alerting.market_heartbeat import (
    MARKET_HEARTBEAT_ANALYSIS_TYPE,
    MARKET_HEARTBEAT_TYPE,
    MarketHeartbeatDecision,
    MarketHeartbeatValidationError,
    sanitize_heartbeat_message_body,
    sanitize_heartbeat_possible_action,
    validate_market_heartbeat_output,
)
from bot.alerting.notification_decision import (
    NotificationDecision,
    NotificationDirection,
    NotificationSeverity,
    NotificationType,
    SignalContext,
    TriggerSource,
)
from bot.coin_icons import build_coin_icon_html, build_coin_icon_prefix, coin_fallback_emoji
from bot.config import (
    ENABLE_NEWS_DRIVEN_ALERTS,
    EVENT_ALERT_SEMANTIC_COOLDOWN_SECONDS,
    SEEN_NEWS_KEEP_LATEST,
    TELEGRAM_CHAT_ID,
)
from bot.db.database import (
    attach_analysis_to_market_event,
    cleanup_seen_news,
    get_active_users_with_alert_preferences,
    get_last_sent_alert,
    get_last_sent_alert_at,
    get_latest_market_heartbeat,
    get_latest_sent_alert_for_symbol,
    get_latest_sent_event_alert_for_event_key,
    get_latest_success_event_ai_analysis,
    get_market_event_by_instance_key,
    get_or_create_market_event,
    get_price_snapshots_since,
    get_price_state,
    get_reference_price_snapshot,
    make_news_key,
    mark_user_bot_blocked,
    reserve_alert_delivery,
    reserve_market_heartbeat_delivery,
    save_alert,
    save_alert_delivery_outcome,
    save_event_llm_analysis,
    save_market_heartbeat,
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
from bot.domain.supported_coins import (
    SUPPORTED_COINS,
    SUPPORTED_SYMBOLS,
    display_symbol,
    normalize_symbol,
)
from bot.news import (
    fetch_news_context,
    remember_news_context,
    select_intelligence_news_for_symbol,
    select_recent_news_items_for_alerts,
)
from bot.news_titles import clean_news_title, clean_related_news_text
from bot.reports import generate_daily_report_cache_job, generate_weekly_report_cache_job
from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL, log
from bot.services.ai_agent_groq import (
    GROQ_EVENT_ANALYSIS_MODEL,
    AISchemaValidationError,
    LLMRateLimitBackoffActive,
    ask_event_analysis_raw,
    ask_market_heartbeat_raw,
    classify_ai_error_reason,
    mark_llm_usage_log_status,
    sanitize_alert_message,
)
from bot.services.price_service import (
    DEFAULT_SYMBOL,
    CoinGeckoRateLimitError,
    get_coin_market_data_batch,
)
from bot.settings import (
    get_db_alert_settings,
    get_state_alert_settings,
    normalize_automatic_check_interval_seconds,
)
from bot.storage import load_state, save_state
from bot.telegram_errors import is_bot_blocked_error

EVENT_ANALYSIS_PAYLOAD_POINTS = _event_identity.EVENT_ANALYSIS_PAYLOAD_POINTS
EVENT_SEMANTIC_MATERIAL_MOVEMENT_DELTA_PERCENT = (
    _event_identity.EVENT_SEMANTIC_MATERIAL_MOVEMENT_DELTA_PERCENT
)
AnalysedWindowReference = _event_identity.AnalysedWindowReference
_analysed_window_minutes_from_payload = _event_identity._analysed_window_minutes_from_payload
_automatic_market_check_job_name = _event_identity._automatic_market_check_job_name
_build_event_analysis_id = _event_identity._build_event_analysis_id
_build_event_instance_key = _event_identity._build_event_instance_key
_build_market_heartbeat_id = _event_identity._build_market_heartbeat_id
_build_news_driven_event_instance_key = _event_identity._build_news_driven_event_instance_key
_build_news_driven_event_key = _event_identity._build_news_driven_event_key
_calculate_price_change = _event_identity._calculate_price_change
_event_alert_change_label = _event_identity._event_alert_change_label
_event_input_hash = _event_identity._event_input_hash
_event_instance_bucket = _event_identity._event_instance_bucket
_event_instance_key_for_decision = _event_identity._event_instance_key_for_decision
_event_movement_percent_from_payload = _event_identity._event_movement_percent_from_payload
_event_semantic_cooldown_allows_escalation = (
    _event_identity._event_semantic_cooldown_allows_escalation
)
_event_semantic_cooldown_escalation_details = (
    _event_identity._event_semantic_cooldown_escalation_details
)
_format_analysed_window_label = _event_identity._format_analysed_window_label
_json_dumps = _event_identity._json_dumps
_numeric_context_payload = _event_identity._numeric_context_payload
_optional_float = _event_identity._optional_float
_raw_event_key_from_payload = _event_identity._raw_event_key_from_payload
_seconds_until_next_symbol_check = _event_identity._seconds_until_next_symbol_check
_select_analysed_window_reference = _event_identity._select_analysed_window_reference
_semantic_family_from_payload = _event_identity._semantic_family_from_payload
_stable_float = _event_identity._stable_float
_stable_market_identity_details = _event_identity._stable_market_identity_details
_stable_market_movement_bucket = _event_identity._stable_market_movement_bucket
_stable_related_news_ids = _event_identity._stable_related_news_ids
_symbol_stagger_offsets_seconds = _event_identity._symbol_stagger_offsets_seconds
_urgency_rank = _event_identity._urgency_rank
_utc_checked_at = _event_identity._utc_checked_at
get_analysed_window_minutes = _event_identity.get_analysed_window_minutes

BTC_ONLY_NEWS_TERMS = _news_context.BTC_ONLY_NEWS_TERMS
CLEAR_MARKET_WIDE_NEWS_TERMS = _news_context.CLEAR_MARKET_WIDE_NEWS_TERMS
COIN_ALIASES = _news_context.COIN_ALIASES
COMPANY_BACKGROUND_NEWS_TERMS = _news_context.COMPANY_BACKGROUND_NEWS_TERMS
CRITICAL_NEWS_CATEGORIES = _news_context.CRITICAL_NEWS_CATEGORIES
GENERIC_NEWS_TERMS = _news_context.GENERIC_NEWS_TERMS
MARKET_MOVING_NEWS_TERMS = _news_context.MARKET_MOVING_NEWS_TERMS
MARKET_WIDE_NEWS_TERMS = _news_context.MARKET_WIDE_NEWS_TERMS
MATERIAL_NEWS_TERMS = _news_context.MATERIAL_NEWS_TERMS
_candidate_news_relevance_label = _news_context._candidate_news_relevance_label
_coin_name = _news_context._coin_name
_format_candidate_news = _news_context._format_candidate_news
_is_clearly_market_wide_news = _news_context._is_clearly_market_wide_news
_log_news_selection_summary = _news_context._log_news_selection_summary
_matches_symbol_alias = _news_context._matches_symbol_alias
_mentions_btc = _news_context._mentions_btc
_news_driven_identity = _news_context._news_driven_identity
_news_id = _news_context._news_id
_news_metadata_matches_symbol = _news_context._news_metadata_matches_symbol
_news_search_text = _news_context._news_search_text
_news_sort_key = _news_context._news_sort_key
_news_symbols = _news_context._news_symbols
_news_text = _news_context._news_text
_news_within_hours = _news_context._news_within_hours
_parse_news_datetime = _news_context._parse_news_datetime
_sort_news_fresh_first = _news_context._sort_news_fresh_first
_stable_news_link = _news_context._stable_news_link
classify_news_relevance = _news_context.classify_news_relevance
filter_news_for_symbol = _news_context.filter_news_for_symbol
is_generic_news_item = _news_context.is_generic_news_item
is_material_news_item = _news_context.is_material_news_item
re_search_word = _news_context.re_search_word

logger = logging.getLogger(__name__)

PRODUCT_ALERT_TYPES = {
    NotificationType.MARKET_UPDATE.value,
    NotificationType.IMPORTANT_ALERT.value,
    NotificationType.CRITICAL_ALERT.value,
}
DELIVERABLE_ALERT_TYPES = (
    {alert_type.value for alert_type in AlertType}
    | PRODUCT_ALERT_TYPES
    | {EVENT_ALERT_TYPE, MARKET_HEARTBEAT_TYPE}
)
AUTOMATIC_MARKET_CHECK_JOB_NAME = "automatic_market_check"
AUTOMATIC_BTC_CHECK_JOB_NAME = AUTOMATIC_MARKET_CHECK_JOB_NAME
MARKET_HEARTBEAT_JOB_NAME = "market_heartbeat_generation"
DAILY_REPORT_CACHE_JOB_NAME = "daily_report_cache"
WEEKLY_REPORT_CACHE_JOB_NAME = "weekly_report_cache"
SEEN_NEWS_CLEANUP_JOB_NAME = "seen_news_cleanup"
TELEGRAM_DELIVERY_MAX_ATTEMPTS = 3
TELEGRAM_DELIVERY_RETRY_BACKOFF_SECONDS = (30, 120)
NEWS_DRIVEN_ALERT_MAX_AGE_HOURS = 6
NEWS_DRIVEN_ALERT_MAX_PER_SYMBOL = 1
NEWS_DRIVEN_ALERT_SOURCE = "news_driven_alert"
NEWS_DRIVEN_ALERT_MODEL = "deterministic-news-driven-alerts-v1"
SUPPRESSION_EXACT_COOLDOWN = "exact_cooldown"
SUPPRESSION_SEMANTIC_COOLDOWN = "semantic_cooldown"
SUPPRESSION_USER_FREQUENCY_COOLDOWN = "user_frequency_cooldown"
SUPPRESSION_NO_ELIGIBLE_RECIPIENT = "no_eligible_recipient"
SUPPRESSION_PREMIUM_REQUIRED = "premium_required"
SUPPRESSION_PRODUCT_GATED = "product_gated"
SUPPRESSION_DELIVERY_FAILED = "delivery_failed"
SUPPRESSION_LLM_RATE_LIMITED = "llm_rate_limited"
SUPPRESSION_STALE_HEARTBEAT = "stale_heartbeat"
SUPPRESSION_UNKNOWN = "unknown"
SUPPRESSION_REASON_VALUES = {
    SUPPRESSION_EXACT_COOLDOWN,
    SUPPRESSION_SEMANTIC_COOLDOWN,
    SUPPRESSION_USER_FREQUENCY_COOLDOWN,
    SUPPRESSION_NO_ELIGIBLE_RECIPIENT,
    SUPPRESSION_PREMIUM_REQUIRED,
    SUPPRESSION_PRODUCT_GATED,
    SUPPRESSION_DELIVERY_FAILED,
    SUPPRESSION_LLM_RATE_LIMITED,
    SUPPRESSION_STALE_HEARTBEAT,
    SUPPRESSION_UNKNOWN,
}
OUTCOME_DELIVERED = "delivered"
OUTCOME_SUPPRESSED = "suppressed"
OUTCOME_FILTERED = "filtered"
OUTCOME_FAILED = "failed"
OUTCOME_RATE_LIMITED = "rate_limited"
OUTCOME_COOLDOWN = "cooldown"
OUTCOME_NOT_SCHEDULED = "not_scheduled"
OUTCOME_NO_ELIGIBLE_RECIPIENTS = "no_eligible_recipients"
REASON_DELIVERED = "delivered"
REASON_DUPLICATE_EVENT = "duplicate_event"
REASON_SIMILAR_EVENT_SUPPRESSED = "similar_event_suppressed"
REASON_USER_NOT_ELIGIBLE = "user_not_eligible"
REASON_PREMIUM_REQUIRED = "premium_required"
REASON_WATCHLIST_DISABLED = "watchlist_disabled"
REASON_COOLDOWN_ACTIVE = "cooldown_active"
REASON_TELEGRAM_SEND_FAILED = "telegram_send_failed"
REASON_LLM_RATE_LIMITED = "llm_rate_limited"
REASON_LLM_INVALID_RESPONSE = "llm_invalid_response"
REASON_NO_RECIPIENTS = "no_recipients"
REASON_DELIVERY_NOT_SCHEDULED = "delivery_not_scheduled"
REASON_ALREADY_DELIVERED = "already_delivered"
REASON_SEVERITY_BELOW_THRESHOLD = "severity_below_threshold"

@dataclass(frozen=True)
class AlertRecipient:
    chat_id: int
    user_id: int | None = None
    alert_frequency_seconds: int | None = field(default=None, compare=False)

@dataclass(frozen=True)
class RecipientOutcome:
    recipient: AlertRecipient
    status: str
    reason_code: str
    eligible: bool
    detail: str | None = None

@dataclass(frozen=True)
class EventRecipientFilterResult:
    recipients: list[AlertRecipient]
    suppression_reason_counts: dict[str, int]
    suppressed: list[RecipientOutcome] = field(default_factory=list)

@dataclass(frozen=True)
class AlertRecipientResolution:
    recipients: list[AlertRecipient]
    filtered: list[RecipientOutcome] = field(default_factory=list)

def _count_suppression(
    counts: dict[str, int],
    reason: str,
) -> None:
    normalized_reason = reason if reason in SUPPRESSION_REASON_VALUES else SUPPRESSION_UNKNOWN
    counts[normalized_reason] = counts.get(normalized_reason, 0) + 1

def _log_event_alert_suppression(
    *,
    symbol: str,
    suppression_reason: str,
    suppression_count: int,
    raw_event_key: str | None = None,
    canonical_event_key: str | None = None,
    semantic_family: str | None = None,
    event_instance_key: str | None = None,
    delivery_count: int = 0,
    analysed_window_minutes: int | None = None,
) -> None:
    normalized_reason = (
        suppression_reason
        if suppression_reason in SUPPRESSION_REASON_VALUES
        else SUPPRESSION_UNKNOWN
    )
    logger.info(
        "ops_event=event_alert_suppression "
        "symbol=%s raw_event_key=%s canonical_event_key=%s semantic_family=%s "
        "event_instance_key=%s delivery_count=%s suppression_count=%s "
        "suppression_reason=%s analysed_window_minutes=%s",
        normalize_symbol(symbol).upper(),
        raw_event_key,
        canonical_event_key,
        semantic_family,
        event_instance_key,
        delivery_count,
        suppression_count,
        normalized_reason,
        analysed_window_minutes,
    )

def _primary_suppression_reason(counts: dict[str, int]) -> str | None:
    if not counts:
        return None
    return max(counts.items(), key=lambda item: item[1])[0]

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

async def _select_related_news_context(
    symbol: str,
    raw_news_items: list[dict] | None,
    *,
    fetch_limit: int,
    intelligence_limit: int = 8,
    intelligence_max_age_hours: int | None = None,
    fallback_max_age_hours: int | None = None,
    now: datetime | None = None,
) -> tuple[list[dict], list[dict] | None, bool]:
    normalized_symbol = normalize_symbol(symbol)
    if DB_ENABLED and DB_SESSION_LOCAL:
        try:
            selection_stats: dict[str, int] = {}
            async with DB_SESSION_LOCAL() as session:
                intelligence_news = await select_intelligence_news_for_symbol(
                    session,
                    normalized_symbol,
                    limit=intelligence_limit,
                    max_age_hours=intelligence_max_age_hours,
                    now=now,
                    selection_stats=selection_stats,
                )
            if intelligence_news:
                filtered_intelligence_news = filter_news_for_symbol(
                    normalized_symbol,
                    intelligence_news,
                    max_direct=intelligence_limit,
                    max_market_wide=min(3, intelligence_limit),
                )
                _log_news_selection_summary(
                    symbol=normalized_symbol,
                    source="news_items",
                    raw_news_items=intelligence_news,
                    selected_news_items=filtered_intelligence_news,
                    fallback_used=False,
                    selection_stats=selection_stats,
                )
                if filtered_intelligence_news:
                    return filtered_intelligence_news, raw_news_items, True
            logger.info(
                "related_news_selection symbol=%s source=news_items candidate_count=%s "
                "direct_news_count=0 market_wide_news_count=0 irrelevant_filtered_count=0 "
                "selected_count=0 selected_news_titles=[] selected_news_relevance_labels=[] "
                "noise_filtered_count=%s dedup_filtered_count=%s fallback_used=%s",
                normalized_symbol.upper(),
                selection_stats.get("candidate_count", 0),
                selection_stats.get("noise_filtered_count", 0),
                selection_stats.get("dedup_filtered_count", 0),
                True,
            )
        except Exception:
            logger.warning(
                "%s intelligence news selection failed; falling back to RSS news.",
                normalized_symbol.upper(),
            )

    if raw_news_items is None:
        raw_news_items = await fetch_news_context(limit=fetch_limit, use_intelligence=False)
        if fallback_max_age_hours is not None:
            raw_news_items = _news_within_hours(
                raw_news_items,
                now=now or datetime.now(timezone.utc),
                hours=fallback_max_age_hours,
            )
    filtered_news = filter_news_for_symbol(normalized_symbol, raw_news_items)
    _log_news_selection_summary(
        symbol=normalized_symbol,
        source="fallback",
        raw_news_items=raw_news_items,
        selected_news_items=filtered_news,
        fallback_used=True,
    )
    return filtered_news, raw_news_items, False

def _truncate_text(value: str, max_chars: int) -> str:
    cleaned = " ".join(str(value or "").split()).strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 1].rstrip(" ,;:") + "."

def _compact_candidate_news(candidate_news: list[dict], *, limit: int = 3) -> list[dict]:
    compacted = []
    for item in candidate_news[:limit]:
        compacted.append(
            {
                **item,
                "summary": _truncate_text(str(item.get("summary") or ""), 300),
            }
        )
    return compacted

def _compact_event_analysis_news(candidate_news: list[dict], *, limit: int = 3) -> list[dict]:
    compacted = []
    for item in candidate_news[:limit]:
        compacted.append(
            {
                "news_id": str(item.get("news_id") or ""),
                "source": str(item.get("source") or "").strip(),
                "title": str(item.get("title") or "").strip(),
                "time": str(item.get("published_at") or "").strip(),
                "summary": _truncate_text(str(item.get("summary") or ""), 300),
                "relevance_label": str(item.get("relevance_label") or "").strip(),
            }
        )
    return compacted

def _select_representative_snapshots(
    snapshots_payload: list[dict], *, limit: int = 6
) -> list[dict]:
    if len(snapshots_payload) <= limit:
        return snapshots_payload
    if limit <= 1:
        return snapshots_payload[-1:]
    last_index = len(snapshots_payload) - 1
    selected_indices = {
        round(index * last_index / (limit - 1))
        for index in range(limit)
    }
    selected_indices.add(last_index)
    selected = [snapshots_payload[index] for index in sorted(selected_indices)]
    return selected[-limit:]

def _compact_event_snapshot(snapshot: dict, *, now: datetime) -> dict:
    raw_timestamp = snapshot.get("timestamp_utc")
    if isinstance(raw_timestamp, datetime):
        timestamp = raw_timestamp
    else:
        timestamp = datetime.fromisoformat(str(raw_timestamp).replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    delta_seconds = (
        timestamp.astimezone(timezone.utc) - now.astimezone(timezone.utc)
    ).total_seconds()
    minutes = int(round(delta_seconds / 60))
    return {
        "m": minutes,
        "p": _stable_float(float(snapshot["price_usd"]), 2),
    }

def _compact_event_snapshots(snapshots_payload: list[dict], *, now: datetime) -> list[dict]:
    return [_compact_event_snapshot(snapshot, now=now) for snapshot in snapshots_payload]

def _snapshot_price(snapshot) -> float:
    return float(snapshot.price)

def _snapshot_change_percent(current_price: float, reference) -> float | None:
    if reference is None:
        return None
    reference_price = _snapshot_price(reference)
    if reference_price == 0:
        return None
    return calculate_price_change_percent(reference_price, current_price)

def _snapshot_at_or_before(snapshots: list, cutoff: datetime):
    cutoff_utc = cutoff.astimezone(timezone.utc)
    eligible = [
        snapshot
        for snapshot in snapshots
        if (
            snapshot.checked_at
            if snapshot.checked_at.tzinfo is not None
            else snapshot.checked_at.replace(tzinfo=timezone.utc)
        ).astimezone(timezone.utc)
        <= cutoff_utc
    ]
    return eligible[-1] if eligible else None

def _related_news_by_id(
    candidate_news: list[dict],
    related_news_ids: list[str],
    *,
    symbol: str | None = None,
    context: str = "related news",
) -> list[dict]:
    by_id = {str(item.get("news_id")): item for item in candidate_news}
    mapped_items: list[dict] = []
    missing_ids: list[str] = []
    for news_id in related_news_ids:
        item = by_id.get(str(news_id))
        if item is None:
            missing_ids.append(str(news_id))
            continue
        mapped_items.append(item)
    if missing_ids:
        logger.warning(
            "%s selected related_news_ids could not be mapped: symbol=%s missing_ids=%s",
            context,
            normalize_symbol(symbol).upper() if symbol else "unknown",
            missing_ids[:5],
        )
    return mapped_items

def _format_optional_percent(value: float | None) -> str:
    return "n/a" if value is None else f"{value:+.2f}%"

def _format_optional_price(value: float | None) -> str:
    return "n/a" if value is None else f"${value:,.2f}"

def _coin_fallback_emoji(symbol: str) -> str:
    return coin_fallback_emoji(symbol)

EVENT_ALERT_PLACEHOLDER_TEXT_RE = re.compile(
    r"(?i)(?<![a-z0-9])(?:n/a|null|unknown|unavailable)(?![a-z0-9])"
)


def _sanitize_event_text(
    value: str | None,
    fallback: str = "",
    *,
    omit_placeholders: bool = False,
) -> str:
    cleaned = " ".join(str(value or "").split()).strip()
    cleaned = re.sub(r"(?i)\bnot financial advice\.?", "", cleaned).strip()
    if omit_placeholders and EVENT_ALERT_PLACEHOLDER_TEXT_RE.search(cleaned):
        return fallback
    return cleaned or fallback


DRAMATIC_EVENT_WORD_REPLACEMENTS = (
    (re.compile(r"(?i)\bbloodbath\b"), "stress"),
    (re.compile(r"(?i)\bmeltdown\b"), "stress"),
    (re.compile(r"(?i)\bpanic(?:s|ked|king)?\b"), "stress"),
    (re.compile(r"(?i)\bcrash(?:es|ed|ing)?\b"), "move"),
    (re.compile(r"(?i)\bcollaps(?:e|es|ed|ing)\b"), "move"),
    (re.compile(r"(?i)\bplung(?:e|es|ed|ing)\b"), "move lower"),
    (re.compile(r"(?i)\bsurg(?:e|es|ed|ing)\b"), "move higher"),
    (
        re.compile(r"(?i)\b(?:explod(?:e|es|ed|ing)|explosion|explosive(?:s)?)\b"),
        "move higher",
    ),
    (re.compile(r"(?i)\bmoon(?:s|ed|ing)?\b"), "move higher"),
    (re.compile(r"(?i)\bskyrocket(?:s|ed|ing)?\b"), "move higher"),
)


def _small_analysed_window_move(analysed_window_change: object) -> bool:
    movement = _optional_float(analysed_window_change)
    return (
        movement is not None
        and abs(movement) < EVENT_SEMANTIC_MATERIAL_MOVEMENT_DELTA_PERCENT
    )


def _guard_small_move_dramatic_event_text(value: str, *, small_move: bool) -> str:
    if not small_move:
        return value
    guarded = value
    for pattern, replacement in DRAMATIC_EVENT_WORD_REPLACEMENTS:
        guarded = pattern.sub(replacement, guarded)
    return " ".join(guarded.split()).strip()

def _utf16_length(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2

def _safe_telegram_link_url(value: str | None) -> str | None:
    url = str(value or "").strip()
    if not url:
        return None
    parsed = urlsplit(url)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return None
    return url

def _format_related_context(related_news: list[dict], *, empty_text: str) -> str:
    if not related_news:
        return empty_text
    lines = []
    for item in related_news[:3]:
        title_text = clean_news_title(str(item.get("title") or ""))
        source = str(item.get("source") or "").strip()
        if not title_text:
            continue
        display_text = clean_related_news_text(
            f"{title_text} - {source}" if source else title_text,
            source=source,
        )
        if not display_text:
            continue
        lines.append(f"\u2022 {display_text}")
    return "\n".join(lines) if lines else empty_text

def _format_event_related_context(
    related_news: list[dict], *, empty_text: str
) -> tuple[str, list[dict], str | None]:
    if not related_news:
        return empty_text, [], None

    lines: list[str] = []
    html_lines: list[str] = []
    link_entities: list[dict] = []
    cursor = 0
    missing_url_count = 0
    for item in related_news[:3]:
        title_text = clean_news_title(str(item.get("title") or ""))
        source = str(item.get("source") or "").strip()
        url = _safe_telegram_link_url(str(item.get("url") or item.get("link") or ""))
        if not title_text:
            continue

        link_text = clean_related_news_text(
            f"{title_text} - {source}" if source else title_text,
            source=source,
        )
        if not link_text:
            continue
        line = f"\u2022 {link_text}"
        escaped_link_text = escape(link_text)
        if lines:
            cursor += 1
        if url:
            link_entities.append(
                {
                    "offset": cursor + _utf16_length("\u2022 "),
                    "length": _utf16_length(link_text),
                    "url": url,
                }
            )
            html_lines.append(
                f'\u2022 <a href="{escape(url, quote=True)}">{escaped_link_text}</a>'
            )
        else:
            missing_url_count += 1
            html_lines.append(f"\u2022 {escaped_link_text}")
        lines.append(line)
        cursor += _utf16_length(line)

    if missing_url_count:
        logger.warning(
            "event related news selected without valid article URL: missing_url_count=%s",
            missing_url_count,
        )
    if not lines:
        return empty_text, [], None
    return "\n".join(lines), link_entities, "\n".join(html_lines)

def _format_market_heartbeat_related_context(
    related_news: list[dict], *, empty_text: str
) -> tuple[str, str | None]:
    if not related_news:
        return empty_text, None

    plain_lines: list[str] = []
    html_lines: list[str] = []
    for item in related_news[:3]:
        title_text = clean_news_title(str(item.get("title") or ""))
        source = str(item.get("source") or "").strip()
        url = _safe_telegram_link_url(str(item.get("url") or item.get("link") or ""))
        if not title_text:
            continue

        display_text = clean_related_news_text(
            f"{title_text} - {source}" if source else title_text,
            source=source,
        )
        if not display_text:
            continue

        plain_lines.append(f"\u2022 {display_text}")
        if url:
            html_lines.append(
                f'\u2022 <a href="{escape(url, quote=True)}">{escape(display_text)}</a>'
            )
        else:
            html_lines.append(f"\u2022 {escape(display_text)}")

    if not plain_lines:
        return empty_text, None
    return "\n".join(plain_lines), "\n".join(html_lines)

def _build_market_heartbeat_html_message(
    *,
    icon_html: str,
    symbol: str,
    title: str,
    price_text: str,
    since_last_text: str,
    change_24h_text: str,
    message_body: str,
    related_section_html: str,
    possible_action: str,
) -> str:
    return (
        f"{icon_html} \U0001f4e1 {escape(symbol)} Market Heartbeat\n\n"
        f"{escape(title)}\n\n"
        f"Price: {escape(price_text)}\n"
        f"Since last {escape(symbol)} message: {escape(since_last_text)}\n"
        f"24h change: {escape(change_24h_text)}\n\n"
        "Situation:\n"
        f"{escape(message_body)}\n\n"
        "Related context:\n"
        f"{related_section_html}\n\n"
        "Possible action:\n"
        f"{escape(possible_action)}\n\n"
        "Not financial advice."
    )

def _build_event_alert_html_message(
    *,
    icon_html: str,
    symbol: str,
    title: str,
    market_context_html: str,
    message_body: str,
    related_section_html: str,
    possible_action: str,
) -> str:
    market_section = f"{market_context_html}\n\n" if market_context_html else ""
    return (
        f"{icon_html} \u26a0\ufe0f {escape(symbol)} Event Alert\n\n"
        f"{escape(title)}\n\n"
        f"{market_section}"
        "Situation:\n"
        f"{escape(message_body)}\n\n"
        "Related context:\n"
        f"{related_section_html}\n\n"
        "Possible action:\n"
        f"{escape(possible_action)}\n\n"
        "Not financial advice."
    )

def _build_html_message_from_plain_with_icon(
    *, plain_text: str, plain_icon: str, icon_html: str
) -> str:
    if plain_text.startswith(plain_icon):
        return f"{icon_html}{escape(plain_text[len(plain_icon) :])}"
    return escape(plain_text)


def _event_alert_market_context_lines(
    *,
    symbol: str,
    price: float | None,
    change_since_message: float | None,
    analysed_window_minutes: int | None,
    analysed_window_change: float | None,
) -> list[str]:
    lines: list[str] = []
    if price is not None:
        lines.append(f"Price: {_format_optional_price(price)}")
    if change_since_message is not None:
        lines.append(
            f"Since last alert/message: {_format_optional_percent(change_since_message)}"
        )
    if analysed_window_minutes is not None and analysed_window_change is not None:
        analysed_window_label = _format_analysed_window_label(analysed_window_minutes)
        if analysed_window_label != "n/a":
            lines.append(
                f"{_event_alert_change_label(analysed_window_label)}: "
                f"{_format_optional_percent(analysed_window_change)}"
            )
    return lines

def _build_event_alert_payload(
    *,
    decision: EventAnalysisDecision,
    input_payload: dict,
    related_news: list[dict],
) -> dict:
    symbol = display_symbol(decision.symbol)
    backend_symbol = normalize_symbol(decision.symbol)
    market_data = input_payload.get("market", input_payload.get("market_data", {}))
    icon, entities = build_coin_icon_prefix(backend_symbol)
    icon_html = build_coin_icon_html(backend_symbol)
    analysed_window_change = market_data.get("chg_window")
    small_move = _small_analysed_window_move(analysed_window_change)
    title = _guard_small_move_dramatic_event_text(
        _sanitize_event_text(
            decision.title,
            f"{symbol} market event",
            omit_placeholders=True,
        ),
        small_move=small_move,
    )
    message_body = _guard_small_move_dramatic_event_text(
        _sanitize_event_text(
            decision.message_body,
            "Market conditions changed.",
            omit_placeholders=True,
        ),
        small_move=small_move,
    )
    possible_action = _guard_small_move_dramatic_event_text(
        _sanitize_event_text(
            decision.possible_action,
            "Review the situation calmly and avoid impulsive decisions.",
            omit_placeholders=True,
        ),
        small_move=small_move,
    )
    related_section, related_link_entities, related_section_html = _format_event_related_context(
        related_news,
        empty_text="No major related news selected.",
    )
    price = market_data.get("price", market_data.get("price_now_usd"))
    change_since_message = market_data.get(
        "chg_since_msg",
        market_data.get("change_since_last_user_visible_message_percent"),
    )
    analysed_window_minutes = market_data.get("analysed_window_minutes")
    market_context_lines = _event_alert_market_context_lines(
        symbol=symbol,
        price=price,
        change_since_message=change_since_message,
        analysed_window_minutes=analysed_window_minutes,
        analysed_window_change=analysed_window_change,
    )
    market_context_text = "\n".join(market_context_lines)
    market_context_block = f"{market_context_text}\n\n" if market_context_text else ""

    before_related = (
        f"{icon} \u26a0\ufe0f {symbol} Event Alert\n\n"
        f"{title}\n\n"
        f"{market_context_block}"
        "Situation:\n"
        f"{message_body}\n\n"
        "Related context:\n"
    )
    after_related = (
        "\n\n"
        "Possible action:\n"
        f"{possible_action}\n\n"
        "Not financial advice."
    )
    message = f"{before_related}{related_section}{after_related}"
    all_entities = list(entities or [])
    related_offset = _utf16_length(before_related)
    for entity in related_link_entities:
        all_entities.append(
            MessageEntity(
                type=MessageEntity.TEXT_LINK,
                offset=related_offset + int(entity["offset"]),
                length=int(entity["length"]),
                url=str(entity["url"]),
            )
        )
    html_message = None
    if icon_html != icon:
        html_message = _build_event_alert_html_message(
            icon_html=icon_html,
            symbol=symbol,
            title=title,
            market_context_html="\n".join(escape(line) for line in market_context_lines),
            message_body=message_body,
            related_section_html=related_section_html or escape(related_section),
            possible_action=possible_action,
        )
    return {"plain_text": message, "html_text": html_message, "entities": all_entities or None}

def _event_numeric_context(
    input_payload: dict,
    decision: EventAnalysisDecision,
    *,
    event_instance_key: str | None = None,
) -> str:
    market_data = input_payload.get("market", input_payload.get("market_data", {}))
    return _json_dumps(
        {
            "notification_type": EVENT_ALERT_TYPE,
            "notification_severity": decision.urgency,
            "notification_direction": None,
            "current_price": market_data.get("price", market_data.get("price_now_usd")),
            "change_since_last_market_update_percent": market_data.get(
                "chg_since_msg",
                market_data.get("change_since_last_user_visible_message_percent"),
            ),
            "analysed_window_minutes": market_data.get("analysed_window_minutes"),
            "analysed_window_change_percent": market_data.get("chg_window"),
            "twenty_four_hour_change_percent": market_data.get(
                "chg24h", market_data.get("change_24h_percent")
            ),
            "event_key": decision.event_key,
            "raw_event_key": _raw_event_key_from_payload(input_payload, decision),
            "semantic_family": _semantic_family_from_payload(input_payload),
            "event_instance_key": event_instance_key,
            "stable_related_news_ids": _stable_related_news_ids(
                input_payload,
                decision.related_news_ids,
            ),
            "confidence": decision.confidence,
        }
    )

def _heartbeat_numeric_context(
    *,
    symbol: str,
    current_price: float,
    change_since_last_message: float | None,
    change_24h: float,
    heartbeat_id: int | None,
    confidence: str | None,
) -> str:
    return _json_dumps(
        {
            "notification_type": MARKET_HEARTBEAT_TYPE,
            "symbol": normalize_symbol(symbol).upper(),
            "current_price": current_price,
            "change_since_last_market_update_percent": change_since_last_message,
            "twenty_four_hour_change_percent": change_24h,
            "market_heartbeat_id": heartbeat_id,
            "confidence": confidence,
        }
    )

def _build_market_heartbeat_payload(
    *,
    heartbeat,
    current_price: float,
    change_since_last_message: float | None,
    change_24h: float,
    related_news: list[dict],
) -> dict:
    backend_symbol = normalize_symbol(heartbeat.symbol)
    symbol = display_symbol(backend_symbol)
    icon, entities = build_coin_icon_prefix(backend_symbol)
    icon_html = build_coin_icon_html(backend_symbol)
    title = _sanitize_event_text(heartbeat.title, f"{symbol} market heartbeat")
    message_body = sanitize_heartbeat_message_body(
        heartbeat.message_body,
        f"{symbol} remains under regular monitoring.",
    )
    possible_action = sanitize_heartbeat_possible_action(heartbeat.possible_action)
    related_section, related_section_html = _format_market_heartbeat_related_context(
        related_news,
        empty_text="No major related news selected.",
    )
    price_text = _format_optional_price(current_price)
    since_last_text = _format_optional_percent(change_since_last_message)
    change_24h_text = _format_optional_percent(change_24h)
    message = (
        f"{icon} \U0001f4e1 {symbol} Market Heartbeat\n\n"
        f"{title}\n\n"
        f"Price: {price_text}\n"
        f"Since last {symbol} message: {since_last_text}\n"
        f"24h change: {change_24h_text}\n\n"
        "Situation:\n"
        f"{message_body}\n\n"
        "Related context:\n"
        f"{related_section}\n\n"
        "Possible action:\n"
        f"{possible_action}\n\n"
        "Not financial advice."
    )
    html_message = None
    if icon_html != icon or related_section_html:
        html_message = _build_market_heartbeat_html_message(
            icon_html=icon_html,
            symbol=symbol,
            title=title,
            price_text=price_text,
            since_last_text=since_last_text,
            change_24h_text=change_24h_text,
            message_body=message_body,
            related_section_html=related_section_html or escape(related_section),
            possible_action=possible_action,
        )
    return {"plain_text": message, "html_text": html_message, "entities": entities}

def _heartbeat_related_news(heartbeat) -> list[dict]:
    try:
        raw_input = json.loads(str(heartbeat.raw_input_json or "{}"))
    except json.JSONDecodeError:
        return []
    candidate_news = raw_input.get("candidate_news")
    if not isinstance(candidate_news, list):
        return []
    try:
        related_news_ids = json.loads(str(heartbeat.related_news_ids or "[]"))
    except json.JSONDecodeError:
        related_news_ids = []
    if not isinstance(related_news_ids, list):
        related_news_ids = []
    return _related_news_by_id(candidate_news, [str(item) for item in related_news_ids])

def _is_fresh_heartbeat(heartbeat, *, now: datetime, max_age_seconds: int = 7200) -> bool:
    generated_at = getattr(heartbeat, "generated_at", None)
    if generated_at is None:
        return False
    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=timezone.utc)
    return (now - generated_at.astimezone(timezone.utc)).total_seconds() <= max_age_seconds

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
    resolution = await resolve_alert_recipient_outcomes(
        symbol=symbol,
        event_type=event_type,
        now=now,
        bypass_frequency=bypass_frequency,
    )
    return resolution.recipients

async def resolve_alert_recipient_outcomes(
    symbol: str,
    event_type: str,
    *,
    now: datetime | None = None,
    bypass_frequency: bool = False,
) -> AlertRecipientResolution:
    """Resolve recipients and preserve queryable reasons for filtered users."""
    normalized_symbol = normalize_symbol(symbol)
    if event_type not in DELIVERABLE_ALERT_TYPES or normalized_symbol not in SUPPORTED_COINS:
        return AlertRecipientResolution(recipients=[])
    if DB_ENABLED and DB_SESSION_LOCAL:
        now = now or datetime.now(timezone.utc)
        recipients = []
        filtered: list[RecipientOutcome] = []
        seen_chat_ids = set()
        async with DB_SESSION_LOCAL() as session:
            for user in await get_active_users_with_alert_preferences(session):
                base_recipient = AlertRecipient(
                    chat_id=int(user.telegram_chat_id or 0),
                    user_id=user.id,
                    alert_frequency_seconds=get_effective_frequency_seconds(user, now),
                )
                if user.telegram_chat_id is None:
                    filtered.append(
                        RecipientOutcome(
                            recipient=base_recipient,
                            status=OUTCOME_FILTERED,
                            reason_code=REASON_USER_NOT_ELIGIBLE,
                            eligible=False,
                            detail="missing_telegram_chat",
                        )
                    )
                    continue
                enabled_by_symbol = _enabled_subscription_by_symbol(user)
                if not enabled_by_symbol.get(normalized_symbol, False):
                    filtered.append(
                        RecipientOutcome(
                            recipient=base_recipient,
                            status=OUTCOME_FILTERED,
                            reason_code=REASON_WATCHLIST_DISABLED,
                            eligible=False,
                        )
                    )
                    continue
                if not is_coin_unlocked_for_user(user, normalized_symbol, now):
                    filtered.append(
                        RecipientOutcome(
                            recipient=base_recipient,
                            status=OUTCOME_FILTERED,
                            reason_code=REASON_PREMIUM_REQUIRED,
                            eligible=False,
                        )
                    )
                    continue
                last_sent_at = await get_last_sent_alert_at(
                    session,
                    user_id=user.id,
                    symbol=normalized_symbol,
                )
                if not bypass_frequency and not can_deliver_now(
                    user, normalized_symbol, now, last_sent_at
                ):
                    filtered.append(
                        RecipientOutcome(
                            recipient=base_recipient,
                            status=OUTCOME_COOLDOWN,
                            reason_code=REASON_COOLDOWN_ACTIVE,
                            eligible=False,
                        )
                    )
                    continue
                chat_id = int(user.telegram_chat_id)
                if chat_id in seen_chat_ids:
                    filtered.append(
                        RecipientOutcome(
                            recipient=base_recipient,
                            status=OUTCOME_FILTERED,
                            reason_code=REASON_USER_NOT_ELIGIBLE,
                            eligible=False,
                            detail="duplicate_chat_id",
                        )
                    )
                    continue
                seen_chat_ids.add(chat_id)
                recipients.append(
                    AlertRecipient(
                        chat_id=chat_id,
                        user_id=user.id,
                        alert_frequency_seconds=get_effective_frequency_seconds(user, now),
                    )
                )
        return AlertRecipientResolution(recipients=recipients, filtered=filtered)

    if normalized_symbol == DEFAULT_SYMBOL and TELEGRAM_CHAT_ID:
        return AlertRecipientResolution(recipients=[AlertRecipient(chat_id=int(TELEGRAM_CHAT_ID))])
    return AlertRecipientResolution(recipients=[])

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
            reason = f"{display_symbol(normalized_symbol)}-specific material market context"
        elif raw_relevance == "direct" and not generic:
            relevance = "medium"
            reason = f"{display_symbol(normalized_symbol)}-specific market context"
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
    if any(term in text for term in COMPANY_BACKGROUND_NEWS_TERMS):
        return "weak"
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
        return f"{display_symbol(symbol)}-specific material market context"
    if relevance == "medium":
        return f"{display_symbol(symbol)}-specific market context"
    if raw_relevance == "direct":
        return f"Weak {display_symbol(symbol)} mention without clear market catalyst"
    return "Broad crypto market context"

def _useful_news_candidates(candidates: list[dict] | None) -> list[dict]:
    return [
        item
        for item in candidates or []
        if str(item.get("relevance") or "").strip().lower() in {"medium", "strong"}
    ]

def _is_clearly_market_moving_news(news_item: dict) -> bool:
    text = _news_text(news_item)
    return any(term in text for term in MARKET_MOVING_NEWS_TERMS)

def _news_symbol_match_strength(symbol: str, news_item: dict) -> str | None:
    normalized_symbol = normalize_symbol(symbol)
    if normalize_symbol(str(news_item.get("primary_symbol") or "")) == normalized_symbol:
        return "primary"
    if normalized_symbol in _news_symbols(news_item, "related_symbols"):
        return "related"
    if normalized_symbol in _news_symbols(news_item, "matched_symbols"):
        return "related"
    return None

def _news_item_can_trigger_standalone_alert(symbol: str, news_item: dict) -> bool:
    if normalize_symbol(symbol) not in SUPPORTED_SYMBOLS:
        return False
    if not _news_driven_identity(news_item):
        return False
    if _parse_news_datetime(news_item) is None:
        return False
    if not str(news_item.get("title") or "").strip():
        return False
    if not str(news_item.get("source") or "").strip():
        return False

    impact_level = str(news_item.get("impact_level") or "").strip().lower()
    category = str(news_item.get("category") or "").strip().lower()
    match_strength = _news_symbol_match_strength(symbol, news_item)
    if match_strength is None:
        return False

    market_moving = _is_clearly_market_moving_news(news_item)
    critical_category = category in CRITICAL_NEWS_CATEGORIES
    if match_strength == "primary":
        return (
            impact_level in {"high", "critical"}
            or (critical_category and market_moving)
            or (market_moving and not is_generic_news_item(news_item))
        )
    return (
        impact_level in {"high", "critical"}
        and critical_category
        and market_moving
        and not is_generic_news_item(news_item)
    )

def _news_driven_candidate_rank(symbol: str, news_item: dict) -> tuple[int, int, int, int, int]:
    impact_rank = {"critical": 3, "high": 2, "medium": 1, "low": 0}
    match_rank = 2 if _news_symbol_match_strength(symbol, news_item) == "primary" else 1
    published_at = _parse_news_datetime(news_item)
    impact_score = int(news_item.get("impact_score") or 0)
    relevance_score = int(news_item.get("relevance_score") or 0)
    return (
        match_rank,
        impact_rank.get(str(news_item.get("impact_level") or "").strip().lower(), 0),
        impact_score if impact_score > 0 else 0,
        relevance_score if relevance_score > 0 else 0,
        int(published_at.timestamp()) if published_at else 0,
    )

def _select_news_driven_alert_candidates(
    news_items: list[dict],
    symbols: list[str] | tuple[str, ...],
    *,
    max_per_symbol: int = NEWS_DRIVEN_ALERT_MAX_PER_SYMBOL,
) -> dict[str, list[dict]]:
    selected_by_symbol: dict[str, list[dict]] = {}
    normalized_symbols = [symbol for symbol in symbols if symbol in SUPPORTED_SYMBOLS]
    for symbol in normalized_symbols:
        eligible = [
            item
            for item in news_items
            if _news_item_can_trigger_standalone_alert(symbol, item)
        ]
        best_by_identity: dict[str, dict] = {}
        for item in eligible:
            identity = _news_driven_identity(item)
            existing = best_by_identity.get(identity)
            if existing is None or _news_driven_candidate_rank(
                symbol, item
            ) > _news_driven_candidate_rank(symbol, existing):
                best_by_identity[identity] = item
        ranked = sorted(
            best_by_identity.values(),
            key=lambda item: _news_driven_candidate_rank(symbol, item),
            reverse=True,
        )
        selected_by_symbol[symbol] = ranked[:max_per_symbol]
    return selected_by_symbol

def _format_news_driven_summary(news_item: dict) -> str:
    summary = str(news_item.get("summary") or "").strip()
    title = str(news_item.get("title") or "").strip()
    return _truncate_text(summary or title, 220)

def _build_news_driven_event_decision(
    *,
    symbol: str,
    news_item: dict,
    event_key: str,
) -> EventAnalysisDecision:
    user_symbol = display_symbol(symbol)
    backend_symbol = normalize_symbol(symbol).upper()
    title = f"High-impact news detected for {user_symbol}"
    context = _format_news_driven_summary(news_item)
    message_body = (
        f"Possible market context: {context} "
        "This could be related to market sentiment, but price impact is uncertain."
    )
    possible_action = (
        f"Review the news calmly and watch how {user_symbol} trades over the next alert window."
    )
    return EventAnalysisDecision(
        symbol=backend_symbol,
        should_alert=True,
        event_key=event_key,
        title=title,
        message_body=message_body,
        related_news_ids=["n1"],
        possible_action=possible_action,
        urgency="high",
        confidence="medium",
        reason_for_no_alert=None,
    )

def _build_news_driven_event_input(
    *,
    analysis_id: str,
    symbol: str,
    news_item: dict,
    current_price: float,
    change_24h: float,
    now: datetime,
    market_context: dict | None = None,
) -> dict:
    published_at = _parse_news_datetime(news_item) or now
    source_market = dict(market_context or {})
    market_payload = {
        "price": source_market.get("price", _stable_float(float(current_price), 2)),
        "snapshots": source_market.get("snapshots", []),
        "chg24h": source_market.get("chg24h", _stable_float(float(change_24h), 4)),
        "chg_since_msg": source_market.get("chg_since_msg"),
    }
    for key in ("payload_points", "analysed_window_minutes", "chg_window"):
        if key in source_market:
            market_payload[key] = source_market[key]
    return {
        "analysis_id": analysis_id,
        "symbol": normalize_symbol(symbol).upper(),
        "display_symbol": display_symbol(symbol),
        "coin_name": _coin_name(symbol),
        "timestamp_utc": published_at.astimezone(timezone.utc).isoformat(),
        "market": market_payload,
        "last_msg": {
            "time": None,
            "type": None,
            "price": None,
        },
        "news": _format_candidate_news([news_item], preserve_order=True, symbol=symbol),
        "policy": {
            "language": "English",
            "audience": "General retail crypto holder.",
            "source": NEWS_DRIVEN_ALERT_SOURCE,
            "causality": "Do not claim news caused a price move.",
        },
    }

def _news_driven_numeric_context(input_payload: dict, news_item: dict) -> str:
    market_data = input_payload.get("market", {})
    return _json_dumps(
        {
            "notification_type": EVENT_ALERT_TYPE,
            "trigger_source": NEWS_DRIVEN_ALERT_SOURCE,
            "semantic_family": "news_catalyst",
            "current_price": market_data.get("price"),
            "change_since_last_market_update_percent": market_data.get("chg_since_msg"),
            "analysed_window_minutes": market_data.get("analysed_window_minutes"),
            "analysed_window_change_percent": market_data.get("chg_window"),
            "twenty_four_hour_change_percent": market_data.get("chg24h"),
            "stable_related_news_ids": [_news_driven_identity(news_item)],
            "news_key": str(news_item.get("news_key") or "").strip() or None,
            "dedup_group_id": str(news_item.get("dedup_group_id") or "").strip() or None,
            "published_at": str(input_payload.get("timestamp_utc") or ""),
            "impact_level": str(news_item.get("impact_level") or "").strip().lower() or None,
            "category": str(news_item.get("category") or "").strip().lower() or None,
        }
    )

async def _get_or_create_news_driven_market_event(
    *,
    symbol: str,
    news_item: dict,
    input_payload: dict,
    event_key: str,
) -> tuple[int | None, str | None]:
    if not DB_ENABLED or not DB_SESSION_LOCAL:
        return None, None
    market_data = input_payload.get("market", {})
    current_price = float(market_data.get("price") or 0.0)
    event_instance_key = _build_news_driven_event_instance_key(
        symbol=symbol,
        event_key=event_key,
        news_item=news_item,
    )
    async with DB_SESSION_LOCAL() as session:
        event = await get_or_create_market_event(
            session,
            symbol=normalize_symbol(symbol),
            event_type=EVENT_ALERT_TYPE,
            event_key=event_key,
            event_instance_key=event_instance_key,
            price=current_price,
            previous_price=None,
            price_change_percent=0.0,
            last_24h_change=market_data.get("chg24h"),
            detected_at=datetime.now(timezone.utc),
        )
        return event.id, event.event_instance_key

async def _save_news_driven_event_analysis(
    *,
    market_event_id: int,
    input_payload: dict,
    decision: EventAnalysisDecision,
    plain_text: str,
) -> int | None:
    if not DB_ENABLED or not DB_SESSION_LOCAL:
        return None
    parsed_result = {
        "symbol": decision.symbol,
        "should_alert": decision.should_alert,
        "event_key": decision.event_key,
        "title": decision.title,
        "message_body": decision.message_body,
        "related_news_ids": decision.related_news_ids,
        "possible_action": decision.possible_action,
        "urgency": decision.urgency,
        "confidence": decision.confidence,
        "reason_for_no_alert": decision.reason_for_no_alert,
    }
    async with DB_SESSION_LOCAL() as session:
        analysis = await save_event_llm_analysis(
            session,
            analysis_id=str(input_payload["analysis_id"]),
            symbol=str(input_payload["symbol"]),
            input_hash=_event_input_hash(input_payload),
            raw_input_json=_json_dumps(input_payload),
            raw_output_json=_json_dumps(parsed_result),
            status="success",
            provider="backend",
            model=NEWS_DRIVEN_ALERT_MODEL,
            analysis_type=EVENT_ANALYSIS_TYPE,
            market_event_id=market_event_id,
            parsed_result_json=_json_dumps(parsed_result),
            should_alert=True,
            event_key=decision.event_key,
            title=decision.title,
            message_body=decision.message_body,
            related_news_ids=_json_dumps(decision.related_news_ids),
            possible_action=decision.possible_action,
            urgency=decision.urgency,
            confidence=decision.confidence,
            plain_text=plain_text,
        )
        return analysis.id if analysis else None

async def _deliver_news_driven_alert_for_symbol(
    app: Application,
    *,
    symbol: str,
    news_item: dict,
    current_price: float,
    change_24h: float,
    event_analysis_input_payload: dict | None = None,
    candidate_recipients: list[AlertRecipient],
    cooldown_seconds: int,
    now: datetime,
) -> bool:
    event_key = _build_news_driven_event_key(symbol=symbol, news_item=news_item)
    event_hash = event_key.rsplit(":", 1)[-1]
    analysis_id = f"{NEWS_DRIVEN_ALERT_SOURCE}_{normalize_symbol(symbol)}_{event_hash}"
    input_payload = _build_news_driven_event_input(
        analysis_id=analysis_id,
        symbol=symbol,
        news_item=news_item,
        current_price=current_price,
        change_24h=change_24h,
        now=now,
        market_context=(event_analysis_input_payload or {}).get("market"),
    )
    decision = _build_news_driven_event_decision(
        symbol=symbol,
        news_item=news_item,
        event_key=event_key,
    )
    related_news = _related_news_by_id(
        input_payload["news"],
        decision.related_news_ids,
        symbol=symbol,
        context="news-driven event",
    )
    alert_payload = _build_event_alert_payload(
        decision=decision,
        input_payload=input_payload,
        related_news=related_news,
    )
    market_event_id, event_instance_key = await _get_or_create_news_driven_market_event(
        symbol=symbol,
        news_item=news_item,
        input_payload=input_payload,
        event_key=event_key,
    )
    event_ai_analysis_id = None
    if market_event_id is not None:
        event_ai_analysis_id = await _save_news_driven_event_analysis(
            market_event_id=market_event_id,
            input_payload=input_payload,
            decision=decision,
            plain_text=alert_payload["plain_text"],
        )

    recipients = await _filter_event_recipients_for_cooldown(
        candidate_recipients,
        symbol=symbol,
        urgency=decision.urgency,
        cooldown_seconds=cooldown_seconds,
        canonical_event_key=event_key,
        semantic_family="news_catalyst",
        current_stable_news_ids=[_news_driven_identity(news_item)],
        now=now,
        return_summary=True,
    )
    await _record_recipient_outcomes(
        recipients.suppressed,
        symbol=symbol,
        alert_type=EVENT_ALERT_TYPE,
        market_event_id=market_event_id,
        event_ai_analysis_id=event_ai_analysis_id,
        trigger_source=NEWS_DRIVEN_ALERT_SOURCE,
        event_instance_key=event_instance_key,
        semantic_family="news_catalyst",
    )
    recipients_to_deliver = recipients.recipients
    if not recipients_to_deliver:
        logger.info("%s news-driven event alert suppressed by backend cooldown.", symbol.upper())
        suppression_reason = (
            _primary_suppression_reason(recipients.suppression_reason_counts)
            or SUPPRESSION_UNKNOWN
        )
        await _record_alert_delivery_outcome(
            symbol=symbol,
            alert_type=EVENT_ALERT_TYPE,
            status=(
                OUTCOME_SUPPRESSED
                if suppression_reason == SUPPRESSION_SEMANTIC_COOLDOWN
                else OUTCOME_COOLDOWN
            ),
            reason_code=(
                REASON_SIMILAR_EVENT_SUPPRESSED
                if suppression_reason == SUPPRESSION_SEMANTIC_COOLDOWN
                else REASON_COOLDOWN_ACTIVE
            ),
            market_event_id=market_event_id,
            event_ai_analysis_id=event_ai_analysis_id,
            trigger_source=NEWS_DRIVEN_ALERT_SOURCE,
            event_instance_key=event_instance_key,
            semantic_family="news_catalyst",
            detail=suppression_reason,
        )
        return False
    return await _deliver_market_event_alert(
        app,
        symbol=symbol,
        alert_payload=alert_payload,
        market_event_id=market_event_id,
        event_ai_analysis_id=event_ai_analysis_id,
        recipients=recipients_to_deliver,
        event_type=EVENT_ALERT_TYPE,
        trigger_reason=decision.title,
        trigger_source=NEWS_DRIVEN_ALERT_SOURCE,
        canonical_event_key=event_key,
        semantic_family="news_catalyst",
        event_instance_key=event_instance_key,
        numeric_context=_news_driven_numeric_context(input_payload, news_item),
        thresholds_used=None,
    )

async def _load_news_driven_alert_candidates(
    symbols: list[str],
    *,
    now: datetime,
) -> dict[str, list[dict]]:
    if not ENABLE_NEWS_DRIVEN_ALERTS:
        return {}
    if not DB_ENABLED or not DB_SESSION_LOCAL:
        logger.info("News-driven alerts skipped because database storage is off.")
        return {}
    active_symbols = [symbol for symbol in symbols if symbol in SUPPORTED_SYMBOLS]
    if not active_symbols:
        return {}
    async with DB_SESSION_LOCAL() as session:
        news_items = await select_recent_news_items_for_alerts(
            session,
            active_symbols,
            max_age_hours=NEWS_DRIVEN_ALERT_MAX_AGE_HOURS,
            now=now,
        )
    candidates = _select_news_driven_alert_candidates(news_items, active_symbols)
    total_selected = sum(len(items) for items in candidates.values())
    if total_selected:
        logger.info(
            "News-driven alert candidates selected: symbols=%s selected_count=%s",
            ",".join(symbol.upper() for symbol in active_symbols),
            total_selected,
        )
    return candidates

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
    selection = _select_analysed_window_reference(
        reference=reference,
        snapshots=snapshots,
        since=since,
        now=now,
        max_reference_age=timedelta(seconds=max(1, int(window_seconds))),
    )
    previous_price = selection.reference_price or fallback_previous_price
    peak = None
    if selection.window_snapshots:
        moves = [
            abs(calculate_price_change_percent(previous_price, float(snapshot.price)))
            for snapshot in selection.window_snapshots
            if previous_price
        ]
        if moves:
            peak = max(moves)
    if peak is None and previous_price:
        peak = abs(calculate_price_change_percent(previous_price, current_price))
    return previous_price, peak

async def _build_event_analysis_input(
    *,
    analysis_id: str,
    symbol: str,
    current_price: float,
    change_24h: float,
    now: datetime,
    state: dict,
    candidate_news: list[dict],
    event_analysis_interval_seconds: int,
) -> dict:
    normalized_symbol = normalize_symbol(symbol)
    fallback_previous_price = float(state.get("last_price") or current_price)
    snapshots_payload: list[dict] = []
    last_message_at = None
    last_message_type = None
    last_message_price = None
    analysed_window_minutes = get_analysed_window_minutes(
        event_analysis_interval_seconds,
        EVENT_ANALYSIS_PAYLOAD_POINTS,
    )
    window_reference_price: float | None = None
    db_snapshots_available = bool(DB_ENABLED and DB_SESSION_LOCAL)

    if db_snapshots_available:
        since = now - timedelta(minutes=analysed_window_minutes)
        async with DB_SESSION_LOCAL() as session:
            reference = await get_reference_price_snapshot(
                session,
                symbol=normalized_symbol,
                at_or_before=since,
            )
            snapshots = await get_price_snapshots_since(
                session,
                symbol=normalized_symbol,
                since=since,
            )
            latest_alert = await get_latest_sent_alert_for_symbol(
                session,
                symbol=normalized_symbol,
                alert_type=EVENT_ALERT_TYPE,
            )
        if latest_alert:
            last_message_at = latest_alert.created_at.astimezone(timezone.utc).isoformat()
            last_message_type = latest_alert.alert_type
            last_message_price = _numeric_context_value(
                latest_alert.numeric_context,
                "current_price",
            )
        selection = _select_analysed_window_reference(
            reference=reference,
            snapshots=snapshots,
            since=since,
            now=now,
            max_reference_age=timedelta(
                seconds=max(1, int(event_analysis_interval_seconds))
            ),
        )
        window_reference_price = selection.reference_price
        if selection.reference_snapshot:
            snapshots_payload.append(
                {
                    "timestamp_utc": _utc_checked_at(
                        selection.reference_snapshot
                    ).isoformat(),
                    "price_usd": float(selection.reference_snapshot.price),
                }
            )
        snapshots_payload.extend(
            {
                "timestamp_utc": _utc_checked_at(snapshot).isoformat(),
                "price_usd": float(snapshot.price),
            }
            for snapshot in selection.window_snapshots
        )
        snapshots_payload = _select_representative_snapshots(
            snapshots_payload,
            limit=EVENT_ANALYSIS_PAYLOAD_POINTS,
        )
    else:
        last_message_at = state.get("last_alert_at")
        last_message_type = EVENT_ALERT_TYPE if last_message_at else None
        last_message_price = (
            float(state.get("last_price") or current_price) if last_message_at else None
        )
        window_reference_price = fallback_previous_price

    change_since_last_message = (
        calculate_price_change_percent(float(last_message_price), current_price)
        if last_message_price
        else None
    )
    if not snapshots_payload:
        if db_snapshots_available:
            snapshots_payload = [
                {
                    "timestamp_utc": now.astimezone(timezone.utc).isoformat(),
                    "price_usd": float(current_price),
                }
            ]
        else:
            window_reference_price = fallback_previous_price
            snapshots_payload = [
                {
                    "timestamp_utc": now.astimezone(timezone.utc).isoformat(),
                    "price_usd": fallback_previous_price,
                }
            ]
    if window_reference_price is None and snapshots_payload and not db_snapshots_available:
        window_reference_price = float(snapshots_payload[0]["price_usd"])
    analysed_window_change = _calculate_price_change(current_price, window_reference_price)
    snapshots_payload = _compact_event_snapshots(snapshots_payload, now=now)
    candidate_news = _compact_event_analysis_news(candidate_news, limit=3)

    return {
        "analysis_id": analysis_id,
        "symbol": normalized_symbol.upper(),
        "display_symbol": display_symbol(normalized_symbol),
        "coin_name": _coin_name(normalized_symbol),
        "timestamp_utc": now.astimezone(timezone.utc).isoformat(),
        "market": {
            "price": _stable_float(float(current_price), 2),
            "snapshots": snapshots_payload,
            "payload_points": EVENT_ANALYSIS_PAYLOAD_POINTS,
            "analysed_window_minutes": analysed_window_minutes,
            "chg_window": _stable_float(analysed_window_change, 4),
            "chg24h": _stable_float(float(change_24h), 4),
            "chg_since_msg": _stable_float(change_since_last_message, 4),
        },
        "last_msg": {
            "time": last_message_at,
            "type": last_message_type,
            "price": _stable_float(last_message_price, 2),
        },
        "news": candidate_news,
        "policy": {
            "language": "English",
            "audience": "General retail crypto holder.",
            "noise": "Prefer fewer useful alerts; avoid repetitive low-value alerts.",
        },
    }

async def _build_market_heartbeat_input(
    *,
    heartbeat_id: str,
    symbol: str,
    current_price: float,
    change_24h: float,
    now: datetime,
    candidate_news: list[dict],
) -> dict:
    normalized_symbol = normalize_symbol(symbol)
    snapshots = []
    reference_6h = None
    if DB_ENABLED and DB_SESSION_LOCAL:
        since = now - timedelta(hours=6)
        async with DB_SESSION_LOCAL() as session:
            snapshots = await get_price_snapshots_since(
                session,
                symbol=normalized_symbol,
                since=since,
            )
            reference_6h = await get_reference_price_snapshot(
                session,
                symbol=normalized_symbol,
                at_or_before=since,
            )
    selection = _select_analysed_window_reference(
        reference=reference_6h,
        snapshots=snapshots,
        since=now - timedelta(hours=6),
        now=now,
        max_reference_age=timedelta(hours=1),
    )
    reference_1h = _snapshot_at_or_before(
        selection.window_snapshots,
        now - timedelta(hours=1),
    )
    observed_prices = [_snapshot_price(snapshot) for snapshot in selection.window_snapshots]
    observed_prices.append(float(current_price))
    candidate_news = _compact_candidate_news(candidate_news, limit=3)
    return {
        "heartbeat_id": heartbeat_id,
        "symbol": normalized_symbol.upper(),
        "display_symbol": display_symbol(normalized_symbol),
        "coin_name": _coin_name(normalized_symbol),
        "timestamp_utc": now.astimezone(timezone.utc).isoformat(),
        "market_data": {
            "price_now_usd": float(current_price),
            "change_1h_percent": _snapshot_change_percent(current_price, reference_1h),
            "change_6h_percent": _calculate_price_change(
                current_price,
                selection.reference_price,
            ),
            "change_24h_percent": float(change_24h),
            "high_6h_usd": max(observed_prices) if observed_prices else None,
            "low_6h_usd": min(observed_prices) if observed_prices else None,
        },
        "candidate_news": candidate_news,
        "policy": {
            "language": "English",
            "purpose": "Calm Market Heartbeat, not an Event Alert.",
        },
    }

async def _save_market_heartbeat_attempt(
    *,
    input_payload: dict,
    raw_output_json: str | None,
    status: str,
    decision: MarketHeartbeatDecision | None = None,
    error_message: str | None = None,
) -> int | None:
    if not DB_ENABLED or not DB_SESSION_LOCAL:
        return None
    async with DB_SESSION_LOCAL() as session:
        heartbeat = await save_market_heartbeat(
            session,
            symbol=str(input_payload["symbol"]),
            generated_at=datetime.now(timezone.utc),
            raw_input_json=_json_dumps(input_payload),
            raw_output_json=raw_output_json,
            title=decision.title if decision else None,
            message_body=decision.message_body if decision else None,
            related_news_ids=_json_dumps(decision.related_news_ids if decision else []),
            possible_action=decision.possible_action if decision else None,
            confidence=decision.confidence if decision else None,
            status=status,
            error_message=error_message,
        )
        return heartbeat.id if heartbeat else None

async def _create_market_heartbeat(input_payload: dict) -> int | None:
    raw_output = None
    parsed = None
    usage_log_id = None
    try:
        result = await ask_market_heartbeat_raw(input_payload)
        raw_output, parsed = result
        usage_log_id = getattr(result, "usage_log_id", None)
    except LLMRateLimitBackoffActive as error:
        await _save_market_heartbeat_attempt(
            input_payload=input_payload,
            raw_output_json=None,
            status="skipped_due_to_rate_limit",
            error_message=str(error),
        )
        return None
    except Exception as error:
        raw_output = getattr(error, "raw_content", raw_output)
        heartbeat_id = await _save_market_heartbeat_attempt(
            input_payload=input_payload,
            raw_output_json=raw_output,
            status="failed",
            error_message=str(error),
        )
        logger.warning(
            "%s market heartbeat generation failed: %s",
            str(input_payload["symbol"]).upper(),
            classify_ai_error_reason(error),
        )
        return heartbeat_id

    try:
        decision = validate_market_heartbeat_output(
            parsed,
            expected_symbol=str(input_payload["symbol"]),
            candidate_news_ids={
                str(item["news_id"])
                for item in input_payload.get("news", input_payload.get("candidate_news", []))
            },
        )
    except MarketHeartbeatValidationError as error:
        await mark_llm_usage_log_status(
            usage_log_id,
            status="schema_error",
            error_reason="schema validation failed",
            error_message=str(error),
        )
        heartbeat_id = await _save_market_heartbeat_attempt(
            input_payload=input_payload,
            raw_output_json=raw_output,
            status="failed",
            error_message=str(error),
        )
        logger.warning(
            "%s market heartbeat schema validation failed: %s",
            str(input_payload["symbol"]).upper(),
            error,
        )
        return heartbeat_id

    return await _save_market_heartbeat_attempt(
        input_payload=input_payload,
        raw_output_json=raw_output,
        status="completed",
        decision=decision,
    )

async def _save_event_analysis_attempt(
    *,
    input_payload: dict,
    raw_output_json: str | None,
    status: str,
    parsed_result: dict | None = None,
    decision: EventAnalysisDecision | None = None,
    error_message: str | None = None,
    error_reason: str | None = None,
    market_event_id: int | None = None,
    plain_text: str | None = None,
) -> int | None:
    if not DB_ENABLED or not DB_SESSION_LOCAL:
        return None
    related_news_ids = decision.related_news_ids if decision else []
    async with DB_SESSION_LOCAL() as session:
        analysis = await save_event_llm_analysis(
            session,
            analysis_id=str(input_payload["analysis_id"]),
            symbol=str(input_payload["symbol"]),
            input_hash=_event_input_hash(input_payload),
            raw_input_json=_json_dumps(input_payload),
            raw_output_json=raw_output_json,
            status=status,
            model=GROQ_EVENT_ANALYSIS_MODEL,
            market_event_id=market_event_id,
            parsed_result_json=_json_dumps(parsed_result) if parsed_result is not None else None,
            should_alert=decision.should_alert if decision else None,
            event_key=decision.event_key if decision else None,
            title=decision.title if decision else None,
            message_body=decision.message_body if decision else None,
            related_news_ids=_json_dumps(related_news_ids),
            possible_action=decision.possible_action if decision else None,
            urgency=decision.urgency if decision else None,
            confidence=decision.confidence if decision else None,
            reason_for_no_alert=decision.reason_for_no_alert if decision else None,
            error_message=error_message,
            error_reason=error_reason,
            plain_text=plain_text,
        )
        return analysis.id if analysis else None

async def _create_event_analysis_decision(
    input_payload: dict,
) -> tuple[EventAnalysisDecision | None, int | None]:
    raw_output = None
    parsed = None
    usage_log_id = None
    try:
        result = await ask_event_analysis_raw(input_payload)
        raw_output, parsed = result
        usage_log_id = getattr(result, "usage_log_id", None)
    except LLMRateLimitBackoffActive as error:
        analysis_id = await _save_event_analysis_attempt(
            input_payload=input_payload,
            raw_output_json=None,
            status="skipped_due_to_rate_limit",
            error_message=str(error),
            error_reason=classify_ai_error_reason(error),
        )
        await _record_alert_delivery_outcome(
            symbol=str(input_payload["symbol"]),
            alert_type=EVENT_ALERT_TYPE,
            status=OUTCOME_RATE_LIMITED,
            reason_code=REASON_LLM_RATE_LIMITED,
            event_ai_analysis_id=analysis_id,
            trigger_source=EVENT_ANALYSIS_TYPE,
            detail="event_analysis_backoff_active",
        )
        _log_event_alert_suppression(
            symbol=str(input_payload["symbol"]),
            suppression_reason=SUPPRESSION_LLM_RATE_LIMITED,
            suppression_count=1,
            analysed_window_minutes=_analysed_window_minutes_from_payload(input_payload),
        )
        return None, None
    except Exception as error:
        raw_output = getattr(error, "raw_content", raw_output)
        reason = classify_ai_error_reason(error)
        status = "invalid_json" if reason == "invalid JSON" else "llm_error"
        analysis_id = await _save_event_analysis_attempt(
            input_payload=input_payload,
            raw_output_json=raw_output,
            status=status,
            error_message=str(error),
            error_reason=reason,
        )
        await _record_alert_delivery_outcome(
            symbol=str(input_payload["symbol"]),
            alert_type=EVENT_ALERT_TYPE,
            status=OUTCOME_FAILED,
            reason_code=REASON_LLM_INVALID_RESPONSE,
            event_ai_analysis_id=analysis_id,
            trigger_source=EVENT_ANALYSIS_TYPE,
            detail=reason,
        )
        logger.warning(
            "%s event analysis failed: %s",
            str(input_payload["symbol"]).upper(),
            reason,
        )
        return None, None

    normalized_parsed = _normalize_event_analysis_result_for_validation(parsed)
    try:
        decision = validate_event_analysis_output(
            normalized_parsed,
            expected_symbol=str(input_payload["symbol"]),
            candidate_news_ids={
                str(item["news_id"])
                for item in input_payload.get("news", input_payload.get("candidate_news", []))
            },
        )
    except EventAnalysisValidationError as error:
        schema_error = AISchemaValidationError(str(error))
        await mark_llm_usage_log_status(
            usage_log_id,
            status="schema_error",
            error_reason=classify_ai_error_reason(schema_error),
            error_message=str(error),
        )
        analysis_id = await _save_event_analysis_attempt(
            input_payload=input_payload,
            raw_output_json=raw_output,
            status="schema_error",
            parsed_result=normalized_parsed,
            error_message=str(error),
            error_reason=classify_ai_error_reason(schema_error),
        )
        await _record_alert_delivery_outcome(
            symbol=str(input_payload["symbol"]),
            alert_type=EVENT_ALERT_TYPE,
            status=OUTCOME_FAILED,
            reason_code=REASON_LLM_INVALID_RESPONSE,
            event_ai_analysis_id=analysis_id,
            trigger_source=EVENT_ANALYSIS_TYPE,
            detail=classify_ai_error_reason(schema_error),
        )
        logger.warning(
            "%s event analysis schema validation failed: %s",
            str(input_payload["symbol"]).upper(),
            error,
        )
        return None, None

    if decision.should_alert:
        decision, canonical = with_canonical_event_key(
            decision,
            related_news=_selected_event_analysis_news(input_payload, decision.related_news_ids),
        )
        input_payload["raw_event_key"] = canonical.raw_event_key
        input_payload["canonical_event_key"] = canonical.canonical_event_key
        input_payload["semantic_family"] = canonical.semantic_family
        logger.info(
            "event_key_canonicalized symbol=%s raw_event_key=%s canonical_event_key=%s "
            "semantic_family=%s reason=%s",
            decision.symbol,
            canonical.raw_event_key,
            canonical.canonical_event_key,
            canonical.semantic_family,
            canonical.reason,
        )

    status = "success" if decision.should_alert else "no_alert"
    analysis_id = await _save_event_analysis_attempt(
        input_payload=input_payload,
        raw_output_json=raw_output,
        status=status,
        parsed_result=normalized_parsed,
        decision=decision,
    )
    return decision, analysis_id

def _selected_event_analysis_news(input_payload: dict, related_news_ids: list[str]) -> list[dict]:
    if not related_news_ids:
        return []
    news_items = input_payload.get("news", input_payload.get("candidate_news", []))
    if not isinstance(news_items, list):
        return []
    by_id = {
        str(item.get("news_id") or ""): item
        for item in news_items
        if isinstance(item, dict)
    }
    return [
        by_id[str(news_id)]
        for news_id in related_news_ids
        if str(news_id) in by_id
    ]

def _normalize_event_analysis_result_for_validation(result: object) -> object:
    if not isinstance(result, dict) or result.get("should_alert") is not False:
        return result

    normalized = dict(result)
    normalized["urgency"] = None
    for field_name in ("event_key", "title", "message_body", "possible_action"):
        value = normalized.get(field_name)
        if isinstance(value, str) and not value.strip():
            normalized[field_name] = None
    return normalized

async def _get_or_create_event_alert_market_event(
    *,
    decision: EventAnalysisDecision,
    input_payload: dict,
) -> tuple[int | None, str | None, str | None, bool]:
    if not decision.event_key:
        return None, None, None, False
    market_data = input_payload.get("market", input_payload.get("market_data", {}))
    current_price = float(market_data.get("price", market_data.get("price_now_usd")))
    change_since_last = market_data.get(
        "chg_since_msg",
        market_data.get("change_since_last_user_visible_message_percent"),
    )
    if change_since_last is None:
        previous_price = None
        price_change_percent = 0.0
    else:
        price_change_percent = float(change_since_last)
        previous_price = current_price / (1 + (price_change_percent / 100.0))
    event_instance_key = _event_instance_key_for_decision(
        decision=decision,
        input_payload=input_payload,
    )
    if not DB_ENABLED or not DB_SESSION_LOCAL:
        return None, decision.event_key, event_instance_key, False
    async with DB_SESSION_LOCAL() as session:
        existing = await get_market_event_by_instance_key(
            session,
            event_instance_key=event_instance_key,
        )
        if existing:
            return existing.id, existing.event_key, existing.event_instance_key, True
        event = await get_or_create_market_event(
            session,
            symbol=decision.symbol,
            event_type=EVENT_ALERT_TYPE,
            event_key=decision.event_key,
            event_instance_key=event_instance_key,
            price=current_price,
            previous_price=previous_price,
            price_change_percent=price_change_percent,
            last_24h_change=market_data.get("chg24h", market_data.get("change_24h_percent")),
            detected_at=datetime.now(timezone.utc),
        )
        return (
            event.id,
            event.event_key,
            event.event_instance_key,
            bool(getattr(event, "_ccwbot_reused", False)),
        )

async def _filter_event_recipients_for_cooldown(
    recipients: list[AlertRecipient],
    *,
    symbol: str,
    urgency: str,
    cooldown_seconds: int,
    canonical_event_key: str | None = None,
    semantic_family: str | None = None,
    current_movement_percent: float | None = None,
    current_stable_news_ids: list[str] | None = None,
    semantic_cooldown_seconds: int = EVENT_ALERT_SEMANTIC_COOLDOWN_SECONDS,
    now: datetime,
    return_summary: bool = False,
) -> list[AlertRecipient] | EventRecipientFilterResult:
    if not DB_ENABLED or not DB_SESSION_LOCAL:
        if return_summary:
            return EventRecipientFilterResult(
                recipients=recipients,
                suppression_reason_counts={},
                suppressed=[],
            )
        return recipients
    effective_cooldown = int(cooldown_seconds)
    if urgency == "high":
        effective_cooldown = min(effective_cooldown, 30 * 60)
    if effective_cooldown <= 0 and (not canonical_event_key or semantic_cooldown_seconds <= 0):
        if return_summary:
            return EventRecipientFilterResult(
                recipients=recipients,
                suppression_reason_counts={},
                suppressed=[],
            )
        return recipients

    filtered: list[AlertRecipient] = []
    suppressed: list[RecipientOutcome] = []
    suppression_reason_counts: dict[str, int] = {}
    async with DB_SESSION_LOCAL() as session:
        for recipient in recipients:
            if recipient.user_id is None:
                filtered.append(recipient)
                continue
            if canonical_event_key and semantic_cooldown_seconds > 0:
                previous_semantic_alert = await get_latest_sent_event_alert_for_event_key(
                    session,
                    user_id=recipient.user_id,
                    symbol=symbol,
                    canonical_event_key=canonical_event_key,
                    alert_type=EVENT_ALERT_TYPE,
                    semantic_family=semantic_family,
                )
                last_semantic_sent_at = (
                    previous_semantic_alert.created_at if previous_semantic_alert else None
                )
                semantic_allowed = True
                semantic_remaining = 0
                semantic_allow_reason = None
                semantic_escalation_details = {}
                if last_semantic_sent_at is not None:
                    semantic_escalation_details = (
                        _event_semantic_cooldown_escalation_details(
                            previous_semantic_alert,
                            current_urgency=urgency,
                            current_movement_percent=current_movement_percent,
                            current_stable_news_ids=current_stable_news_ids or [],
                        )
                    )
                    if last_semantic_sent_at.tzinfo is None:
                        last_semantic_sent_at = last_semantic_sent_at.replace(
                            tzinfo=timezone.utc
                        )
                    elapsed = (
                        now - last_semantic_sent_at.astimezone(timezone.utc)
                    ).total_seconds()
                    semantic_remaining = max(0, int(semantic_cooldown_seconds - elapsed))
                    semantic_allowed = elapsed >= semantic_cooldown_seconds
                    if not semantic_allowed:
                        (
                            semantic_allowed,
                            semantic_allow_reason,
                        ) = _event_semantic_cooldown_allows_escalation(
                            previous_semantic_alert,
                            current_urgency=urgency,
                            current_movement_percent=current_movement_percent,
                            current_stable_news_ids=current_stable_news_ids or [],
                        )
                logger.debug(
                    "event_alert_semantic_cooldown_check symbol=%s canonical_event_key=%s "
                    "semantic_family=%s last_sent_at=%s cooldown_seconds=%s allowed=%s "
                    "allow_reason=%s urgency_increased=%s material_movement_increased=%s "
                    "new_news_driver=%s previous_movement_percent=%s "
                    "current_movement_percent=%s previous_news_count=%s current_news_count=%s",
                    normalize_symbol(symbol),
                    canonical_event_key,
                    semantic_family,
                    (
                        last_semantic_sent_at.isoformat()
                        if last_semantic_sent_at is not None
                        else None
                    ),
                    semantic_cooldown_seconds,
                    semantic_allowed,
                    semantic_allow_reason,
                    semantic_escalation_details.get("urgency_increased"),
                    semantic_escalation_details.get("material_movement_increased"),
                    semantic_escalation_details.get("new_news_driver"),
                    semantic_escalation_details.get("previous_movement_percent"),
                    semantic_escalation_details.get("current_movement_percent"),
                    semantic_escalation_details.get("previous_news_count"),
                    semantic_escalation_details.get("current_news_count"),
                )
                if not semantic_allowed:
                    _count_suppression(
                        suppression_reason_counts,
                        SUPPRESSION_SEMANTIC_COOLDOWN,
                    )
                    suppressed.append(
                        RecipientOutcome(
                            recipient=recipient,
                            status=OUTCOME_SUPPRESSED,
                            reason_code=REASON_SIMILAR_EVENT_SUPPRESSED,
                            eligible=False,
                            detail=SUPPRESSION_SEMANTIC_COOLDOWN,
                        )
                    )
                    logger.debug(
                        "event_alert_suppressed symbol=%s canonical_event_key=%s "
                        "semantic_family=%s suppression_reason=%s "
                        "cooldown_remaining_seconds=%s urgency_increased=%s "
                        "material_movement_increased=%s new_news_driver=%s",
                        normalize_symbol(symbol),
                        canonical_event_key,
                        semantic_family,
                        SUPPRESSION_SEMANTIC_COOLDOWN,
                        semantic_remaining,
                        semantic_escalation_details.get("urgency_increased"),
                        semantic_escalation_details.get("material_movement_increased"),
                        semantic_escalation_details.get("new_news_driver"),
                    )
                    continue
                if semantic_allow_reason:
                    filtered.append(recipient)
                    continue
            if effective_cooldown <= 0:
                filtered.append(recipient)
                continue
            last_sent_at = await get_last_sent_alert_at(
                session,
                user_id=recipient.user_id,
                symbol=symbol,
                alert_type=EVENT_ALERT_TYPE,
            )
            if last_sent_at is None:
                filtered.append(recipient)
                continue
            if last_sent_at.tzinfo is None:
                last_sent_at = last_sent_at.replace(tzinfo=timezone.utc)
            elapsed = (now - last_sent_at.astimezone(timezone.utc)).total_seconds()
            if elapsed >= effective_cooldown:
                filtered.append(recipient)
                continue
            _count_suppression(suppression_reason_counts, SUPPRESSION_EXACT_COOLDOWN)
            suppressed.append(
                RecipientOutcome(
                    recipient=recipient,
                    status=OUTCOME_COOLDOWN,
                    reason_code=REASON_COOLDOWN_ACTIVE,
                    eligible=False,
                    detail=SUPPRESSION_EXACT_COOLDOWN,
                )
            )
            logger.debug(
                "event_alert_suppressed symbol=%s canonical_event_key=%s "
                "semantic_family=%s suppression_reason=%s cooldown_remaining_seconds=%s",
                normalize_symbol(symbol),
                canonical_event_key,
                semantic_family,
                SUPPRESSION_EXACT_COOLDOWN,
                max(0, int(effective_cooldown - elapsed)),
            )
    if return_summary:
        return EventRecipientFilterResult(
            recipients=filtered,
            suppression_reason_counts=suppression_reason_counts,
            suppressed=suppressed,
        )
    return filtered

def _strip_existing_alert_title(plain_text: str) -> str:
    lines = plain_text.strip().splitlines()
    if lines and any(term in lines[0].lower() for term in ("alert", "signal")):
        return "\n".join(lines[1:]).strip()
    return plain_text.strip()

def _coin_display_line(symbol: str) -> str:
    user_symbol = display_symbol(symbol)
    try:
        coin_name = _coin_name(symbol)
    except KeyError:
        return f"Coin: {user_symbol}"
    if coin_name.lower() == user_symbol.lower():
        return f"Coin: {user_symbol}"
    return f"Coin: {user_symbol} / {coin_name}"

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
    user_symbol = display_symbol(symbol)
    header = (
        f"{severity_icon_text(severity.severity)} {severity_label_text(severity.severity)} - "
        f"{user_symbol} {alert_title_action(severity.primary_alert_type)}\n\n"
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
    backend_symbol = normalize_symbol(context.symbol)
    symbol = display_symbol(backend_symbol)
    coin_icon, entities = build_coin_icon_prefix(backend_symbol)
    coin_icon_html = build_coin_icon_html(backend_symbol)
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
            title = clean_news_title(str(item.get("title") or ""))
            source = str(item.get("source") or "").strip()
            link = str(item.get("url") or item.get("link") or "").strip()
            if not title:
                continue
            detail = f" - {source}" if source else ""
            display_text = clean_related_news_text(
                f"{title}{detail}",
                source=source,
            )
            if not display_text:
                continue
            lines.append(f"- {display_text}")
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
        f"{coin_icon} {decision.icon} {_notification_type_label(decision.notification_type)} - "
        f"{symbol}\n\n"
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
    plain_text = sanitize_alert_message(message)
    html_text = None
    if coin_icon_html != coin_icon:
        html_text = _build_html_message_from_plain_with_icon(
            plain_text=plain_text,
            plain_icon=coin_icon,
            icon_html=coin_icon_html,
        )
    return {"plain_text": plain_text, "html_text": html_text, "entities": entities}

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
    sent, error_message, _ = await _send_alert_to_recipient_once(app, recipient, alert_payload)
    return sent, error_message

async def _send_alert_to_recipient_once(
    app: Application, recipient: AlertRecipient, alert_payload: dict
) -> tuple[bool, str | None, BaseException | None]:
    logger.debug("alert_delivery_path_used")
    html_text = alert_payload.get("html_text")
    plain_text = str(alert_payload.get("plain_text", ""))
    entities = alert_payload.get("entities")
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
                fallback_kwargs = {"chat_id": recipient.chat_id, "text": plain_text}
                if entities:
                    fallback_kwargs["entities"] = entities
                await app.bot.send_message(**fallback_kwargs)
        else:
            kwargs = {"chat_id": recipient.chat_id, "text": plain_text}
            if entities:
                kwargs["entities"] = entities
            await app.bot.send_message(**kwargs)
    except Exception as error:
        return False, str(error), error
    return True, None, None

def _is_permanent_telegram_delivery_error(error: BaseException | str | None) -> bool:
    if error is None:
        return False
    if isinstance(error, (BadRequest, Forbidden)):
        return True
    return is_bot_blocked_error(error)

def _is_transient_telegram_delivery_error(error: BaseException | str | None) -> bool:
    if error is None or _is_permanent_telegram_delivery_error(error):
        return False
    if isinstance(error, (RetryAfter, TimedOut, NetworkError)):
        return True
    message = " ".join(str(error).lower().split())
    transient_terms = (
        "timed out",
        "timeout",
        "temporarily unavailable",
        "connection reset",
        "connection aborted",
        "network is unreachable",
        "bad gateway",
        "service unavailable",
        "gateway timeout",
        "internal server error",
        "too many requests",
        "retry after",
    )
    return any(term in message for term in transient_terms)

def _retry_after_seconds(error: BaseException | str | None) -> int | None:
    retry_after = getattr(error, "retry_after", None)
    if retry_after is None:
        return None
    try:
        return max(int(retry_after), 0)
    except (TypeError, ValueError):
        return None

def _delivery_retry_delay_seconds(error: BaseException | str | None, attempt_number: int) -> int:
    telegram_delay = _retry_after_seconds(error)
    if telegram_delay is not None:
        return telegram_delay
    index = max(attempt_number - 1, 0)
    if index >= len(TELEGRAM_DELIVERY_RETRY_BACKOFF_SECONDS):
        return int(TELEGRAM_DELIVERY_RETRY_BACKOFF_SECONDS[-1])
    return int(TELEGRAM_DELIVERY_RETRY_BACKOFF_SECONDS[index])

async def _send_alert_to_recipient_with_retry(
    app: Application,
    recipient: AlertRecipient,
    alert_payload: dict,
    *,
    alert_id: int | None = None,
) -> tuple[bool, str | None]:
    last_error: str | None = None
    for attempt in range(1, TELEGRAM_DELIVERY_MAX_ATTEMPTS + 1):
        sent, error_message, error = await _send_alert_to_recipient_once(
            app, recipient, alert_payload
        )
        if sent:
            return True, None
        last_error = error_message
        classification_error = error if error is not None else error_message
        if not _is_transient_telegram_delivery_error(classification_error):
            return False, error_message
        if attempt >= TELEGRAM_DELIVERY_MAX_ATTEMPTS:
            return False, error_message

        delay_seconds = _delivery_retry_delay_seconds(classification_error, attempt)
        next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
        if DB_ENABLED and DB_SESSION_LOCAL and alert_id is not None:
            async with DB_SESSION_LOCAL() as session:
                await update_alert_delivery_status(
                    session,
                    alert_id=alert_id,
                    status="retry_pending",
                    error_message=error_message,
                    retry_count=attempt,
                    last_error=error_message,
                    next_retry_at=next_retry_at,
                )
        logger.info(
            "ops_event=telegram_delivery_retrying attempt=%s next_retry_seconds=%s error_class=%s",
            attempt,
            delay_seconds,
            type(classification_error).__name__,
        )
        await asyncio.sleep(delay_seconds)
    return False, last_error

async def _disable_recipient_if_bot_blocked(
    recipient: AlertRecipient,
    error_message: str | None,
) -> None:
    if not is_bot_blocked_error(error_message):
        if error_message:
            logger.info(
                "ops_event=telegram_delivery_failure_not_permanent error_class=%s",
                type(error_message).__name__,
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
            logger.info("ops_event=user_deactivated_after_delivery_failure")

def _prefix_for_utf16_length(text: str, utf16_length: int) -> str:
    consumed = 0
    chars: list[str] = []
    for char in text:
        consumed += len(char.encode("utf-16-le")) // 2
        chars.append(char)
        if consumed >= utf16_length:
            break
    if consumed != utf16_length:
        return ""
    return "".join(chars)

def _preserve_leading_entities_after_sanitize(
    *,
    entities: object,
    original_text: str,
    sanitized_text: str,
) -> object | None:
    if not entities:
        return None
    for entity in entities:
        offset = getattr(entity, "offset", None)
        length = getattr(entity, "length", None)
        if offset != 0 or not isinstance(length, int) or length <= 0:
            return None
        prefix = _prefix_for_utf16_length(original_text, length)
        if not prefix or not sanitized_text.startswith(prefix):
            return None
    return entities

def _sanitize_alert_payload(alert_payload: dict) -> dict:
    plain_text = str(alert_payload.get("plain_text", ""))
    sanitized_plain_text = sanitize_alert_message(plain_text)
    html_text = alert_payload.get("html_text")
    entities = alert_payload.get("entities")
    if sanitized_plain_text != plain_text:
        html_text = None
        entities = _preserve_leading_entities_after_sanitize(
            entities=entities,
            original_text=plain_text,
            sanitized_text=sanitized_plain_text,
        )
    return {"plain_text": sanitized_plain_text, "html_text": html_text, "entities": entities}

async def _record_alert_delivery(
    *,
    symbol: str,
    alert_type: str,
    recipient: AlertRecipient,
    plain_text: str,
    status: str,
    market_event_id: int | None,
    market_heartbeat_id: int | None = None,
    event_ai_analysis_id: int | None = None,
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
            market_heartbeat_id=market_heartbeat_id,
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

async def _record_alert_delivery_outcome(
    *,
    symbol: str,
    alert_type: str,
    status: str,
    reason_code: str,
    market_event_id: int | None = None,
    event_ai_analysis_id: int | None = None,
    alert_id: int | None = None,
    recipient: AlertRecipient | None = None,
    recipient_eligible: bool | None = None,
    trigger_source: str | None = None,
    event_instance_key: str | None = None,
    semantic_family: str | None = None,
    detail: str | None = None,
) -> None:
    if not DB_ENABLED or not DB_SESSION_LOCAL:
        return
    async with DB_SESSION_LOCAL() as session:
        await save_alert_delivery_outcome(
            session,
            symbol=symbol,
            alert_type=alert_type,
            status=status,
            reason_code=reason_code,
            market_event_id=market_event_id,
            event_ai_analysis_id=event_ai_analysis_id,
            alert_id=alert_id,
            user_id=recipient.user_id if recipient else None,
            sent_to_chat_id=(
                recipient.chat_id if recipient and recipient.chat_id != 0 else None
            ),
            recipient_considered=recipient is not None,
            recipient_eligible=recipient_eligible,
            trigger_source=trigger_source,
            event_instance_key=event_instance_key,
            semantic_family=semantic_family,
            detail=detail,
        )

async def _record_recipient_outcomes(
    outcomes: list[RecipientOutcome],
    *,
    symbol: str,
    alert_type: str,
    market_event_id: int | None,
    event_ai_analysis_id: int | None,
    trigger_source: str | None = None,
    event_instance_key: str | None = None,
    semantic_family: str | None = None,
) -> None:
    for outcome in outcomes:
        await _record_alert_delivery_outcome(
            symbol=symbol,
            alert_type=alert_type,
            status=outcome.status,
            reason_code=outcome.reason_code,
            market_event_id=market_event_id,
            event_ai_analysis_id=event_ai_analysis_id,
            recipient=outcome.recipient,
            recipient_eligible=outcome.eligible,
            trigger_source=trigger_source,
            event_instance_key=event_instance_key,
            semantic_family=semantic_family,
            detail=outcome.detail,
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
    raw_event_key: str | None = None,
    canonical_event_key: str | None = None,
    semantic_family: str | None = None,
    event_instance_key: str | None = None,
    analysed_window_minutes: int | None = None,
    numeric_context: str | None = None,
    thresholds_used: str | None = None,
) -> bool:
    """Send one sanitized event analysis to every resolved recipient."""
    if event_type not in PRODUCT_ALERT_TYPES and event_type != EVENT_ALERT_TYPE:
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
        await _record_alert_delivery_outcome(
            symbol=normalized_symbol,
            alert_type=event_type,
            status=OUTCOME_NO_ELIGIBLE_RECIPIENTS,
            reason_code=REASON_NO_RECIPIENTS,
            market_event_id=market_event_id,
            event_ai_analysis_id=event_ai_analysis_id,
            trigger_source=trigger_source,
            event_instance_key=event_instance_key,
            semantic_family=semantic_family,
        )
        _log_event_alert_suppression(
            symbol=normalized_symbol,
            suppression_reason=SUPPRESSION_NO_ELIGIBLE_RECIPIENT,
            suppression_count=1,
            raw_event_key=raw_event_key,
            canonical_event_key=canonical_event_key,
            semantic_family=semantic_family,
            event_instance_key=event_instance_key,
            analysed_window_minutes=analysed_window_minutes,
        )
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
                if should_send:
                    logger.info(
                        "ops_event=event_alert_delivery_reserved symbol=%s alert_type=%s "
                        "trigger_source=%s market_event_id=%s",
                        normalized_symbol.upper(),
                        event_type,
                        trigger_source,
                        market_event_id,
                    )
            if not should_send:
                outcome_status = (
                    OUTCOME_SUPPRESSED
                    if alert_row.status == "sent"
                    else OUTCOME_NOT_SCHEDULED
                )
                reason_code = (
                    REASON_ALREADY_DELIVERED
                    if alert_row.status == "sent"
                    else REASON_DELIVERY_NOT_SCHEDULED
                )
                await _record_alert_delivery_outcome(
                    symbol=normalized_symbol,
                    alert_type=event_type,
                    status=outcome_status,
                    reason_code=reason_code,
                    market_event_id=market_event_id,
                    event_ai_analysis_id=event_ai_analysis_id,
                    alert_id=alert_row.id,
                    recipient=recipient,
                    recipient_eligible=False,
                    trigger_source=trigger_source,
                    event_instance_key=event_instance_key,
                    semantic_family=semantic_family,
                    detail=f"existing_alert_status:{alert_row.status}",
                )
                skipped_count += 1
                continue
        else:
            alert_id = None
        sent, error_message = await _send_alert_to_recipient_with_retry(
            app,
            recipient,
            alert_payload,
            alert_id=alert_id,
        )
        if DB_ENABLED and DB_SESSION_LOCAL and alert_id is not None:
            async with DB_SESSION_LOCAL() as session:
                await update_alert_delivery_status(
                    session,
                    alert_id=alert_id,
                    status="sent" if sent else "failed",
                    error_message=error_message,
                    retry_count=(
                        None
                        if sent
                        else TELEGRAM_DELIVERY_MAX_ATTEMPTS
                        if _is_transient_telegram_delivery_error(error_message)
                        else 1
                    ),
                    last_error=error_message,
                    final_failed_at=None if sent else datetime.now(timezone.utc),
                )
            await _record_alert_delivery_outcome(
                symbol=normalized_symbol,
                alert_type=event_type,
                status=OUTCOME_DELIVERED if sent else OUTCOME_FAILED,
                reason_code=REASON_DELIVERED if sent else REASON_TELEGRAM_SEND_FAILED,
                market_event_id=market_event_id,
                event_ai_analysis_id=event_ai_analysis_id,
                alert_id=alert_id,
                recipient=recipient,
                recipient_eligible=True,
                trigger_source=trigger_source,
                event_instance_key=event_instance_key,
                semantic_family=semantic_family,
                detail=None if sent else _truncate_text(str(error_message or ""), 255),
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
            await _record_alert_delivery_outcome(
                symbol=normalized_symbol,
                alert_type=event_type,
                status=OUTCOME_DELIVERED if sent else OUTCOME_FAILED,
                reason_code=REASON_DELIVERED if sent else REASON_TELEGRAM_SEND_FAILED,
                market_event_id=market_event_id,
                event_ai_analysis_id=event_ai_analysis_id,
                recipient=recipient,
                recipient_eligible=True,
                trigger_source=trigger_source,
                event_instance_key=event_instance_key,
                semantic_family=semantic_family,
                detail=None if sent else _truncate_text(str(error_message or ""), 255),
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
            _log_event_alert_suppression(
                symbol=normalized_symbol,
                suppression_reason=SUPPRESSION_DELIVERY_FAILED,
                suppression_count=1,
                raw_event_key=raw_event_key,
                canonical_event_key=canonical_event_key,
                semantic_family=semantic_family,
                event_instance_key=event_instance_key,
                delivery_count=sent_count,
                analysed_window_minutes=analysed_window_minutes,
            )
            log(
                "ops_event=telegram_delivery_failed "
                f"symbol={normalized_symbol.upper()} error_class={type(error_message).__name__}"
            )
    suppression_count = skipped_count + (len(recipients) - sent_count - skipped_count)
    summary_reason = None
    if len(recipients) - sent_count - skipped_count > 0:
        summary_reason = SUPPRESSION_DELIVERY_FAILED
    elif skipped_count > 0:
        summary_reason = SUPPRESSION_UNKNOWN
    log(
        "ops_event=event_alert_delivery_summary "
        f"symbol={normalized_symbol.upper()} market_event_id={market_event_id} "
        f"raw_event_key={raw_event_key} canonical_event_key={canonical_event_key} "
        f"semantic_family={semantic_family} event_instance_key={event_instance_key} "
        f"delivery_count={sent_count} suppression_count={suppression_count} "
        f"suppression_reason={summary_reason} analysed_window_minutes={analysed_window_minutes} "
        f"eligible={len(recipients)} sent={sent_count} "
        f"failed={len(recipients) - sent_count - skipped_count} skipped_duplicates={skipped_count}"
    )
    return delivered

async def _get_due_market_heartbeat_recipients(
    *,
    symbol: str,
    now: datetime,
) -> list[tuple[AlertRecipient, float | None]]:
    if not DB_ENABLED or not DB_SESSION_LOCAL:
        return []
    normalized_symbol = normalize_symbol(symbol)
    due: list[tuple[AlertRecipient, float | None]] = []
    seen_chat_ids: set[int] = set()
    async with DB_SESSION_LOCAL() as session:
        for user in await get_active_users_with_alert_preferences(session):
            if user.telegram_chat_id is None:
                continue
            enabled_by_symbol = _enabled_subscription_by_symbol(user)
            if not enabled_by_symbol.get(normalized_symbol, False):
                continue
            if not is_coin_unlocked_for_user(user, normalized_symbol, now):
                continue
            last_sent = await get_last_sent_alert(
                session,
                user_id=user.id,
                symbol=normalized_symbol,
                alert_type=MARKET_HEARTBEAT_TYPE,
            )
            last_sent_at = last_sent.created_at if last_sent else None
            frequency_seconds = get_effective_frequency_seconds(user, now)
            due_now = can_deliver_now(user, normalized_symbol, now, last_sent_at)
            logger.debug(
                "heartbeat_due_check symbol=%s frequency_seconds=%s last_heartbeat_at=%s due=%s",
                normalized_symbol,
                frequency_seconds,
                last_sent_at.isoformat() if last_sent_at else None,
                due_now,
            )
            if not due_now:
                logger.debug(
                    "heartbeat_delivery_frequency_skipped symbol=%s frequency_seconds=%s "
                    "last_heartbeat_at=%s",
                    normalized_symbol,
                    frequency_seconds,
                    last_sent_at.isoformat() if last_sent_at else None,
                )
                continue
            chat_id = int(user.telegram_chat_id)
            if chat_id in seen_chat_ids:
                continue
            seen_chat_ids.add(chat_id)
            last_price = (
                _numeric_context_value(last_sent.numeric_context, "current_price")
                if last_sent
                else None
            )
            due.append(
                (
                    AlertRecipient(
                        chat_id=chat_id,
                        user_id=user.id,
                        alert_frequency_seconds=frequency_seconds,
                    ),
                    last_price,
                )
            )
    return due

async def _deliver_market_heartbeat(
    app: Application,
    *,
    symbol: str,
    current_price: float,
    change_24h: float,
    now: datetime,
) -> bool:
    if not DB_ENABLED or not DB_SESSION_LOCAL:
        return False
    normalized_symbol = normalize_symbol(symbol)
    due_recipients = await _get_due_market_heartbeat_recipients(
        symbol=normalized_symbol,
        now=now,
    )
    if not due_recipients:
        return False

    async with DB_SESSION_LOCAL() as session:
        heartbeat = await get_latest_market_heartbeat(
            session,
            symbol=normalized_symbol,
            statuses={"completed"},
        )
    if heartbeat is None:
        logger.info("%s market heartbeat skipped: no cached heartbeat.", normalized_symbol.upper())
        return False
    if not _is_fresh_heartbeat(heartbeat, now=now):
        logger.info(
            "%s market heartbeat skipped: latest cached heartbeat is stale.",
            normalized_symbol.upper(),
        )
        return False

    related_news = _heartbeat_related_news(heartbeat)
    delivered = False
    sent_count = 0
    for recipient, last_message_price in due_recipients:
        change_since_last_message = (
            calculate_price_change_percent(float(last_message_price), current_price)
            if last_message_price
            else None
        )
        alert_payload = _sanitize_alert_payload(
            _build_market_heartbeat_payload(
                heartbeat=heartbeat,
                current_price=current_price,
                change_since_last_message=change_since_last_message,
                change_24h=change_24h,
                related_news=related_news,
            )
        )
        plain_text = str(alert_payload.get("plain_text", ""))
        numeric_context = _heartbeat_numeric_context(
            symbol=normalized_symbol,
            current_price=current_price,
            change_since_last_message=change_since_last_message,
            change_24h=change_24h,
            heartbeat_id=heartbeat.id,
            confidence=heartbeat.confidence,
        )
        alert_id = None
        if recipient.user_id is not None:
            async with DB_SESSION_LOCAL() as session:
                alert_row, should_send = await reserve_market_heartbeat_delivery(
                    session,
                    user_id=recipient.user_id,
                    symbol=normalized_symbol,
                    alert_type=MARKET_HEARTBEAT_TYPE,
                    sent_to_chat_id=recipient.chat_id,
                    market_heartbeat_id=heartbeat.id,
                    message=plain_text,
                    trigger_reason=heartbeat.title,
                    trigger_source=MARKET_HEARTBEAT_ANALYSIS_TYPE,
                    numeric_context=numeric_context,
                    llm_severity=heartbeat.confidence,
                    llm_reasoning_summary=heartbeat.message_body,
                )
                alert_id = alert_row.id
            if not should_send:
                continue
        sent, error_message = await _send_alert_to_recipient_with_retry(
            app,
            recipient,
            alert_payload,
            alert_id=alert_id,
        )
        if alert_id is not None:
            async with DB_SESSION_LOCAL() as session:
                await update_alert_delivery_status(
                    session,
                    alert_id=alert_id,
                    status="sent" if sent else "failed",
                    error_message=error_message,
                    retry_count=(
                        None
                        if sent
                        else TELEGRAM_DELIVERY_MAX_ATTEMPTS
                        if _is_transient_telegram_delivery_error(error_message)
                        else 1
                    ),
                    last_error=error_message,
                    final_failed_at=None if sent else datetime.now(timezone.utc),
                )
        else:
            await _record_alert_delivery(
                symbol=normalized_symbol,
                alert_type=MARKET_HEARTBEAT_TYPE,
                recipient=recipient,
                plain_text=plain_text,
                status="sent" if sent else "failed",
                market_event_id=None,
                market_heartbeat_id=heartbeat.id,
                event_ai_analysis_id=None,
                error_message=error_message,
                trigger_reason=heartbeat.title,
                trigger_source=MARKET_HEARTBEAT_ANALYSIS_TYPE,
                numeric_context=numeric_context,
                llm_severity=heartbeat.confidence,
                llm_reasoning_summary=heartbeat.message_body,
            )
        if sent:
            delivered = True
            sent_count += 1
        else:
            await _disable_recipient_if_bot_blocked(recipient, error_message)
            log(
                "ops_event=heartbeat_delivery_failed "
                f"symbol={normalized_symbol.upper()} error_class={type(error_message).__name__}"
            )
    log(
        "ops_event=heartbeat_delivery_summary "
        f"symbol={normalized_symbol.upper()} heartbeat_id={heartbeat.id} "
        f"due={len(due_recipients)} sent={sent_count} failed={len(due_recipients) - sent_count}"
    )
    return delivered

def schedule_automatic_market_check(app: Application, interval_seconds: int) -> None:
    interval_seconds = normalize_automatic_check_interval_seconds(interval_seconds)
    job_names = [AUTOMATIC_MARKET_CHECK_JOB_NAME] + [
        _automatic_market_check_job_name(symbol) for symbol in SUPPORTED_SYMBOLS
    ]
    for job_name in job_names:
        for job in app.job_queue.get_jobs_by_name(job_name):
            job.schedule_removal()

    now = datetime.now(timezone.utc)
    scheduled_symbols = []
    for symbol in SUPPORTED_SYMBOLS:
        first = _seconds_until_next_symbol_check(
            symbol=symbol,
            interval_seconds=interval_seconds,
            now=now,
        )
        app.job_queue.run_repeating(
            automatic_price_check,
            interval=interval_seconds,
            first=first,
            name=_automatic_market_check_job_name(symbol),
            data={"symbol": symbol},
            job_kwargs={"max_instances": 1, "coalesce": True, "misfire_grace_time": 15},
        )
        scheduled_symbols.append(f"{display_symbol(symbol)}:{first}s")
    log(
        "ops_event=automatic_check_scheduled "
        f"interval_seconds={interval_seconds} symbol_first_delays={','.join(scheduled_symbols)}"
    )

def schedule_automatic_btc_check(app: Application, interval_seconds: int) -> None:
    """Compatibility wrapper for older imports; schedules the market-wide check."""
    schedule_automatic_market_check(app, interval_seconds)

def schedule_market_heartbeat_generation(app: Application) -> None:
    for job in app.job_queue.get_jobs_by_name(MARKET_HEARTBEAT_JOB_NAME):
        job.schedule_removal()
    app.job_queue.run_repeating(
        generate_market_heartbeats,
        interval=3600,
        first=30,
        name=MARKET_HEARTBEAT_JOB_NAME,
        job_kwargs={"max_instances": 1, "coalesce": True, "misfire_grace_time": 60},
    )
    log("ops_event=heartbeat_generation_scheduled interval_seconds=3600")

def schedule_report_cache_generation(app: Application) -> None:
    for job_name in (DAILY_REPORT_CACHE_JOB_NAME, WEEKLY_REPORT_CACHE_JOB_NAME):
        for job in app.job_queue.get_jobs_by_name(job_name):
            job.schedule_removal()

    app.job_queue.run_repeating(
        generate_daily_report_cache_job,
        interval=4 * 3600,
        first=60,
        name=DAILY_REPORT_CACHE_JOB_NAME,
        job_kwargs={"max_instances": 1, "coalesce": True, "misfire_grace_time": 120},
    )
    app.job_queue.run_repeating(
        generate_weekly_report_cache_job,
        interval=24 * 3600,
        first=120,
        name=WEEKLY_REPORT_CACHE_JOB_NAME,
        job_kwargs={"max_instances": 1, "coalesce": True, "misfire_grace_time": 300},
    )
    log(
        "ops_event=market_report_cache_scheduled "
        "daily_interval_seconds=14400 weekly_interval_seconds=86400"
    )

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

async def generate_market_heartbeats(context: ContextTypes.DEFAULT_TYPE):
    if not DB_ENABLED or not DB_SESSION_LOCAL:
        logger.info("Market heartbeat generation skipped because database storage is off.")
        return
    now = datetime.now(timezone.utc)
    try:
        market_data = await get_coin_market_data_batch(list(SUPPORTED_SYMBOLS))
        if not market_data:
            log("Market heartbeat generation skipped because CoinGecko returned no usable data.")
            return
        raw_news_items: list[dict] | None = None
        generated = 0
        skipped_fresh = 0
        for symbol in SUPPORTED_SYMBOLS:
            normalized_symbol = normalize_symbol(symbol)
            async with DB_SESSION_LOCAL() as session:
                latest = await get_latest_market_heartbeat(
                    session,
                    symbol=normalized_symbol,
                    statuses={"completed"},
                )
            if latest and _is_fresh_heartbeat(latest, now=now, max_age_seconds=3600):
                skipped_fresh += 1
                continue
            symbol_data = market_data.get(normalized_symbol)
            if not symbol_data:
                continue
            current_price = float(symbol_data["price"])
            change_24h = float(symbol_data.get("change_24h") or 0.0)
            news_items, raw_news_items, used_intelligence_news = await _select_related_news_context(
                normalized_symbol,
                raw_news_items,
                fetch_limit=30,
                intelligence_max_age_hours=12,
                fallback_max_age_hours=12,
                now=now,
            )
            candidate_news = _format_candidate_news(
                news_items,
                preserve_order=used_intelligence_news,
                symbol=normalized_symbol,
            )
            input_payload = await _build_market_heartbeat_input(
                heartbeat_id=_build_market_heartbeat_id(normalized_symbol),
                symbol=normalized_symbol,
                current_price=current_price,
                change_24h=change_24h,
                now=now,
                candidate_news=candidate_news,
            )
            heartbeat_id = await _create_market_heartbeat(input_payload)
            if heartbeat_id:
                generated += 1
        log(
            "ops_event=heartbeat_generation_completed "
            f"generated={generated} fresh_skipped={skipped_fresh}"
        )
    except CoinGeckoRateLimitError:
        log("ops_event=coingecko_rate_limit context=heartbeat_generation")
    except Exception as error:
        log(
            "ops_event=heartbeat_generation_failed "
            f"error_class={type(error).__name__}"
        )

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
    elif event_type == EVENT_ALERT_TYPE:
        pass
    else:
        return
    async with DB_SESSION_LOCAL() as session:
        await upsert_user_symbol_alert_state(session, **kwargs)
    if event_type == NotificationType.MARKET_UPDATE.value:
        logger.debug(
            "last_market_update_time_persisted symbol=%s value=%s",
            normalized_symbol.upper(),
            now.isoformat(),
        )
    elif event_type in {
        NotificationType.IMPORTANT_ALERT.value,
        NotificationType.CRITICAL_ALERT.value,
    }:
        logger.debug(
            "alert_baseline_updated_after_send symbol=%s alert_type=%s value=%s",
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
    logger.debug("Running automatic LLM event-analysis check.")
    try:
        db_active = DB_ENABLED and DB_SESSION_LOCAL
        now = datetime.now(timezone.utc)
        job_data = getattr(getattr(context, "job", None), "data", None)
        target_symbol = None
        if isinstance(job_data, dict) and job_data.get("symbol"):
            target_symbol = normalize_symbol(str(job_data["symbol"]))
        symbols_to_check = await resolve_symbols_to_check(now)
        if target_symbol:
            symbols_to_check = [symbol for symbol in symbols_to_check if symbol == target_symbol]
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
        news_driven_candidates = await _load_news_driven_alert_candidates(
            symbols_to_check,
            now=now,
        )

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
            last_alert_at = None
            db_row = None
            if DB_ENABLED and DB_SESSION_LOCAL:
                async with DB_SESSION_LOCAL() as session:
                    db_row = await get_price_state(session, symbol)
                    last_alert_at = db_row.last_alert_at if db_row else None
            else:
                last_alert_at = _parse_state_alert_at(state.get("last_alert_at"))

            recipient_resolution = await resolve_alert_recipient_outcomes(
                symbol=symbol,
                event_type=EVENT_ALERT_TYPE,
                now=now,
                bypass_frequency=True,
            )
            candidate_recipients = recipient_resolution.recipients
            if not candidate_recipients:
                log(f"No subscribed recipients for {symbol.upper()} automatic alerts.")
                await _record_recipient_outcomes(
                    recipient_resolution.filtered,
                    symbol=symbol,
                    alert_type=EVENT_ALERT_TYPE,
                    market_event_id=None,
                    event_ai_analysis_id=None,
                    trigger_source=EVENT_ANALYSIS_TYPE,
                )
                await _record_alert_delivery_outcome(
                    symbol=symbol,
                    alert_type=EVENT_ALERT_TYPE,
                    status=OUTCOME_NO_ELIGIBLE_RECIPIENTS,
                    reason_code=REASON_NO_RECIPIENTS,
                    trigger_source=EVENT_ANALYSIS_TYPE,
                    detail="no_recipients_before_event_analysis",
                )
                _log_event_alert_suppression(
                    symbol=symbol,
                    suppression_reason=SUPPRESSION_NO_ELIGIBLE_RECIPIENT,
                    suppression_count=1,
                    analysed_window_minutes=get_analysed_window_minutes(
                        int(alert_settings.get("automatic_check_interval_seconds", 300))
                    ),
                )
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

            delivered = False
            news_items, raw_news_items, used_intelligence_news = await _select_related_news_context(
                symbol,
                raw_news_items,
                fetch_limit=20,
                intelligence_max_age_hours=24,
                now=now,
            )
            candidate_news = _format_candidate_news(
                news_items,
                preserve_order=used_intelligence_news,
                symbol=symbol,
            )
            analysis_id = _build_event_analysis_id(symbol)
            input_payload = await _build_event_analysis_input(
                analysis_id=analysis_id,
                symbol=symbol,
                current_price=current_price,
                change_24h=change_24h,
                now=now,
                state=state,
                candidate_news=candidate_news,
                event_analysis_interval_seconds=int(
                    alert_settings.get("automatic_check_interval_seconds", 300)
                ),
            )
            decision, event_ai_analysis_id = await _create_event_analysis_decision(input_payload)
            if decision is None:
                news_delivered = False
                for news_item in news_driven_candidates.get(symbol, []):
                    news_delivered = await _deliver_news_driven_alert_for_symbol(
                        app,
                        symbol=symbol,
                        news_item=news_item,
                        current_price=current_price,
                        change_24h=change_24h,
                        event_analysis_input_payload=input_payload,
                        candidate_recipients=candidate_recipients,
                        cooldown_seconds=int(
                            alert_settings.get("automatic_check_interval_seconds", 300)
                        ),
                        now=now,
                    )
                    if news_delivered:
                        used_news_items.append(news_item)
                        delivered_symbols += 1
                        break
                if news_delivered:
                    await _save_price_state(
                        symbol=symbol,
                        state=state,
                        current_price=current_price,
                        change_24h=change_24h,
                        change_7d=change_7d if isinstance(change_7d, float) else None,
                        checked_at=checked_at,
                        last_alert_at=datetime.now(timezone.utc),
                    )
                    continue
                await _deliver_market_heartbeat(
                    app,
                    symbol=symbol,
                    current_price=current_price,
                    change_24h=change_24h,
                    now=now,
                )
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
            if not decision.should_alert:
                logger.info(
                    "%s LLM event analysis returned no alert: %s",
                    symbol.upper(),
                    decision.reason_for_no_alert,
                )
                _log_event_alert_suppression(
                    symbol=symbol,
                    suppression_reason=SUPPRESSION_UNKNOWN,
                    suppression_count=1,
                    raw_event_key=_raw_event_key_from_payload(input_payload, decision),
                    canonical_event_key=decision.event_key,
                    semantic_family=_semantic_family_from_payload(input_payload),
                    analysed_window_minutes=_analysed_window_minutes_from_payload(input_payload),
                )
                news_delivered = False
                for news_item in news_driven_candidates.get(symbol, []):
                    news_delivered = await _deliver_news_driven_alert_for_symbol(
                        app,
                        symbol=symbol,
                        news_item=news_item,
                        current_price=current_price,
                        change_24h=change_24h,
                        event_analysis_input_payload=input_payload,
                        candidate_recipients=candidate_recipients,
                        cooldown_seconds=int(
                            alert_settings.get("automatic_check_interval_seconds", 300)
                        ),
                        now=now,
                    )
                    if news_delivered:
                        used_news_items.append(news_item)
                        delivered_symbols += 1
                        break
                if news_delivered:
                    await _save_price_state(
                        symbol=symbol,
                        state=state,
                        current_price=current_price,
                        change_24h=change_24h,
                        change_7d=change_7d if isinstance(change_7d, float) else None,
                        checked_at=checked_at,
                        last_alert_at=datetime.now(timezone.utc),
                    )
                    continue
                await _deliver_market_heartbeat(
                    app,
                    symbol=symbol,
                    current_price=current_price,
                    change_24h=change_24h,
                    now=now,
                )
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

            (
                market_event_id,
                _,
                event_instance_key,
                _reused_market_event,
            ) = await _get_or_create_event_alert_market_event(
                decision=decision,
                input_payload=input_payload,
            )
            related_news = _related_news_by_id(
                candidate_news,
                decision.related_news_ids,
                symbol=symbol,
                context="event analysis",
            )
            alert_payload = _build_event_alert_payload(
                decision=decision,
                input_payload=input_payload,
                related_news=related_news,
            )
            if DB_ENABLED and DB_SESSION_LOCAL and market_event_id is not None:
                async with DB_SESSION_LOCAL() as session:
                    existing_analysis = await get_latest_success_event_ai_analysis(
                        session,
                        market_event_id=market_event_id,
                    )
                    if existing_analysis:
                        event_ai_analysis_id = existing_analysis.id
                        if existing_analysis.plain_text:
                            alert_payload["plain_text"] = existing_analysis.plain_text
                        if existing_analysis.html_text:
                            alert_payload["html_text"] = existing_analysis.html_text
                    else:
                        analysis = await attach_analysis_to_market_event(
                            session,
                            analysis_id=analysis_id,
                            market_event_id=market_event_id,
                            plain_text=alert_payload["plain_text"],
                        )
                        event_ai_analysis_id = analysis.id if analysis else event_ai_analysis_id
            await _record_recipient_outcomes(
                recipient_resolution.filtered,
                symbol=symbol,
                alert_type=EVENT_ALERT_TYPE,
                market_event_id=market_event_id,
                event_ai_analysis_id=event_ai_analysis_id,
                trigger_source=EVENT_ANALYSIS_TYPE,
                event_instance_key=event_instance_key,
                semantic_family=_semantic_family_from_payload(input_payload),
            )

            recipient_filter = await _filter_event_recipients_for_cooldown(
                candidate_recipients,
                symbol=symbol,
                urgency=decision.urgency,
                cooldown_seconds=int(alert_settings.get("automatic_check_interval_seconds", 300)),
                canonical_event_key=decision.event_key,
                semantic_family=_semantic_family_from_payload(input_payload),
                current_movement_percent=_event_movement_percent_from_payload(input_payload),
                current_stable_news_ids=_stable_related_news_ids(
                    input_payload,
                    decision.related_news_ids,
                ),
                now=now,
                return_summary=True,
            )
            recipients = recipient_filter.recipients
            await _record_recipient_outcomes(
                recipient_filter.suppressed,
                symbol=symbol,
                alert_type=EVENT_ALERT_TYPE,
                market_event_id=market_event_id,
                event_ai_analysis_id=event_ai_analysis_id,
                trigger_source=EVENT_ANALYSIS_TYPE,
                event_instance_key=event_instance_key,
                semantic_family=_semantic_family_from_payload(input_payload),
            )
            if not recipients:
                suppression_reason = (
                    _primary_suppression_reason(recipient_filter.suppression_reason_counts)
                    or SUPPRESSION_UNKNOWN
                )
                suppression_count = sum(recipient_filter.suppression_reason_counts.values())
                logger.info("%s event alert suppressed by backend cooldown.", symbol.upper())
                await _record_alert_delivery_outcome(
                    symbol=symbol,
                    alert_type=EVENT_ALERT_TYPE,
                    status=(
                        OUTCOME_SUPPRESSED
                        if suppression_reason == SUPPRESSION_SEMANTIC_COOLDOWN
                        else OUTCOME_COOLDOWN
                    ),
                    reason_code=(
                        REASON_SIMILAR_EVENT_SUPPRESSED
                        if suppression_reason == SUPPRESSION_SEMANTIC_COOLDOWN
                        else REASON_COOLDOWN_ACTIVE
                    ),
                    market_event_id=market_event_id,
                    event_ai_analysis_id=event_ai_analysis_id,
                    trigger_source=EVENT_ANALYSIS_TYPE,
                    event_instance_key=event_instance_key,
                    semantic_family=_semantic_family_from_payload(input_payload),
                    detail=suppression_reason,
                )
                _log_event_alert_suppression(
                    symbol=symbol,
                    suppression_reason=suppression_reason,
                    suppression_count=suppression_count or len(candidate_recipients),
                    raw_event_key=_raw_event_key_from_payload(input_payload, decision),
                    canonical_event_key=decision.event_key,
                    semantic_family=_semantic_family_from_payload(input_payload),
                    event_instance_key=event_instance_key,
                    analysed_window_minutes=_analysed_window_minutes_from_payload(input_payload),
                )
                await _deliver_market_heartbeat(
                    app,
                    symbol=symbol,
                    current_price=current_price,
                    change_24h=change_24h,
                    now=now,
                )
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

            used_news_items.extend(news_items)
            delivered = await _deliver_market_event_alert(
                app,
                symbol=symbol,
                alert_payload=alert_payload,
                market_event_id=market_event_id,
                event_ai_analysis_id=event_ai_analysis_id,
                recipients=recipients,
                event_type=EVENT_ALERT_TYPE,
                trigger_reason=decision.title,
                trigger_source=EVENT_ANALYSIS_TYPE,
                raw_event_key=_raw_event_key_from_payload(input_payload, decision),
                canonical_event_key=decision.event_key,
                semantic_family=_semantic_family_from_payload(input_payload),
                event_instance_key=event_instance_key,
                analysed_window_minutes=_analysed_window_minutes_from_payload(input_payload),
                numeric_context=_event_numeric_context(
                    input_payload,
                    decision,
                    event_instance_key=event_instance_key,
                ),
                thresholds_used=None,
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
                last_alert_at=(datetime.now(timezone.utc) if delivered else last_alert_at),
            )
        if used_news_items:
            deduped_news = list({make_news_key(item): item for item in used_news_items}.values())
            await remember_news_context(deduped_news)
        if not db_active:
            save_state(state)
        checked_symbols_text = ", ".join(display_symbol(symbol) for symbol in symbols_to_check)
        log(
            "ops_event=automatic_check_completed "
            f"symbols={checked_symbols_text.replace(' ', '')} "
            f"delivered_symbols={delivered_symbols} "
            f"duration_seconds={perf_counter() - cycle_started_at:.2f}"
        )
    except CoinGeckoRateLimitError:
        log("ops_event=coingecko_rate_limit context=automatic_price_check")
    except httpx.HTTPStatusError as error:
        log(
            "ops_event=automatic_check_failed reason=http_error "
            f"error_class={type(error).__name__}"
        )
    except Exception as error:
        log(
            "ops_event=automatic_check_failed reason=unexpected_error "
            f"error_class={type(error).__name__}"
        )
    finally:
        logger.info(
            "ops_event=automatic_check_cycle_finished duration_seconds=%.2f",
            perf_counter() - cycle_started_at,
        )
