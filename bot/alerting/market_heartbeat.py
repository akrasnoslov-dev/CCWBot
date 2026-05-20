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
    if DIRECT_ADVICE_RE.search(possible_action):
        raise MarketHeartbeatValidationError("possible_action contains direct financial advice")

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
