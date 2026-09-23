from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Any

from bot.domain.supported_coins import normalize_symbol

logger = logging.getLogger(__name__)

EVENT_ALERT_TYPE = "event_alert"
EVENT_ANALYSIS_TYPE = "event_analysis"
EVENT_ANALYSIS_SUCCESS_STATUSES = {"success", "no_alert"}
EVENT_ANALYSIS_FAILURE_STATUSES = {"invalid_json", "llm_error", "schema_error"}
ALLOWED_URGENCY = {"low", "normal", "high"}
ALLOWED_CONFIDENCE = {"low", "medium", "high"}
EVENT_RESULT_FIELDS = {
    "symbol",
    "should_alert",
    "event_key",
    "title",
    "message_body",
    "related_news_ids",
    "possible_action",
    "urgency",
    "confidence",
    "reason_for_no_alert",
}
FORBIDDEN_USER_ALERT_TYPES = {
    "important_alert",
    "critical_alert",
    "market_update",
    "strong_signal",
    "market_heartbeat",
    "buy_signal",
    "sell_signal",
}

_PERCENT_CLAIM_RE = re.compile(
    r"(?P<value>[+-]?\s*\d+(?:\.\d+)?)\s*(?:%|percent(?:age)?(?:\s+points?)?\b)",
    re.IGNORECASE,
)
_DURATION_RE = re.compile(
    r"\b(?P<value>\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|twenty[- ]four)\s*[- ]?\s*(?P<unit>hours?|hrs?|hr|h|minutes?|mins?|min|m)\b",
    re.IGNORECASE,
)
_SINCE_PREVIOUS_ALERT_RE = re.compile(
    r"\bsince\s+(?:the\s+)?(?:previous|last)\s+(?:alert|message)\b", re.IGNORECASE
)
_TRAJECTORY_MARKER_RE = re.compile(
    r"\b(?:consistent(?:ly)?|persistent(?:ly)?|persisted|throughout|across)\b",
    re.IGNORECASE,
)
_MOVEMENT_DIRECTION_RE = re.compile(
    r"\b(?:declin\w*|fell|fall\w*|slipp\w*|dip\w*|down\w*|drop\w*|lower\w*|rose|ris\w*|rall\w*|gain\w*|up\w*|climb\w*)\b",
    re.IGNORECASE,
)
_DOWNWARD_CLAIM_RE = re.compile(
    r"\b(?:down|fell|fall\w*|slipp\w*|dip\w*|drop\w*|declin\w*|lower\w*)\b", re.I
)
_UPWARD_CLAIM_RE = re.compile(
    r"\b(?:up|rose|ris\w*|rall\w*|gain\w*|higher\w*|climb\w*)\b", re.I
)
_CLAUSE_BOUNDARY_RE = re.compile(r"(?<!\d)[.!?;,]|\n")
_FUTURE_CONDITIONAL_RE = re.compile(
    r"\b(?:if|when|unless)\b.*\b(?:next|upcoming|future)\b", re.IGNORECASE
)
_NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "twenty-four": 24,
    "twenty four": 24,
}


class EventAnalysisValidationError(ValueError):
    """Raised when LLM event-analysis JSON cannot be trusted."""


@dataclass(frozen=True)
class EventAnalysisDecision:
    symbol: str
    should_alert: bool
    event_key: str | None
    title: str | None
    message_body: str | None
    related_news_ids: list[str]
    possible_action: str | None
    urgency: str | None
    confidence: str | None
    reason_for_no_alert: str | None


_DATE_SUFFIX_RE = re.compile(r"(?:_?\d{4}[_-]\d{2}[_-]\d{2}|_?\d{8})$")
_REPEATED_UNDERSCORE_RE = re.compile(r"_+")
_RANDOM_TOKEN_RE = re.compile(r"^[0-9a-f]{16,}$")
_UUID_LIKE_RE = re.compile(
    r"^[0-9a-f]{8}[_-]?[0-9a-f]{4}[_-]?[0-9a-f]{4}[_-]?[0-9a-f]{4}[_-]?[0-9a-f]{12}$"
)
_NON_KEY_CHARS_RE = re.compile(r"[^a-z0-9_]+")
_SYMBOL_ALIASES = {
    "bitcoin": "btc",
    "ethereum": "eth",
    "solana": "sol",
    "ton": "gram",
    "toncoin": "gram",
}


