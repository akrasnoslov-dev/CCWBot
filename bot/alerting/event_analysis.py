from __future__ import annotations

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

    if should_alert:
        urgency = _required_choice(result["urgency"], ALLOWED_URGENCY, "urgency")
        confidence = _required_choice(result["confidence"], ALLOWED_CONFIDENCE, "confidence")
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
            value for value in (event_key, title, message_body, possible_action) if value
        ).lower()
        if any(forbidden in joined_values for forbidden in FORBIDDEN_USER_ALERT_TYPES):
            raise EventAnalysisValidationError("legacy alert type returned by LLM")
        if not event_key:
            raise EventAnalysisValidationError("event_key is required for should_alert=true")
        if not title or not message_body or not possible_action:
            raise EventAnalysisValidationError("alert fields are required for should_alert=true")
        if reason_for_no_alert is not None:
            raise EventAnalysisValidationError("reason_for_no_alert must be null for alerts")
    else:
        urgency = _required_null(result["urgency"], "urgency")
        confidence = (
            None
            if result["confidence"] is None
            else _required_choice(result["confidence"], ALLOWED_CONFIDENCE, "confidence")
        )
        related_news_ids = _validate_no_alert_related_news_ids(result["related_news_ids"])
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
    return value


def _validate_no_alert_related_news_ids(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list) and not value:
        return []
    raise EventAnalysisValidationError("related_news_ids must be null or empty for no-alert result")


def _required_null(value: Any, field_name: str) -> None:
    if value is not None:
        raise EventAnalysisValidationError(f"{field_name} must be null for no-alert result")
    return None
