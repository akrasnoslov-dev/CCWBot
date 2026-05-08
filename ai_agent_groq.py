"""Groq-backed AI helpers.

The bot asks for structured JSON so code can validate output before posting messages.
When parsing/validation fails, callers fall back to deterministic templates.
All prompts explicitly avoid direct financial advice.
"""

import json
import logging
import os
import re
from html import escape

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
) -> str:
    """Deterministic fallback used when structured AI output cannot be trusted."""
    interval_text = f" in {check_interval_seconds} sec" if check_interval_seconds else ""
    weekly_trend_line = f"7d trend: {change_7d:+.2f}%\n" if change_7d is not None else ""
    return (
        "🚨 BTC movement alert\n\n"
        f"Price: ${current_price:,.2f}\n"
        f"Since last check: {price_change_percent:+.2f}%{interval_text}\n"
        f"24h trend: {change_24h:+.2f}%\n"
        f"{weekly_trend_line}"
        "Risk level: Medium\n"
        "Risk reason: The short-term BTC move is notable while broader context remains uncertain.\n\n"
        "Context:\n"
        "Short-term movement is notable while broader market context remains uncertain. "
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


def _fallback_risk_reason(
    price_change_percent: float | None = None,
    change_24h: float | None = None,
    news_relevance: str = "",
) -> str:
    news_relevance = news_relevance.strip()
    if news_relevance in {"relevant", "partly_relevant"}:
        return "Related news may affect short-term BTC sentiment."
    if price_change_percent is not None and abs(price_change_percent) >= 1:
        return "The short-term BTC move is elevated compared with normal monitoring noise."
    if change_24h is not None and abs(change_24h) >= 2:
        return "The 24h BTC trend is elevated, so short-term risk may be higher."
    return "The risk level reflects the BTC move, 24h trend, and available news context."


def _sanitize_risk_reason(reason: str, fallback_reason: str) -> str:
    cleaned = " ".join(str(reason or "").split())
    cleaned = _DIRECT_ADVICE_RE.sub("review risk", cleaned)
    cleaned = re.sub(r"(?i)\bnot financial advice\.?", "", cleaned).strip()
    if not cleaned:
        cleaned = fallback_reason
    first_sentence = re.match(r"^(.+?[.!?])(?:\s|$)", cleaned)
    if first_sentence:
        cleaned = first_sentence.group(1)
    if len(cleaned) > _RISK_REASON_MAX_CHARS:
        cleaned = cleaned[: _RISK_REASON_MAX_CHARS - 1].rstrip(" ,;:") + "."
    return cleaned.rstrip(".!?") + "."


def _ensure_risk_reason_after_level(message: str, risk_reason: str) -> str:
    lines = message.splitlines()
    if not any(line.strip().startswith("Risk level:") for line in lines):
        return message

    cleaned_reason = _sanitize_risk_reason(
        risk_reason,
        "The risk level reflects the BTC move, 24h trend, and available news context.",
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
    with_risk_reason = _ensure_risk_reason_after_level(
        sanitized,
        "The risk level reflects the BTC move, 24h trend, and available news context.",
    )
    return _sanitize_telegram_message(with_risk_reason)


def _build_alert_message_with_related_news(
    structured: dict,
    price_change_percent: float,
    change_24h: float,
) -> str:
    fallback_reason = _fallback_risk_reason(
        price_change_percent,
        change_24h,
        str(structured.get("news_relevance", "")).strip(),
    )
    telegram_message = _sanitize_telegram_message(
        str(structured.get("telegram_message", "")).strip()
    )
    telegram_message = _ensure_risk_reason_after_level(
        telegram_message,
        str(structured.get("risk_reason", "")).strip() or fallback_reason,
    )
    telegram_message = _sanitize_telegram_message(telegram_message)
    related_news_section = _format_related_news_section(
        str(structured.get("news_relevance", "")).strip(), structured.get("related_news")
    )
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
) -> str:
    change_7d_text = f"{change_7d:.4f}%" if change_7d is not None else "unavailable"
    trend_7d_instruction = "7d trend: ...%\n" if change_7d is not None else ""
    trend_7d_rule = (
        "Include the 7d trend line only when the provided 7d value is available. "
        "When it is unavailable, omit the entire 7d trend line. Never write '7d trend: unknown'."
    )
    threshold_text = alert_threshold_percent if alert_threshold_percent is not None else "unknown"
    interval_text = check_interval_seconds if check_interval_seconds is not None else "unknown"
    return f"""
Return only minified JSON with fields severity, short_term_trend, weekly_trend,
news_relevance, risk_level, risk_reason, market_interpretation, possible_actions,
related_news_ids, telegram_message.
Values: severity/risk_level low|medium|high; risk_reason one short sentence;
trends up|down|flat|unclear;
news_relevance relevant|partly_relevant|not_relevant|unknown.
Do not give direct buy/sell advice. Never say 'buy now' or 'sell now'.
telegram_message must be multi-line, section-based, and never a dense paragraph.
Risk level guidance:
- Low: small price movement, calm 24h trend, no clearly relevant news.
- Medium: moderate price movement, uncertain 24h trend, or relevant news that may affect sentiment.
- High: strong price movement, sharp 24h trend, or clearly exceptional news/risk.
High should be rare.
If both the short-term movement and 24h trend are small, do not use High unless the news context clearly indicates exceptional risk.
If using High despite small price movement, risk_reason must explicitly explain why.
related_news_ids must be an array containing up to 2 numeric IDs from the provided News list.
Set related_news_ids to [] when news_relevance is not_relevant or unknown.
Do not include raw Data or News blocks in telegram_message. {trend_7d_rule}
telegram_message must include both:
Risk level: Low|Medium|High
Risk reason: <short reason>
Use this exact style and labels:
🚨 BTC movement alert

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
Data: previous={previous_price:.2f}, current={current_price:.2f},
move={price_change_percent:.4f}%, change24h={change_24h:.4f}%,
change7d={change_7d_text}, threshold={threshold_text}%, interval={interval_text} sec.
News:\n{news_text}
"""


def _build_news_text(news_items: list[dict] | None) -> str:
    return (
        "\n".join(f"- {item.get('title', 'No title')}" for item in (news_items or []))
        or "No relevant recent news found."
    )


async def _ask_json(prompt: str) -> dict | None:
    """Request JSON from Groq/OpenAI-compatible API and parse it."""
    client = get_groq_client()
    response = await client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
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
) -> str:
    """Create BTC alert message from structured model output with safe fallback."""
    result = await create_ai_alert_payload(
        previous_price,
        current_price,
        price_change_percent,
        change_24h,
        change_7d,
        news_items,
        alert_threshold_percent,
        check_interval_seconds,
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
