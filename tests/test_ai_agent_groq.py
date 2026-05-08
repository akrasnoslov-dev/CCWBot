import asyncio
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import ai_agent_groq


ALERT_ARGS = {
    "previous_price": 100000.0,
    "current_price": 102500.0,
    "price_change_percent": 2.5,
    "change_24h": 3.1,
    "change_7d": 5.2,
    "news_items": [{"title": "ETF inflows rise", "source": "Example News", "link": "https://example.com/etf"}],
    "alert_threshold_percent": 2.0,
    "check_interval_seconds": 300,
}


VALID_TELEGRAM_MESSAGE = """BTC movement alert

Price: $102,500.00
Since last check: +2.50% in 300 sec
24h trend: +3.10%
7d trend: +5.20%
Risk level: Medium

Context:
Short-term movement is notable. Recent news appears partly relevant.

Possible action:
Monitor for continuation; no immediate action required.

Not financial advice."""


def test_create_ai_alert_message_returns_string(monkeypatch):
    async def fake_ask_json(prompt):
        return {
            "news_relevance": "partly_relevant",
            "related_news_ids": [1],
            "telegram_message": VALID_TELEGRAM_MESSAGE,
        }

    monkeypatch.setattr(ai_agent_groq, "_ask_json", fake_ask_json)

    result = asyncio.run(ai_agent_groq.create_ai_alert_message(**ALERT_ARGS))

    assert isinstance(result, str)
    assert not isinstance(result, dict)


def test_create_ai_alert_payload_returns_dict_with_plain_text(monkeypatch):
    async def fake_ask_json(prompt):
        return {
            "news_relevance": "partly_relevant",
            "related_news_ids": [1],
            "telegram_message": VALID_TELEGRAM_MESSAGE,
        }

    monkeypatch.setattr(ai_agent_groq, "_ask_json", fake_ask_json)

    result = asyncio.run(ai_agent_groq.create_ai_alert_payload(**ALERT_ARGS))

    assert isinstance(result, dict)
    assert "plain_text" in result
    assert isinstance(result["plain_text"], str)


def test_alert_message_and_payload_use_fallback_when_model_response_is_invalid(monkeypatch):
    async def fake_ask_json(prompt):
        return {"telegram_message": "dense invalid response"}

    monkeypatch.setattr(ai_agent_groq, "_ask_json", fake_ask_json)
    expected_fallback = ai_agent_groq.build_fallback_alert_message(
        ALERT_ARGS["previous_price"],
        ALERT_ARGS["current_price"],
        ALERT_ARGS["price_change_percent"],
        ALERT_ARGS["change_24h"],
        ALERT_ARGS["change_7d"],
        ALERT_ARGS["alert_threshold_percent"],
        ALERT_ARGS["check_interval_seconds"],
    )

    message_result = asyncio.run(ai_agent_groq.create_ai_alert_message(**ALERT_ARGS))
    payload_result = asyncio.run(ai_agent_groq.create_ai_alert_payload(**ALERT_ARGS))

    assert message_result == expected_fallback
    assert payload_result["plain_text"] == expected_fallback
