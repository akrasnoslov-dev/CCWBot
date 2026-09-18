"""Deterministic quality guards for user-visible Event Alert text."""

from __future__ import annotations

import re
from datetime import datetime, timezone

_PERCENT_RE = re.compile(r"[+-]?\d+(?:\.\d+)?\s*%")
_MOVE_RE = re.compile(
    r"(?i)\b(move|moved|movement|up|down|higher|lower|rose|fell|gain|drop|decline|rally)\w*\b"
)
_EXPLANATION_RE = re.compile(
    r"(?i)\b(after|because|due to|amid|following|confirmed|protocol|exploit|etf|news)\b"
)
_MARKET_RESTATEMENT_RE = re.compile(
    r"(?i)\b(?:price|market|move|movement|momentum|rose|fell|up|down)\b"
)
_CONDITIONAL_ACTION_RE = re.compile(r"(?i)\b(?:if|unless|when|only if)\b")
_PERCENT_VALUE_RE = re.compile(
    r"(?i)([+-]?\d+(?:\.\d+)?)\s*(?:%|percent(?:age)?(?:\s+points?)?\b)"
)
_MONEY_VALUE_RE = re.compile(
    r"(?i)(?:\$\s*([+-]?\d+(?:\.\d+)?)|([+-]?\d+(?:\.\d+)?)\s*usd\b)"
)
_ACTION_VERB = (
    r"buy|sell(?:ing)?|close|exit|enter|short|long|add|reduce|tighten|liquidate|"
    r"go\s+(?:long|short)|open(?:ing)?|take\s+profit|hold|dca"
)
_DIRECT_FINANCIAL_INSTRUCTION_RE = re.compile(
    rf"(?ix)(?:^\s*(?:please\s+)?"
    rf"(?!(?:selling\b|(?:buy|sell|short|long)-))|"
    rf"\b(?:you|we|i)\s+(?:should|must|need\s+to|have\s+to|recommend|advise)"
    rf"(?:\s+\w+){{0,4}}\s+|"
    rf"\bit\s+is\s+time\s+to\s+|\b(?:now|immediately)\s+)"
    rf"(?P<verb>{_ACTION_VERB})\b"
)
_EXTREME_ACTION_RE = re.compile(
    r"(?i)\b(?:entire|all|fully|immediately)\b.*\b(?:position|exposure)\b|"
    r"\b(?:liquidate|close|exit)\b.*\b(?:entire|all|fully|immediately)\b"
)


def compact_elapsed_since(previous_at: object, current_at: object) -> str | None:
    previous = _parse_datetime(previous_at)
    current = _parse_datetime(current_at)
    if previous is None or current is None:
        return None
    seconds = max(int((current - previous).total_seconds()), 0)
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        remaining_minutes = minutes % 60
        return f"{hours}h {remaining_minutes}m ago" if remaining_minutes else f"{hours}h ago"
    days = hours // 24
    remaining_hours = hours % 24
    return f"{days}d {remaining_hours}h ago" if remaining_hours else f"{days}d ago"


def ensure_useful_situation(
    value: str,
    *,
    significance_reason: str | None,
) -> str:
    """Replace a bare percentage restatement with why the event crossed significance."""
    words = value.split()
    if (
        not _MOVE_RE.search(value)
        or len(words) > 16
        or _EXPLANATION_RE.search(value)
        or (_PERCENT_RE.search(value) is None and len(words) > 8)
    ):
        return value
    return {
        "persistent_cumulative_trend": (
            "A persistent sequence of moves has accumulated into a meaningful trend."
        ),
        "material_acceleration": (
            "The latest move accelerated relative to the earlier analysed-window trajectory."
        ),
        "broader_24h_trend_continuation": (
            "The shorter move continues a materially larger trend visible over 24 hours."
        ),
        "material_change_since_previous_alert": (
            "Market conditions have moved materially beyond the previous delivered alert."
        ),
        "relevant_context_supports_market_move": (
            "Relevant context accompanies a market reaction large enough to matter."
        ),
    }.get(
        str(significance_reason or ""),
        "The analysed-window move is large enough to represent a meaningful market change.",
    )


