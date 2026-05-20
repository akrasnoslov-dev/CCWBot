from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from bot.domain.supported_coins import normalize_symbol

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
DIRECT_ADVICE_RE = re.compile(
    r"(?i)\b(buy|sell|liquidate|short|long|move all|all money|all funds)\b"
)


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
    urgency: str
    confidence: str
    reason_for_no_alert: str | None


def validate_event_analysis_output(
    result: dict[str, Any],
    *,
    expected_symbol: str,
    candidate_news_ids: set[str],
) -> EventAnalysisDecision:
    """Validate the single event-analysis schema accepted from the LLM."""
    extra_fields = set(result) - EVENT_RESULT_FIELDS
    missing_fields = EVENT_RESULT_FIELDS - set(result)
    if extra_fields:
        raise EventAnalysisValidationError(f"unexpected fields: {sorted(extra_fields)}")
    if missing_fields:
        raise EventAnalysisValidationError(f"missing fields: {sorted(missing_fields)}")

    symbol = str(result["symbol"]).strip().upper()
    if symbol != normalize_symbol(expected_symbol).upper():
        raise EventAnalysisValidationError("symbol mismatch")

    should_alert = result["should_alert"]
    if not isinstance(should_alert, bool):
        raise EventAnalysisValidationError("should_alert must be boolean")

    urgency = str(result["urgency"]).strip().lower()
    confidence = str(result["confidence"]).strip().lower()
    if urgency not in ALLOWED_URGENCY:
        raise EventAnalysisValidationError("invalid urgency")
    if confidence not in ALLOWED_CONFIDENCE:
        raise EventAnalysisValidationError("invalid confidence")

    related_news_ids = result["related_news_ids"]
    if not isinstance(related_news_ids, list) or not all(
        isinstance(item, str) for item in related_news_ids
    ):
        raise EventAnalysisValidationError("related_news_ids must be a string array")
    if len(set(related_news_ids)) != len(related_news_ids):
        raise EventAnalysisValidationError("related_news_ids contains duplicates")
    unknown_ids = set(related_news_ids) - candidate_news_ids
    if unknown_ids:
        raise EventAnalysisValidationError(f"unknown related_news_ids: {sorted(unknown_ids)}")

    event_key = _optional_str(result["event_key"])
    title = _optional_str(result["title"])
    message_body = _optional_str(result["message_body"])
    possible_action = _optional_str(result["possible_action"])
    reason_for_no_alert = _optional_str(result["reason_for_no_alert"])

    joined_values = " ".join(
        value for value in (event_key, title, message_body, possible_action) if value
    ).lower()
    if any(forbidden in joined_values for forbidden in FORBIDDEN_USER_ALERT_TYPES):
        raise EventAnalysisValidationError("legacy alert type returned by LLM")
    if possible_action and DIRECT_ADVICE_RE.search(possible_action):
        raise EventAnalysisValidationError("possible_action contains direct financial advice")

    if should_alert:
        if not event_key:
            raise EventAnalysisValidationError("event_key is required for should_alert=true")
        if not title or not message_body or not possible_action:
            raise EventAnalysisValidationError("alert fields are required for should_alert=true")
        if reason_for_no_alert is not None:
            raise EventAnalysisValidationError("reason_for_no_alert must be null for alerts")
    else:
        if event_key is not None or title is not None or message_body is not None:
            raise EventAnalysisValidationError("alert fields must be null for no-alert result")
        if possible_action is not None:
            raise EventAnalysisValidationError("possible_action must be null for no-alert result")
        if not reason_for_no_alert:
            raise EventAnalysisValidationError(
                "reason_for_no_alert is required for no-alert result"
            )

    return EventAnalysisDecision(
        symbol=symbol,
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


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise EventAnalysisValidationError("nullable text fields must be strings or null")
    stripped = " ".join(value.split()).strip()
    return stripped or None
