import asyncio
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import bot.runtime as runtime
import bot.services.ai_agent_groq as ai_agent_groq
from bot.db.database import Base, LlmUsageLog

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


VALID_RISK_REASON = (
    "Medium because the short-term move is notable and related news may affect sentiment, "
    "though the broader trend is not extreme."
)


VALID_TELEGRAM_MESSAGE = """BTC movement alert

Price: $102,500.00
Since last check: +2.50% in 300 sec
24h trend: +3.10%
7d trend: +5.20%
Risk level: Medium
Risk reason: {risk_reason}

Context:
Short-term movement is notable. Recent news appears partly relevant.

Possible action:
Monitor for continuation; no immediate action required.

Not financial advice."""
VALID_TELEGRAM_MESSAGE = VALID_TELEGRAM_MESSAGE.format(risk_reason=VALID_RISK_REASON)


async def build_usage_session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_local = async_sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    return engine, session_local


def valid_compact_alert_response(**overrides):
    response = {
        "news_relevance": "partly_relevant",
        "risk_level": "Medium",
        "risk_reason": VALID_RISK_REASON,
        "context_sentence": (
            "Short-term movement is notable and recent news appears partly relevant."
        ),
        "possible_action": "Monitor for continuation; no immediate action required.",
        "related_news_ids": [1],
    }
    response.update(overrides)
    return response


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
    assert "5m move: +2.50%" in message
    assert "24h trend: +3.10%" in message
    assert "AI analysis is temporarily unavailable." in message
    assert "Possible actions:" not in message
    assert "Not financial advice." in message


def test_build_fallback_alert_message_is_symbol_aware():
    message = ai_agent_groq.build_fallback_alert_message(
        previous_price=2900.0,
        current_price=3000.0,
        price_change_percent=3.45,
        change_24h=2.0,
        alert_threshold_percent=2.0,
        check_interval_seconds=300,
        symbol="ETH",
        coin_name="Ethereum",
    )

    assert "ETH basic price alert" in message
    assert "BTC basic price alert" not in message


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


def test_ask_json_mode_success_returns_parsed_payload(monkeypatch):
    captured_kwargs = {}

    class FakeCompletions:
        async def create(self, **kwargs):
            captured_kwargs.update(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content='{"risk_level":"Medium"}'))]
            )

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    monkeypatch.setenv("GROQ_JSON_MODE", "true")
    monkeypatch.setattr(ai_agent_groq, "get_groq_client", lambda: fake_client)

    result = asyncio.run(ai_agent_groq._ask_json("prompt"))

    assert result == {"risk_level": "Medium"}
    assert captured_kwargs["response_format"] == {"type": "json_object"}


def test_ask_json_requests_json_object_and_returns_none_for_invalid_json(monkeypatch):
    captured_kwargs = {}

    class FakeCompletions:
        async def create(self, **kwargs):
            captured_kwargs.update(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content='{"telegram_message": "unterminated')
                    )
                ]
            )

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    monkeypatch.setenv("GROQ_JSON_MODE", "true")
    monkeypatch.setattr(ai_agent_groq, "get_groq_client", lambda: fake_client)

    result = asyncio.run(ai_agent_groq._ask_json("prompt"))

    assert result is None
    assert captured_kwargs["temperature"] == 0.0
    assert captured_kwargs["max_tokens"] == 450
    assert captured_kwargs["response_format"] == {"type": "json_object"}


def test_ask_json_omits_response_format_when_json_mode_disabled(monkeypatch):
    captured_kwargs = {}

    class FakeCompletions:
        async def create(self, **kwargs):
            captured_kwargs.update(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content='{"risk_level":"Medium"}'))]
            )

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    monkeypatch.setenv("GROQ_JSON_MODE", "false")
    monkeypatch.setattr(ai_agent_groq, "get_groq_client", lambda: fake_client)

    result = asyncio.run(ai_agent_groq._ask_json("prompt"))

    assert result == {"risk_level": "Medium"}
    assert "response_format" not in captured_kwargs


