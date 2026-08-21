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
