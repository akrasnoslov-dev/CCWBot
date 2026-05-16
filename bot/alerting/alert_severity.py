"""Alert severity and alert-type classification helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from bot.domain.supported_coins import normalize_symbol


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
    CHANGE_24H_THRESHOLD = "24h_change_threshold"
    VOLATILITY_SPIKE = "volatility_spike"
    WEEKLY_TREND_CHANGE = "weekly_trend_change"
    NEWS_SPIKE = "news_spike"


ALERT_SEVERITY_ICONS = {
    AlertSeverity.INFO: "\N{INFORMATION SOURCE}\ufe0f",
    AlertSeverity.WATCH: "\N{WARNING SIGN}\ufe0f",
    AlertSeverity.HIGH: "\N{POLICE CARS REVOLVING LIGHT}",
    AlertSeverity.EXTREME: "\N{FIRE}",
}

ALERT_SEVERITY_LABELS = {
    AlertSeverity.INFO: "Info",
    AlertSeverity.WATCH: "Watch",
    AlertSeverity.HIGH: "High",
    AlertSeverity.EXTREME: "Extreme",
}

ALERT_TYPE_LABELS = {
    AlertType.PRICE_MOVEMENT: "Price movement",
    AlertType.TREND_24H: "24h trend",
    AlertType.NEWS: "News",
    AlertType.COMBINED: "Combined",
    AlertType.STRONG_SIGNAL: "Strong signal",
    AlertType.CHANGE_24H_THRESHOLD: "24h threshold crossed",
    AlertType.VOLATILITY_SPIKE: "Volatility spike",
    AlertType.WEEKLY_TREND_CHANGE: "Weekly trend change",
    AlertType.NEWS_SPIKE: "News spike",
}

COIN_VOLATILITY_BASELINES = {
    "btc": 2.5,
    "eth": 3.5,
    "sol": 5.0,
    "xrp": 5.0,
    "bnb": 3.5,
    "doge": 6.0,
    "ada": 4.5,
    "ton": 5.0,
    "link": 5.0,
    "trx": 3.5,
}


@dataclass(frozen=True)
class SeverityInput:
    symbol: str
    price_change_percent: float = 0.0
    change_24h: float | None = None
    change_7d: float | None = None
    previous_24h_change: float | None = None
    alert_threshold_percent: float | None = None
    news_relevance: str = "none"
    strong_signal_strength: str | None = None


@dataclass(frozen=True)
class SeverityEvaluation:
    severity: AlertSeverity
    primary_alert_type: AlertType
    signals: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class AlertThresholds:
    movement_percent: float
    trend_24h_medium_percent: float
    trend_24h_high_percent: float


@dataclass(frozen=True)
class AlertDecision:
    should_alert: bool
    alert_type: AlertType | None
    backend_severity_ceiling: AlertSeverity
    trigger_reason: str
    signals: tuple[str, ...] = field(default_factory=tuple)


def severity_icon(severity: AlertSeverity) -> str:
    return ALERT_SEVERITY_ICONS[severity]


def severity_label(severity: AlertSeverity) -> str:
    return ALERT_SEVERITY_LABELS[severity]


def alert_type_label(alert_type: AlertType | str) -> str:
    try:
        normalized = alert_type if isinstance(alert_type, AlertType) else AlertType(alert_type)
    except ValueError:
        return str(alert_type).replace("_", " ").strip().capitalize()
    return ALERT_TYPE_LABELS[normalized]


def render_severity_heading(severity: AlertSeverity) -> str:
    return f"{severity_icon(severity)} {severity_label(severity)}"


def alert_title_action(alert_type: AlertType | str) -> str:
    try:
        normalized = alert_type if isinstance(alert_type, AlertType) else AlertType(alert_type)
    except ValueError:
        return "market alert"
    if normalized is AlertType.PRICE_MOVEMENT:
        return "movement alert"
    if normalized is AlertType.TREND_24H:
        return "24h trend alert"
    if normalized is AlertType.NEWS:
        return "news alert"
    if normalized is AlertType.COMBINED:
        return "combined alert"
    if normalized is AlertType.STRONG_SIGNAL:
        return "strong signal"
    if normalized is AlertType.CHANGE_24H_THRESHOLD:
        return "24h threshold alert"
    if normalized is AlertType.VOLATILITY_SPIKE:
        return "volatility spike"
    if normalized is AlertType.WEEKLY_TREND_CHANGE:
        return "weekly trend change"
    if normalized is AlertType.NEWS_SPIKE:
        return "news spike"
    return "market alert"


def thresholds_for_symbol(settings: dict, symbol: str) -> AlertThresholds:
    normalized_symbol = normalize_symbol(symbol)
    is_major = normalized_symbol in {"btc", "eth"}
    return AlertThresholds(
        movement_percent=float(
            settings.get(
                (
                    "major_movement_threshold_percent"
                    if is_major
                    else "alt_movement_threshold_percent"
                ),
                1.0 if is_major else 2.0,
            )
        ),
        trend_24h_medium_percent=float(
            settings.get(
                "major_24h_medium_threshold_percent"
                if is_major
                else "alt_24h_medium_threshold_percent",
                3.0 if is_major else 5.0,
            )
        ),
        trend_24h_high_percent=float(
            settings.get(
                "major_24h_high_threshold_percent"
                if is_major
                else "alt_24h_high_threshold_percent",
                5.0 if is_major else 8.0,
            )
        ),
    )


def evaluate_alert_decision(
    *,
    symbol: str,
    movement_percent: float,
    change_24h: float,
    thresholds: AlertThresholds,
    news_relevance: str = "none",
    peak_intrawindow_movement_percent: float | None = None,
) -> AlertDecision:
    """Decide whether an automatic alert is valid before asking the LLM."""
    abs_move = abs(float(movement_percent))
    abs_24h = abs(float(change_24h or 0.0))
    abs_peak = abs(float(peak_intrawindow_movement_percent or 0.0))
    relevance = (news_relevance or "none").strip().lower()

    price_triggered = (
        abs_move >= thresholds.movement_percent or abs_peak >= thresholds.movement_percent
    )
    trend_medium_triggered = abs_24h >= thresholds.trend_24h_medium_percent
    trend_high_triggered = abs_24h >= thresholds.trend_24h_high_percent
    news_triggered = relevance in {"relevant", "very_relevant"}

    signals: list[str] = []
    if price_triggered:
        if abs_move >= thresholds.movement_percent:
            signals.append("User-window movement threshold crossed")
        elif abs_peak >= thresholds.movement_percent:
            signals.append("Intrawindow movement threshold crossed")
    if trend_medium_triggered:
        signals.append("24h trend threshold crossed")
    if news_triggered:
        signals.append("Clearly relevant news found")

    if not signals:
        return AlertDecision(False, None, AlertSeverity.INFO, "No alert threshold crossed", ())

    if news_triggered and (price_triggered or trend_medium_triggered):
        alert_type = AlertType.COMBINED
    elif price_triggered:
        alert_type = AlertType.PRICE_MOVEMENT
    elif trend_medium_triggered:
        alert_type = AlertType.TREND_24H
    else:
        alert_type = AlertType.NEWS

    if trend_high_triggered or (price_triggered and trend_medium_triggered and news_triggered):
        ceiling = AlertSeverity.HIGH
    elif alert_type is AlertType.NEWS:
        ceiling = AlertSeverity.WATCH
    else:
        ceiling = AlertSeverity.WATCH

    if alert_type is AlertType.PRICE_MOVEMENT:
        reason = (
            f"The movement crossed the configured threshold of "
            f"{thresholds.movement_percent:.1f}%."
        )
    elif alert_type is AlertType.TREND_24H:
        reason = (
            f"The 24h trend crossed the medium threshold of "
            f"{thresholds.trend_24h_medium_percent:.1f}%."
        )
    elif alert_type is AlertType.NEWS:
        reason = "Clearly relevant news was found while price movement stayed below threshold."
    else:
        reason = "Price or trend signals align with clearly relevant news."

    return AlertDecision(True, alert_type, ceiling, reason, tuple(signals))


def evaluate_alert_severity(data: SeverityInput) -> SeverityEvaluation:
    """Classify alert severity from market, news, and strong-signal context."""
    normalized_symbol = normalize_symbol(data.symbol)
    baseline = COIN_VOLATILITY_BASELINES.get(normalized_symbol, 4.0)
    threshold = abs(data.alert_threshold_percent or baseline)
    abs_move = abs(data.price_change_percent)
    abs_24h = abs(data.change_24h or 0.0)
    abs_7d = abs(data.change_7d or 0.0)
    abs_previous_24h = abs(data.previous_24h_change or 0.0)
    news_relevance = data.news_relevance.strip().lower()
    strong_signal = (data.strong_signal_strength or "").strip().lower()

    signals: list[str] = []
    score = 0

    threshold_crossed = abs_move >= threshold
    if threshold_crossed:
        signals.append("Price movement threshold crossed")
        score += 2
    elif abs_move >= threshold * 0.5:
        signals.append("Price movement is building")
        score += 1

    threshold_24h = max(3.0, threshold * 1.5)
    crossed_24h_now = abs_24h >= threshold_24h and abs_previous_24h < threshold_24h
    if crossed_24h_now:
        signals.append("24h threshold crossed")
        score += 2
    elif abs_24h >= threshold_24h:
        signals.append("24h trend is elevated")
        score += 1

    volatility_spike = abs_move >= baseline * 1.5 or abs_24h >= baseline * 2.0
    if volatility_spike:
        signals.append("Volatility spike detected")
        score += 2

    weekly_trend_change = (
        data.change_7d is not None
        and data.change_24h is not None
        and abs_7d >= 3.0
        and abs_24h >= 2.0
        and (data.change_7d > 0 > data.change_24h or data.change_7d < 0 < data.change_24h)
    )
    if weekly_trend_change:
        signals.append("Weekly trend direction is changing")
        score += 1

    if news_relevance == "very_relevant":
        signals.append("Very relevant news context found")
        score += 2
    elif news_relevance == "relevant":
        signals.append("Relevant news context found")
        score += 1

    if strong_signal == "strong":
        signals.append("Strong signal classification")
        score += 2
    elif strong_signal == "medium":
        signals.append("Medium signal classification")
        score += 1

    confirming_signals = sum(
        bool(value)
        for value in (
            threshold_crossed,
            crossed_24h_now or abs_24h >= threshold_24h,
            volatility_spike,
            weekly_trend_change,
            news_relevance in {"relevant", "very_relevant"},
            strong_signal in {"medium", "strong"},
        )
    )
    if confirming_signals >= 3:
        score += 1

    if score >= 5:
        severity = AlertSeverity.EXTREME
    elif score >= 2:
        severity = AlertSeverity.HIGH
    elif score == 1:
        severity = AlertSeverity.WATCH
    else:
        severity = AlertSeverity.INFO

    primary_type = _select_primary_alert_type(
        strong_signal=strong_signal,
        news_relevance=news_relevance,
        volatility_spike=volatility_spike,
        crossed_24h=crossed_24h_now,
        weekly_trend_change=weekly_trend_change,
        threshold_crossed=threshold_crossed,
    )
    return SeverityEvaluation(
        severity=severity,
        primary_alert_type=primary_type,
        signals=tuple(signals),
    )


def _select_primary_alert_type(
    *,
    strong_signal: str,
    news_relevance: str,
    volatility_spike: bool,
    crossed_24h: bool,
    weekly_trend_change: bool,
    threshold_crossed: bool,
) -> AlertType:
    if strong_signal in {"medium", "strong"}:
        return AlertType.STRONG_SIGNAL
    if news_relevance == "very_relevant":
        return AlertType.NEWS_SPIKE
    if volatility_spike:
        return AlertType.VOLATILITY_SPIKE
    if crossed_24h:
        return AlertType.CHANGE_24H_THRESHOLD
    if weekly_trend_change:
        return AlertType.WEEKLY_TREND_CHANGE
    if threshold_crossed:
        return AlertType.PRICE_MOVEMENT
    return AlertType.PRICE_MOVEMENT
