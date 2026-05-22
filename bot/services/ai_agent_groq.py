"""Groq-backed AI helpers.

The bot asks for structured JSON so code can validate output before posting messages.
When parsing/validation fails, callers fall back to deterministic templates.
All prompts explicitly avoid direct financial advice.
"""

import asyncio
import json
import logging
import os
import re
from html import escape

import httpx
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()


def _get_int_env(name: str, default: int, minimum: int = 0) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value >= minimum else default


GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_EVENT_ANALYSIS_MODEL = os.getenv(
    "GROQ_EVENT_ANALYSIS_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct"
)
GROQ_EVENT_ANALYSIS_MAX_TOKENS = _get_int_env("GROQ_EVENT_ANALYSIS_MAX_TOKENS", 300, minimum=1)
GROQ_MARKET_HEARTBEAT_MODEL = os.getenv(
    "GROQ_MARKET_HEARTBEAT_MODEL", "llama-3.1-8b-instant"
)
GROQ_REPORT_MODEL = os.getenv("GROQ_REPORT_MODEL", "llama-3.1-8b-instant")

logger = logging.getLogger(__name__)

_groq_client: AsyncOpenAI | None = None

SYSTEM_PROMPT = "You are a careful crypto monitoring assistant."
_RAW_DIAGNOSTIC_LINE_RE = re.compile(
    r"(?i)\b(move|change24h|change7d|threshold|interval|previous|current|price)\s*="
)
_NOT_FINANCIAL_ADVICE = "Not financial advice."
_DIRECT_ADVICE_RE = re.compile(r"(?i)\b(buy(?:ing)? now|sell(?:ing)? now)\b")
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


class AIGroqRateLimitError(RuntimeError):
    """Raised when Groq refuses a request because the account is rate limited."""


class AIInvalidJsonError(RuntimeError):
    """Raised when the provider response is not valid JSON."""

    def __init__(self, message: str, raw_content: str | None = None):
        super().__init__(message)
        self.raw_content = raw_content


class AISchemaValidationError(RuntimeError):
    """Raised when validated JSON does not match the expected schema."""


class LLMJsonResult(tuple):
    """Tuple-compatible raw JSON result with attached usage log id."""

    usage_log_id: int | None

    def __new__(cls, raw_content: str, parsed: dict, usage_log_id: int | None = None):
        value = super().__new__(cls, (raw_content, parsed))
        value.usage_log_id = usage_log_id
        return value


def classify_ai_error_reason(error: Exception) -> str:
    """Return admin-safe LLM failure reason."""
    if isinstance(error, AIGroqRateLimitError) or _is_groq_rate_limit_error(error):
        return "rate limit"
    if isinstance(error, AIInvalidJsonError):
        return "invalid JSON"
    if isinstance(error, AISchemaValidationError):
        return "schema validation failed"
    if isinstance(error, (TimeoutError, asyncio.TimeoutError)):
        return "timeout"
    status_code = getattr(error, "status_code", None)
    response = getattr(error, "response", None)
    if status_code in {401, 403} or getattr(response, "status_code", None) in {401, 403}:
        return "auth error"
    message = str(error).lower()
    if "api key" in message or "unauthorized" in message or "forbidden" in message:
        return "auth error"
    if "timeout" in message or "timed out" in message:
        return "timeout"
    return "unknown error"


def _usage_status_for_error(error: Exception) -> str:
    reason = classify_ai_error_reason(error)
    if reason == "rate limit":
        return "rate_limit"
    if reason == "invalid JSON":
        return "invalid_json"
    if reason == "schema validation failed" or _is_groq_json_validation_error(error):
        return "schema_error"
    if reason == "timeout":
        return "timeout"
    if reason == "auth error":
        return "auth_error"
    return "other_error"


def _safe_error_message(error: Exception, max_chars: int = 500) -> str:
    message = " ".join(str(error).split())
    return message[:max_chars]