def test_ask_json_validation_failure_retries_without_response_format(monkeypatch):
    request_kwargs = []

    class FakeCompletions:
        async def create(self, **kwargs):
            request_kwargs.append(kwargs)
            if len(request_kwargs) == 1:
                raise RuntimeError("Failed to validate JSON. Please adjust your prompt.")
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content='{"risk_level":"Medium"}'))]
            )

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    monkeypatch.setenv("GROQ_JSON_MODE", "true")
    monkeypatch.setenv("GROQ_JSON_MODE_RETRY_PLAIN", "true")
    monkeypatch.setattr(ai_agent_groq, "get_groq_client", lambda: fake_client)

    result = asyncio.run(ai_agent_groq._ask_json("prompt"))

    assert result == {"risk_level": "Medium"}
    assert request_kwargs[0]["response_format"] == {"type": "json_object"}
    assert "response_format" not in request_kwargs[1]


def test_ask_json_validation_failure_returns_none_when_plain_retry_disabled(monkeypatch):
    request_kwargs = []

    class FakeCompletions:
        async def create(self, **kwargs):
            request_kwargs.append(kwargs)
            raise RuntimeError("Failed to validate JSON. Please adjust your prompt.")

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    monkeypatch.setenv("GROQ_JSON_MODE", "true")
    monkeypatch.setenv("GROQ_JSON_MODE_RETRY_PLAIN", "false")
    monkeypatch.setattr(ai_agent_groq, "get_groq_client", lambda: fake_client)

    result = asyncio.run(ai_agent_groq._ask_json("prompt"))

    assert result is None
    assert len(request_kwargs) == 1


def test_ask_json_uses_hard_15_second_timeout(monkeypatch):
    captured_timeout = None

    class FakeCompletions:
        async def create(self, **kwargs):
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content='{"risk_level":"Medium"}'))]
            )

    async def fake_wait_for(awaitable, timeout):
        nonlocal captured_timeout
        captured_timeout = timeout
        return await awaitable

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    monkeypatch.setattr(ai_agent_groq, "get_groq_client", lambda: fake_client)
    monkeypatch.setattr(ai_agent_groq.asyncio, "wait_for", fake_wait_for)

    result = asyncio.run(ai_agent_groq._ask_json("prompt"))

    assert result == {"risk_level": "Medium"}
    assert captured_timeout == 15


def test_ask_event_analysis_raw_uses_event_model_max_tokens_and_logs_usage(monkeypatch):
    async def run_test():
        engine, session_local = await build_usage_session_factory()
        captured_kwargs = {}
        try:
            monkeypatch.setattr(runtime, "DB_ENABLED", True)
            runtime.DB_SESSION_LOCAL.set(session_local)
            monkeypatch.setattr(
                ai_agent_groq,
                "GROQ_EVENT_ANALYSIS_MODEL",
                "event-model",
            )

            class FakeCompletions:
                async def create(self, **kwargs):
                    captured_kwargs.update(kwargs)
                    return SimpleNamespace(
                        choices=[
                            SimpleNamespace(
                                message=SimpleNamespace(
                                    content=(
                                        '{"symbol":"BTC","should_alert":false,'
                                        '"event_key":null,"title":null,'
                                        '"message_body":null,"related_news_ids":[],'
                                        '"possible_action":null,"urgency":null,'
                                        '"confidence":null,'
                                        '"reason_for_no_alert":"No event."}'
                                    )
                                )
                            )
                        ],
                        usage=SimpleNamespace(
                            prompt_tokens=12,
                            completion_tokens=8,
                            total_tokens=20,
                        ),
                        headers={"x-ratelimit-remaining-requests": "999"},
                    )

            fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
            monkeypatch.setattr(ai_agent_groq, "get_groq_client", lambda: fake_client)

            await ai_agent_groq.ask_event_analysis_raw({"symbol": "BTC"})

            assert captured_kwargs["model"] == "event-model"
            assert captured_kwargs["max_tokens"] == 300
            prompt = captured_kwargs["messages"][1]["content"]
            assert "Return valid JSON only." in prompt
            assert "symbol, should_alert, event_key, title, message_body" in prompt
            assert "urgency: low, normal, high" in prompt
            assert "confidence: low, medium, high" in prompt
            assert "If should_alert=false:" in prompt
            assert "urgency null" in prompt
            assert "reason_for_no_alert non-empty" in prompt
            assert "In snapshots, m is minutes before timestamp_utc and p is USD price." in prompt
            async with session_local() as session:
                row = await session.scalar(select(LlmUsageLog))
            assert row.call_type == "event_analysis"
            assert row.model == "event-model"
            assert row.symbol == "BTC"
            assert row.status == "success"
            assert row.total_tokens == 20
            assert row.max_tokens == 300
            assert row.rate_limit_remaining_requests == "999"
        finally:
            runtime.DB_SESSION_LOCAL.clear()
            await engine.dispose()

    asyncio.run(run_test())


