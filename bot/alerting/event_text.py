"""Deterministic quality guards for user-visible Event Alert text."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

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
_UNSUPPORTED_MARKET_CLAIM_RE = re.compile(
    r"(?i)\b(?:volume|order[ -]?flow|support|resistance|liquidations?|funding(?:[ -]?rate)?|"
    r"etf[ -]?flows?|technical indicators?|rsi|macd|participation|open interest|"
    r"whales?|on[ -]?chain)\b"
)
_UNSUPPORTED_CAUSAL_CLAIM_RE = re.compile(
    r"(?i)\b(?:because|due to|caused by|driven by|explains?|after)\b"
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
    related_news: list[dict] | None = None,
) -> str:
    """Keep Event Alert explanations useful instead of repeating the metric block."""
    fallback, _ = event_alert_presentation_fallback(
        market_data or {}, related_news or []
    )
    cleaned = " ".join(str(value or "").split()).strip()
    if not cleaned:
        return fallback
    if _UNSUPPORTED_MARKET_CLAIM_RE.search(cleaned) or _UNSUPPORTED_CAUSAL_CLAIM_RE.search(
        cleaned
    ):
        return fallback
    # Free-form LLM copy cannot establish unstructured facts (for example demand, sentiment,
    # volume, or causality). Preserve only a bounded market interpretation that matches the
    # structured snapshot/trend relationships; related news stays in its own section.
    if not _is_safe_llm_situation(cleaned, market_data=market_data or {}):
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
    if (
        _MARKET_RESTATEMENT_RE.search(compacted)
        and not _EXPLANATION_RE.search(compacted)
        and not _is_safe_structured_market_interpretation(compacted, market_data or {})
    ):
        return fallback
    return compacted


def _is_safe_llm_situation(
    value: str,
    *,
    market_data: dict,
) -> bool:
    return _is_safe_structured_market_interpretation(value, market_data)


def _is_safe_structured_market_interpretation(value: str, market_data: dict) -> bool:
    """Allow concise LLM context only when its relationship exists in market input."""
    lowered = value.lower()
    if _PERCENT_RE.search(value) or _MONEY_VALUE_RE.search(value):
        return False

    step_changes = _snapshot_step_changes(market_data)
    window_change = _decimal_market_value(market_data.get("chg_window_percent"))
    change_24h = _decimal_market_value(market_data.get("chg24h_percent"))
    has_reversal = len(step_changes) >= 2 and step_changes[-1] * step_changes[-2] < 0
    has_persistence = _has_persistent_snapshot_direction(step_changes)
    has_broader_comparison = (
        window_change is not None
        and change_24h is not None
        and window_change != 0
        and change_24h != 0
    )
    has_divergence = has_broader_comparison and (window_change > 0) != (change_24h > 0)
    has_alignment = has_broader_comparison and not has_divergence

    if not any(
        term in lowered
        for term in (
            "snapshot",
            "short-term",
            "short term",
            "broader",
            "24-hour",
            "24 hour",
            "persistent",
            "persistence",
            "reversal",
            "diverg",
            "align",
        )
    ):
        return False
    if any(term in lowered for term in ("snapshot", "persistent", "persistence")) and not (
        step_changes and (has_persistence or has_reversal)
    ):
        return False
    if "reversal" in lowered and not has_reversal:
        return False
    if "diverg" in lowered and not has_divergence:
        return False
    if "align" in lowered and not has_alignment:
        return False
    if (
        any(
            term in lowered
            for term in ("broader", "24-hour", "24 hour", "short-term", "short term")
        )
        and not has_broader_comparison
    ):
        return False

    current_direction = window_change
    if current_direction is None and step_changes:
        current_direction = step_changes[-1]
    if any(term in lowered for term in ("lower", "declin", "weakness", "weaker", "down")) and not (
        current_direction is not None and current_direction < 0
    ):
        return False
    if any(
        term in lowered for term in ("higher", "rally", "strength", "stronger", "upward")
    ) and not (current_direction is not None and current_direction > 0):
        return False
    if "positive" in lowered and not (
        change_24h is not None and change_24h > 0
    ):
        return False
    if "negative" in lowered and not (
        change_24h is not None and change_24h < 0
    ):
        return False
    return True


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
        or _UNSUPPORTED_MARKET_CLAIM_RE.search(clause)
        or _UNSUPPORTED_CAUSAL_CLAIM_RE.search(clause)
    ):
        return None
    return clause[:1].upper() + clause[1:]


def event_alert_presentation_fallback(
    market_data: dict, related_news: list[dict],
) -> tuple[str, str]:
    """Return display-only context from supplied evidence, never alert eligibility.

    This deliberately uses only direction and sequence relationships.  It does not add a
    numerical significance rule, causal claim, or policy gate; the Event Analysis decision
    remains entirely upstream with the LLM.
    """
    step_changes = _snapshot_step_changes(market_data)
    window_change = _decimal_market_value(market_data.get("chg_window_percent"))
    change_24h = _decimal_market_value(market_data.get("chg24h_percent"))
    has_broader_comparison = (
        window_change is not None
        and change_24h is not None
        and window_change != 0
        and change_24h != 0
    )
    has_divergence = has_broader_comparison and (window_change > 0) != (change_24h > 0)
    has_persistence = _has_persistent_snapshot_direction(step_changes)

    if len(step_changes) >= 2 and step_changes[-1] * step_changes[-2] < 0:
        return (
            "The most recent supplied snapshot reverses part of the earlier path, so the "
            "current move may be fading rather than extending.",
            "Watch the next short-term snapshots for further reversal versus renewed movement "
            "in the current direction.",
        )

    if has_persistence and has_divergence:
        return (
            "The move persisted across the supplied short-term snapshots while the broader "
            "24-hour direction remained opposite, indicating short-term divergence.",
            "Watch whether the next short-term snapshots continue in the current direction "
            "or reverse back toward the broader 24-hour direction.",
        )

    if has_divergence:
        return (
            "The short-term move runs against the broader 24-hour direction, so the current "
            "change is a short-term divergence rather than full trend alignment.",
            "Watch whether upcoming snapshots begin aligning with the broader 24-hour "
            "direction or continue diverging.",
        )

    if has_persistence:
        return (
            "The move developed across the supplied snapshots rather than a single observation, "
            "which makes the current trajectory more persistent.",
            "Watch the next few short-term snapshots to see whether the move continues or "
            "starts giving back the recent change.",
        )

    if has_broader_comparison:
        return (
            "The short-term move continues the same direction as the broader 24-hour trend, "
            "giving the event broader-trend context.",
            "Watch the next short-term snapshots for continuation in the broader-trend "
            "direction or a quick reversal.",
        )

    if window_change is None:
        if change_24h is not None:
            return (
                "The 24-hour market direction is the available verified context; no "
                "analysed-window move is confirmed.",
                "Watch the next short-term snapshots for confirmation or reversal.",
            )
        if _decimal_market_value(market_data.get("chg_since_msg_percent")) is not None:
            return (
                "A move since the previous alert is available, but no analysed-window "
                "trajectory is confirmed.",
                "Watch the next short-term snapshots for confirmation or reversal.",
            )
        return (
            "Only the current market observation is available; no analysed-window trajectory "
            "is confirmed.",
            "Watch the next short-term snapshots for confirmation or reversal.",
        )

    return (
        "The analysed-window price move is the only confirmed signal in the supplied market "
        "data.",
        "Watch the next short-term snapshots for continuation or a quick reversal of the "
        "current move.",
    )


def _has_persistent_snapshot_direction(step_changes: list[Decimal]) -> bool:
    return len(step_changes) >= 2 and all(
        change != 0 and (change > 0) == (step_changes[0] > 0) for change in step_changes
    )


def _snapshot_step_changes(market_data: dict) -> list[Decimal]:
    snapshots = market_data.get("snapshots")
    if not isinstance(snapshots, list):
        return []
    ordered: list[tuple[Decimal, Decimal]] = []
    for snapshot in snapshots:
        if not isinstance(snapshot, dict):
            continue
        minute = _decimal_market_value(snapshot.get("m"))
        price = _decimal_market_value(snapshot.get("p", snapshot.get("price_usd")))
        if minute is None or price is None or price == 0:
            continue
        ordered.append((minute, price))
    # Compact snapshots use signed minutes relative to timestamp_utc: historical observations
    # are negative, so ascending order is chronological (oldest to newest).
    ordered.sort(key=lambda item: item[0])
    return [
        (current - previous) / previous
        for (_, previous), (_, current) in zip(ordered, ordered[1:], strict=False)
        if previous != 0
    ]


def _decimal_market_value(value: object) -> Decimal | None:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return parsed if parsed.is_finite() else None


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


def compact_event_alert_possible_action(value: str, *, fallback: str | None = None) -> str:
    """Keep Event Alert actions short, conditional, and non-prescriptive."""
    cleaned = " ".join(str(value or "").split()).strip()
    if (
        len(cleaned.split()) > 20
        or len(re.findall(r"[.!?]", cleaned)) > 1
        or not _CONDITIONAL_ACTION_RE.search(cleaned)
        or re.search(r"(?i)\b(?:risk plan|risk controls?|exposure|impulsive)\b", cleaned)
    ):
        return fallback or "Watch the next short-term snapshots for confirmation or reversal."
    return cleaned


def is_news_centered_event_action(value: str) -> bool:
    """Keep monitoring copy focused on market evidence, not supporting headlines."""
    return (
        re.search(
            r"(?i)\b(?:news|headline|article|story)\b|"
            r"\b(?:selected|related|current)\s+(?:context|news|headline|article|story)\b",
            str(value or ""),
        )
        is not None
    )


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