def _groq_json_mode_enabled() -> bool:
    return os.getenv("GROQ_JSON_MODE", "true").strip().lower() not in {"0", "false", "no", "off"}


def _groq_json_mode_retry_plain_enabled() -> bool:
    return os.getenv("GROQ_JSON_MODE_RETRY_PLAIN", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _is_groq_json_validation_error(error: Exception) -> bool:
    message = str(error).lower()
    return (
        "json_validate_failed" in message
        or "validate json" in message
        or "json validation" in message
    )


def _is_groq_rate_limit_error(error: Exception) -> bool:
    status_code = getattr(error, "status_code", None)
    response = getattr(error, "response", None)
    if status_code == 429 or getattr(response, "status_code", None) == 429:
        return True
    message = str(error).lower()
    return "429" in message or "rate limit" in message or "tokens per day" in message


def get_groq_client() -> AsyncOpenAI:
    """Create the Groq client only when an AI call is actually needed."""
    global _groq_client
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured.")
    if _groq_client is None:
        _groq_client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
            timeout=httpx.Timeout(20.0, connect=10.0),
            max_retries=0,
        )
    return _groq_client


def _message_input_chars(messages: list[dict]) -> int:
    return sum(len(str(message.get("content") or "")) for message in messages)


def _response_content(response) -> str:
    try:
        return response.choices[0].message.content or ""
    except (AttributeError, IndexError, TypeError):
        return ""


def _usage_int(response, name: str) -> int | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    value = usage.get(name) if isinstance(usage, dict) else getattr(usage, name, None)
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _headers_from_error(error: Exception):
    response = getattr(error, "response", None)
    return getattr(response, "headers", None)


def _header_value(headers, name: str) -> str | None:
    if headers is None:
        return None
    for candidate in (name, name.lower(), name.upper()):
        try:
            value = headers.get(candidate)
        except AttributeError:
            value = None
        if value is not None:
            return str(value)
    return None


def _rate_limit_header_payload(headers) -> dict:
    return {
        "rate_limit_limit_requests": _header_value(headers, "x-ratelimit-limit-requests"),
        "rate_limit_remaining_requests": _header_value(
            headers, "x-ratelimit-remaining-requests"
        ),
        "rate_limit_reset_requests": _header_value(headers, "x-ratelimit-reset-requests"),
        "rate_limit_limit_tokens": _header_value(headers, "x-ratelimit-limit-tokens"),
        "rate_limit_remaining_tokens": _header_value(headers, "x-ratelimit-remaining-tokens"),
        "rate_limit_reset_tokens": _header_value(headers, "x-ratelimit-reset-tokens"),
        "retry_after": _header_value(headers, "retry-after"),
    }


async def _write_llm_usage_log(
    *,
    call_type: str,
    symbol: str | None,
    model: str,
    status: str,
    input_chars: int | None,
    output_chars: int | None,
    max_tokens: int | None,
    headers=None,
    response=None,
    error_reason: str | None = None,
    error_message: str | None = None,
) -> int | None:
    try:
        from bot.db.database import save_llm_usage_log
        from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL

        if not DB_ENABLED or not DB_SESSION_LOCAL:
            return None
        async with DB_SESSION_LOCAL() as session:
            row = await save_llm_usage_log(
                session,
                provider="groq",
                model=model,
                call_type=call_type,
                symbol=symbol,
                status=status,
                prompt_tokens=_usage_int(response, "prompt_tokens"),
                completion_tokens=_usage_int(response, "completion_tokens"),
                total_tokens=_usage_int(response, "total_tokens"),
                input_chars=input_chars,
                output_chars=output_chars,
                max_tokens=max_tokens,
                error_reason=error_reason,
                error_message=error_message,
                **_rate_limit_header_payload(headers),
            )
            return row.id
    except Exception as log_error:
        logger.debug("LLM usage logging failed: %s", log_error)
        return None


