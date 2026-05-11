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

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

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


def _groq_json_mode_enabled() -> bool:
    return os.getenv("GROQ_JSON_MODE", "true").strip().lower() not in {"0", "false", "no", "off"}


def _is_groq_json_validation_error(error: Exception) -> bool:
    message = str(error).lower()
    return "validate json" in message or "json validation" in message


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
            max_retries=1,
        )
    return _groq_client


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
) -> str:
    """Deterministic fallback used when structured AI output cannot be trusted."""
    interval_text = f" in {check_interval_seconds} sec" if check_interval_seconds else ""
    weekly_trend_line = f"7d trend: {change_7d:+.2f}%\n" if change_7d is not None else ""
    display_symbol = symbol.upper()
    risk_reason = _build_fallback_risk_reason(
        price_change_percent=price_change_percent,
        change_24h=change_24h,
        alert_threshold_percent=alert_threshold_percent,
        news_relevance="not_relevant",
        has_related_news=False,
    )
    return (
        f"🚨 {display_symbol} movement alert\n\n"
        f"Price: ${current_price:,.2f}\n"
        f"Since last check: {price_change_percent:+.2f}%{interval_text}\n"
        f"24h trend: {change_24h:+.2f}%\n"
        f"{weekly_trend_line}"
        "Risk level: Medium\n"
        f"Risk reason: {risk_reason}\n\n"
        "Context:\n"
        f"Short-term {coin_name} movement is notable while broader market context "
        "remains uncertain. "
        "Recent news does not appear to be a clear driver.\n\n"
        "Possible action:\n"
        "Monitor for continuation; no immediate action required.\n\n"
        "Not financial advice."
    )


