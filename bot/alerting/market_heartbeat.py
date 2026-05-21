from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from bot.domain.supported_coins import normalize_symbol

MARKET_HEARTBEAT_TYPE = "market_heartbeat"
MARKET_HEARTBEAT_ANALYSIS_TYPE = "market_heartbeat"
ALLOWED_HEARTBEAT_CONFIDENCE = {"low", "medium", "high"}
HEARTBEAT_RESULT_FIELDS = {
    "symbol",
    "title",
    "message_body",
    "related_news_ids",
    "possible_action",
    "confidence",
}
DIRECT_ADVICE_RE = re.compile(
    r"(?i)\b(buy|sell|liquidate|short|long|move all|all money|all funds)\b"
)
HEARTBEAT_ADVICE_RE = re.compile(
    r"(?i)\b("
    r"review(?:ing)?\s+(?:your\s+)?(?:investment\s+)?portfolio|"
    r"adjust(?:ing)?\s+(?:your\s+)?portfolio|"
    r"rebalance|"
    r"investment\s+strategy|"
    r"financial\s+goals?|"
    r"risk\s+tolerance|"
    r"good\s+time\s+to\s+review|"
    r"consider\s+adjust(?:ing|ments?)?|"
    r"(?:any\s+)?adjustments?\s+(?:are|is)\s+needed|"
    r"holdings?|"
    r"exposure|"
    r"allocation|"
    r"portfolio|"
    r"investment\s+portfolio|"
    r"investment\s+plan|"
    r"investment\s+approach"
    r")\b"
)
SAFE_NEUTRAL_HEARTBEAT_ACTION = (
    "No immediate action is suggested by this heartbeat. Continue monitoring if this coin "
    "is on your watchlist."
)


class MarketHeartbeatValidationError(ValueError):
    """Raised when LLM heartbeat JSON cannot be trusted."""


@dataclass(frozen=True)
class MarketHeartbeatDecision:
    symbol: str
    title: str
    message_body: str
    related_news_ids: list[str]
    possible_action: str
    confidence: str


def validate_market_heartbeat_output(
    result: dict[str, Any],
    *,
    expected_symbol: str,
    candidate_news_ids: set[str],
) -> MarketHeartbeatDecision:
    extra_fields = set(result) - HEARTBEAT_RESULT_FIELDS
    missing_fields = HEARTBEAT_RESULT_FIELDS - set(result)
    if extra_fields:
        raise MarketHeartbeatValidationError(f"unexpected fields: {sorted(extra_fields)}")
    if missing_fields:
        raise MarketHeartbeatValidationError(f"missing fields: {sorted(missing_fields)}")

    symbol = str(result["symbol"]).strip().upper()
    if symbol != normalize_symbol(expected_symbol).upper():
        raise MarketHeartbeatValidationError("symbol mismatch")

    title = _required_text(result["title"], "title")
    message_body = _required_text(result["message_body"], "message_body")
    possible_action = _required_text(result["possible_action"], "possible_action")
    confidence = str(result["confidence"]).strip().lower()
    if confidence not in ALLOWED_HEARTBEAT_CONFIDENCE:
        raise MarketHeartbeatValidationError("invalid confidence")
    _reject_heartbeat_advice(message_body, "message_body")
    _reject_heartbeat_advice(possible_action, "possible_action")

    related_news_ids = result["related_news_ids"]
    if not isinstance(related_news_ids, list) or not all(
        isinstance(item, str) for item in related_news_ids
    ):
        raise MarketHeartbeatValidationError("related_news_ids must be a string array")
    if len(set(related_news_ids)) != len(related_news_ids):
        raise MarketHeartbeatValidationError("related_news_ids contains duplicates")
    unknown_ids = set(related_news_ids) - candidate_news_ids
    if unknown_ids:
        raise MarketHeartbeatValidationError(f"unknown related_news_ids: {sorted(unknown_ids)}")

    return MarketHeartbeatDecision(
        symbol=symbol,
        title=title,
        message_body=message_body,
        related_news_ids=related_news_ids,
        possible_action=possible_action,
        confidence=confidence,
    )


def _required_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise MarketHeartbeatValidationError(f"{field_name} must be text")
    stripped = " ".join(value.split()).strip()
    if not stripped:
        raise MarketHeartbeatValidationError(f"{field_name} is required")
    return stripped


def _reject_heartbeat_advice(value: str, field_name: str) -> None:
    if DIRECT_ADVICE_RE.search(value):
        raise MarketHeartbeatValidationError(f"{field_name} contains direct financial advice")
    if HEARTBEAT_ADVICE_RE.search(value):
        raise MarketHeartbeatValidationError(
            f"{field_name} contains portfolio or investment advice"
        )


def sanitize_heartbeat_possible_action(value: str | None) -> str:
    text = " ".join(str(value or "").split()).strip()
    if not text or DIRECT_ADVICE_RE.search(text) or HEARTBEAT_ADVICE_RE.search(text):
        return SAFE_NEUTRAL_HEARTBEAT_ACTION
    return text


def sanitize_heartbeat_message_body(value: str | None, fallback: str) -> str:
    text = " ".join(str(value or "").split()).strip()
    if not text:
        return fallback
    safe_sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text)
        if sentence.strip()
        and not DIRECT_ADVICE_RE.search(sentence)
        and not HEARTBEAT_ADVICE_RE.search(sentence)
    ]
    return " ".join(safe_sentences).strip() or fallback
