import os
import json

from dotenv import load_dotenv
from openai import AsyncOpenAI


load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

groq_client = AsyncOpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)

REQUIRED_ALERT_FIELDS = {
    "severity",
    "price_summary",
    "news_relevance",
    "news_summary",
    "risk_note",
    "telegram_message",
}
ALLOWED_SEVERITY = {"low", "medium", "high"}
ALLOWED_NEWS_RELEVANCE = {"relevant", "partly_relevant", "not_relevant", "unknown"}


def build_fallback_alert_message(
    previous_price: float,
    current_price: float,
    price_change_percent: float,
    change_24h: float,
) -> str:
    severity = "high" if abs(price_change_percent) >= 2 else "medium" if abs(price_change_percent) >= 1 else "low"
    direction_text = "increase" if price_change_percent > 0 else "decrease" if price_change_percent < 0 else "no change"
    return (
        "🚨 BTC movement alert\n\n"
        f"Price: ${current_price:,.2f}\n"
        f"Move since last check: {price_change_percent:+.2f}%\n"
        f"24h change: {change_24h:+.2f}%\n"
        f"Severity: {severity.title()}\n\n"
        "Context: This appears to be a short-term "
        f"{direction_text} in BTC. Recent news relevance is unknown, so the move is not clearly explained by current headlines."
    )


def parse_ai_alert_response(raw_content: str | None) -> dict | None:
    if not raw_content:
        print("AI alert parsing failed: empty response.")
        return None
    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError as error:
        print(f"AI alert parsing failed: invalid JSON ({error}).")
        return None
    if not isinstance(parsed, dict):
        print("AI alert validation failed: top-level JSON is not an object.")
        return None
    missing = REQUIRED_ALERT_FIELDS - set(parsed.keys())
    if missing:
        print(f"AI alert validation failed: missing required fields {sorted(missing)}.")
        return None
    severity = str(parsed.get("severity", "")).strip().lower()
    news_relevance = str(parsed.get("news_relevance", "")).strip().lower()
    if severity not in ALLOWED_SEVERITY:
        print(f"AI alert validation failed: invalid severity '{severity}'.")
        return None
    if news_relevance not in ALLOWED_NEWS_RELEVANCE:
        print(f"AI alert validation failed: invalid news_relevance '{news_relevance}'.")
        return None
    for field in REQUIRED_ALERT_FIELDS:
        if not str(parsed.get(field, "")).strip():
            print(f"AI alert validation failed: field '{field}' is empty.")
            return None
    parsed["severity"] = severity
    parsed["news_relevance"] = news_relevance
    return parsed


async def create_ai_alert_message(
    previous_price: float,
    current_price: float,
    price_change_percent: float,
    change_24h: float,
    news_items: list[dict] | None = None,
) -> str:
    """Create a human-friendly BTC alert message using Groq."""

    direction = "up" if price_change_percent > 0 else "down"
    news_items = news_items or []

    if news_items:
        news_text = "\n".join(
            [
                f"- {item.get('title', 'No title')} ({item.get('source', 'Unknown source')})"
                for item in news_items
            ]
        )
    else:
        news_text = "No relevant recent news found."

    fallback_message = build_fallback_alert_message(
        previous_price=previous_price,
        current_price=current_price,
        price_change_percent=price_change_percent,
        change_24h=change_24h,
    )

    prompt = f"""
You are a careful BTC monitoring assistant.

Return only valid minified JSON. No markdown and no extra text.

Price data:
- Previous BTC price: ${previous_price:,.2f}
- Current BTC price: ${current_price:,.2f}
- Movement since last check: {price_change_percent:.4f}%
- Direction: {direction}
- 24h change: {change_24h:.4f}%

Recent crypto/BTC-related news:
{news_text}

Rules:
- Do not give financial advice.
- Do not tell the user to buy or sell.
- Keep it concise and readable.
- Use simple language.
- Severity must be one of: low, medium, high.
- News relevance must be one of: relevant, partly_relevant, not_relevant, unknown.
- If the news does not clearly explain the move, say so in news_summary.
- telegram_message must be a user-facing multi-line message with 4-7 short lines (blank lines are allowed).
- telegram_message must not look like JSON and must not be a single compressed line.
- telegram_message must include BTC symbol, current price, movement since last check, 24h change, severity, short interpretation, and whether news seems relevant.
- telegram_message should follow this style:
  🚨 BTC movement alert

  Price: $77,332
  Move since last check: +0.17%
  24h change: +1.54%
  Severity: Low

  Context: short neutral interpretation mentioning news relevance.
- telegram_message must stay neutral and must not tell the user to buy or sell.

Expected JSON fields:
{{
  "severity": "low|medium|high",
  "price_summary": "short price movement summary",
  "news_relevance": "relevant|partly_relevant|not_relevant|unknown",
  "news_summary": "short news explanation",
  "risk_note": "short neutral risk note with no financial advice",
  "telegram_message": "final user-facing Telegram alert"
}}
"""

    response = await groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a careful crypto monitoring assistant.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.3,
    )

    raw_content = response.choices[0].message.content
    structured = parse_ai_alert_response(raw_content)
    if structured is None:
        print("AI alert fallback used due to parsing/validation failure.")
        return fallback_message
    return structured["telegram_message"]