async def mark_llm_usage_log_status(
    usage_log_id: int | None,
    *,
    status: str,
    error_reason: str | None = None,
    error_message: str | None = None,
) -> None:
    if usage_log_id is None:
        return
    try:
        from bot.db.database import update_llm_usage_log_status
        from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL

        if not DB_ENABLED or not DB_SESSION_LOCAL:
            return
        async with DB_SESSION_LOCAL() as session:
            await update_llm_usage_log_status(
                session,
                usage_log_id=usage_log_id,
                status=status,
                error_reason=error_reason,
                error_message=error_message,
            )
    except Exception as log_error:
        logger.debug("LLM usage status update failed: %s", log_error)


async def _run_groq_chat_completion(
    *,
    call_type: str,
    symbol: str | None,
    model: str,
    messages: list[dict],
    max_tokens: int,
    response_format: dict | None,
    timeout: int = 15,
):
    client = get_groq_client()
    request_kwargs = {
        "model": model,
        "messages": messages,
        "temperature": 0.0,
        "max_tokens": max_tokens,
    }
    if response_format is not None:
        request_kwargs["response_format"] = response_format

    input_chars = _message_input_chars(messages)
    try:
        completions = client.chat.completions
        raw_resource = getattr(completions, "with_raw_response", None)
        raw_create = getattr(raw_resource, "create", None)
        if raw_create is not None:
            raw_response = await asyncio.wait_for(raw_create(**request_kwargs), timeout=timeout)
            headers = getattr(raw_response, "headers", None)
            response = raw_response.parse()
        else:
            response = await asyncio.wait_for(completions.create(**request_kwargs), timeout=timeout)
            headers = getattr(response, "headers", None)
    except Exception as error:
        headers = _headers_from_error(error)
        status = _usage_status_for_error(error)
        await _write_llm_usage_log(
            call_type=call_type,
            symbol=symbol,
            model=model,
            status=status,
            input_chars=input_chars,
            output_chars=None,
            max_tokens=max_tokens,
            headers=headers,
            error_reason=classify_ai_error_reason(error),
            error_message=_safe_error_message(error),
        )
        if _is_groq_rate_limit_error(error):
            raise AIGroqRateLimitError(str(error)) from error
        raise
    return response, headers, input_chars


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
    display_symbol = symbol.upper()
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
        title = str(item.get("title", "")).strip()
        source = str(item.get("source", "")).strip()
        link = str(item.get("link", "")).strip()
        if not title:
            continue
        detail_parts = [part for part in (source, link) if part]
        detail_text = f" - {' - '.join(detail_parts)}" if detail_parts else ""
        lines.append(f"- {title}{detail_text}")

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
    cleaned = _DIRECT_ADVICE_RE.sub("review risk", cleaned)
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
    cleaned = _DIRECT_ADVICE_RE.sub("review risk", cleaned)
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
        f"{structured['risk_level']} - {symbol.upper()} market alert\n\n"
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
        title = str(item.get("title", "")).strip()
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
    display_symbol = symbol.upper()
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

