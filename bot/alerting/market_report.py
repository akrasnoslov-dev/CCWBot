from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bot.domain.supported_coins import SUPPORTED_SYMBOLS, display_symbol, normalize_symbol

REPORT_TYPES = {"daily", "weekly"}
REPORT_RESULT_FIELDS = {
    "report_type",
    "title",
    "market_overview",
    "coin_summaries",
    "news_context",
    "possible_action",
    "telegram_message",
}
_NOT_FINANCIAL_ADVICE = "Not financial advice."


class MarketReportValidationError(ValueError):
    """Raised when LLM market-report JSON cannot be trusted."""


@dataclass(frozen=True)
class MarketReportDecision:
    report_type: str
    title: str
    market_overview: str
    coin_summaries: list[dict[str, str]]
    news_context: str
    possible_action: str
    telegram_message: str


def validate_market_report_output(
    result: dict[str, Any],
    *,
    expected_report_type: str,
    active_symbols: tuple[str, ...] = SUPPORTED_SYMBOLS,
) -> MarketReportDecision:
    if not isinstance(result, dict):
        raise MarketReportValidationError("report result must be an object")

    extra_fields = set(result) - REPORT_RESULT_FIELDS
    missing_fields = REPORT_RESULT_FIELDS - set(result)
    if extra_fields:
        raise MarketReportValidationError(f"unexpected fields: {sorted(extra_fields)}")
    if missing_fields:
        raise MarketReportValidationError(f"missing fields: {sorted(missing_fields)}")

    report_type = _required_text(result["report_type"], "report_type").lower()
    if report_type not in REPORT_TYPES or report_type != expected_report_type:
        raise MarketReportValidationError("report_type mismatch")

    title = _required_text(result["title"], "title")
    market_overview = _required_text(result["market_overview"], "market_overview")
    news_context = _required_text(result["news_context"], "news_context")
    possible_action = _required_text(result["possible_action"], "possible_action")
    telegram_message = _append_disclaimer_if_missing(
        _required_text(result["telegram_message"], "telegram_message")
    )

    coin_summaries = _validate_coin_summaries(
        result["coin_summaries"],
        active_symbols=active_symbols,
    )

    return MarketReportDecision(
        report_type=report_type,
        title=title,
        market_overview=market_overview,
        coin_summaries=coin_summaries,
        news_context=news_context,
        possible_action=possible_action,
        telegram_message=telegram_message,
    )


def _required_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise MarketReportValidationError(f"{field_name} must be text")
    stripped = value.strip()
    if not stripped:
        raise MarketReportValidationError(f"{field_name} must be non-empty")
    return stripped


def _append_disclaimer_if_missing(message: str) -> str:
    if _NOT_FINANCIAL_ADVICE in message:
        return message
    return f"{message.rstrip()}\n\n{_NOT_FINANCIAL_ADVICE}"


def _validate_coin_summaries(
    value: Any,
    *,
    active_symbols: tuple[str, ...],
) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise MarketReportValidationError("coin_summaries must be an array")

    allowed = {display_symbol(symbol) for symbol in active_symbols}
    summaries: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            raise MarketReportValidationError("coin summary must be an object")
        symbol = _required_text(item.get("symbol"), "coin_summaries.symbol").upper()
        if normalize_symbol(symbol) not in active_symbols or symbol not in allowed:
            raise MarketReportValidationError("coin summary symbol is not active")
        summary = _required_text(item.get("summary"), "coin_summaries.summary")
        summaries.append({"symbol": symbol, "summary": summary})

    if not summaries:
        raise MarketReportValidationError("coin_summaries must not be empty")
    return summaries