@dataclass(frozen=True)
class CanonicalEventKey:
    raw_event_key: str | None
    canonical_event_key: str
    semantic_family: str | None
    reason: str


def canonicalize_event_key(
    symbol: str,
    raw_event_key: str | None,
    title: str | None = None,
    message_body: str | None = None,
    related_news: list[dict[str, Any]] | None = None,
) -> CanonicalEventKey:
    """Return a stable backend key for semantic event identity."""
    normalized_symbol = normalize_symbol(symbol)
    raw = " ".join(str(raw_event_key or "").split()).strip()
    canonical = _normalize_event_key_text(raw)
    reason = "normalized"
    if canonical:
        canonical = _replace_symbol_aliases(canonical)
        canonical = canonical.replace("nadaq", "nasdaq")
        canonical = _strip_date_suffix(canonical)
        canonical = _collapse_event_key(canonical)
    semantic_family = normalize_event_semantic_family(
        normalized_symbol,
        canonical or raw,
        title=title,
        message_body=message_body,
        related_news=related_news,
    )
    if not canonical:
        return CanonicalEventKey(
            raw or None,
            _semantic_event_key(normalized_symbol, semantic_family)
            or _fallback_event_key(normalized_symbol, title, message_body),
            semantic_family,
            "fallback_empty",
        )
    if _is_random_event_key(normalized_symbol, canonical):
        return CanonicalEventKey(
            raw or None,
            _semantic_event_key(normalized_symbol, semantic_family)
            or _fallback_event_key(normalized_symbol, title, message_body),
            semantic_family,
            "fallback_random",
        )
    if semantic_family:
        semantic_event_key = _semantic_event_key(normalized_symbol, semantic_family)
        return CanonicalEventKey(
            raw or None,
            semantic_event_key,
            semantic_family,
            "semantic_family",
        )
    if canonical == raw:
        reason = "unchanged"
    return CanonicalEventKey(raw or None, canonical, None, reason)