Do not give direct buy/sell/short advice or guaranteed-outcome language.
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
    max_tokens: int = 450,
) -> tuple[dict | None, int | None]:
    """Request JSON from Groq/OpenAI-compatible API and parse it."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    json_mode_enabled = _groq_json_mode_enabled()
    response_format = {"type": "json_object"} if json_mode_enabled else None
    selected_model = model or GROQ_MODEL

    try:
        response, headers, input_chars = await _run_groq_chat_completion(
            call_type=call_type,
            symbol=symbol,
            model=selected_model,
            messages=messages,
            max_tokens=max_tokens,
            response_format=response_format,
        )
    except Exception as error:
        if _is_groq_rate_limit_error(error):
            raise AIGroqRateLimitError(str(error)) from error
        if not json_mode_enabled or not _is_groq_json_validation_error(error):
            raise
        if not _groq_json_mode_retry_plain_enabled():
            logger.warning("Groq JSON mode failed; using deterministic fallback.")
            return None, None
        logger.warning("Groq JSON mode failed; retrying once without response_format.")
        try:
            response, headers, input_chars = await _run_groq_chat_completion(
                call_type=call_type,
                symbol=symbol,
                model=selected_model,
                messages=messages,
                max_tokens=max_tokens,
                response_format=None,
            )
        except Exception as retry_error:
            if _is_groq_rate_limit_error(retry_error):
                raise AIGroqRateLimitError(str(retry_error)) from retry_error
            raise
    raw_content = _response_content(response)
    parsed = _parse_json(raw_content)
    status = "success" if parsed is not None else "invalid_json"
    usage_log_id = await _write_llm_usage_log(
        call_type=call_type,
        symbol=symbol,
        model=selected_model,
        status=status,
        input_chars=input_chars,
        output_chars=len(raw_content),
        max_tokens=max_tokens,
        headers=headers,
        response=response,
        error_reason=None if parsed is not None else "invalid JSON",
        error_message=None if parsed is not None else "Provider response was not valid JSON.",
    )
    return parsed, usage_log_id


async def _ask_json(prompt: str) -> dict | None:
    parsed, _ = await _ask_json_with_usage(prompt)
    return parsed


async def ask_event_analysis_raw(input_payload: dict) -> tuple[str, dict]:
    """Ask the LLM for one event-analysis decision and return raw + parsed JSON."""
    prompt = (
        "Return valid JSON only. Write English.\n"
        "Use exactly these fields: symbol, should_alert, event_key, title, message_body, "
        "related_news_ids, possible_action, urgency, confidence, reason_for_no_alert.\n"
        "urgency: low, normal, high. confidence: low, medium, high.\n"
        "event_key is required only when should_alert=true.\n"
        "If should_alert=false: event_key null or \"\", title \"\", message_body \"\", "
        "related_news_ids [], possible_action \"\", urgency null, confidence low|medium|high, "
        "reason_for_no_alert non-empty.\n"
        "related_news_ids must come from news.news_id.\n"
        "Prefer fewer useful alerts. If no meaningful event exists, set should_alert=false.\n"
        "No direct trading commands or guaranteed outcomes.\n"
        "In snapshots, m is minutes before timestamp_utc and p is USD price.\n\n"
        "Input JSON:\n"
        f"{json.dumps(input_payload, ensure_ascii=False, sort_keys=True)}"
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    response_format = {"type": "json_object"} if _groq_json_mode_enabled() else None
    symbol = str(input_payload.get("symbol") or "").strip() or None

    try:
        response, headers, input_chars = await _run_groq_chat_completion(
            call_type="event_analysis",
            symbol=symbol,
            model=GROQ_EVENT_ANALYSIS_MODEL,
            messages=messages,
            max_tokens=GROQ_EVENT_ANALYSIS_MAX_TOKENS,
            response_format=response_format,
        )
    except Exception as error:
        if _is_groq_rate_limit_error(error):
            raise AIGroqRateLimitError(str(error)) from error
        raise
    raw_content = _response_content(response)
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_content.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as error:
        await _write_llm_usage_log(
            call_type="event_analysis",
            symbol=symbol,
            model=GROQ_EVENT_ANALYSIS_MODEL,
            status="invalid_json",
            input_chars=input_chars,
            output_chars=len(raw_content),
            max_tokens=GROQ_EVENT_ANALYSIS_MAX_TOKENS,
            headers=headers,
            response=response,
            error_reason="invalid JSON",
            error_message=_safe_error_message(error),
        )
        raise AIInvalidJsonError(str(error), raw_content=raw_content) from error
    if not isinstance(parsed, dict):
        await _write_llm_usage_log(
            call_type="event_analysis",
            symbol=symbol,
            model=GROQ_EVENT_ANALYSIS_MODEL,
            status="invalid_json",
            input_chars=input_chars,
            output_chars=len(raw_content),
            max_tokens=GROQ_EVENT_ANALYSIS_MAX_TOKENS,
            headers=headers,
            response=response,
            error_reason="invalid JSON",
            error_message="top-level JSON is not an object",
        )
        raise AIInvalidJsonError("top-level JSON is not an object", raw_content=raw_content)
    usage_log_id = await _write_llm_usage_log(
        call_type="event_analysis",
        symbol=symbol,
        model=GROQ_EVENT_ANALYSIS_MODEL,
        status="success",
        input_chars=input_chars,
        output_chars=len(raw_content),
        max_tokens=GROQ_EVENT_ANALYSIS_MAX_TOKENS,
        headers=headers,
        response=response,
    )
    return LLMJsonResult(raw_content, parsed, usage_log_id)


def build_market_heartbeat_prompt(input_payload: dict) -> str:
    return (
        "Return valid JSON only, in English.\n"
        "Use exactly these fields: symbol, title, message_body, related_news_ids, "
        "possible_action, confidence.\n"
        'Allowed confidence values: "low", "medium", "high".\n'
        "This is a calm Market Heartbeat, not an Event Alert. Do not return "
        "should_alert, event_key, urgency, market_update, important_alert, "
        "critical_alert, strong_signal, buy_signal, or sell_signal.\n"
        "Be concise and useful. Mention selected relevant news if useful, but avoid exact "
        "causality claims. Do not repeat exact price values or exact percentage values in "
        "message_body; describe the current price, since-last-message change, and 24h "
        "change qualitatively.\n"
        "related_news_ids must only contain news_id values from candidate_news.\n"
        "Do not provide personalised financial advice or portfolio instructions. "
        "possible_action must be cautious and non-prescriptive.\n\n"
        "Input JSON:\n"
        f"{json.dumps(input_payload, ensure_ascii=False, sort_keys=True)}"
    )


async def ask_market_heartbeat_raw(input_payload: dict) -> tuple[str, dict]:
    """Ask the LLM for one cached market heartbeat and return raw + parsed JSON."""
    prompt = build_market_heartbeat_prompt(input_payload)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    response_format = {"type": "json_object"} if _groq_json_mode_enabled() else None
    symbol = str(input_payload.get("symbol") or "").strip() or None

    try:
        response, headers, input_chars = await _run_groq_chat_completion(
            call_type="market_heartbeat",
            symbol=symbol,
            model=GROQ_MARKET_HEARTBEAT_MODEL,
            messages=messages,
            max_tokens=350,
            response_format=response_format,
        )
    except Exception as error:
        if _is_groq_rate_limit_error(error):
            raise AIGroqRateLimitError(str(error)) from error
        raise
    raw_content = _response_content(response)
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_content.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as error:
        await _write_llm_usage_log(
            call_type="market_heartbeat",
            symbol=symbol,
            model=GROQ_MARKET_HEARTBEAT_MODEL,
            status="invalid_json",
            input_chars=input_chars,
            output_chars=len(raw_content),
            max_tokens=350,
            headers=headers,
            response=response,
            error_reason="invalid JSON",
            error_message=_safe_error_message(error),
        )
        raise AIInvalidJsonError(str(error), raw_content=raw_content) from error
    if not isinstance(parsed, dict):
        await _write_llm_usage_log(
            call_type="market_heartbeat",
            symbol=symbol,
            model=GROQ_MARKET_HEARTBEAT_MODEL,
            status="invalid_json",
            input_chars=input_chars,
            output_chars=len(raw_content),
            max_tokens=350,
            headers=headers,
            response=response,
            error_reason="invalid JSON",
            error_message="top-level JSON is not an object",
        )
        raise AIInvalidJsonError("top-level JSON is not an object", raw_content=raw_content)
    usage_log_id = await _write_llm_usage_log(
        call_type="market_heartbeat",
        symbol=symbol,
        model=GROQ_MARKET_HEARTBEAT_MODEL,
        status="success",
        input_chars=input_chars,
        output_chars=len(raw_content),
        max_tokens=350,
        headers=headers,
        response=response,
    )
    return LLMJsonResult(raw_content, parsed, usage_log_id)


def build_market_report_prompt(input_payload: dict) -> str:
    report_type = str(input_payload.get("report_type") or "daily").strip().lower()
    overview_label = "Weekly overview" if report_type == "weekly" else "Market overview"
    news_label = "Weekly news theme" if report_type == "weekly" else "News context"
    return (
        "Return valid JSON only, in English.\n"
        "Use exactly these fields: report_type, title, market_overview, coin_summaries, "
        "news_context, possible_action, telegram_message.\n"
        f"report_type must be {report_type!r}.\n"
        "coin_summaries must be an array of objects with symbol and summary.\n"
        "telegram_message must be concise, sectioned, and readable in Telegram.\n"
        "Mention all active coins from input once in the Coins section. Use the supplied "
        "coin symbols and do not invent symbols.\n"
        'telegram_message must end with exactly this final line: "Not financial advice."\n'
        "Do not omit the disclaimer. Do not wrap the disclaimer in Markdown italics, bold, "
        "quotes, or punctuation.\n"
        "Use this Telegram structure:\n"
        f"📊 {'Weekly' if report_type == 'weekly' else 'Daily'} Market Report\n\n"
        f"{overview_label}:\n"
        "<1-2 short sentences across active coins>\n\n"
        "Coins:\n"
        "• BTC: $..., 24h ...\n"
        "• ETH: $..., 24h ...\n\n"
        f"{news_label}:\n"
        "<1-2 short sentences or No major market-wide news selected.>\n\n"
        "Possible action:\n"
        "<one cautious non-prescriptive sentence>\n\n"
        "Not financial advice.\n"
        "No raw JSON in telegram_message. No dense paragraphs. No direct buy, sell, "
        "short, or long commands. Do not provide personalised financial advice.\n\n"
        "Input JSON:\n"
        f"{json.dumps(input_payload, ensure_ascii=False, sort_keys=True)}"
    )


async def ask_market_report_raw(input_payload: dict) -> tuple[str, dict]:
    """Ask the LLM for one cached market-wide report and return raw + parsed JSON."""
    report_type = str(input_payload.get("report_type") or "").strip().lower()
    call_type = f"{report_type}_report" if report_type in {"daily", "weekly"} else "market_report"
    prompt = build_market_report_prompt(input_payload)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    response_format = {"type": "json_object"} if _groq_json_mode_enabled() else None

    try:
        response, headers, input_chars = await _run_groq_chat_completion(
            call_type=call_type,
            symbol=None,
            model=GROQ_REPORT_MODEL,
            messages=messages,
            max_tokens=800,
            response_format=response_format,
            timeout=20,
        )
    except Exception as error:
        if _is_groq_rate_limit_error(error):
            raise AIGroqRateLimitError(str(error)) from error
        raise
    raw_content = _response_content(response)
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_content.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as error:
        await _write_llm_usage_log(
            call_type=call_type,
            symbol=None,
            model=GROQ_REPORT_MODEL,
            status="invalid_json",
            input_chars=input_chars,
            output_chars=len(raw_content),
            max_tokens=800,
            headers=headers,
            response=response,
            error_reason="invalid JSON",
            error_message=_safe_error_message(error),
        )
        raise AIInvalidJsonError(str(error), raw_content=raw_content) from error
    if not isinstance(parsed, dict):
        await _write_llm_usage_log(
            call_type=call_type,
            symbol=None,
            model=GROQ_REPORT_MODEL,
            status="invalid_json",
            input_chars=input_chars,
            output_chars=len(raw_content),
            max_tokens=800,
            headers=headers,
            response=response,
            error_reason="invalid JSON",
            error_message="top-level JSON is not an object",
        )
        raise AIInvalidJsonError("top-level JSON is not an object", raw_content=raw_content)
    usage_log_id = await _write_llm_usage_log(
        call_type=call_type,
        symbol=None,
        model=GROQ_REPORT_MODEL,
        status="success",
        input_chars=input_chars,
        output_chars=len(raw_content),
        max_tokens=800,
        headers=headers,
        response=response,
    )
    return LLMJsonResult(raw_content, parsed, usage_log_id)


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


async def create_daily_report(
    current_price: float, change_24h: float, news_items: list[dict] | None = None
) -> dict | None:
    news_text = _build_news_text(news_items)
    prompt = f"""
