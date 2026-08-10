"""Groq-backed AI helpers.

The bot asks for structured JSON so code can validate output before posting messages.
When parsing/validation fails, callers fall back to deterministic templates where callers allow it.
"""

import json
import logging
import os
import re
from html import escape

from dotenv import load_dotenv

from bot.domain.supported_coins import display_symbol as coin_display_symbol
from bot.news_titles import clean_news_title, clean_related_news_text
from bot.services.llm import config as llm_config
from bot.services.llm import get_router
from bot.services.llm.env import get_int_env

# Several names below are re-exports: they now live in bot.services.llm but remain importable
# from this module for backward compatibility. `import x as x` marks a re-export intentionally
# so the linter does not flag it as unused. AIGroqRateLimitError stays an alias of the
# provider-agnostic error type.
from bot.services.llm.errors import (
    AIGroqRateLimitError,
    AIInvalidJsonError,
)
from bot.services.llm.errors import (
    AIProviderRateLimitError as AIProviderRateLimitError,
)
from bot.services.llm.errors import (
    AISchemaValidationError as AISchemaValidationError,
)
from bot.services.llm.errors import (
    AllProvidersFailedError as AllProvidersFailedError,
)
from bot.services.llm.errors import (
    LLMRateLimitBackoffActive as LLMRateLimitBackoffActive,
)
from bot.services.llm.telemetry import (
    _llm_rate_limit_backoffs as _llm_rate_limit_backoffs,
)
from bot.services.llm.telemetry import (
    classify_ai_error_reason as classify_ai_error_reason,
)
from bot.services.llm.telemetry import (
    get_llm_rate_limit_backoff as get_llm_rate_limit_backoff,
)
from bot.services.llm.telemetry import (
    is_json_validation_error,
    is_rate_limit_error,
    safe_error_message,
    write_llm_usage_log,
)
from bot.services.llm.telemetry import (
    mark_llm_usage_log_status as mark_llm_usage_log_status,
)
from bot.services.llm.telemetry import (
    reset_llm_rate_limit_backoffs as reset_llm_rate_limit_backoffs,
)

load_dotenv()


def _get_int_env(name: str, default: int, minimum: int = 0) -> int:
    """Backward-compatible wrapper over the shared parser, which now warns on a bad value."""
    return get_int_env(name, default, minimum=minimum)


# Import-time snapshots kept for backward compatibility: several modules import these names
# directly. The live per-call values are resolved at call time via ``llm_config`` so an .env
# change takes effect on restart without any code path holding a stale value.
# "default" is not a real call type, so this resolves GROQ_MODEL — the generic Groq model.
GROQ_MODEL = llm_config.model_for("groq", "default")
GROQ_EVENT_ANALYSIS_MODEL = llm_config.model_for("groq", "event_analysis")
GROQ_EVENT_ANALYSIS_MAX_TOKENS = llm_config.max_tokens_for("event_analysis")
GROQ_MARKET_HEARTBEAT_MODEL = llm_config.model_for("groq", "market_heartbeat")
GROQ_REPORT_MODEL = llm_config.model_for("groq", "daily_report")
GROQ_NEWS_INTELLIGENCE_MODEL = llm_config.model_for("groq", "news_intelligence")

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = "You are a careful crypto monitoring assistant."
_RAW_DIAGNOSTIC_LINE_RE = re.compile(
    r"(?i)\b(move|change24h|change7d|threshold|interval|previous|current|price)\s*="
)
_NOT_FINANCIAL_ADVICE = "Not financial advice."
_RISK_REASON_MAX_CHARS = 180
_RISK_REASON_GENERIC_RE = re.compile(
    r"(?i)\b("
    r"risk level reflects|"
    r"based on market data and news|"
    r"risk is based on current conditions|"
    r"available news context|"
    r"current market conditions"
    r")\b"
)
_RISK_REASON_NEWS_RE = re.compile(r"(?i)\b(news|headline|headlines|sentiment|driver)\b")


class LLMJsonResult(tuple):
    """Tuple-compatible raw JSON result with attached usage log id and provider/model.

    Remains a 2-tuple ``(raw_content, parsed)`` for backward compatibility; ``provider`` and
    ``model`` expose which provider actually answered so callers can attribute the analysis.
    """

    usage_log_id: int | None
    provider: str | None
    model: str | None

    def __new__(
        cls,
        raw_content: str,
        parsed: dict,
        usage_log_id: int | None = None,
        *,
        provider: str | None = None,
        model: str | None = None,
    ):
        value = super().__new__(cls, (raw_content, parsed))
        value.usage_log_id = usage_log_id
        value.provider = provider
        value.model = model
        return value


