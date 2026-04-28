import os

from dotenv import load_dotenv
from openai import AsyncOpenAI


load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

groq_client = AsyncOpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)


async def create_ai_alert_message(
    previous_price: float,
    current_price: float,
    price_change_percent: float,
    change_24h: float,
) -> str:
    """Create a human-friendly BTC alert message using Groq."""

    direction = "up" if price_change_percent > 0 else "down"

    prompt = f"""
You are a careful BTC monitoring assistant.

Create a short Telegram alert for the user.

Data:
- Previous BTC price: ${previous_price:,.2f}
- Current BTC price: ${current_price:,.2f}
- Movement since last check: {price_change_percent:.4f}%
- Direction: {direction}
- 24h change: {change_24h:.4f}%

Rules:
- Do not give financial advice.
- Do not tell the user to buy or sell.
- Keep it short.
- Use simple language.
- Classify severity as Low, Medium, or High.
- Explain why this movement may or may not matter.
- Maximum 6 lines.
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

    return response.choices[0].message.content
