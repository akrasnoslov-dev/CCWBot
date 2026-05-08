import asyncio

import ai_agent_groq

ALERT_ARGS = {
    "previous_price": 100000.0,
    "current_price": 102500.0,
    "price_change_percent": 2.5,
    "change_24h": 3.1,
    "change_7d": 5.2,
    "news_items": [
        {"title": "ETF inflows rise", "source": "Example News", "link": "https://example.com/etf"}
    ],
    "alert_threshold_percent": 2.0,
    "check_interval_seconds": 300,
}


VALID_TELEGRAM_MESSAGE = """BTC movement alert

Price: $102,500.00
Since last check: +2.50% in 300 sec
24h trend: +3.10%
7d trend: +5.20%
Risk level: Medium
Risk reason: Medium because the short-term move is notable and related news may affect sentiment, though the broader trend is not extreme.

Context:
Short-term movement is notable. Recent news appears partly relevant.

Possible action:
Monitor for continuation; no immediate action required.

Not financial advice."""


def test_parse_json_valid():
    assert ai_agent_groq._parse_json('{"risk_level":"medium"}') == {"risk_level": "medium"}


def test_parse_json_with_markdown_fence():
    assert ai_agent_groq._parse_json('```json\n{"risk_level":"medium"}\n```') == {
        "risk_level": "medium"
    }


def test_parse_json_empty_returns_none():
    assert ai_agent_groq._parse_json("") is None


def test_build_fallback_alert_message_contains_required_fields():
    message = ai_agent_groq.build_fallback_alert_message(
        previous_price=100000.0,
        current_price=102500.0,
        price_change_percent=2.5,
        change_24h=3.1,
        change_7d=5.2,
        alert_threshold_percent=2.0,
        check_interval_seconds=300,
    )

    assert "Price: $102,500.00" in message
    assert "Since last check: +2.50% in 300 sec" in message
    assert "24h trend: +3.10%" in message
    assert "7d trend: +5.20%" in message
    assert "Risk level: Medium\nRisk reason:" in message
    assert "stronger 24h trend" in message
    assert "Not financial advice." in message


def test_build_fallback_alert_message_omits_missing_7d_trend():
    message = ai_agent_groq.build_fallback_alert_message(
        previous_price=100000.0,
        current_price=102500.0,
        price_change_percent=2.5,
        change_24h=3.1,
        change_7d=None,
        alert_threshold_percent=2.0,
        check_interval_seconds=300,
    )

    assert "24h trend: +3.10%" in message
    assert "7d trend:" not in message
    assert "unknown" not in message.lower()


def test_create_ai_alert_payload_uses_fallback_without_groq_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(ai_agent_groq, "_groq_client", None)
    expected_fallback = ai_agent_groq.build_fallback_alert_message(
        ALERT_ARGS["previous_price"],
        ALERT_ARGS["current_price"],
        ALERT_ARGS["price_change_percent"],
        ALERT_ARGS["change_24h"],
        ALERT_ARGS["change_7d"],
        ALERT_ARGS["alert_threshold_percent"],
        ALERT_ARGS["check_interval_seconds"],
    )

    result = asyncio.run(ai_agent_groq.create_ai_alert_payload(**ALERT_ARGS))

    assert result == {"plain_text": expected_fallback, "html_text": None}


def test_is_structured_alert_message_returns_true_for_valid():
    assert ai_agent_groq._is_structured_alert_message(VALID_TELEGRAM_MESSAGE) is True


def test_is_structured_alert_message_returns_false_for_plain_text():
    assert ai_agent_groq._is_structured_alert_message("BTC moved quickly.") is False


def test_create_ai_alert_message_returns_string(monkeypatch):
    async def fake_ask_json(prompt):
        return {
            "news_relevance": "partly_relevant",
            "risk_reason": (
                "Medium because the short-term move is notable and related news may affect "
                "sentiment, though the broader trend is not extreme."
            ),
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
            "risk_reason": (
                "Medium because the short-term move is notable and related news may affect "
                "sentiment, though the broader trend is not extreme."
            ),
            "related_news_ids": [1],
            "telegram_message": VALID_TELEGRAM_MESSAGE,
        }

    monkeypatch.setattr(ai_agent_groq, "_ask_json", fake_ask_json)

    result = asyncio.run(ai_agent_groq.create_ai_alert_payload(**ALERT_ARGS))

    assert isinstance(result, dict)
    assert "plain_text" in result
    assert isinstance(result["plain_text"], str)