def _json_response_validator(
    *,
    call_type: str,
    symbol: str | None,
    max_tokens: int,
    schema_check=None,
):
    """Build the router ``validate_response`` callback for structured-JSON call types.

    The callback parses one provider's raw output (stripping optional code fences), runs the
    optional caller-supplied ``schema_check(parsed)`` (which raises
    ``AISchemaValidationError`` on mismatch), writes the per-attempt usage log for that
    provider, and returns an :class:`LLMJsonResult`. Raising ``AIInvalidJsonError`` /
    ``AISchemaValidationError`` makes the router advance to the next provider in the chain,
    so invalid output is handled like any other provider failure while keeping per-provider
    attribution in ``llm_usage_logs``.
    """

    async def _validate(result) -> LLMJsonResult:
        raw_content = result.raw_content
        attempt_max_tokens = getattr(result, "max_tokens", max_tokens)
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw_content.strip())
        cleaned = re.sub(r"\s*```$", "", cleaned)
        parsed = None
        parse_error: AIInvalidJsonError | None = None
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as error:
            parse_error = AIInvalidJsonError(str(error), raw_content=raw_content)
            parse_error.__cause__ = error
        if parse_error is None and not isinstance(parsed, dict):
            parse_error = AIInvalidJsonError(
                "top-level JSON is not an object", raw_content=raw_content
            )
        if parse_error is not None:
            # Attribute the failure to the provider that produced it, for terminal handlers.
            parse_error.provider = result.provider
            parse_error.model = result.model
            await write_llm_usage_log(
                provider=result.provider,
                call_type=call_type,
                symbol=symbol,
                model=result.model,
                status="invalid_json",
                input_chars=result.input_chars,
                output_chars=len(raw_content),
                max_tokens=attempt_max_tokens,
                headers=result.headers,
                response=result.response,
                error_reason="invalid_json",
                error_message=safe_error_message(parse_error),
            )
            raise parse_error
        if schema_check is not None:
            try:
                schema_check(parsed)
            except AISchemaValidationError as error:
                if error.raw_content is None:
                    error.raw_content = raw_content
                error.provider = result.provider
                error.model = result.model
                await write_llm_usage_log(
                    provider=result.provider,
                    call_type=call_type,
                    symbol=symbol,
                    model=result.model,
                    status="schema_error",
                    input_chars=result.input_chars,
                    output_chars=len(raw_content),
                    max_tokens=attempt_max_tokens,
                    headers=result.headers,
                    response=result.response,
                    error_reason="schema_validation_failed",
                    error_message=safe_error_message(error),
                )
                raise
        usage_log_id = await write_llm_usage_log(
            provider=result.provider,
            call_type=call_type,
            symbol=symbol,
            model=result.model,
            status="success",
            input_chars=result.input_chars,
            output_chars=len(raw_content),
            max_tokens=attempt_max_tokens,
            headers=result.headers,
            response=result.response,
        )
        return LLMJsonResult(
            raw_content, parsed, usage_log_id, provider=result.provider, model=result.model
        )

    return _validate


def _groq_json_mode_enabled() -> bool:
    return os.getenv("GROQ_JSON_MODE", "true").strip().lower() not in {"0", "false", "no", "off"}


