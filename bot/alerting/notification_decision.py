"""Product-level notification decisions for automatic market monitoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any


class NotificationType(str, Enum):
    NO_ALERT = "no_alert"
    MARKET_UPDATE = "market_update"
    IMPORTANT_ALERT = "important_alert"
    CRITICAL_ALERT = "critical_alert"


class NotificationSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class NotificationDirection(str, Enum):
    UP = "up"
    DOWN = "down"
    MIXED = "mixed"
    NEUTRAL = "neutral"


class TriggerSource(str, Enum):
    FAST_MOVEMENT = "fast_movement"
    CUMULATIVE_MOVEMENT = "cumulative_movement"
    USER_PERIOD_MOVEMENT = "user_period_movement"
    NEWS = "news"
    COMBINED_SIGNAL = "combined_signal"
    SCHEDULED_MARKET_UPDATE = "scheduled_market_update"
    VOLATILITY = "volatility"
    TREND_24H = "trend_24h"


SEVERITY_RANK = {
    NotificationSeverity.LOW: 1,
    NotificationSeverity.MEDIUM: 2,
    NotificationSeverity.HIGH: 3,
    NotificationSeverity.EXTREME: 4,
}


@dataclass(frozen=True)
class SignalContext:
    symbol: str
    current_price: float
    latest_5m_change_percent: float | None = None
    change_since_last_market_update_percent: float | None = None
    user_period_change_percent: float | None = None
    one_hour_change_percent: float | None = None
    four_hour_change_percent: float | None = None
    twenty_four_hour_change_percent: float | None = None
    relevant_news_items: list[dict[str, Any]] = field(default_factory=list)
    news_candidates: list[dict[str, Any]] = field(default_factory=list)
    news_relevance_score: str | None = None
    last_notification_time: datetime | None = None
    last_notification_type: str | None = None
    last_notification_severity: str | None = None
    last_notification_direction: str | None = None
    last_market_update_time: datetime | None = None
    user_alert_frequency_seconds: int | None = None
    trigger_candidates: list[str] = field(default_factory=list)
    suppression_context: dict[str, Any] = field(default_factory=dict)
    scheduled_market_update_due: bool = False
    fast_movement_threshold_percent: float = 1.0
    cumulative_movement_threshold_percent: float = 1.0
    extreme_movement_threshold_percent: float = 5.0
    material_worsening_percent: float = 0.5


@dataclass(frozen=True)
class NotificationDecision:
    notification_type: NotificationType
    severity: NotificationSeverity
    direction: NotificationDirection
    should_send: bool
    should_suppress: bool
    trigger_source: TriggerSource | None
    reasoning_summary: str
    possible_action: str
    icon: str


def decide_notification(context: SignalContext) -> NotificationDecision:
    """Return one of the three user-facing notification decisions."""
    fast = _value(context.latest_5m_change_percent)
    cumulative = _value(context.change_since_last_market_update_percent)
    period = _value(context.user_period_change_percent)
    trend_24h = _value(context.twenty_four_hour_change_percent)
    news_score = (context.news_relevance_score or "none").lower()
    useful_news = _useful_news_candidates(context)
    has_relevant_news = bool(useful_news) and news_score in {
        "relevant",
        "very_relevant",
        "medium",
        "strong",
    }
    has_strong_news = any(
        str(item.get("relevance") or "").lower() in {"strong", "very_relevant", "high"}
        for item in useful_news
    ) or news_score in {"strong", "very_relevant", "high"}

    direction = _direction(fast, cumulative, period, trend_24h)
    fast_abs = abs(fast)
    cumulative_abs = abs(cumulative)
    period_abs = abs(period)
    trend_abs = abs(trend_24h)
    threshold = abs(context.fast_movement_threshold_percent)
    cumulative_threshold = abs(context.cumulative_movement_threshold_percent)
    extreme_threshold = abs(context.extreme_movement_threshold_percent)

    fast_trigger = fast_abs >= threshold
    cumulative_trigger = cumulative_abs >= cumulative_threshold
    period_trigger = period_abs >= cumulative_threshold
    extreme_trigger = fast_abs >= extreme_threshold or cumulative_abs >= extreme_threshold
    combined_trigger = (
        (fast_trigger or cumulative_trigger or period_trigger)
        and (has_relevant_news or trend_abs >= max(cumulative_threshold * 1.5, 2.0))
    )
    news_trigger = has_strong_news

    if _contains_market_shock(context.relevant_news_items):
        decision = _decision(
            NotificationType.CRITICAL_ALERT,
            NotificationSeverity.EXTREME,
            direction,
            TriggerSource.NEWS,
            "Major market-shock news was detected.",
            "Avoid impulsive action. Check news, liquidity, and your risk exposure.",
        )
    elif extreme_trigger or (
        combined_trigger
        and (max(fast_abs, cumulative_abs, period_abs) >= threshold * 2.5 or trend_abs >= 8.0)
    ):
        decision = _decision(
            NotificationType.CRITICAL_ALERT,
            NotificationSeverity.EXTREME,
            direction,
            TriggerSource.COMBINED_SIGNAL if combined_trigger else _movement_trigger_source(
                fast_abs, cumulative_abs, period_abs
            ),
            "An extreme market move or confirmed combined signal was detected.",
            "Avoid impulsive action. Check market depth, news, and your risk exposure.",
        )
    elif combined_trigger:
        combined_severity = (
            NotificationSeverity.HIGH
            if max(fast_abs, cumulative_abs, period_abs) >= threshold * 1.5
            else NotificationSeverity.MEDIUM
        )
        if has_relevant_news:
            reason = "Price movement has possible news context."
        elif trend_abs >= max(cumulative_threshold * 1.5, 2.0):
            reason = "Price movement aligns with the broader price trend."
        else:
            reason = "Price movement crossed the user movement threshold."
        decision = _decision(
            NotificationType.IMPORTANT_ALERT,
            combined_severity,
            direction,
            TriggerSource.COMBINED_SIGNAL,
            reason,
            "Watch whether the move stabilises or continues over the next update window.",
        )
    elif fast_trigger:
        decision = _decision(
            NotificationType.IMPORTANT_ALERT,
            NotificationSeverity.MEDIUM,
            direction,
            TriggerSource.FAST_MOVEMENT,
            _movement_reason("5-minute move", fast, threshold),
            "Watch whether this is a brief spike or the start of a sustained move.",
        )
    elif cumulative_trigger:
        decision = _decision(
            NotificationType.IMPORTANT_ALERT,
            NotificationSeverity.MEDIUM,
            direction,
            TriggerSource.CUMULATIVE_MOVEMENT,
            _movement_reason(
                "since the previous alert baseline",
                cumulative,
                cumulative_threshold,
            ),
            "Watch whether the coin stabilises near the current level or keeps moving.",
        )
    elif period_trigger:
        decision = _decision(
            NotificationType.IMPORTANT_ALERT,
            NotificationSeverity.MEDIUM,
            direction,
            TriggerSource.USER_PERIOD_MOVEMENT,
            _movement_reason("over the last update window", period, cumulative_threshold),
            "Watch whether the move continues or fades.",
        )
    elif news_trigger:
        severity = (
            NotificationSeverity.MEDIUM
            if news_score == "very_relevant" or trend_abs >= 2.0
            else NotificationSeverity.LOW
        )
        decision = _decision(
            NotificationType.IMPORTANT_ALERT,
            severity,
            direction,
            TriggerSource.NEWS,
            "Relevant market news appeared without a strong confirmed price reaction.",
            "Monitor whether price starts reacting during the next update window.",
        )
    elif context.scheduled_market_update_due:
        severity = _scheduled_market_update_severity(period_abs, trend_abs, has_relevant_news)
        decision = _decision(
            NotificationType.MARKET_UPDATE,
            severity,
            direction,
            TriggerSource.SCHEDULED_MARKET_UPDATE,
            _scheduled_reason(period, trend_24h, has_relevant_news),
            "No urgent action needed. Continue monitoring.",
        )
    else:
        return _decision(
            NotificationType.NO_ALERT,
            NotificationSeverity.LOW,
            direction,
            None,
            "No scheduled update is due and no meaningful trigger was detected.",
            "Continue monitoring.",
            should_send=False,
        )

    suppressed = _should_suppress_event_alert(context, decision)
    if suppressed:
        return NotificationDecision(
            notification_type=decision.notification_type,
            severity=decision.severity,
            direction=decision.direction,
            should_send=False,
            should_suppress=True,
            trigger_source=decision.trigger_source,
            reasoning_summary=(
                "event_alert_suppressed: same_direction=true "
                "severity_increased=false material_extension=false"
            ),
            possible_action=decision.possible_action,
            icon=decision.icon,
        )
    return decision


def notification_icon(
    notification_type: NotificationType | str,
    direction: NotificationDirection | str,
    severity: NotificationSeverity | str,
    trigger_source: TriggerSource | str | None = None,
) -> str:
    ntype = NotificationType(notification_type)
    direction_value = NotificationDirection(direction)
    severity_value = NotificationSeverity(severity)
    source_value = TriggerSource(trigger_source) if trigger_source else None

    if ntype is NotificationType.MARKET_UPDATE:
        if source_value is TriggerSource.NEWS:
            return "\U0001f4f0"
        if direction_value is NotificationDirection.MIXED:
            return "\u2696\ufe0f"
        if direction_value is NotificationDirection.NEUTRAL:
            return "\U0001f7e2"
        return "\U0001f4ca"
    if ntype is NotificationType.IMPORTANT_ALERT:
        if source_value is TriggerSource.NEWS:
            return "\U0001f4f0"
        if (
            source_value is TriggerSource.COMBINED_SIGNAL
            and direction_value is NotificationDirection.MIXED
        ):
            return "\u26a0\ufe0f"
        if direction_value is NotificationDirection.DOWN:
            return "\U0001f4c9"
        if direction_value is NotificationDirection.UP:
            return "\U0001f4c8"
        if source_value is TriggerSource.COMBINED_SIGNAL:
            return "\u26a0\ufe0f"
        return "\U0001f30a"
    if ntype is NotificationType.CRITICAL_ALERT:
        if source_value is TriggerSource.NEWS:
            return "\U0001f6d1"
        if source_value is TriggerSource.VOLATILITY:
            return "\U0001f525"
        if direction_value is NotificationDirection.UP:
            return "\U0001f680"
        if severity_value is NotificationSeverity.EXTREME:
            return "\U0001f6a8"
        return "\U0001f525"
    return ""


def _decision(
    notification_type: NotificationType,
    severity: NotificationSeverity,
    direction: NotificationDirection,
    trigger_source: TriggerSource | None,
    reasoning_summary: str,
    possible_action: str,
    *,
    should_send: bool = True,
) -> NotificationDecision:
    return NotificationDecision(
        notification_type=notification_type,
        severity=severity,
        direction=direction,
        should_send=should_send,
        should_suppress=False,
        trigger_source=trigger_source,
        reasoning_summary=reasoning_summary,
        possible_action=possible_action,
        icon=notification_icon(notification_type, direction, severity, trigger_source),
    )


def _value(value: float | None) -> float:
    return float(value or 0.0)


def _direction(*values: float) -> NotificationDirection:
    meaningful = [value for value in values if abs(value) >= 0.1]
    if not meaningful:
        return NotificationDirection.NEUTRAL
    has_up = any(value > 0 for value in meaningful)
    has_down = any(value < 0 for value in meaningful)
    if has_up and has_down:
        total = sum(meaningful)
        if abs(total) < 0.1:
            return NotificationDirection.MIXED
        return NotificationDirection.UP if total > 0 else NotificationDirection.DOWN
    return NotificationDirection.UP if has_up else NotificationDirection.DOWN


def _movement_trigger_source(
    fast_abs: float,
    cumulative_abs: float,
    period_abs: float,
) -> TriggerSource:
    if fast_abs >= cumulative_abs and fast_abs >= period_abs:
        return TriggerSource.FAST_MOVEMENT
    if cumulative_abs >= period_abs:
        return TriggerSource.CUMULATIVE_MOVEMENT
    return TriggerSource.USER_PERIOD_MOVEMENT


def _movement_reason(label: str, move: float, threshold: float) -> str:
    verb = "moved up" if move > 0 else "moved down"
    preposition = "" if label.startswith(("since ", "over ")) else "on the "
    if label.startswith("since the previous alert"):
        label = "since the previous alert"
    return (
        f"The coin {verb} by {abs(move):.2f}% {preposition}{label}, crossing the "
        f"{abs(threshold):.1f}% movement threshold."
    )


def _scheduled_market_update_severity(
    period_abs: float,
    trend_abs: float,
    has_relevant_news: bool,
) -> NotificationSeverity:
    if period_abs >= 3.0:
        return NotificationSeverity.HIGH
    if period_abs >= 2.0 and trend_abs >= 3.0:
        return NotificationSeverity.HIGH
    if period_abs >= 1.0 or has_relevant_news:
        return NotificationSeverity.MEDIUM
    return NotificationSeverity.LOW


def _scheduled_reason(period: float, trend_24h: float, has_relevant_news: bool) -> str:
    if abs(period) < 1.0 and abs(trend_24h) < 3.0 and not has_relevant_news:
        return "The market is calm over the last update window."
    if has_relevant_news:
        return "The scheduled update includes relevant news context."
    if abs(period) < 1.0:
        return "No significant short-term movement detected."
    if abs(period) < 2.0:
        return "The scheduled update shows mild movement over the last update window."
    return "The scheduled update shows meaningful movement over the last update window."


def _should_suppress_event_alert(
    context: SignalContext,
    decision: NotificationDecision,
) -> bool:
    if decision.notification_type not in {
        NotificationType.IMPORTANT_ALERT,
        NotificationType.CRITICAL_ALERT,
    }:
        return False
    if not context.last_notification_time:
        return False
    cooldown_seconds = max(int(context.user_alert_frequency_seconds or 3600), 0)
    if (datetime.now(timezone.utc) - _aware_utc(context.last_notification_time)) > timedelta(
        seconds=cooldown_seconds
    ):
        return False
    if (context.last_notification_type or "") not in {
        NotificationType.IMPORTANT_ALERT.value,
        NotificationType.CRITICAL_ALERT.value,
    }:
        return False
    if (context.last_notification_direction or "") != decision.direction.value:
        return False
    previous_severity = _severity_from_string(context.last_notification_severity)
    if previous_severity and SEVERITY_RANK[decision.severity] > SEVERITY_RANK[previous_severity]:
        return False
    if context.suppression_context.get("new_highly_relevant_news") is True or (
        _has_strong_news(context) and _contains_market_shock(context.relevant_news_items)
    ):
        return False
    if _price_extended_materially_from_last_alert(context, decision):
        return False
    return True


def _useful_news_candidates(context: SignalContext) -> list[dict[str, Any]]:
    candidates = context.news_candidates or context.relevant_news_items
    return [
        item
        for item in candidates
        if str(item.get("relevance") or context.news_relevance_score or "").lower()
        in {"medium", "strong", "relevant", "very_relevant", "high"}
    ]


def _price_extended_materially_from_last_alert(
    context: SignalContext,
    decision: NotificationDecision,
) -> bool:
    previous_price = context.suppression_context.get(
        "last_event_alert_price",
        context.suppression_context.get("last_important_alert_price"),
    )
    try:
        previous = float(previous_price)
    except (TypeError, ValueError):
        return False
    if previous <= 0 or context.current_price <= 0:
        return False
    extension_percent = _material_extension_percent(context.symbol)
    threshold = extension_percent / 100.0
    if decision.direction is NotificationDirection.UP:
        return context.current_price >= previous * (1 + threshold)
    if decision.direction is NotificationDirection.DOWN:
        return context.current_price <= previous * (1 - threshold)
    return False


def _material_extension_percent(symbol: str) -> float:
    return 1.0 if str(symbol).strip().lower() in {"btc", "eth"} else 1.5


def _has_strong_news(context: SignalContext) -> bool:
    if str(context.news_relevance_score or "").lower() in {"strong", "very_relevant", "high"}:
        return True
    return any(
        str(item.get("relevance") or "").lower() in {"strong", "very_relevant", "high"}
        for item in context.news_candidates
    )


def _severity_from_string(value: str | None) -> NotificationSeverity | None:
    if not value:
        return None
    normalized = value.lower()
    aliases = {
        "watch": "medium",
        "info": "low",
        "moderate": "medium",
        "critical": "extreme",
    }
    try:
        return NotificationSeverity(aliases.get(normalized, normalized))
    except ValueError:
        return None


def _contains_market_shock(news_items: list[dict[str, Any]]) -> bool:
    shock_terms = (
        "exchange collapse",
        "bankruptcy",
        "major hack",
        "exploit",
        "liquidation cascade",
        "systemic",
        "halted withdrawals",
    )
    for item in news_items:
        text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
        if any(term in text for term in shock_terms):
            return True
    return False


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
