from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from bot.domain.supported_coins import SUPPORTED_SYMBOLS, display_symbol, normalize_symbol

logger = logging.getLogger(__name__)

REPORT_TYPES = {"daily", "weekly"}
REPORT_RESULT_FIELDS = {
    "report_type",
    "title",
    "market_pulse",
    "dashboard",
    "coin_cards",
    "market_catalysts",
    "why_it_matters",
    "watch_next",
    "week_timeline",
    "themes",
    "next_week_focus",
}
_BANNED_ADVICE_PHRASES = (
    "buy now",
    "sell now",
    "short immediately",
    "go long",
)
_TRADE_TARGET_PATTERN = r"(btc|bitcoin|eth|ethereum|gram|ton|sol|solana|crypto)"
_BANNED_ADVICE_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (
        rf"\b(buy|sell|short|long)\s+{_TRADE_TARGET_PATTERN}\b",
        rf"\b{_TRADE_TARGET_PATTERN}\s+(buy|sell|short|long)\b",
        rf"\b(increase|decrease|add|reduce|exit|enter)\s+{_TRADE_TARGET_PATTERN}\s+(exposure|position)\b",
        rf"\b(increase|decrease|add|reduce|exit|enter)\s+(exposure|position)\s+(to|in)\s+{_TRADE_TARGET_PATTERN}\b",
        rf"\b(exit|enter)\s+{_TRADE_TARGET_PATTERN}\s+(trade|position)\b",
        r"\bgo\s+(long|short)\b",
    )
)
_RAW_DIAGNOSTIC_PATTERN = re.compile(
    r"(?i)(\b(data|debug|diagnostic|traceback|stack\s+trace)\s*:|"
    r"\b(move|change24h|change7d|threshold|interval|previous|current)\s*=|"
    r"```|^\s*[\[{])"
)
_REPORT_LIST_TEXT_FIELDS = ("period", "day", "label", "title", "summary", "event", "note", "text")
_REPORT_LIST_LABEL_FIELDS = ("period", "day", "label", "title")
_REPORT_LIST_DETAIL_FIELDS = ("event", "summary", "note", "text")


class MarketReportValidationError(ValueError):
    """Raised when LLM market-report JSON cannot be trusted."""


@dataclass(frozen=True)
class MarketReportDecision:
    report_type: str
    title: str
    market_pulse: str
    dashboard: list[str]
    coin_cards: list[dict[str, str]]
    market_catalysts: list[str]
    why_it_matters: str
    watch_next: str
    week_timeline: list[str]
    themes: list[str]
    next_week_focus: str


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
        # Tolerance is additive only: unknown top-level fields are dropped instead of
        # rejecting the whole report. Field names only — never values, truncated because
        # the names themselves come from LLM output.
        logger.debug(
            "market_report_unknown_fields_stripped fields=%s",
            sorted(str(name)[:40] for name in extra_fields),
        )
        result = {key: value for key, value in result.items() if key in REPORT_RESULT_FIELDS}
    if missing_fields:
        raise MarketReportValidationError(f"missing fields: {sorted(missing_fields)}")

    report_type = _required_text(result["report_type"], "report_type").lower()
    if report_type not in REPORT_TYPES or report_type != expected_report_type:
        raise MarketReportValidationError("report_type mismatch")

    title = _required_text(result["title"], "title")
    market_pulse = _required_text(result["market_pulse"], "market_pulse")
    dashboard = _validate_text_list(result["dashboard"], "dashboard")
    coin_cards = _validate_coin_cards(
        result["coin_cards"],
        active_symbols=active_symbols,
    )
    market_catalysts = _validate_text_list(
        result["market_catalysts"],
        "market_catalysts",
        allow_empty=True,
    )
    why_it_matters = _required_text(result["why_it_matters"], "why_it_matters")
    watch_next = _required_text(result["watch_next"], "watch_next")
    week_timeline = _validate_report_text_list(
        result["week_timeline"],
        "week_timeline",
        allow_empty=report_type == "daily",
    )
    themes = _validate_report_text_list(
        result["themes"],
        "themes",
        allow_empty=report_type == "daily",
    )
    next_week_focus = (
        _required_text(result["next_week_focus"], "next_week_focus")
        if report_type == "weekly"
        else _optional_text(result["next_week_focus"], "next_week_focus")
    )

    return MarketReportDecision(
        report_type=report_type,
        title=title,
        market_pulse=market_pulse,
        dashboard=dashboard,
        coin_cards=coin_cards,
        market_catalysts=market_catalysts,
        why_it_matters=why_it_matters,
        watch_next=watch_next,
        week_timeline=week_timeline,
        themes=themes,
        next_week_focus=next_week_focus,
    )


def _required_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise MarketReportValidationError(f"{field_name} must be text")
    stripped = value.strip()
    if not stripped:
        raise MarketReportValidationError(f"{field_name} must be non-empty")
    _reject_banned_advice(stripped)
    return stripped


def _optional_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise MarketReportValidationError(f"{field_name} must be text")
    stripped = value.strip()
    if stripped:
        _reject_banned_advice(stripped)
    return stripped