def test_event_analysis_model_and_max_token_defaults():
    assert (
        ai_agent_groq.GROQ_EVENT_ANALYSIS_MODEL
        == "meta-llama/llama-4-scout-17b-16e-instruct"
    )
    assert ai_agent_groq.GROQ_EVENT_ANALYSIS_MAX_TOKENS == 300


def test_event_analysis_prompt_quality_requirements():
    prompt = ai_agent_groq.build_event_analysis_prompt(
        {
            "symbol": "TON",
            "market": {"chg24h": 5.8, "snapshots": [{"m": -30, "p": 3.1}]},
            "news": [],
        }
    )

    assert "Analyze exactly one symbol" in prompt
    assert "altcoins, a 24h move around 5-7% can be meaningful" in prompt
    assert "reason_for_no_alert must mention the actual 24h change" in prompt
    assert "recent short-term snapshot behavior" in prompt
    assert "Do not generate UUID-like or random event keys" in prompt
    assert "event_analysis_btc_<random>" in prompt


def test_ask_market_heartbeat_raw_uses_heartbeat_model_and_max_tokens(monkeypatch):
    captured_kwargs = {}

    class FakeCompletions:
        async def create(self, **kwargs):
            captured_kwargs.update(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=(
                                '{"symbol":"BTC","title":"BTC calm",'
                                '"message_body":"BTC is calm.",'
                                '"related_news_ids":[],"possible_action":"Monitor only.",'
                                '"confidence":"medium"}'
                            )
                        )
                    )
                ]
            )

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    monkeypatch.setattr(ai_agent_groq, "GROQ_MARKET_HEARTBEAT_MODEL", "heartbeat-model")
    monkeypatch.setattr(ai_agent_groq, "get_groq_client", lambda: fake_client)

    asyncio.run(ai_agent_groq.ask_market_heartbeat_raw({"symbol": "BTC"}))

    assert captured_kwargs["model"] == "heartbeat-model"
    assert captured_kwargs["max_tokens"] == 350


def test_market_heartbeat_prompt_quality_requirements():
    prompt = ai_agent_groq.build_market_heartbeat_prompt(
        {
            "symbol": "SOL",
            "candidate_news": [
                {
                    "news_id": "n1",
                    "title": "Bitcoin ETF outflows deepen",
                    "relevance_label": "irrelevant",
                }
            ],
        }
    )

    assert "calm Market Heartbeat, not an Event Alert" in prompt
    assert "Do not present BTC-only news as related context for ETH, SOL, TON" in prompt
    assert (
        "possible_action must be specific, practical, and tied to the current market context"
        in prompt
    )
    assert "Monitor market developments" in prompt
    assert "Monitor market sentiment" in prompt
    assert "Keep watching" in prompt


def test_ask_market_report_raw_uses_report_model_and_logs_success(monkeypatch):
    async def run_test():
        engine, session_local = await build_usage_session_factory()
        captured_kwargs = {}
        try:
            monkeypatch.setattr(runtime, "DB_ENABLED", True)
            runtime.DB_SESSION_LOCAL.set(session_local)
            monkeypatch.setattr(ai_agent_groq, "GROQ_REPORT_MODEL", "report-model")

            class FakeCompletions:
                async def create(self, **kwargs):
                    captured_kwargs.update(kwargs)
                    return SimpleNamespace(
                        choices=[
                            SimpleNamespace(
                                message=SimpleNamespace(
                                    content=(
                                        '{"report_type":"daily","title":"Daily Market Report",'
                                        '"market_overview":"Review your portfolio.",'
                                        '"coin_summaries":['
                                        '{"symbol":"BTC","summary":"BTC steady"}],'
                                        '"news_context":"No major news.",'
                                        '"possible_action":"Adjust your strategy.",'
                                        '"telegram_message":"Daily Market Report"}'
                                    )
                                )
                            )
                        ],
                        usage=SimpleNamespace(
                            prompt_tokens=20,
                            completion_tokens=30,
                            total_tokens=50,
                        ),
                        headers={},
                    )

            fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
            monkeypatch.setattr(ai_agent_groq, "get_groq_client", lambda: fake_client)

            await ai_agent_groq.ask_market_report_raw({"report_type": "daily", "coins": []})

            assert captured_kwargs["model"] == "report-model"
            assert captured_kwargs["max_tokens"] == 800
            async with session_local() as session:
                row = await session.scalar(select(LlmUsageLog))
            assert row.call_type == "daily_report"
            assert row.model == "report-model"
            assert row.status == "success"
            assert row.total_tokens == 50
        finally:
            runtime.DB_SESSION_LOCAL.clear()
            await engine.dispose()

    asyncio.run(run_test())


