"""Groq-backed AI helpers.

The bot asks for structured JSON so code can validate output before posting messages.
When parsing/validation fails, callers fall back to deterministic templates.
All prompts explicitly avoid direct financial advice.
"""

import json
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

groq_client = AsyncOpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")

SYSTEM_PROMPT = "You are a careful crypto monitoring assistant."


def _parse_json(raw_content: str | None) -> dict | None:
    """Parse and validate top-level JSON object responses from the model."""
    if not raw_content:
        print("AI parsing failed: empty response.")
        return None
    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError as error:
        print(f"AI parsing failed: invalid JSON ({error}).")
        return None
    if not isinstance(parsed, dict):
        print("AI parsing failed: top-level JSON is not an object.")
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
    weekly_trend = f"{change_7d:+.2f}%" if change_7d is not None else "unknown"
    interval_text = f" in {check_interval_seconds} sec" if check_interval_seconds else ""
    threshold_text = f"{alert_threshold_percent:.2f}%" if alert_threshold_percent is not None else "unknown"
    return (
        "🚨 BTC movement alert\n\n"
        f"Price: ${current_price:,.2f}\n"
        f"Since last check: {price_change_percent:+.2f}%{interval_text}\n"
        f"Alert threshold: {threshold_text}\n"
        f"24h trend: {change_24h:+.2f}%\n"
        f"7d trend: {weekly_trend}\n"
        "Risk level: Medium\n\n"
        "Why this alert:\n"
        "BTC moved above your configured threshold since the previous check.\n\n"
        "Context:\n"
        "Short-term movement is notable while broader market context remains uncertain.\n\n"
        "Possible action:\n"
        "Monitor for confirmation before acting.\n\n"
        "Not financial advice."
    )


def _is_structured_alert_message(message: str) -> bool:
    required_markers = [
        "Since last check:",
        "Alert threshold:",
        "24h trend:",
        "Why this alert:",
        "Context:",
        "Possible action:",
    ]
    return "\n" in message and all(marker in message for marker in required_markers)


async def _ask_json(prompt: str) -> dict | None:
    """Request JSON from Groq/OpenAI-compatible API and parse it."""
    response = await groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
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
    news_text = "\n".join([f"- {item.get('title', 'No title')}" for item in (news_items or [])]) or "No relevant recent news found."
    prompt = f"""
Return only minified JSON with fields severity, short_term_trend, weekly_trend, news_relevance, risk_level, market_interpretation, possible_actions, telegram_message.
Values: severity/risk_level low|medium|high; trends up|down|flat|unclear; news_relevance relevant|partly_relevant|not_relevant|unknown.
Do not give direct buy/sell advice. Never say 'buy now' or 'sell now'.
telegram_message must be multi-line, section-based, and never a dense paragraph.
Use this exact style and labels:
🚨 BTC movement alert

Price: $...
Since last check: ...% in ... sec
Alert threshold: ...%
24h trend: ...%
7d trend: ...% or unknown
Risk level: Low|Medium|High

Why this alert:
BTC moved above your configured threshold since the previous check.

Context:
<1 short cautious sentence>

Possible action:
<1 short cautious sentence>

Not financial advice.
Data: previous={previous_price:.2f}, current={current_price:.2f}, move={price_change_percent:.4f}%, change24h={change_24h:.4f}%, change7d={change_7d if change_7d is not None else 'unknown'}, threshold={alert_threshold_percent if alert_threshold_percent is not None else 'unknown'}%, interval={check_interval_seconds if check_interval_seconds is not None else 'unknown'} sec.
News:\n{news_text}
"""
    structured = await _ask_json(prompt)
    if not structured or not structured.get("telegram_message"):
        print("AI alert fallback used due to parsing/validation failure.")
        return build_fallback_alert_message(previous_price, current_price, price_change_percent, change_24h, change_7d, alert_threshold_percent, check_interval_seconds)
    telegram_message = str(structured["telegram_message"])
    if not _is_structured_alert_message(telegram_message):
        print("AI alert fallback used due to non-structured telegram_message.")
        return build_fallback_alert_message(previous_price, current_price, price_change_percent, change_24h, change_7d, alert_threshold_percent, check_interval_seconds)
    return telegram_message


async def create_daily_report(current_price: float, change_24h: float, news_items: list[dict] | None = None) -> dict | None:
    news_text = "\n".join([f"- {item.get('title', 'No title')}" for item in (news_items or [])]) or "No relevant recent news found."
    prompt = f"""
Return only minified JSON with required fields: risk_level(low|medium|high), market_interpretation, possible_actions(array), telegram_message.
telegram_message must be a concise, readable Telegram message (about 7-10 short lines) using this style:
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
Use cautious wording such as: consider reviewing exposure, consider waiting for confirmation, monitor risk, avoid impulsive action.
Data: price={current_price:.2f}, change24h={change_24h:.4f}%.
News:\n{news_text}
"""
    result = await _ask_json(prompt)
    if not result:
        return None
    required = {"risk_level", "market_interpretation", "possible_actions", "telegram_message"}
    if required - set(result.keys()):
        print("Daily report validation failed: missing required fields.")
        return None
    return result


async def create_weekly_report(current_price: float, change_24h: float | None, change_7d: float | None, news_items: list[dict] | None = None) -> dict | None:
    news_text = "\n".join([f"- {item.get('title', 'No title')}" for item in (news_items or [])]) or "No relevant recent news found."
    prompt = f"""
Return only minified JSON with required fields: risk_level(low|medium|high), weekly_interpretation, possible_actions(array), telegram_message.
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
Use cautious wording such as: consider reviewing exposure, consider waiting for confirmation, monitor risk, avoid impulsive action.
Data: price={current_price:.2f}, change24h={change_24h if change_24h is not None else 'unknown'}%, change7d={change_7d if change_7d is not None else 'unknown'}%.
News:\n{news_text}
"""
    result = await _ask_json(prompt)
    if not result:
        return None
    required = {"risk_level", "weekly_interpretation", "possible_actions", "telegram_message"}
    if required - set(result.keys()):
        print("Weekly report validation failed: missing required fields.")
        return None
    return result


async def classify_strong_signal(current_price: float, change_24h: float, change_7d: float | None, news_items: list[dict] | None = None) -> dict | None:
    """Classify strong-signal conditions with structured output for downstream checks."""
    news_text = "\n".join([f"- {item.get('title', 'No title')}" for item in (news_items or [])]) or "No relevant recent news found."
    prompt = f"""
Return only minified JSON with fields:
signal_strength(none|weak|medium|strong), direction(bullish|bearish|mixed|unclear), risk_level(low|medium|high), should_alert(boolean), reason, possible_actions(array), telegram_message.
Only cautious wording. Include 'Not financial advice.' in telegram_message.
Data: price={current_price:.2f}, change24h={change_24h:.4f}%, change7d={change_7d if change_7d is not None else 'unknown'}%.
News:\n{news_text}
"""
    result = await _ask_json(prompt)
    if not result:
        return None
    required = {"signal_strength", "direction", "risk_level", "should_alert", "reason", "possible_actions", "telegram_message"}
    if required - set(result.keys()):
        print("Strong-signal validation failed: missing required fields.")
        return None
    return result