def _validate_text_list(
    value: Any,
    field_name: str,
    *,
    allow_empty: bool = False,
) -> list[str]:
    if not isinstance(value, list):
        raise MarketReportValidationError(f"{field_name} must be an array")
    if not value and not allow_empty:
        raise MarketReportValidationError(f"{field_name} must not be empty")

    items: list[str] = []
    for item in value:
        # Coerce occasional dict-shaped bullets (e.g. {"summary": "..."}) to plain
        # text instead of failing the whole report, matching the tolerance already
        # applied to week_timeline/themes below.
        text = _normalize_report_text_list_item(item, field_name)
        _reject_banned_advice(text)
        items.append(text)
    return items


def _validate_report_text_list(
    value: Any,
    field_name: str,
    *,
    allow_empty: bool = False,
) -> list[str]:
    if not isinstance(value, list):
        raise MarketReportValidationError(f"{field_name} must be an array")
    if not value and not allow_empty:
        raise MarketReportValidationError(f"{field_name} must not be empty")

    items: list[str] = []
    for item in value:
        text = _normalize_report_text_list_item(item, field_name)
        _reject_raw_diagnostics(text)
        _reject_banned_advice(text)
        items.append(text)
    return items


def _normalize_report_text_list_item(item: Any, field_name: str) -> str:
    if isinstance(item, str):
        text = item.strip()
    elif isinstance(item, dict):
        if any(isinstance(value, (dict, list, tuple, set)) for value in item.values()):
            raise MarketReportValidationError(f"{field_name} must be text")
        text = _format_report_text_dict(item)
    else:
        raise MarketReportValidationError(f"{field_name} must be text")

    if not text:
        raise MarketReportValidationError(f"{field_name} must be non-empty")
    return text


def _format_report_text_dict(item: dict[str, Any]) -> str:
    label = _first_text_field(item, _REPORT_LIST_LABEL_FIELDS)
    details = _unique_text_fields(item, _REPORT_LIST_DETAIL_FIELDS, skip=label)
    if label and details:
        return f"{label}: {' '.join(details)}"
    if label:
        return label
    return " ".join(_unique_text_fields(item, _REPORT_LIST_TEXT_FIELDS))


def _first_text_field(item: dict[str, Any], field_names: tuple[str, ...]) -> str:
    for field_name in field_names:
        value = item.get(field_name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _unique_text_fields(
    item: dict[str, Any],
    field_names: tuple[str, ...],
    *,
    skip: str = "",
) -> list[str]:
    values: list[str] = []
    seen = {skip.lower()} if skip else set()
    for field_name in field_names:
        value = item.get(field_name)
        if not isinstance(value, str):
            continue
        text = value.strip()
        if not text or text.lower() in seen:
            continue
        values.append(text)
        seen.add(text.lower())
    return values


def _validate_coin_cards(
    value: Any,
    *,
    active_symbols: tuple[str, ...],
) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise MarketReportValidationError("coin_cards must be an array")

    cards: list[dict[str, str]] = []
    seen_symbols: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            raise MarketReportValidationError("coin card must be an object")
        extra_fields = set(item) - {"symbol", "summary", "watch"}
        missing_fields = {"symbol", "summary", "watch"} - set(item)
        if extra_fields:
            # Same additive tolerance as the top level: drop unknown coin-card fields.
            logger.debug(
                "market_report_coin_card_unknown_fields_stripped fields=%s",
                sorted(str(name)[:40] for name in extra_fields),
            )
        if missing_fields:
            raise MarketReportValidationError(f"missing coin card fields: {sorted(missing_fields)}")
        symbol = _required_text(item.get("symbol"), "coin_cards.symbol").upper()
        normalized_symbol = normalize_symbol(symbol)
        if normalized_symbol not in active_symbols:
            raise MarketReportValidationError("coin card symbol is not active")
        if normalized_symbol in seen_symbols:
            raise MarketReportValidationError("coin card symbol is duplicated")
        seen_symbols.add(normalized_symbol)
        summary = _required_text(item.get("summary"), "coin_cards.summary")
        watch = _required_text(item.get("watch"), "coin_cards.watch")
        cards.append(
            {
                "symbol": display_symbol(normalized_symbol),
                "summary": summary,
                "watch": watch,
            }
        )

    if not cards:
        raise MarketReportValidationError("coin_cards must not be empty")
    missing_symbols = set(active_symbols) - seen_symbols
    extra_symbols = seen_symbols - set(active_symbols)
    if missing_symbols or extra_symbols:
        raise MarketReportValidationError("coin_cards must include each active symbol exactly once")
    return cards


def _reject_banned_advice(text: str) -> None:
    lowered = text.lower()
    if any(phrase in lowered for phrase in _BANNED_ADVICE_PHRASES) or any(
        pattern.search(lowered) for pattern in _BANNED_ADVICE_PATTERNS
    ):
        raise MarketReportValidationError("direct trading instruction is not allowed")


def _reject_raw_diagnostics(text: str) -> None:
    if _RAW_DIAGNOSTIC_PATTERN.search(text):
        raise MarketReportValidationError("raw diagnostic output is not allowed")