def test_llm_usage_log_is_written_on_rate_limit(monkeypatch):
    async def run_test():
        engine, session_local = await build_usage_session_factory()
        try:
            monkeypatch.setattr(runtime, "DB_ENABLED", True)
            runtime.DB_SESSION_LOCAL.set(session_local)

            class FakeResponse:
                status_code = 429
                headers = {"retry-after": "10"}

            class RateLimitError(RuntimeError):
                status_code = 429
                response = FakeResponse()

            class FakeCompletions:
                async def create(self, **kwargs):
                    raise RateLimitError("429 rate limit")

            fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
            monkeypatch.setattr(ai_agent_groq, "get_groq_client", lambda: fake_client)

            try:
                await ai_agent_groq.ask_event_analysis_raw({"symbol": "BTC"})
            except ai_agent_groq.AIGroqRateLimitError:
                pass

            async with session_local() as session:
                row = await session.scalar(select(LlmUsageLog))
            assert row.call_type == "event_analysis"
            assert row.status == "rate_limit"
            assert row.max_tokens == 300
            assert row.retry_after == "10"
        finally:
            runtime.DB_SESSION_LOCAL.clear()
            await engine.dispose()

    asyncio.run(run_test())


def test_create_ai_alert_payload_uses_fallback_when_json_mode_fails(monkeypatch):
    async def fake_ask_json(prompt):
        return None

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

    result = asyncio.run(ai_agent_groq.create_ai_alert_payload(**ALERT_ARGS))

    assert result == {"plain_text": expected_fallback, "html_text": None}


def test_compact_json_success_builds_valid_telegram_alert(monkeypatch):
    async def fake_ask_json(prompt):
        return valid_compact_alert_response()

    monkeypatch.setattr(ai_agent_groq, "_ask_json", fake_ask_json)

    result = asyncio.run(ai_agent_groq.create_ai_alert_payload(**ALERT_ARGS))
    message = result["plain_text"]

    assert "BTC market alert" in message
    assert "Price: $102,500.00" in message
    assert "5m move: +2.50%" in message
    assert "24h trend: +3.10%" in message
    assert "Why this alert:" in message
    assert "Medium because the short-term move is notable" in message
    assert "Possible actions:" in message
    assert "Related news:" in message
    assert "Coin:" not in message
    assert "Since last check" not in message
    assert "Not financial advice." in message
    assert "telegram_message" not in message


def test_create_ai_alert_payload_uses_fallback_when_groq_times_out(monkeypatch):
    async def fake_ask_json(prompt):
        raise asyncio.TimeoutError()

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

    result = asyncio.run(ai_agent_groq.create_ai_alert_payload(**ALERT_ARGS))

    assert result == {"plain_text": expected_fallback, "html_text": None}


def test_create_ai_alert_payload_marks_groq_rate_limit_fallback(monkeypatch):
    async def fake_ask_json(prompt):
        raise ai_agent_groq.AIGroqRateLimitError("Rate limit reached: 429 tokens per day")

    monkeypatch.setattr(ai_agent_groq, "_ask_json", fake_ask_json)

    result = asyncio.run(ai_agent_groq.create_ai_alert_payload(**ALERT_ARGS))

    assert result["rate_limited"] is True
    assert "BTC basic price alert" in result["plain_text"]
    assert result["html_text"] is None


