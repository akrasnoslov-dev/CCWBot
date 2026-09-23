"""Presentation-only severity labels retained for non-Event-Alert compatibility.

Event Alert significance is owned by Event Analysis. This module intentionally contains no
market-threshold configuration or automatic-alert decision policy.
"""

from dataclasses import dataclass, field
from enum import Enum


class AlertSeverity(str, Enum):
    INFO = "info"
    WATCH = "watch"
    HIGH = "high"
    EXTREME = "extreme"


class AlertType(str, Enum):
    PRICE_MOVEMENT = "price_movement"
    TREND_24H = "24h_trend"
    NEWS = "news"
    COMBINED = "combined"
    STRONG_SIGNAL = "strong_signal"
    VOLATILITY_SPIKE = "volatility_spike"
    WEEKLY_TREND_CHANGE = "weekly_trend_change"
    NEWS_SPIKE = "news_spike"


@dataclass(frozen=True)
class SeverityEvaluation:
    severity: AlertSeverity
    primary_alert_type: AlertType
    signals: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class AlertDecision:
    should_alert: bool
    alert_type: AlertType | None
    backend_severity_ceiling: AlertSeverity
    trigger_reason: str
    signals: tuple[str, ...] = field(default_factory=tuple)


def alert_title_action(alert_type: AlertType | str) -> str:
    try:
        normalized = alert_type if isinstance(alert_type, AlertType) else AlertType(alert_type)
    except ValueError:
        return "market alert"
    return {
        AlertType.PRICE_MOVEMENT: "movement alert",
        AlertType.TREND_24H: "24h trend alert",
        AlertType.NEWS: "news alert",
        AlertType.COMBINED: "combined alert",
        AlertType.STRONG_SIGNAL: "strong signal",
        AlertType.VOLATILITY_SPIKE: "volatility spike",
        AlertType.WEEKLY_TREND_CHANGE: "weekly trend change",
        AlertType.NEWS_SPIKE: "news spike",
    }[normalized]
