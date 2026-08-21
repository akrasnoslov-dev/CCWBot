"""Deterministic significance policy for LLM-positive Event Alert decisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bot.domain.supported_coins import normalize_symbol
from bot.settings import (
    DEFAULT_ALT_MOVEMENT_THRESHOLD_PERCENT,
    DEFAULT_MAJOR_MOVEMENT_THRESHOLD_PERCENT,
)


@dataclass(frozen=True)
class EventSignificance:
    is_significant: bool
    reason: str
    window_change_percent: float | None
    cumulative_change_percent: float | None
    persistence_ratio: float
    acceleration_ratio: float | None


def evaluate_event_significance(
    input_payload: dict[str, Any],
    *,
    urgency: str | None,
    related_news: list[dict[str, Any]] | None = None,
) -> EventSignificance:
    """Require quantitative market support for an LLM-positive alert.

    No single fixed movement threshold decides every case. A moderate move can qualify
    through a persistent cumulative trajectory, acceleration, broader 24-hour continuation,
    or a meaningful change since the previous delivered alert. News is supporting evidence
    only and cannot qualify an otherwise weak market move.
    """
    market = input_payload.get("market", input_payload.get("market_data", {}))
    if not isinstance(market, dict):
        market = {}
    window = _number(market.get("chg_window"))
    since_message = _number(
        market.get(
            "chg_since_msg",
            market.get("change_since_last_user_visible_message_percent"),
        )
    )
    day = _number(market.get("chg24h", market.get("change_24h_percent")))
    prices = _snapshot_prices(market.get("snapshots"))
    cumulative = _change(prices[0], prices[-1]) if len(prices) >= 2 else window
    persistence = _persistence_ratio(prices, cumulative)
    acceleration = _acceleration_ratio(prices, cumulative)
    primary = window if window is not None else cumulative

    result_kwargs = {
        "window_change_percent": window,
        "cumulative_change_percent": cumulative,
        "persistence_ratio": persistence,
        "acceleration_ratio": acceleration,
    }
    if primary is None:
        return EventSignificance(False, "missing_market_movement", **result_kwargs)

    primary_abs = abs(primary)
    cumulative_abs = abs(cumulative) if cumulative is not None else 0.0
    since_abs = abs(since_message) if since_message is not None else 0.0
    day_abs = abs(day) if day is not None else 0.0
    same_day_direction = _same_direction(primary, day)
    same_since_direction = _same_direction(primary, since_message)
    same_cumulative_direction = _same_direction(primary, cumulative)
    symbol = normalize_symbol(str(input_payload.get("symbol") or "btc"))
    material_window_threshold = (
        DEFAULT_MAJOR_MOVEMENT_THRESHOLD_PERCENT
        if symbol in {"btc", "eth"}
        else DEFAULT_ALT_MOVEMENT_THRESHOLD_PERCENT
    )
    has_material_news = any(
        bool(item.get("material"))
        and str(item.get("relevance_label") or "").lower()
        in {"direct_symbol", "market_wide"}
        for item in (related_news or [])
        if isinstance(item, dict)
    )

    if cumulative_abs >= 1.0 and persistence >= 0.67 and same_cumulative_direction:
        return EventSignificance(True, "persistent_cumulative_trend", **result_kwargs)
    if primary_abs >= material_window_threshold:
        return EventSignificance(True, "material_analysed_window_move", **result_kwargs)
    if (
        primary_abs >= 0.5
        and acceleration is not None
        and acceleration >= 1.5
        and persistence >= 0.6
        and same_cumulative_direction
    ):
        return EventSignificance(True, "material_acceleration", **result_kwargs)
    if primary_abs >= 0.35 and day_abs >= 3.0 and same_day_direction:
        return EventSignificance(True, "broader_24h_trend_continuation", **result_kwargs)
    if primary_abs >= 0.25 and since_abs >= 1.0 and same_since_direction:
        return EventSignificance(True, "material_change_since_previous_alert", **result_kwargs)
    if (
        primary_abs >= 0.5
        and day_abs >= 1.0
        and same_day_direction
        and has_material_news
    ):
        return EventSignificance(True, "relevant_context_supports_market_move", **result_kwargs)

    # High urgency remains an LLM interpretation, never a substitute for evidence.
    if str(urgency or "").lower() == "high":
        return EventSignificance(False, "unsupported_urgency", **result_kwargs)
    return EventSignificance(False, "insufficient_market_significance", **result_kwargs)


def significance_context(result: EventSignificance) -> dict[str, Any]:
    """Return compact, non-sensitive evidence suitable for durable input telemetry."""
    return {
        "reason": result.reason,
        "window_change_percent": result.window_change_percent,
        "cumulative_change_percent": result.cumulative_change_percent,
        "persistence_ratio": round(result.persistence_ratio, 3),
        "acceleration_ratio": (
            round(result.acceleration_ratio, 3)
            if result.acceleration_ratio is not None
            else None
        ),
    }


def _snapshot_prices(value: object) -> list[float]:
    if not isinstance(value, list):
        return []
    prices: list[float] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        price = _number(item.get("p", item.get("price_usd")))
        if price is not None and price > 0:
            prices.append(price)
    return prices


def _persistence_ratio(prices: list[float], total_change: float | None) -> float:
    if len(prices) < 2 or not total_change:
        return 0.0
    direction = 1 if total_change > 0 else -1
    steps = [right - left for left, right in zip(prices, prices[1:], strict=False)]
    directional = sum(1 for step in steps if step * direction > 0)
    return directional / len(steps) if steps else 0.0


def _acceleration_ratio(prices: list[float], total_change: float | None) -> float | None:
    if len(prices) < 4 or not total_change:
        return None
    direction = 1 if total_change > 0 else -1
    changes = [_change(left, right) for left, right in zip(prices, prices[1:], strict=False)]
    directional = [change * direction for change in changes if change is not None]
    if len(directional) < 3 or directional[-1] <= 0:
        return None
    earlier = [max(value, 0.0) for value in directional[:-1]]
    baseline = sum(earlier) / len(earlier)
    if baseline <= 0:
        return None
    return directional[-1] / baseline


def _same_direction(left: float | None, right: float | None) -> bool:
    return left is not None and right is not None and left != 0 and left * right > 0


def _change(old: float, new: float) -> float | None:
    if old == 0:
        return None
    return ((new - old) / old) * 100


def _number(value: object) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