def normalize_event_semantic_family(
    symbol: str,
    raw_event_key: str | None,
    *,
    title: str | None = None,
    message_body: str | None = None,
    related_news: list[dict[str, Any]] | None = None,
    _allow_price_direction: bool = True,
) -> str | None:
    """Map core event wording to a stable family, using material news only as fallback."""
    normalized_symbol = normalize_symbol(symbol)
    parts = [
        _normalize_event_key_text(str(raw_event_key or "")),
        _normalize_event_key_text(str(title or "")),
        _normalize_event_key_text(str(message_body or "")),
    ]
    text = _replace_symbol_aliases(
        _collapse_event_key("_".join(part for part in parts if part))
    )
    tokens = {
        token for token in text.split("_") if token and token != normalized_symbol
    }
    phrases = f"_{text}_"

    # Event Analysis is market-event-first. A clear price direction in its own key/title/body
    # is the identity even when the explanation mentions supporting derivatives, ETF, or
    # regulatory context. Those terms describe context, not a replacement event family.
    if _allow_price_direction and _contains_price_downtrend_signal(phrases, tokens):
        return "price_downtrend"
    if _allow_price_direction and _contains_price_uptrend_signal(phrases, tokens):
        return "price_uptrend"

    if normalized_symbol == "btc" and (
        tokens.intersection(
            {
                "quantum",
                "security",
                "cryptography",
                "encryption",
                "protocol",
                "vulnerability",
                "vulnerabilities",
                "exploit",
                "exploits",
                "attack",
                "attacks",
                "threat",
                "threats",
            }
        )
        and tokens.intersection(
            {
                "quantum",
                "security",
                "cryptography",
                "encryption",
                "vulnerability",
                "vulnerabilities",
                "exploit",
                "exploits",
                "attack",
                "attacks",
                "threat",
                "threats",
                "risk",
                "risks",
            }
        )
    ):
        return "protocol_security_risk"

    if _contains_any_phrase(
        phrases,
        {"etf_flow", "etf_flows", "fund_flow", "fund_flows", "inflow", "outflow"},
    ) or tokens.intersection({"etf", "inflow", "inflows", "outflow", "outflows"}):
        return "etf_flows"

    if tokens.intersection({"liquidation", "liquidations", "leverage", "deleveraging"}):
        return "liquidations"

    if tokens.intersection({"regulation", "regulatory", "sec", "policy", "lawsuit"}):
        return "regulatory"

    if tokens.intersection(
        {"option", "options", "derivative", "derivatives", "futures"}
    ):
        return "derivatives_positioning"

    if _contains_any_phrase(phrases, {"hash_rate", "hashrate"}) or tokens.intersection(
        {"mining", "miner", "miners", "hashrate", "difficulty"}
    ):
        return "network_mining"

    if _contains_price_downtrend_signal(phrases, tokens):
        return "price_downtrend"

    if _contains_price_uptrend_signal(phrases, tokens):
        return "price_uptrend"

    if _contains_any_phrase(
        phrases,
        {
            "key_level",
            "price_level",
            "near_level",
            "near_key_level",
            "support_resistance",
            "support_level",
            "resistance_level",
            "holds_near",
            "hold_near",
            "price_holds",
            "price_hold",
            "stays_around",
            "stays_near",
            "volatility_around",
            "around_level",
        },
    ) or (
        tokens.intersection(
            {
                "near",
                "around",
                "hovering",
                "holds",
                "hold",
                "stays",
                "range",
                "rangebound",
                "sideways",
                "consolidation",
                "support",
                "resistance",
                "level",
                "levels",
            }
        )
        and tokens.intersection(
            {
                "price",
                "market",
                "volatility",
                "support",
                "resistance",
                "level",
                "levels",
            }
        )
    ):
        return "price_level_range"

    if _contains_any_phrase(
        phrases,
        {
            "price_drop",
            "price_decline",
            "price_down",
            "price_pressure",
            "market_drop",
            "selloff",
            "sell_off",
            "downward_pressure",
            "downside_pressure",
            "break_below",
            "breaks_below",
            "price_test_low",
            "price_test_february_low",
            "test_low",
            "price_movement_lower",
            "market_movement_lower",
        },
    ) or tokens.intersection(
        {
            "decline",
            "declines",
            "declined",
            "declining",
            "drop",
            "drops",
            "dropped",
            "dropping",
            "fall",
            "falls",
            "falling",
            "fell",
            "selloff",
            "sell",
            "lower",
            "downward",
            "downside",
            "slump",
            "weak",
            "weakened",
            "weakening",
            "bearish",
        }
    ):
        return "price_downtrend"

    if _contains_any_phrase(
        phrases,
        {
            "price_rally",
            "market_rally",
            "price_rebound",
            "price_breakout",
            "break_above",
            "breaks_above",
            "upward_pressure",
            "upside_pressure",
        },
    ) or tokens.intersection(
        {
            "rally",
            "rallies",
            "rise",
            "rises",
            "rose",
            "rebound",
            "rebounds",
            "surge",
            "surges",
            "up",
            "breakout",
            "higher",
            "upward",
            "upside",
            "strength",
            "strengthening",
            "bullish",
        }
    ):
        return "price_uptrend"

    if tokens.intersection({"volatility", "volatile", "choppy", "whipsaw"}):
        return "volatility"

    if tokens.intersection({"news", "headline", "headlines", "catalyst"}):
        return "news_catalyst"

    return _semantic_family_from_material_related_news(normalized_symbol, related_news)


def _semantic_family_from_material_related_news(
    symbol: str,
    related_news: list[dict[str, Any]] | None,
) -> str | None:
    """Use selected material news only when core event evidence was ambiguous."""
    parts: list[str] = []
    for item in related_news or []:
        if not isinstance(item, dict) or item.get("material") is not True:
            continue
        parts.extend(
            str(item.get(field) or "") for field in ("title", "source", "url", "link")
        )
    if not any(part.strip() for part in parts):
        return None
    # This recursive call has no related news, so it classifies only the fallback evidence.
    return normalize_event_semantic_family(
        symbol,
        " ".join(parts),
        _allow_price_direction=False,
    )


def _semantic_event_key(symbol: str, semantic_family: str | None) -> str | None:
    if not semantic_family:
        return None
    return f"{normalize_symbol(symbol)}_{semantic_family}"


def _contains_any_phrase(text: str, phrases: set[str]) -> bool:
    return any(f"_{phrase}_" in text for phrase in phrases)