Return only minified JSON with required fields: risk_level(low|medium|high),
market_interpretation, possible_actions(array), telegram_message.
telegram_message must be a concise, readable Telegram message
(about 7-10 short lines) using this style:
📊 BTC Daily Report

Price: $...
24h change: ...%
7d trend: optional if context helps
Risk level: ...

Market view:
<1 short sentence>

News:
<1 short sentence>

Possible action:
<1 cautious sentence>
Not financial advice.
No raw JSON in telegram_message. No dense paragraphs. No direct buy/sell advice.
Use cautious wording such as: consider reviewing exposure, consider waiting for
confirmation, monitor risk, avoid impulsive action.
Data: price={current_price:.2f}, change24h={change_24h:.4f}%.
News:\n{news_text}
"""
    result, usage_log_id = await _ask_json_with_usage(
        prompt,
        call_type="daily_report",
        symbol="BTC",
        model=GROQ_REPORT_MODEL,
    )
    if not result:
        return None
    required = {"risk_level", "market_interpretation", "possible_actions", "telegram_message"}
    if required - set(result.keys()):
        await mark_llm_usage_log_status(
            usage_log_id,
            status="schema_error",
            error_reason="schema validation failed",
            error_message="Daily report validation failed: missing required fields.",
        )
        logger.error("Daily report validation failed: missing required fields.")
        return None
    return result


async def create_weekly_report(
    current_price: float,
    change_24h: float | None,
    change_7d: float | None,
    news_items: list[dict] | None = None,
) -> dict | None:
    news_text = _build_news_text(news_items)
    change_24h_text = change_24h if change_24h is not None else "unknown"
    change_7d_text = change_7d if change_7d is not None else "unknown"
    prompt = f"""