def _groq_json_mode_retry_plain_enabled() -> bool:
    return os.getenv("GROQ_JSON_MODE_RETRY_PLAIN", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _parse_json(raw_content: str | None) -> dict | None:
    """Parse and validate top-level JSON object responses from the model."""
    if not raw_content:
        logger.error("AI parsing failed: empty response.")
        return None
    raw_content = re.sub(r"^```(?:json)?\s*", "", raw_content.strip())
    raw_content = re.sub(r"\s*```$", "", raw_content)
    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError as error:
        logger.error("AI parsing failed: invalid JSON (%s).", error)
        return None
    if not isinstance(parsed, dict):
        logger.error("AI parsing failed: top-level JSON is not an object.")
        return None
    return parsed


def build_fallback_alert_message(
    previous_price: float,
    current_price: float,
    price_change_percent: float,
    change_24h: float,
    change_7d: float | None = None,
    alert_threshold_percent: float | None = None,
    check_interval_seconds: int | None = None,
    symbol: str = "BTC",
    coin_name: str = "Bitcoin",
    alert_type_label: str = "basic price",
    window_seconds: int | None = None,
    peak_movement_percent: float | None = None,
) -> str:
    """Deterministic fallback used when structured AI output cannot be trusted."""
    display_symbol = coin_display_symbol(symbol)
    window_label = _format_window_label(window_seconds or check_interval_seconds)
    peak_line = (
        f"Peak intrahour move: {peak_movement_percent:+.2f}%\n"
        if peak_movement_percent is not None
        else ""
    )
    return (
        f"{display_symbol} {alert_type_label} alert\n\n"
        f"Price: ${current_price:,.2f}\n"
        f"{window_label} move: {price_change_percent:+.2f}%\n"
        f"{peak_line}"
        f"24h trend: {change_24h:+.2f}%\n"
        "\nAI analysis is temporarily unavailable. This is a basic price alert.\n"
        "Not financial advice."
    )


def _format_window_label(seconds: int | None) -> str:
    if seconds == 3600:
        return "1h"
    if seconds == 21600:
        return "6h"
    if seconds == 86400:
        return "24h"
    if seconds and seconds % 3600 == 0:
        return f"{seconds // 3600}h"
    if seconds and seconds % 60 == 0:
        return f"{seconds // 60}m"
    return "Window"


def _build_fallback_alert_payload(
    previous_price: float,
    current_price: float,
    price_change_percent: float,
    change_24h: float,
    change_7d: float | None,
    alert_threshold_percent: float | None,
    check_interval_seconds: int | None,
    symbol: str,
    coin_name: str,
    *,
    rate_limited: bool = False,
) -> dict:
    plain_message = build_fallback_alert_message(
        previous_price,
        current_price,
        price_change_percent,
        change_24h,
        change_7d,
        alert_threshold_percent,
        check_interval_seconds,
        symbol,
        coin_name,
    )
    payload = {"plain_text": plain_message, "html_text": None}
    if rate_limited:
        payload["rate_limited"] = True
    return payload


def _is_structured_alert_message(message: str) -> bool:
    current_markers = [
        "move:",
        "24h trend:",
        "Why this alert:",
        "Possible actions:",
    ]
    legacy_markers = [
        "Since last check:",
        "24h trend:",
        "Risk level:",
        "Risk reason:",
        "Context:",
        "Possible action:",
    ]
    return "\n" in message and (
        all(marker in message for marker in current_markers)
        or all(marker in message for marker in legacy_markers)
    )


def _format_related_news_section(news_relevance: str, related_news: list[dict] | None) -> str:
    if news_relevance not in {"relevant", "partly_relevant"}:
        return ""
    if not related_news:
        return ""

    lines: list[str] = []
    for item in related_news[:2]:
        if not isinstance(item, dict):
            continue
        title = clean_news_title(str(item.get("title", "")))
        source = str(item.get("source", "")).strip()
        link = str(item.get("link", "")).strip()
        if not title:
            continue
        display_text = clean_related_news_text(
            f"{title} - {source}" if source else title,
            source=source,
        )
        if link and display_text:
            display_text = f"{display_text} - {link}"
        if display_text:
            lines.append(f"- {display_text}")

    if not lines:
        return ""
    return "Related news:\n" + "\n".join(lines)


def _build_news_listing_with_ids(news_items: list[dict] | None) -> tuple[str, list[dict]]:
    indexed_items: list[dict] = []
    lines: list[str] = []
    for item in news_items or []:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        source = str(item.get("source", "")).strip()
        link = str(item.get("link", "")).strip()
        if not title:
            continue
        indexed_items.append({"title": title, "source": source, "link": link})
        source_text = source or "Source unavailable"
        link_text = link or "No link"
        lines.append(f"[{len(indexed_items)}] {title} | {source_text} | {link_text}")

    if not lines:
        return "No relevant recent news found.", []
    return "\n".join(lines), indexed_items


def _extract_related_news_from_ids(
    news_relevance: str, related_news_ids: list[int] | None, indexed_news_items: list[dict]
) -> list[dict]:
    if news_relevance not in {"relevant", "partly_relevant"}:
        return []
    if not isinstance(related_news_ids, list):
        return []

    valid_items: list[dict] = []
    used_ids: set[int] = set()
    for raw_id in related_news_ids:
        if len(valid_items) >= 2:
            break
        if not isinstance(raw_id, int) or raw_id in used_ids:
            continue
        used_ids.add(raw_id)
        if raw_id < 1 or raw_id > len(indexed_news_items):
            continue
        item = indexed_news_items[raw_id - 1]
        link = str(item.get("link", "")).strip()
        if not link:
            continue
        valid_items.append(
            {
                "title": str(item.get("title", "")).strip(),
                "source": str(item.get("source", "")).strip(),
                "link": link,
            }
        )
    return valid_items


def _sanitize_telegram_message(telegram_message: str) -> str:
    removed_prefixes = ("Data:", "News:", "Debug:")
    kept_lines: list[str] = []
    dropping_debug_block = False
    for line in telegram_message.splitlines():
        stripped = line.strip()
        if not stripped:
            dropping_debug_block = False
            kept_lines.append(line)
            continue
        if stripped.startswith(removed_prefixes):
            dropping_debug_block = True
            continue
        if dropping_debug_block and (_RAW_DIAGNOSTIC_LINE_RE.search(stripped) or "=" in stripped):
            continue
        dropping_debug_block = False
        if _RAW_DIAGNOSTIC_LINE_RE.search(stripped):
            continue
        if re.match(r"(?i)^7d trend:\s*(unknown|n/a|none|null|unavailable)\s*\.?$", stripped):
            continue
        if stripped == _NOT_FINANCIAL_ADVICE:
            continue
        kept_lines.append(line)
    cleaned = "\n".join(kept_lines).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    if not cleaned:
        return _NOT_FINANCIAL_ADVICE
    return cleaned.rstrip() + f"\n\n{_NOT_FINANCIAL_ADVICE}"


def _build_fallback_risk_reason(
    *,
    price_change_percent: float | None = None,
    change_24h: float | None = None,
    alert_threshold_percent: float | None = None,
    news_relevance: str = "",
    has_related_news: bool = False,
) -> str:
    """Build a specific risk reason from alert facts without replacing AI scoring."""
    news_relevance = news_relevance.strip()
    abs_move = abs(price_change_percent) if price_change_percent is not None else None
    abs_24h = abs(change_24h) if change_24h is not None else None
    abs_threshold = abs(alert_threshold_percent) if alert_threshold_percent is not None else None
    crossed_threshold = (
        abs_move is not None and abs_threshold is not None and abs_move >= abs_threshold
    )

    if abs_24h is not None and abs_24h >= 2:
        reason = (
            "The short-term move happened alongside a stronger 24h trend, "
            "increasing volatility risk."
        )
    elif abs_move is not None and abs_move >= 1:
        reason = "The short-term move is notable, while the 24h trend remains relatively mild."
    elif abs_move is not None and abs_24h is not None and abs_move < 1 and abs_24h < 1:
        if crossed_threshold:
            reason = "The move crossed the alert threshold, but the 24h trend remains mild."
        else:
            reason = "The short-term move is small and the 24h trend remains mild."
    elif crossed_threshold:
        reason = "The move crossed the alert threshold while the broader trend remains contained."
    else:
        reason = "The short-term move is limited and the 24h trend is not showing sharp volatility."

    if news_relevance in {"relevant", "partly_relevant"} and has_related_news:
        reason = reason.rstrip(".") + ", and related news may also affect short-term sentiment."
    return reason


def _extract_percent_from_message(message: str, label: str) -> float | None:
    pattern = rf"(?im)^{re.escape(label)}:\s*([+-]?\d+(?:\.\d+)?)%"
    match = re.search(pattern, message)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _risk_reason_mentions_news(reason: str) -> bool:
    return bool(_RISK_REASON_NEWS_RE.search(reason))


def _is_generic_risk_reason(reason: str) -> bool:
    stripped = " ".join(str(reason or "").split()).strip()
    return len(stripped) < 25 or bool(_RISK_REASON_GENERIC_RE.search(stripped))


def _sanitize_risk_reason(
    reason: str,
    fallback_reason: str,
    *,
    can_mention_news: bool = False,
) -> str:
    cleaned = " ".join(str(reason or "").split())
    cleaned = re.sub(r"(?i)\bnot financial advice\.?", "", cleaned).strip()
    if (
        not cleaned
        or _is_generic_risk_reason(cleaned)
        or (_risk_reason_mentions_news(cleaned) and not can_mention_news)
    ):
        cleaned = fallback_reason
    first_sentence = re.match(r"^(.+?[.!?])(?:\s|$)", cleaned)
    if first_sentence:
        cleaned = first_sentence.group(1)
    if len(cleaned) > _RISK_REASON_MAX_CHARS:
        cleaned = cleaned[: _RISK_REASON_MAX_CHARS - 1].rstrip(" ,;:") + "."
    return cleaned.rstrip(".!?") + "."


def _fallback_risk_reason_from_message(message: str) -> str:
    has_related_news = "Related news:" in message
    return _build_fallback_risk_reason(
        price_change_percent=_extract_percent_from_message(message, "Since last check"),
        change_24h=_extract_percent_from_message(message, "24h trend"),
        alert_threshold_percent=None,
        news_relevance="partly_relevant" if has_related_news else "not_relevant",
        has_related_news=has_related_news,
    )


def _ensure_risk_reason_after_level(
    message: str,
    risk_reason: str,
    fallback_reason: str | None = None,
    *,
    can_mention_news: bool = False,
) -> str:
    lines = message.splitlines()
    if not any(line.strip().startswith("Risk level:") for line in lines):
        return message

    existing_reason = next(
        (
            line.split(":", 1)[1].strip()
            for line in lines
            if line.strip().startswith("Risk reason:") and ":" in line
        ),
        "",
    )
    cleaned_reason = _sanitize_risk_reason(
        risk_reason or existing_reason,
        fallback_reason or _fallback_risk_reason_from_message(message),
        can_mention_news=can_mention_news,
    )
    without_existing_reason = [
        line for line in lines if not line.strip().startswith("Risk reason:")
    ]
    risk_level_index = next(
        index
        for index, line in enumerate(without_existing_reason)
        if line.strip().startswith("Risk level:")
    )
    without_existing_reason.insert(risk_level_index + 1, f"Risk reason: {cleaned_reason}")
    return "\n".join(without_existing_reason).strip()


def sanitize_alert_message(telegram_message: str) -> str:
    """Public sanitizer for alert messages loaded from AI output or cache."""
    sanitized = _sanitize_telegram_message(telegram_message)
    can_mention_news = "Related news:" in sanitized
    with_risk_reason = _ensure_risk_reason_after_level(
        sanitized,
        "",
        _fallback_risk_reason_from_message(sanitized),
        can_mention_news=can_mention_news,
    )
    return _sanitize_telegram_message(with_risk_reason)


def _build_alert_message_with_related_news(
    structured: dict,
    price_change_percent: float,
    change_24h: float,
    alert_threshold_percent: float | None,
) -> str:
    news_relevance = str(structured.get("news_relevance", "")).strip()
    related_news_section = _format_related_news_section(
        news_relevance, structured.get("related_news")
    )
    can_mention_news = bool(related_news_section)
    fallback_reason = _build_fallback_risk_reason(
        price_change_percent=price_change_percent,
        change_24h=change_24h,
        alert_threshold_percent=alert_threshold_percent,
        news_relevance=news_relevance,
        has_related_news=can_mention_news,
    )
    telegram_message = _sanitize_telegram_message(
        str(structured.get("telegram_message", "")).strip()
    )
    telegram_message = _ensure_risk_reason_after_level(
        telegram_message,
        str(structured.get("risk_reason", "")).strip() or fallback_reason,
        fallback_reason,
        can_mention_news=can_mention_news,
    )
    telegram_message = _sanitize_telegram_message(telegram_message)
    if not related_news_section:
        return telegram_message
    if "Related news:" in telegram_message:
        return telegram_message
    if "Possible action:" not in telegram_message:
        return telegram_message
    return telegram_message.replace(
        "Possible action:", f"{related_news_section}\n\nPossible action:", 1
    )


def _sanitize_ai_sentence(value: str, fallback: str, *, max_chars: int = 180) -> str:
    cleaned = " ".join(str(value or "").split())
    cleaned = re.sub(r"(?i)\bnot financial advice\.?", "", cleaned).strip()
    if not cleaned:
        cleaned = fallback
    first_sentence = re.match(r"^(.+?[.!?])(?:\s|$)", cleaned)
    if first_sentence:
        cleaned = first_sentence.group(1)
    if len(cleaned) > max_chars:
        cleaned = cleaned[: max_chars - 1].rstrip(" ,;:") + "."
    return cleaned.rstrip(".!?") + "."


def _build_specific_possible_actions(
    *,
    price_change_percent: float,
    change_24h: float,
    alert_threshold_percent: float | None,
    news_relevance: str,
) -> list[str]:
    abs_move = abs(price_change_percent)
    abs_24h = abs(change_24h)
    threshold = abs(alert_threshold_percent or 0.0)
    relevant_news = news_relevance in {"relevant", "partly_relevant"}
    if relevant_news and (threshold <= 0 or abs_move < threshold) and abs_24h < 2.0:
        return [
            "No immediate portfolio action is suggested by price data alone.",
            "Watch whether the coin reacts over the next alert window.",
        ]
    if abs_move >= threshold > 0 or abs_24h >= 3.0:
        return [
            "Monitor whether volatility continues over the next few hours.",
            "Check whether this move changes your target allocation.",
        ]
    return [
        "No immediate portfolio action is suggested by price data alone.",
        "Review exposure only if you already planned to rebalance.",
    ]


def _normalize_alert_structured_fields(structured: dict) -> dict | None:
    required_fields = {
        "news_relevance",
        "risk_level",
        "risk_reason",
        "context_sentence",
        "possible_action",
        "related_news_ids",
    }
    if not required_fields.issubset(structured):
        return None

    news_relevance = str(structured.get("news_relevance", "")).strip().lower()
    if news_relevance not in {"relevant", "partly_relevant", "not_relevant", "unknown"}:
        return None

    risk_level_input = str(structured.get("risk_level", "")).strip().lower()
    risk_level_by_value = {
        "info": "low",
        "watch": "medium",
        "moderate": "medium",
        "critical": "extreme",
        "low": "low",
        "medium": "medium",
        "high": "high",
        "extreme": "extreme",
    }
    risk_level = risk_level_by_value.get(risk_level_input)
    if risk_level is None:
        return None

    related_news_ids = structured.get("related_news_ids")
    if not isinstance(related_news_ids, list):
        return None

    return {
        **structured,
        "news_relevance": news_relevance,
        "risk_level": risk_level,
        "related_news_ids": related_news_ids,
    }


def _build_deterministic_ai_alert_message(
    structured: dict,
    previous_price: float,
    current_price: float,
    price_change_percent: float,
    change_24h: float,
    change_7d: float | None,
    alert_threshold_percent: float | None,
    check_interval_seconds: int | None,
    symbol: str,
    coin_name: str,
) -> str:
    related_news_section = _format_related_news_section(
        str(structured.get("news_relevance", "")).strip(),
        structured.get("related_news"),
    )
    can_mention_news = bool(related_news_section)
    fallback_reason = _build_fallback_risk_reason(
        price_change_percent=price_change_percent,
        change_24h=change_24h,
        alert_threshold_percent=alert_threshold_percent,
        news_relevance=str(structured.get("news_relevance", "")).strip(),
        has_related_news=can_mention_news,
    )
    risk_reason = _sanitize_risk_reason(
        str(structured.get("risk_reason", "")),
        fallback_reason,
        can_mention_news=can_mention_news,
    )
    context_sentence = _sanitize_ai_sentence(
        str(structured.get("context_sentence", "")),
        (
            f"Short-term {coin_name} movement is notable while broader market context "
            "remains uncertain."
        ),
        max_chars=220,
    )
    possible_actions = _build_specific_possible_actions(
        price_change_percent=price_change_percent,
        change_24h=change_24h,
        alert_threshold_percent=alert_threshold_percent,
        news_relevance=str(structured.get("news_relevance", "")).strip(),
    )
    window_label = _format_window_label(check_interval_seconds)
    news_text = related_news_section or "News relevance:\nNo clearly relevant news found."
    message = (
        f"{structured['risk_level']} - {coin_display_symbol(symbol)} market alert\n\n"
        f"Price: ${current_price:,.2f}\n"
        f"{window_label} move: {price_change_percent:+.2f}%\n"
        f"24h trend: {change_24h:+.2f}%\n\n"
        "Why this alert:\n"
        f"{risk_reason} {context_sentence}\n\n"
        f"{news_text}\n\n"
        "Possible actions:\n"
        f"- {possible_actions[0]}\n"
        f"- {possible_actions[1]}\n\n"
        "Not financial advice."
    )
    return _sanitize_telegram_message(message)


def _extract_related_news_with_links(
    news_relevance: str, related_news: list[dict] | None
) -> list[dict]:
    if news_relevance not in {"relevant", "partly_relevant"} or not related_news:
        return []
    valid_items: list[dict] = []
    for item in related_news[:2]:
        if not isinstance(item, dict):
            continue
        title = clean_news_title(str(item.get("title", "")))
        source = str(item.get("source", "")).strip()
        link = str(item.get("link", "")).strip()
        if not title or not link:
            continue
        valid_items.append({"title": title, "source": source, "link": link})
    return valid_items


def build_html_alert_message(plain_message: str, related_news_links: list[dict]) -> str | None:
    if not related_news_links or "Related news:" not in plain_message:
        return None
    escaped_message = escape(plain_message)
    escaped_lines = escaped_message.split("\n")

    try:
        header_index = escaped_lines.index("Related news:")
    except ValueError:
        return None

    html_lines: list[str] = []
    for item in related_news_links[:2]:
        title = escape(item["title"])
        source = escape(item["source"])
        link = escape(item["link"], quote=True)
        if source:
            html_lines.append(f'- <a href="{link}">{title}</a> - {source}')
        else:
            html_lines.append(f'- <a href="{link}">{title}</a>')
    if not html_lines:
        return None

    end_index = header_index + 1
    while end_index < len(escaped_lines) and escaped_lines[end_index].startswith("- "):
        end_index += 1
    return "\n".join(escaped_lines[: header_index + 1] + html_lines + escaped_lines[end_index:])


def _build_alert_prompt(
    previous_price: float,
    current_price: float,
    price_change_percent: float,
    change_24h: float,
    change_7d: float | None,
    alert_threshold_percent: float | None,
    check_interval_seconds: int | None,
    news_text: str,
    symbol: str = "BTC",
    coin_name: str = "Bitcoin",
) -> str:
    display_symbol = coin_display_symbol(symbol)
    change_7d_text = f"{change_7d:.4f}%" if change_7d is not None else "unavailable"
    threshold_text = alert_threshold_percent if alert_threshold_percent is not None else "unknown"
    window_label = _format_window_label(check_interval_seconds)
    return f"""
Return one valid JSON object only.
Do not use Markdown.
Do not wrap in code fences.
Do not include text before or after JSON.
All string values must be valid JSON strings.

Required JSON fields:
- news_relevance: "relevant", "partly_relevant", "not_relevant", or "unknown"
- risk_level: "low", "medium", "high", or "extreme"
- risk_reason: one short specific sentence
- context_sentence: one short cautious sentence
- possible_action: one short cautious sentence
- related_news_ids: an array with up to 2 numeric IDs from the News list

Do not use guaranteed-outcome language.
High should be rare. Extreme should be used only for clearly abnormal market shocks.
News-only alerts should be Low unless the news is clearly material.
Never use Medium only because news may affect sentiment.
If the user-window move is near 0 and the 24h trend is mild, use Low or not_relevant.
risk_reason must cite concrete alert factors: {window_label} move, 24h trend,
threshold crossing, and material news only when relevant.
Do not mention internal polling, check interval, raw Data blocks, or debug labels.
Set related_news_ids to [] when news_relevance is not_relevant or unknown.
Possible action must be specific and cautious, such as watching reaction over the next
alert window or checking target allocation. Do not use generic investment-strategy wording.

Alert data:
- Symbol: {display_symbol}
- Coin name: {coin_name}
- Previous user-window price: ${previous_price:.2f}
- Current price: ${current_price:.2f}
- {window_label} move: {price_change_percent:.4f}%
- 24h trend: {change_24h:.4f}%
- 7d trend: {change_7d_text}
- Movement threshold: {threshold_text}%

News:
{news_text}
"""


def _build_news_text(news_items: list[dict] | None) -> str:
    return (
        "\n".join(f"- {item.get('title', 'No title')}" for item in (news_items or []))
        or "No relevant recent news found."
    )


async def _ask_json_with_usage(
    prompt: str,
    *,
    call_type: str = "legacy_alert_payload",
    symbol: str | None = None,
    model: str | None = None,
    max_tokens: int | None = None,
    schema_check=None,
) -> tuple[dict | None, int | None]:
    """Request JSON from Groq/OpenAI-compatible API and parse it.

    ``max_tokens=None`` resolves the configured budget for the call type, so this path is
    covered by the same environment configuration as the others.
    """
    if max_tokens is None:
        max_tokens = llm_config.max_tokens_for(call_type)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    json_mode_enabled = _groq_json_mode_enabled()
    response_format = {"type": "json_object"} if json_mode_enabled else None
    # Honour an explicit Groq model override for the primary provider; fallback providers use
    # their own configured models.
    model_overrides = {"groq": model} if model else None
    validator = _json_response_validator(
        call_type=call_type,
        symbol=symbol,
        max_tokens=max_tokens,
        schema_check=schema_check,
    )

    try:
        result = await get_router().chat_completion(
            call_type=call_type,
            messages=messages,
            max_tokens=max_tokens,
            response_format=response_format,
            symbol=symbol,
            model_overrides=model_overrides,
            validate_response=validator,
        )
    except Exception as error:
        # Rate-limit / all-providers-failed already carry the correct type from the router.
        if is_rate_limit_error(error):
            raise
        if not json_mode_enabled or not is_json_validation_error(error):
            raise
        if not _groq_json_mode_retry_plain_enabled():
            logger.warning("LLM JSON mode failed; using deterministic fallback.")
            return None, None
        logger.warning("LLM JSON mode failed; retrying once without response_format.")
        result = await get_router().chat_completion(
            call_type=call_type,
            messages=messages,
            max_tokens=max_tokens,
            response_format=None,
            symbol=symbol,
            model_overrides=model_overrides,
            validate_response=validator,
        )
    _, parsed = result
    return parsed, result.usage_log_id


async def _ask_json(prompt: str) -> dict | None:
    def _schema_check(parsed: dict) -> None:
        if _normalize_alert_structured_fields(parsed) is None:
            raise AISchemaValidationError("legacy alert payload schema mismatch")

    try:
        parsed, _ = await _ask_json_with_usage(prompt, schema_check=_schema_check)
    except (AIInvalidJsonError, AISchemaValidationError):
        # Chain exhausted on unusable structured output; keep this helper's None contract so
        # the legacy alert path builds its deterministic fallback exactly as before.
        return None
    return parsed


def build_event_analysis_prompt(input_payload: dict) -> str:
    return (
        "Return valid JSON only. Write English.\n"
        "Use exactly these fields: symbol, should_alert, event_key, title, message_body, "
        "related_news_ids, possible_action, urgency, confidence, reason_for_no_alert.\n"
        "urgency: low, normal, high. confidence: low, medium, high.\n"
        "Analyze exactly one symbol: the symbol in the input payload. Use display_symbol for "
        "user-facing wording when it is present. Do not change backend alert types.\n"
        "Use only direct symbol news or clearly market-wide crypto news. Do not treat "
        "BTC-only news as related context for ETH, SOL, GRAM, or any non-BTC symbol.\n"
        "Event Alerts are market-event-first. Set should_alert=true only when the "
        "analysed-window market data shows a meaningful market event or meaningful "
        "market-context change. News may support or explain the alert, but news alone "
        "must not trigger should_alert=true. If the only notable input is repeated, "
        "similar, or old news and the analysed-window market context does not justify "
        "a new alert, set should_alert=false.\n"
        "Do not claim news caused a price move. Avoid overconfident trading instructions.\n"
        "Use market.chg_window and the short-term snapshots as the primary trigger basis; "
        "market.chg24h is broader context, not the primary trigger.\n"
        "Do not ignore meaningful price moves only because direct news is absent. For "
        "altcoins, a 24h move around 5-7% can be meaningful even without coin-specific news.\n"
        "event_key is required only when should_alert=true.\n"
        "When should_alert=true, use a stable event_key based on symbol and event theme. Do "
        "not generate UUID-like or random event keys such as event_analysis_btc_<random>.\n"
        "If should_alert=false: event_key null or \"\", title \"\", message_body \"\", "
        "related_news_ids [], possible_action \"\", urgency null, confidence low|medium|high, "
        "reason_for_no_alert non-empty.\n"
        "For should_alert=false, reason_for_no_alert must mention the actual analysed-window "
        "change when market.chg_window is not null, or say fresh analysed-window data is "
        "insufficient when it is null. Also mention recent short-term snapshot behavior, "
        "whether news was direct, "
        "market-wide, irrelevant, or absent, and why that does or does not justify an alert.\n"
        "Use market.chg24h only as broader context, not as the analysed-window move.\n"
        "Avoid generic no-alert reasons like \"No significant price movement\" or "
        "\"No relevant news\" unless backed by the actual input numbers.\n"
        "related_news_ids must come from news.news_id.\n"
        "possible_action should be specific to the actual market event. Avoid generic "
        "\"Monitor price movement\" wording when a more useful cautious action is available. "
        "If monitoring is genuinely the best cautious action, it is allowed.\n"
        "Prefer fewer useful alerts. If no meaningful event exists, set should_alert=false.\n"
        "No guaranteed outcomes.\n"
        "In snapshots, m is minutes before timestamp_utc and p is USD price.\n\n"
        "Input JSON:\n"
        f"{json.dumps(input_payload, ensure_ascii=False, sort_keys=True)}"
    )


async def ask_event_analysis_raw(input_payload: dict, *, schema_check=None) -> tuple[str, dict]:
    """Ask the LLM for one event-analysis decision and return raw + parsed JSON.

    ``schema_check(parsed)`` optionally validates each provider's parsed output during the
    router pass (raising ``AISchemaValidationError`` on mismatch), so a schema-invalid answer
    from one provider falls back to the next provider in the chain.
    """
    prompt = build_event_analysis_prompt(input_payload)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    response_format = {"type": "json_object"} if _groq_json_mode_enabled() else None
    symbol = str(input_payload.get("symbol") or "").strip() or None
    max_tokens = llm_config.max_tokens_for("event_analysis")

    return await get_router().chat_completion(
        call_type="event_analysis",
        messages=messages,
        max_tokens=max_tokens,
        response_format=response_format,
        symbol=symbol,
        validate_response=_json_response_validator(
            call_type="event_analysis",
            symbol=symbol,
            max_tokens=max_tokens,
            schema_check=schema_check,
        ),
    )


def build_market_heartbeat_prompt(input_payload: dict) -> str:
    return (
        "Return valid JSON only, in English.\n"
        "Use exactly these fields: symbol, title, message_body, related_news_ids, "
        "possible_action, confidence.\n"
        'Allowed confidence values: "low", "medium", "high".\n'
        "This is a calm Market Heartbeat, not an Event Alert. Do not return "
        "should_alert, event_key, urgency, market_update, important_alert, "
        "critical_alert, strong_signal, buy_signal, or sell_signal.\n"
        "Use direct symbol news first. Use display_symbol for user-facing wording when it is "
        "present. Use clearly market-wide crypto news only when useful. "
        "Do not present BTC-only news as related context for ETH, SOL, GRAM, or any non-BTC "
        "symbol.\n"
        "Be concise and useful. Mention selected relevant news if useful, but avoid exact "
        "causality claims. Do not repeat exact price values or exact percentage values in "
        "message_body; describe the current price, since-last-message change, and 24h "
        "change qualitatively.\n"
        "related_news_ids must only contain news_id values from candidate_news.\n"
        "possible_action must be specific, practical, and tied to the current market context. "
        "Prefer guidance about the price range, volatility, confirmation, whether news is "
        "direct or only market-wide, or whether the market is quiet. Avoid generic "
        "possible_action phrases such as \"Monitor market developments\", \"Monitor market "
        "sentiment\", or \"Keep watching\" unless there is genuinely no better action. "
        "Avoid overconfident trading instructions.\n\n"
        "Input JSON:\n"
        f"{json.dumps(input_payload, ensure_ascii=False, sort_keys=True)}"
    )


async def ask_market_heartbeat_raw(input_payload: dict, *, schema_check=None) -> tuple[str, dict]:
    """Ask the LLM for one cached market heartbeat and return raw + parsed JSON.

    ``schema_check(parsed)`` validates each provider response during the router pass, so a
    schema-invalid heartbeat can fall through to the next configured provider.
    """
    prompt = build_market_heartbeat_prompt(input_payload)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    response_format = {"type": "json_object"} if _groq_json_mode_enabled() else None
    symbol = str(input_payload.get("symbol") or "").strip() or None
    max_tokens = llm_config.max_tokens_for("market_heartbeat")

    return await get_router().chat_completion(
        call_type="market_heartbeat",
        messages=messages,
        max_tokens=max_tokens,
        response_format=response_format,
        symbol=symbol,
        validate_response=_json_response_validator(
            call_type="market_heartbeat",
            symbol=symbol,
            max_tokens=max_tokens,
            schema_check=schema_check,
        ),
    )


def build_market_report_prompt(input_payload: dict) -> str:
    report_type = str(input_payload.get("report_type") or "daily").strip().lower()
    weekly_guidance = (
        "For weekly reports, week_timeline and themes must be non-empty and "
        "next_week_focus must be a concise cautious sentence. "
        "week_timeline must be an array of short strings only. "
        "themes must be an array of short strings only. "
        "Do not return objects inside week_timeline or themes. "
        "Do not use {day, event, summary} style entries. "
        "Use weekly_context.scoreboard, weekly_context.breadth, and weekly_context.timeline "
        "when they are present. weekly_context.timeline is market-data path evidence, not a "
        "place for news headlines. If weekly_context says a block is unavailable, say so "
        "directly and do not invent dates or catalysts. "
        "For daily reports, week_timeline and themes may be empty arrays and "
        "next_week_focus may be an empty string.\n"
    )
    return (
        "Return valid JSON only, in English.\n"
        "Use exactly these fields: report_type, title, market_pulse, dashboard, coin_cards, "
        "market_catalysts, why_it_matters, watch_next, week_timeline, themes, "
        "next_week_focus.\n"
        f"report_type must be {report_type!r}.\n"
        "title must match the report type. market_pulse is one short sentence.\n"
        "dashboard is 2-4 concise bullets as plain strings only (not objects), grounded in "
        "prices, volume, range, or trend context from input.\n"
        "coin_cards must include one object per active coin with symbol, summary, and watch. "
        "Use supplied coin symbols only.\n"
        "market_catalysts is 0-3 concise market-data strings as plain strings only (not "
        "objects); do not put unsourced news claims there.\n"
        "why_it_matters and watch_next are concise cautious sentences.\n"
        f"{weekly_guidance}"
        "Use only supplied news title/source/link context. Do not invent news, sources, "
        'links, or reasons. Do not use the phrase "No major market-wide news selected." '
        "Do not include raw JSON, Markdown tables, stack traces, or diagnostic labels.\n"
        "Do not write direct financial advice such as buy now, sell now, short immediately, "
        "or go long. No dense paragraphs.\n\n"
        "Input JSON:\n"
        f"{json.dumps(input_payload, ensure_ascii=False, sort_keys=True)}"
    )


async def ask_market_report_raw(input_payload: dict, *, schema_check=None) -> tuple[str, dict]:
    """Ask the LLM for one cached market-wide report and return raw + parsed JSON.

    ``schema_check(parsed)`` optionally validates each provider's parsed output during the
    router pass (raising ``AISchemaValidationError`` on mismatch), so a schema-invalid answer
    from one provider falls back to the next provider in the chain.
    """
    report_type = str(input_payload.get("report_type") or "").strip().lower()
    call_type = f"{report_type}_report" if report_type in {"daily", "weekly"} else "market_report"
    prompt = build_market_report_prompt(input_payload)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    response_format = {"type": "json_object"} if _groq_json_mode_enabled() else None
    max_tokens = llm_config.max_tokens_for(call_type)

    return await get_router().chat_completion(
        call_type=call_type,
        messages=messages,
        max_tokens=max_tokens,
        response_format=response_format,
        timeout=20,
        symbol=None,
        validate_response=_json_response_validator(
            call_type=call_type,
            symbol=None,
            max_tokens=max_tokens,
            schema_check=schema_check,
        ),
    )


async def ask_news_intelligence_raw(
    messages: list[dict],
    *,
    model: str | None = None,
    timeout: int = 20,
    max_tokens: int | None = None,
    schema_check=None,
) -> tuple[str, dict]:
    """Ask the LLM for one compact structured news intelligence JSON response.

    ``max_tokens=None`` resolves the configured budget for this call type and ``model=None``
    lets the router resolve the model; explicit values still win, so existing callers that pass
    one keep their behaviour.
    """
    if max_tokens is None:
        max_tokens = llm_config.max_tokens_for("news_intelligence")
    response_format = {"type": "json_object"} if _groq_json_mode_enabled() else None
    return await get_router().chat_completion(
        call_type="news_intelligence",
        messages=messages,
        max_tokens=max_tokens,
        response_format=response_format,
        timeout=timeout,
        symbol=None,
        model_overrides={"groq": model} if model else None,
        validate_response=_json_response_validator(
            call_type="news_intelligence",
            symbol=None,
            max_tokens=max_tokens,
            schema_check=schema_check,
        ),
    )


async def create_ai_alert_message(
    previous_price: float,
    current_price: float,
    price_change_percent: float,
    change_24h: float,
    change_7d: float | None,
    news_items: list[dict] | None = None,
    alert_threshold_percent: float | None = None,
    check_interval_seconds: int | None = None,
    symbol: str = "BTC",
    coin_name: str = "Bitcoin",
) -> str:
    """Create a symbol-aware alert message from structured model output."""
    result = await create_ai_alert_payload(
        previous_price,
        current_price,
        price_change_percent,
        change_24h,
        change_7d,
        news_items,
        alert_threshold_percent,
        check_interval_seconds,
        symbol,
        coin_name,
    )
    return result["plain_text"]


async def create_ai_alert_payload(
    previous_price: float,
    current_price: float,
    price_change_percent: float,
    change_24h: float,
    change_7d: float | None,
    news_items: list[dict] | None = None,
    alert_threshold_percent: float | None = None,
    check_interval_seconds: int | None = None,
    symbol: str = "BTC",
    coin_name: str = "Bitcoin",
) -> dict:
    """Create alert payload with plain text and optional HTML variant for Telegram."""
    news_text, indexed_news_items = _build_news_listing_with_ids(news_items)
    prompt = _build_alert_prompt(
        previous_price,
        current_price,
        price_change_percent,
        change_24h,
        change_7d,
        alert_threshold_percent,
        check_interval_seconds,
        news_text,
        symbol,
        coin_name,
    )
    try:
        structured = await _ask_json(prompt)
    except AIGroqRateLimitError as error:
        logger.warning(
            "AI alert generation rate limited; using fallback alert message. error=%s",
            error,
        )
        return _build_fallback_alert_payload(
            previous_price,
            current_price,
            price_change_percent,
            change_24h,
            change_7d,
            alert_threshold_percent,
            check_interval_seconds,
            symbol,
            coin_name,
            rate_limited=True,
        )
    except Exception as error:
        logger.warning("AI alert generation failed; using fallback alert message. error=%s", error)
        structured = None
    structured = _normalize_alert_structured_fields(structured or {})
    if not structured:
        return _build_fallback_alert_payload(
            previous_price,
            current_price,
            price_change_percent,
            change_24h,
            change_7d,
            alert_threshold_percent,
            check_interval_seconds,
            symbol,
            coin_name,
        )
    structured["related_news"] = _extract_related_news_from_ids(
        str(structured.get("news_relevance", "")).strip(),
        structured.get("related_news_ids"),
        indexed_news_items,
    )
    plain_message = _build_deterministic_ai_alert_message(
        structured,
        previous_price,
        current_price,
        price_change_percent,
        change_24h,
        change_7d,
        alert_threshold_percent,
        check_interval_seconds,
        symbol,
        coin_name,
    )
    if not _is_structured_alert_message(plain_message):
        return _build_fallback_alert_payload(
            previous_price,
            current_price,
            price_change_percent,
            change_24h,
            change_7d,
            alert_threshold_percent,
            check_interval_seconds,
            symbol,
            coin_name,
        )
    related_news_links = _extract_related_news_with_links(
        str(structured.get("news_relevance", "")).strip(),
        structured.get("related_news"),
    )
    html_message = build_html_alert_message(plain_message, related_news_links)
    return {"plain_text": plain_message, "html_text": html_message}