def _contains_price_downtrend_signal(phrases: str, tokens: set[str]) -> bool:
    if _contains_any_phrase(
        phrases,
        {
            "price_drop",
            "price_decline",
            "price_down",
            "market_drop",
            "break_below",
            "breaks_below",
            "downward_pressure",
            "downside_pressure",
        },
    ):
        return True
    if tokens.intersection(
        {
            "drop",
            "drops",
            "fall",
            "falls",
            "selloff",
            "lower",
            "downward",
            "downside",
        }
    ):
        return True
    return "breakdown" in tokens and not tokens.intersection({"without", "no", "not"})


def _contains_price_uptrend_signal(phrases: str, tokens: set[str]) -> bool:
    if _contains_any_phrase(
        phrases,
        {
            "price_rally",
            "market_rally",
            "price_rebound",
            "price_breakout",
            "break_above",
            "breaks_above",
            "upward_pressure",
            "upside_pressure",
        },
    ):
        return True
    if tokens.intersection(
        {
            "rally",
            "rallies",
            "rise",
            "rises",
            "rose",
            "surge",
            "surges",
            "up",
            "higher",
            "upward",
            "upside",
        }
    ):
        return True
    return "breakout" in tokens and not tokens.intersection({"without", "no", "not"})


def with_canonical_event_key(
    decision: EventAnalysisDecision,
    *,
    related_news: list[dict[str, Any]] | None = None,
) -> tuple[EventAnalysisDecision, CanonicalEventKey]:
    canonical = canonicalize_event_key(
        decision.symbol,
        decision.event_key,
        title=decision.title,
        message_body=decision.message_body,
        related_news=related_news,
    )
    if decision.event_key == canonical.canonical_event_key:
        return decision, canonical
    return (
        EventAnalysisDecision(
            symbol=decision.symbol,
            should_alert=decision.should_alert,
            event_key=canonical.canonical_event_key,
            title=decision.title,
            message_body=decision.message_body,
            related_news_ids=decision.related_news_ids,
            possible_action=decision.possible_action,
            urgency=decision.urgency,
            confidence=decision.confidence,
            reason_for_no_alert=decision.reason_for_no_alert,
        ),
        canonical,
    )


