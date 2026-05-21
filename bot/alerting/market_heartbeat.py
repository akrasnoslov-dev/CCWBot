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
HEARTBEAT_EXACT_PRICE_RE = re.compile(r"\$\s*\d+(?:,\d{3})*(?:\.\d+)?")
HEARTBEAT_EXACT_PERCENT_RE = re.compile(r"[+-]?\d+(?:\.\d+)?\s*%")
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
    message_body = sanitize_heartbeat_message_body(
        _required_text(result["message_body"], "message_body"),
        f"{symbol} is showing routine market movement without a major signal.",
    )
    possible_action = _required_text(result["possible_action"], "possible_action")
    confidence = str(result["confidence"]).strip().lower()
    if confidence not in ALLOWED_HEARTBEAT_CONFIDENCE:
        raise MarketHeartbeatValidationError("invalid confidence")

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


def sanitize_heartbeat_possible_action(value: str | None) -> str:
    text = " ".join(str(value or "").split()).strip()
    if not text:
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
        and not HEARTBEAT_EXACT_PRICE_RE.search(sentence)
        and not HEARTBEAT_EXACT_PERCENT_RE.search(sentence)
    ]
    return " ".join(safe_sentences).strip() or fallback