Return only minified JSON with required fields: risk_level(low|medium|high),
weekly_interpretation, possible_actions(array), telegram_message.
telegram_message must be concise and easy to read in Telegram, using short sections and line breaks:
📊 BTC Weekly Report

Price: $...
7d trend: ...%
24h change: optional
Risk level: ...

Weekly market view:
<1 short sentence>

Weekly news theme:
<1 short sentence>

Possible action:
<1 cautious sentence>
Not financial advice.
No raw JSON in telegram_message. No dense paragraphs. No direct buy/sell advice.
Use cautious wording such as: consider reviewing exposure, consider waiting for
confirmation, monitor risk, avoid impulsive action.
Data: price={current_price:.2f}, change24h={change_24h_text}%,
change7d={change_7d_text}%.
News:\n{news_text}
"""
    result, usage_log_id = await _ask_json_with_usage(
        prompt,
        call_type="weekly_report",
        symbol="BTC",
        model=GROQ_REPORT_MODEL,
    )
    if not result:
        return None
    required = {"risk_level", "weekly_interpretation", "possible_actions", "telegram_message"}
    if required - set(result.keys()):
        await mark_llm_usage_log_status(
            usage_log_id,
            status="schema_error",
            error_reason="schema validation failed",
            error_message="Weekly report validation failed: missing required fields.",
        )
        logger.error("Weekly report validation failed: missing required fields.")
        return None
    return result