def _normalize_event_key_text(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_")
    normalized = re.sub(r"\s+", "_", normalized)
    normalized = _NON_KEY_CHARS_RE.sub("_", normalized)
    return _collapse_event_key(normalized)


def _collapse_event_key(value: str) -> str:
    return _REPEATED_UNDERSCORE_RE.sub("_", value).strip("_")


def _replace_symbol_aliases(value: str) -> str:
    parts = value.split("_")
    return "_".join(_SYMBOL_ALIASES.get(part, part) for part in parts)


def _strip_date_suffix(value: str) -> str:
    return _collapse_event_key(_DATE_SUFFIX_RE.sub("", value))


def _is_random_event_key(symbol: str, value: str) -> bool:
    parts = value.split("_")
    last = parts[-1] if parts else ""
    if _UUID_LIKE_RE.match(last) or _RANDOM_TOKEN_RE.match(last):
        return True
    if len(parts) >= 4 and parts[0] == "event" and parts[1] == "analysis":
        if parts[2] in {normalize_symbol(symbol), "btc", "eth", "sol", "gram"}:
            return True
    return False


def _fallback_event_key(
    symbol: str, title: str | None, message_body: str | None
) -> str:
    text = _normalize_event_key_text(
        " ".join(part for part in (title, message_body) if part)
    )
    if text:
        words = [part for part in text.split("_") if part and part != symbol][:8]
        if words:
            return _collapse_event_key(f"{symbol}_{'_'.join(words)}")[:120]
    digest = sha256(f"{symbol}|{title or ''}|{message_body or ''}".encode()).hexdigest()
    return f"{symbol}_event_{digest[:16]}"


def validate_event_analysis_output(
    result: dict[str, Any],
    *,
    expected_symbol: str,
    candidate_news_ids: set[str],
    market_data: dict[str, Any] | None = None,
    last_msg: dict[str, Any] | None = None,
    timestamp_utc: object | None = None,
) -> EventAnalysisDecision:
    """Validate the single event-analysis schema accepted from the LLM."""
    extra_fields = set(result) - EVENT_RESULT_FIELDS
    missing_fields = EVENT_RESULT_FIELDS - set(result)
    if extra_fields:
        # Tolerance is additive only: unknown fields (e.g. an extra display_symbol) are
        # dropped instead of rejecting the whole analysis. Field names only — never values,
        # truncated because the names themselves come from LLM output.
        logger.debug(
            "event_analysis_unknown_fields_stripped fields=%s",
            sorted(str(name)[:40] for name in extra_fields),
        )
        result = {
            key: value for key, value in result.items() if key in EVENT_RESULT_FIELDS
        }
    if missing_fields:
        raise EventAnalysisValidationError(f"missing fields: {sorted(missing_fields)}")

    symbol = str(result["symbol"]).strip().upper()
    normalized_symbol = normalize_symbol(symbol)
    if normalized_symbol != normalize_symbol(expected_symbol):
        raise EventAnalysisValidationError("symbol mismatch")

    should_alert = result["should_alert"]
    if not isinstance(should_alert, bool):
        raise EventAnalysisValidationError("should_alert must be boolean")

    if should_alert:
        urgency = _required_choice(result["urgency"], ALLOWED_URGENCY, "urgency")
        confidence = _required_choice(
            result["confidence"], ALLOWED_CONFIDENCE, "confidence"
        )
        related_news_ids = _validate_alert_related_news_ids(
            result["related_news_ids"],
            candidate_news_ids=candidate_news_ids,
        )
        event_key = _optional_str(result["event_key"])
        title = _optional_str(result["title"])
        message_body = _optional_str(result["message_body"])
        possible_action = _optional_str(result["possible_action"])
        reason_for_no_alert = _optional_str(result["reason_for_no_alert"])

        joined_values = " ".join(
            value
            for value in (event_key, title, message_body, possible_action)
            if value
        ).lower()
        if any(forbidden in joined_values for forbidden in FORBIDDEN_USER_ALERT_TYPES):
            raise EventAnalysisValidationError("legacy alert type returned by LLM")
        if not title or not message_body or not possible_action:
            raise EventAnalysisValidationError(
                "alert fields are required for should_alert=true"
            )
        if reason_for_no_alert is not None:
            raise EventAnalysisValidationError(
                "reason_for_no_alert must be null for alerts"
            )
        if market_data is not None:
            _validate_positive_market_claims(
                title=title,
                message_body=message_body,
                possible_action=possible_action,
                market_data=market_data,
                last_msg=last_msg,
                timestamp_utc=timestamp_utc,
            )
    else:
        urgency = _required_null(result["urgency"], "urgency")
        confidence = (
            None
            if result["confidence"] is None
            else _required_choice(
                result["confidence"], ALLOWED_CONFIDENCE, "confidence"
            )
        )
        related_news_ids = _validate_no_alert_related_news_ids(
            result["related_news_ids"]
        )
        event_key = _required_null(result["event_key"], "event_key")
        title = _required_null(result["title"], "title")
        message_body = _required_null(result["message_body"], "message_body")
        possible_action = _required_null(result["possible_action"], "possible_action")
        reason_for_no_alert = _optional_str(result["reason_for_no_alert"])
        if not reason_for_no_alert:
            raise EventAnalysisValidationError(
                "reason_for_no_alert is required for no-alert result"
            )

    return EventAnalysisDecision(
        symbol=normalized_symbol.upper(),
        should_alert=should_alert,
        event_key=event_key,
        title=title,
        message_body=message_body,
        related_news_ids=related_news_ids,
        possible_action=possible_action,
        urgency=urgency,
        confidence=confidence,
        reason_for_no_alert=reason_for_no_alert,
    )


def _validate_positive_market_claims(
    *,
    title: str,
    message_body: str,
    possible_action: str,
    market_data: dict[str, Any],
    last_msg: dict[str, Any] | None,
    timestamp_utc: object | None,
) -> None:
    """Reject factual market claims that cannot be sourced to their stated period.

    This deliberately validates attribution and availability only.  It has no materiality
    threshold and does not decide whether a grounded movement merits an Event Alert.
    """
    text = f"{title}\n{message_body}"
    snapshot_count = sum(
        1 for item in market_data.get("snapshots", []) if isinstance(item, dict)
    )
    if (
        snapshot_count < 2
        and _TRAJECTORY_MARKER_RE.search(text)
        and _MOVEMENT_DIRECTION_RE.search(text)
    ):
        raise EventAnalysisValidationError("analysed-window trajectory is unsupported")
    if (
        _TRAJECTORY_MARKER_RE.search(text)
        and _MOVEMENT_DIRECTION_RE.search(text)
        and not (_supported_snapshot_trajectory(text, market_data))
    ):
        raise EventAnalysisValidationError("analysed-window trajectory is unsupported")
    _validate_unquantified_time_window_claims(
        text, market_data=market_data, last_msg=last_msg, timestamp_utc=timestamp_utc
    )

    values = {
        "window": _decimal_market_value(market_data.get("chg_window_percent")),
        "24h": _decimal_market_value(market_data.get("chg24h_percent")),
        "since": _decimal_market_value(market_data.get("chg_since_msg_percent")),
    }
    for match in _PERCENT_CLAIM_RE.finditer(text):
        context, claim_index = _claim_clause(text, match.start(), match.end())
        source = _market_claim_source(
            context, claim_index, market_data, last_msg, timestamp_utc
        )
        claimed = _claimed_percent(match.group("value"), context, claim_index)
        if source is not None:
            source_value = values[source]
            if source_value is None:
                raise EventAnalysisValidationError(
                    f"{source} market claim is unavailable"
                )
            if not _percent_values_match(claimed, source_value):
                raise EventAnalysisValidationError(
                    f"{source} market claim does not match input"
                )
            continue
        # A percentage without an explicit period is still a factual market assertion. It may
        # match any supplied fact, but matching magnitude alone never permits a mismatched
        # period because period-labelled claims took the branch above.
        if not any(
            value is not None and _percent_values_match(claimed, value)
            for value in values.values()
        ):
            raise EventAnalysisValidationError(
                "market percentage claim does not match input"
            )
    _validate_action_market_claims(
        possible_action,
        market_data=market_data,
        last_msg=last_msg,
        timestamp_utc=timestamp_utc,
    )


def _market_claim_source(
    context: str,
    claim_index: int,
    market_data: dict[str, Any],
    last_msg: dict[str, Any] | None,
    timestamp_utc: object | None,
) -> str | None:
    duration_matches = list(_DURATION_RE.finditer(context))
    candidates: list[tuple[int, str, re.Match[str], re.Match[str] | None]] = []
    linked_duration_starts: set[int] = set()
    for since_match in _SINCE_PREVIOUS_ALERT_RE.finditer(context):
        linked_duration = next(
            (
                duration
                for duration in duration_matches
                if since_match.start() <= duration.start() <= since_match.end() + 50
                and _PERCENT_CLAIM_RE.search(
                    context, since_match.end(), duration.start()
                )
                is None
            ),
            None,
        )
        if linked_duration is not None:
            linked_duration_starts.add(linked_duration.start())
        candidates.append((since_match.start(), "since", since_match, linked_duration))
    for duration_match in duration_matches:
        if duration_match.start() not in linked_duration_starts:
            candidates.append(
                (duration_match.start(), "duration", duration_match, None)
            )
    if not candidates:
        return None
    _, source_kind, source_match, linked_duration = min(
        candidates,
        # Bind the nearest label. In a tie, English market labels usually follow the percentage
        # ("down 3% over 24 hours"), while a prior label still supports "24-hour decline of 3%".
        key=lambda candidate: (
            abs(candidate[0] - claim_index),
            candidate[0] < claim_index,
        ),
    )
    if source_kind == "since":
        if not _has_last_message_context(last_msg):
            raise EventAnalysisValidationError(
                "since-previous-alert claim lacks prior alert context"
            )
        if linked_duration is not None:
            elapsed_minutes = _elapsed_minutes(last_msg.get("time"), timestamp_utc)
            if (
                elapsed_minutes is None
                or abs(_duration_minutes(linked_duration) - elapsed_minutes) > 5
            ):
                raise EventAnalysisValidationError(
                    "since-previous-alert duration does not match prior alert context"
                )
        return "since"
    duration_minutes = _duration_minutes(source_match)
    if duration_minutes == 24 * 60:
        return "24h"
    analysed_window = _integer_value(market_data.get("analysed_window_minutes"))
    if analysed_window is None or duration_minutes != analysed_window:
        raise EventAnalysisValidationError(
            "claimed analysed-window duration does not match input"
        )
    return "window"


def _duration_minutes_from_claim(context: str) -> int | None:
    match = _DURATION_RE.search(context)
    return _duration_minutes(match) if match is not None else None


def _duration_minutes(match: re.Match[str]) -> int:
    raw_value = match.group("value").lower()
    try:
        value = Decimal(raw_value)
    except InvalidOperation:
        value = Decimal(_NUMBER_WORDS.get(raw_value, 0))
    if value <= 0:
        return 0
    unit = match.group("unit").lower()
    return int(value * (60 if unit.startswith(("h", "hr")) else 1))


def _claim_clause(text: str, start: int, end: int) -> tuple[str, int]:
    clause_start = 0
    clause_end = len(text)
    for boundary in _CLAUSE_BOUNDARY_RE.finditer(text):
        if boundary.end() <= start:
            clause_start = boundary.end()
        elif boundary.start() >= end:
            clause_end = boundary.start()
            break
    return text[clause_start:clause_end], start - clause_start


def _validate_action_market_claims(
    possible_action: str,
    *,
    market_data: dict[str, Any],
    last_msg: dict[str, Any] | None,
    timestamp_utc: object | None,
) -> None:
    """Validate time-labelled facts in action copy without restricting action policy."""
    historical_action = " ".join(
        clause
        for clause in _text_clauses(possible_action)
        if not _FUTURE_CONDITIONAL_RE.search(clause)
    )
    if (
        _TRAJECTORY_MARKER_RE.search(historical_action)
        and _MOVEMENT_DIRECTION_RE.search(historical_action)
        and not _supported_snapshot_trajectory(possible_action, market_data)
    ):
        raise EventAnalysisValidationError("analysed-window trajectory is unsupported")
    _validate_unquantified_time_window_claims(
        possible_action,
        market_data=market_data,
        last_msg=last_msg,
        timestamp_utc=timestamp_utc,
    )
    for match in _PERCENT_CLAIM_RE.finditer(possible_action):
        context, claim_index = _claim_clause(
            possible_action, match.start(), match.end()
        )
        if _FUTURE_CONDITIONAL_RE.search(context):
            continue
        source = _market_claim_source(
            context, claim_index, market_data, last_msg, timestamp_utc
        )
        if source is None:
            continue
        supplied = _decimal_market_value(
            market_data.get(
                {
                    "window": "chg_window_percent",
                    "24h": "chg24h_percent",
                    "since": "chg_since_msg_percent",
                }[source]
            )
        )
        claimed = _claimed_percent(match.group("value"), context, claim_index)
        if supplied is None or not _percent_values_match(claimed, supplied):
            raise EventAnalysisValidationError(
                f"{source} market claim does not match input"
            )


def _validate_unquantified_time_window_claims(
    text: str,
    *,
    market_data: dict[str, Any],
    last_msg: dict[str, Any] | None,
    timestamp_utc: object | None,
) -> None:
    """Require a supplied metric for directional claims that name a period but no percent."""
    for clause in _text_clauses(text):
        if _FUTURE_CONDITIONAL_RE.search(clause):
            continue
        if not _MOVEMENT_DIRECTION_RE.search(clause):
            continue
        for duration in _DURATION_RE.finditer(clause):
            source = _market_claim_source(
                clause, duration.start(), market_data, last_msg, timestamp_utc
            )
            if source is None:
                continue
            field = {
                "window": "chg_window_percent",
                "24h": "chg24h_percent",
                "since": "chg_since_msg_percent",
            }[source]
            if _decimal_market_value(market_data.get(field)) is None:
                raise EventAnalysisValidationError(
                    f"{source} market claim is unavailable"
                )
            direction = _direction_for_claim(clause, duration.start())
            supplied = _decimal_market_value(market_data.get(field))
            if direction == "down" and supplied is not None and supplied >= 0:
                raise EventAnalysisValidationError(
                    f"{source} market claim direction does not match input"
                )
            if direction == "up" and supplied is not None and supplied <= 0:
                raise EventAnalysisValidationError(
                    f"{source} market claim direction does not match input"
                )


def _supported_snapshot_trajectory(text: str, market_data: dict[str, Any]) -> bool:
    observations: list[tuple[Decimal, Decimal]] = []
    for index, item in enumerate(market_data.get("snapshots", [])):
        if not isinstance(item, dict):
            continue
        price = _decimal_market_value(item.get("p", item.get("price_usd")))
        minute = _decimal_market_value(item.get("m", index))
        if price is not None and minute is not None:
            observations.append((minute, price))
    if len(observations) < 3:
        return False
    observations.sort(key=lambda observation: observation[0])
    moves = [
        current - previous
        for (_, previous), (_, current) in zip(
            observations, observations[1:], strict=False
        )
    ]
    if not moves or any(move == 0 for move in moves):
        return False
    if _DOWNWARD_CLAIM_RE.search(text):
        return all(move < 0 for move in moves)
    if _UPWARD_CLAIM_RE.search(text):
        return all(move > 0 for move in moves)
    return False


def _text_clauses(text: str) -> list[str]:
    clauses: list[str] = []
    start = 0
    for boundary in _CLAUSE_BOUNDARY_RE.finditer(text):
        clause = text[start : boundary.start()].strip()
        if clause:
            clauses.append(clause)
        start = boundary.end()
    trailing = text[start:].strip()
    if trailing:
        clauses.append(trailing)
    return clauses


def _claimed_percent(raw_value: str, context: str, claim_index: int) -> Decimal:
    value = _decimal_market_value(raw_value)
    if value is None:
        raise EventAnalysisValidationError("invalid market percentage claim")
    if not raw_value.lstrip().startswith(("+", "-")):
        if _direction_for_claim(context, claim_index) == "down":
            return -abs(value)
        if _direction_for_claim(context, claim_index) == "up":
            return abs(value)
    return value


def _direction_for_claim(context: str, claim_index: int) -> str | None:
    directions = [
        (match.start(), "down") for match in _DOWNWARD_CLAIM_RE.finditer(context)
    ] + [(match.start(), "up") for match in _UPWARD_CLAIM_RE.finditer(context)]
    if not directions:
        return None
    return min(directions, key=lambda direction: abs(direction[0] - claim_index))[1]


def _percent_values_match(claimed: Decimal, supplied: Decimal) -> bool:
    # Rounded display values (for example -3.258... -> -3.3%) are valid. This is a
    # representation tolerance, not a movement/significance threshold.
    precision = claimed.as_tuple().exponent
    rounding_tolerance = Decimal("0.5") * (Decimal(10) ** min(precision, 0))
    return (
        claimed.is_signed() == supplied.is_signed()
        and abs(abs(claimed) - abs(supplied)) <= rounding_tolerance
    )


def _decimal_market_value(value: Any) -> Decimal | None:
    try:
        parsed = Decimal(str(value).replace(" ", ""))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _integer_value(value: Any) -> int | None:
    parsed = _decimal_market_value(value)
    if parsed is None or parsed != parsed.to_integral_value() or parsed <= 0:
        return None
    return int(parsed)


def _has_last_message_context(last_msg: dict[str, Any] | None) -> bool:
    if not isinstance(last_msg, dict):
        return False
    return last_msg.get("time") is not None and last_msg.get("price") is not None


def _elapsed_minutes(previous: object, current: object) -> int | None:
    previous_at = _parse_utc_datetime(previous)
    current_at = _parse_utc_datetime(current)
    if previous_at is None or current_at is None:
        return None
    return max(0, int((current_at - previous_at).total_seconds() // 60))


def _parse_utc_datetime(value: object) -> datetime | None:
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


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise EventAnalysisValidationError(
            "nullable text fields must be strings or null"
        )
    stripped = " ".join(value.split()).strip()
    return stripped or None


def _required_choice(value: Any, allowed_values: set[str], field_name: str) -> str:
    normalized = str(value).strip().lower()
    if normalized not in allowed_values:
        raise EventAnalysisValidationError(f"invalid {field_name}")
    return normalized


def _validate_alert_related_news_ids(
    value: Any,
    *,
    candidate_news_ids: set[str],
) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise EventAnalysisValidationError("related_news_ids must be a string array")
    if len(set(value)) != len(value):
        raise EventAnalysisValidationError("related_news_ids contains duplicates")
    unknown_ids = {str(item) for item in value} - candidate_news_ids
    if unknown_ids:
        raise EventAnalysisValidationError("related_news_ids contains unknown news ids")
    return value


def _validate_no_alert_related_news_ids(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list) and not value:
        return []
    raise EventAnalysisValidationError(
        "related_news_ids must be null or empty for no-alert result"
    )


def _required_null(value: Any, field_name: str) -> None:
    if value is not None:
        raise EventAnalysisValidationError(
            f"{field_name} must be null for no-alert result"
        )
    return None