def test_sanitize_telegram_message_removes_raw_debug_and_unknown_7d():
    raw_message = """BTC movement alert

Price: $102,500.00
Since last check: +2.50% in 300 sec
24h trend: +3.10%
7d trend: unknown
Risk level: Medium
Risk reason: Consider buying now because momentum is strong and selling now if it reverses.

Context:
Short-term movement is notable.

Data: previous=100000.00, current=102500.00,
move=2.5000%, change24h=3.1000%,
change7d=unknown, threshold=2.0%, interval=300 sec.
News:
- ETF inflows rise
Debug:
model_notes=internal

Possible action:
Monitor for continuation; no immediate action required.

Not financial advice.
Not financial advice."""

    message = ai_agent_groq.sanitize_alert_message(raw_message)

    assert "7d trend:" not in message
    assert "Data:" not in message
    assert "News:" not in message
    assert "Debug:" not in message
    assert "model_notes=" not in message
    assert "move=" not in message
    assert "change24h=" not in message
    assert "change7d=" not in message
    assert "threshold=" not in message
    assert "interval=" not in message
    assert "buy now" not in message.lower()
    assert "sell now" not in message.lower()
    assert message.count("Not financial advice.") == 1


def test_sanitize_alert_message_adds_missing_risk_reason_after_risk_level():
    raw_message = """BTC movement alert

Price: $102,500.00
Since last check: +2.50% in 300 sec
24h trend: +3.10%
Risk level: High

Context:
Short-term movement is notable.

Possible action:
Monitor for continuation; no immediate action required.

Not financial advice."""

    message = ai_agent_groq.sanitize_alert_message(raw_message)

    assert "Risk level: High\nRisk reason:" in message
    assert "stronger 24h trend" in message
    assert message.find("Risk level: High") < message.find("Risk reason:")
    assert message.count("Not financial advice.") == 1


def test_fallback_risk_reason_for_small_move_uses_threshold_without_news():
    reason = ai_agent_groq._build_fallback_risk_reason(
        price_change_percent=0.0511,
        change_24h=0.0461,
        alert_threshold_percent=0.05,
        news_relevance="not_relevant",
        has_related_news=False,
    )

    assert reason == "The move crossed the alert threshold, but the 24h trend remains mild."
    assert "news" not in reason.lower()


def test_generic_or_news_inconsistent_risk_reason_is_replaced(monkeypatch):
    async def fake_ask_json(prompt):
        return {
            "news_relevance": "not_relevant",
            "risk_reason": "Based on market data and news.",
            "related_news_ids": [],
            "telegram_message": """BTC movement alert

Price: $100,051.10
Since last check: +0.05% in 60 sec
24h trend: +0.05%
Risk level: Medium
Risk reason: The risk level reflects the BTC move, 24h trend, and available news context.

Context:
The move is small, and recent news does not appear to be a clear driver.

Possible action:
Monitor for continuation; no immediate action required.

Not financial advice.""",
        }

    monkeypatch.setattr(ai_agent_groq, "_ask_json", fake_ask_json)
    args = {
        **ALERT_ARGS,
        "current_price": 100051.1,
        "price_change_percent": 0.0511,
        "change_24h": 0.0461,
        "change_7d": None,
        "news_items": [],
        "alert_threshold_percent": 0.05,
        "check_interval_seconds": 60,
    }

    result = asyncio.run(ai_agent_groq.create_ai_alert_payload(**args))
    message = result["plain_text"]

    assert "Risk reason: The move crossed the alert threshold, but the 24h trend remains mild." in message
    assert "Related news:" not in message
    assert "available news context" not in message
    assert "based on market data and news" not in message.lower()
    assert message.count("Not financial advice.") == 1


def test_related_news_reason_is_allowed_only_when_related_news_is_included(monkeypatch):
    async def fake_ask_json(prompt):
        return {
            "news_relevance": "partly_relevant",
            "risk_reason": (
                "Medium because the short-term move is notable and related news may affect "
                "sentiment, though the broader trend is not extreme."
            ),
            "related_news_ids": [1],
            "telegram_message": VALID_TELEGRAM_MESSAGE,
        }

    monkeypatch.setattr(ai_agent_groq, "_ask_json", fake_ask_json)

    result = asyncio.run(ai_agent_groq.create_ai_alert_payload(**ALERT_ARGS))
    message = result["plain_text"]

    assert "Risk reason: Medium because the short-term move is notable" in message
    assert "related news may affect sentiment" in message
    assert "Related news:" in message


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