def compact_event_alert_situation(
    value: str,
    *,
    significance_reason: str | None,
    market_data: dict | None = None,
) -> str:
    """Keep Event Alert explanations useful instead of repeating the metric block."""
    fallback = ensure_useful_situation(
        "The analysed-window move",
        significance_reason=significance_reason,
    )
    cleaned = " ".join(str(value or "").split()).strip()
    if not cleaned:
        return fallback
    if _repeats_rendered_market_fact(cleaned, market_data or {}):
        explanation = _concise_explanation_clause(cleaned, market_data or {})
        return explanation or fallback
    if len(cleaned.split()) > 28:
        return fallback
    compacted = ensure_useful_situation(
        cleaned,
        significance_reason=significance_reason,
    )
    if _MARKET_RESTATEMENT_RE.search(compacted) and not _EXPLANATION_RE.search(compacted):
        return fallback
    return compacted


def _repeats_rendered_market_fact(value: str, market_data: dict) -> bool:
    percent_values = _market_numeric_values(
        market_data,
        "chg_window_percent",
        "chg_since_msg_percent",
        "chg24h_percent",
    )
    for match in _PERCENT_VALUE_RE.finditer(value):
        if _value_matches_market_fact(match.group(1), percent_values):
            return True
    price_values = _market_numeric_values(market_data, "price", "price_now_usd")
    snapshots = market_data.get("snapshots")
    if isinstance(snapshots, list):
        for snapshot in snapshots:
            if isinstance(snapshot, dict):
                price_values.extend(_market_numeric_values(snapshot, "p", "price_usd"))
    for match in _MONEY_VALUE_RE.finditer(value):
        if _value_matches_market_fact(match.group(1) or match.group(2), price_values):
            return True
    return False


def _market_numeric_values(market_data: dict, *keys: str) -> list[float]:
    values: list[float] = []
    for key in keys:
        try:
            value = float(market_data.get(key))
        except (TypeError, ValueError):
            continue
        values.append(value)
    return values


def _value_matches_market_fact(value: str | None, market_values: list[float]) -> bool:
    try:
        claimed = float(value)
    except (TypeError, ValueError):
        return False
    return any(
        abs(claimed - market_value) <= 0.05
        or (
            0 < abs(market_value) < 0.1
            and 0 < abs(claimed) <= 0.1
            and (claimed > 0) == (market_value > 0)
        )
        for market_value in market_values
    )


def _concise_explanation_clause(value: str, market_data: dict) -> str | None:
    match = _EXPLANATION_RE.search(value)
    if match is None:
        return None
    clause = value[match.start() :].strip()
    if (
        not clause
        or len(clause.split()) > 28
        or _repeats_rendered_market_fact(clause, market_data)
    ):
        return None
    return clause[:1].upper() + clause[1:]


def soften_possible_action(value: str, *, urgency: str | None) -> str:
    """Keep trading-oriented guidance conditional and proportionate."""
    match = _DIRECT_FINANCIAL_INSTRUCTION_RE.search(value)
    if not match and _EXTREME_ACTION_RE.search(value):
        return "Consider reducing exposure only if your predefined risk limits are breached."
    if not match:
        return value
    verb = match.group("verb").lower()
    if verb == "selling":
        verb = "sell"
    if verb in {"buy", "enter", "long", "add", "go long", "open", "opening", "dca"}:
        return "Consider a cautious entry only if the move confirms and fits your risk plan."
    if verb in {"sell", "reduce", "liquidate", "take profit"}:
        return "Consider reducing exposure if the change no longer fits your risk plan."
    if verb in {"close", "exit", "short", "go short"}:
        return "Consider reducing or closing exposure if your risk limits are breached."
    if str(urgency or "").lower() == "high":
        return "Consider tightening risk controls if the move continues to accelerate."
    return "Consider reviewing risk controls and waiting for confirmation."


def compact_event_alert_possible_action(value: str) -> str:
    """Keep Event Alert actions short, conditional, and non-prescriptive."""
    cleaned = " ".join(str(value or "").split()).strip()
    if (
        len(cleaned.split()) > 20
        or len(re.findall(r"[.!?]", cleaned)) > 1
        or not _CONDITIONAL_ACTION_RE.search(cleaned)
    ):
        return "Watch for confirmation before acting, if it fits your risk plan."
    return cleaned


def sanitize_financial_instruction(value: str, *, fallback: str) -> str:
    """Reject direct trading instructions in every user-visible Event Alert field."""
    if _DIRECT_FINANCIAL_INSTRUCTION_RE.search(value):
        return fallback
    return value


def _parse_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