def _is_structured_alert_message(message: str) -> bool:
    required_markers = [
        "Since last check:",
        "24h trend:",
        "Risk level:",
        "Risk reason:",
        "Context:",
        "Possible action:",
    ]
    return (
        "\n" in message
        and all(marker in message for marker in required_markers)
        and message.find("Risk level:") < message.find("Risk reason:")
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
        if not title:
            continue
        lines.append(f"- {title} - {source}" if source else f"- {title}")

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
    trend_7d_instruction = "7d trend: ...%\n" if change_7d is not None else ""
    trend_7d_rule = (
        "Include the 7d trend line only when the provided 7d value is available. "
        "When it is unavailable, omit the entire 7d trend line. Never write '7d trend: unknown'."
    )
    threshold_text = alert_threshold_percent if alert_threshold_percent is not None else "unknown"
    interval_text = check_interval_seconds if check_interval_seconds is not None else "unknown"
    return f"""
Return one valid JSON object only.
Do not use Markdown.
Do not wrap in code fences.
Do not include text before or after JSON.
All string values must be valid JSON strings.
Escape newlines inside telegram_message as \\n.

Required JSON fields:
- news_relevance: "relevant", "partly_relevant", "not_relevant", or "unknown"
- risk_level: "Low", "Medium", or "High"
- risk_reason: one short specific sentence
- related_news_ids: an array with up to 2 numeric IDs from the News list
- telegram_message: one formatted alert message string

Do not give direct buy/sell advice. Never say 'buy now' or 'sell now'.
telegram_message must be multi-line, section-based, and never a dense paragraph.
Risk level guidance:
- Low: small price movement, calm 24h trend, no clearly relevant news.
- Medium: moderate price movement, uncertain 24h trend, or relevant news
  that may affect sentiment.
- High: strong price movement, sharp 24h trend, or clearly exceptional news/risk.
High should be rare.
If both the short-term movement and 24h trend are small, do not use High
unless the news context clearly indicates exceptional risk.
If using High despite small price movement, risk_reason must explicitly explain why.
risk_reason must explain why this risk_level was chosen over lower or higher levels.
Consider {coin_name}'s coin-specific volatility when explaining risk.
risk_reason must cite concrete alert factors: short-term move size, 24h trend,
threshold crossing when relevant, and news only when news_relevance is
relevant or partly_relevant.
risk_reason must not use vague boilerplate such as "based on market data and
news" or "current conditions".
risk_reason must not mention news as a risk driver when news_relevance is
not_relevant or unknown.
Set related_news_ids to [] when news_relevance is not_relevant or unknown.
Do not include raw Data or News blocks in telegram_message. {trend_7d_rule}
telegram_message must include both:
Risk level: Low|Medium|High
Risk reason: <short reason>
Use this exact style and labels:
🚨 {display_symbol} movement alert

Price: $...
Since last check: ...% in ... sec
24h trend: ...%
{trend_7d_instruction}Risk level: Low|Medium|High
Risk reason: <one short sentence explaining the level>

Context:
<1-2 short cautious sentences, including whether recent news appears relevant to this move>

Possible action:
<1 short cautious sentence>

Not financial advice.

Alert data:
- Symbol: {display_symbol}
- Coin name: {coin_name}
- Previous price: ${previous_price:.2f}
- Current price: ${current_price:.2f}
- Since last check: {price_change_percent:.4f}%
- 24h trend: {change_24h:.4f}%
- 7d trend: {change_7d_text}
- Alert threshold: {threshold_text}%
- Check interval: {interval_text} sec

News:
{news_text}
"""


def _build_news_text(news_items: list[dict] | None) -> str:
    return (
        "\n".join(f"- {item.get('title', 'No title')}" for item in (news_items or []))
        or "No relevant recent news found."
    )


async def _ask_json(prompt: str) -> dict | None:
    """Request JSON from Groq/OpenAI-compatible API and parse it."""
    client = get_groq_client()
    request_kwargs = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 900,
    }
    json_mode_enabled = _groq_json_mode_enabled()
    if json_mode_enabled:
        request_kwargs["response_format"] = {"type": "json_object"}

    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(**request_kwargs),
            timeout=25,
        )
    except Exception as error:
        if not json_mode_enabled or not _is_groq_json_validation_error(error):
            raise
        logger.warning("Groq JSON mode failed; retrying once without response_format.")
        retry_kwargs = dict(request_kwargs)
        retry_kwargs.pop("response_format", None)
        response = await asyncio.wait_for(
            client.chat.completions.create(**retry_kwargs),
            timeout=25,
        )
    return _parse_json(response.choices[0].message.content)


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
    except Exception as error:
        logger.warning("AI alert generation failed; using fallback alert message. error=%s", error)
        structured = None
    if not structured or not structured.get("telegram_message"):
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
        return {"plain_text": plain_message, "html_text": None}
    structured["related_news"] = _extract_related_news_from_ids(
        str(structured.get("news_relevance", "")).strip(),
        structured.get("related_news_ids"),
        indexed_news_items,
    )
    plain_message = _build_alert_message_with_related_news(
        structured,
        price_change_percent,
        change_24h,
        alert_threshold_percent,
    )
    if not _is_structured_alert_message(plain_message):
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
        return {"plain_text": plain_message, "html_text": None}
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
    result = await _ask_json(prompt)
    if not result:
        return None
    required = {"risk_level", "market_interpretation", "possible_actions", "telegram_message"}
    if required - set(result.keys()):
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
    result = await _ask_json(prompt)
    if not result:
        return None
    required = {"risk_level", "weekly_interpretation", "possible_actions", "telegram_message"}
    if required - set(result.keys()):
        logger.error("Weekly report validation failed: missing required fields.")
        return None
    return result


async def classify_strong_signal(
    current_price: float,
    change_24h: float,
    change_7d: float | None,
    news_items: list[dict] | None = None,
) -> dict | None:
    """Classify strong-signal conditions with structured output for downstream checks."""
    news_text = _build_news_text(news_items)
    change_7d_text = change_7d if change_7d is not None else "unknown"
    prompt = f"""
Return only minified JSON with fields:
signal_strength(none|weak|medium|strong), direction(bullish|bearish|mixed|unclear),
risk_level(low|medium|high), should_alert(boolean), reason, possible_actions(array),
telegram_message.
Only cautious wording. Include 'Not financial advice.' in telegram_message.
Data: price={current_price:.2f}, change24h={change_24h:.4f}%,
change7d={change_7d_text}%.
News:\n{news_text}
"""
    result = await _ask_json(prompt)
    if not result:
        return None
    required = {
        "signal_strength",
        "direction",
        "risk_level",
        "should_alert",
        "reason",
        "possible_actions",
        "telegram_message",
    }
    if required - set(result.keys()):
        logger.error("Strong-signal validation failed: missing required fields.")
        return None
    return result