def test_alert_prompt_is_simplified_and_keeps_market_context():
    news_text, _ = ai_agent_groq._build_news_listing_with_ids(ALERT_ARGS["news_items"])

    prompt = ai_agent_groq._build_alert_prompt(
        ALERT_ARGS["previous_price"],
        ALERT_ARGS["current_price"],
        ALERT_ARGS["price_change_percent"],
        ALERT_ARGS["change_24h"],
        ALERT_ARGS["change_7d"],
        ALERT_ARGS["alert_threshold_percent"],
        ALERT_ARGS["check_interval_seconds"],
        news_text,
        symbol="BTC",
        coin_name="Bitcoin",
    )

    assert "Return one valid JSON object only." in prompt
    assert "news_relevance" in prompt
    assert "risk_level" in prompt
    assert "risk_reason" in prompt
    assert "context_sentence" in prompt
    assert "possible_action" in prompt
    assert "related_news_ids" in prompt
    assert "telegram_message" not in prompt
    assert "severity" not in prompt
    assert "short_term_trend" not in prompt
    assert "weekly_trend" not in prompt
    assert "market_interpretation" not in prompt
    assert "possible_actions" not in prompt
    assert "Symbol: BTC" in prompt
    assert "5m move: 2.5000%" in prompt
    assert "24h trend: 3.1000%" in prompt
    assert "7d trend: 5.2000%" in prompt
    assert "Movement threshold: 2.0%" in prompt
    assert "Since last check" not in prompt
    assert "Check interval" not in prompt
    assert "[1] ETF inflows rise | Example News | https://example.com/etf" in prompt


def test_specific_possible_actions_are_backend_generated_for_legacy_payload(monkeypatch):
    async def fake_ask_json(prompt):
        return valid_compact_alert_response(
            news_relevance="relevant",
            risk_level="Low",
            risk_reason="Recent BTC news is mixed, but price has not reacted strongly yet.",
            possible_action=(
                "Consider reviewing your investment strategy in light of recent market "
                "developments."
            ),
        )

    monkeypatch.setattr(ai_agent_groq, "_ask_json", fake_ask_json)
    result = asyncio.run(
        ai_agent_groq.create_ai_alert_payload(
            **{
                **ALERT_ARGS,
                "price_change_percent": 0.0,
                "change_24h": -1.02,
                "alert_threshold_percent": 1.0,
                "check_interval_seconds": 3600,
            }
        )
    )
    message = result["plain_text"]

    assert "No immediate portfolio action is suggested by price data alone." in message
    assert "Watch whether the coin reacts over the next alert window." in message


def test_is_structured_alert_message_returns_true_for_valid():
    assert ai_agent_groq._is_structured_alert_message(VALID_TELEGRAM_MESSAGE) is True


def test_is_structured_alert_message_returns_false_for_plain_text():
    assert ai_agent_groq._is_structured_alert_message("BTC moved quickly.") is False


def test_create_ai_alert_message_returns_string(monkeypatch):
    async def fake_ask_json(prompt):
        return valid_compact_alert_response()

    monkeypatch.setattr(ai_agent_groq, "_ask_json", fake_ask_json)

    result = asyncio.run(ai_agent_groq.create_ai_alert_message(**ALERT_ARGS))

    assert isinstance(result, str)
    assert not isinstance(result, dict)


def test_create_ai_alert_payload_returns_dict_with_plain_text(monkeypatch):
    async def fake_ask_json(prompt):
        return valid_compact_alert_response()

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
    assert "buying now" in message.lower()
    assert "selling now" in message.lower()
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
        return valid_compact_alert_response(
            news_relevance="not_relevant",
            risk_reason="Based on market data and news.",
            related_news_ids=[],
            context_sentence=(
                "The move is small, and recent news does not appear to be a clear driver."
            ),
        )

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

    assert (
        "The move crossed the alert threshold, but the 24h trend remains mild."
        in message
    )
    assert "Related news:" not in message
    assert "available news context" not in message
    assert "based on market data and news" not in message.lower()
    assert message.count("Not financial advice.") == 1


def test_related_news_reason_is_allowed_only_when_related_news_is_included(monkeypatch):
    async def fake_ask_json(prompt):
        return valid_compact_alert_response()

    monkeypatch.setattr(ai_agent_groq, "_ask_json", fake_ask_json)

    result = asyncio.run(ai_agent_groq.create_ai_alert_payload(**ALERT_ARGS))
    message = result["plain_text"]

    assert "Medium because the short-term move is notable" in message
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
