import asyncio
from decimal import Decimal
from types import SimpleNamespace

import pytest

import bot.services.ai_agent_groq as ai_agent_groq
from bot.services.llm import groq_provider, telemetry


def _set_groq_client(monkeypatch, client):
    monkeypatch.setattr(groq_provider.get_provider(), "_client", client)


@pytest.fixture(autouse=True)
def _single_groq_provider(monkeypatch):
    telemetry.reset_llm_rate_limit_backoffs()
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("LLM_PROVIDER_PRIORITY", "groq")
    monkeypatch.setattr(groq_provider.get_provider(), "_client", None)
    yield
    telemetry.reset_llm_rate_limit_backoffs()
    monkeypatch.setattr(groq_provider.get_provider(), "_client", None)


def test_event_analysis_prompt_makes_llm_the_market_significance_decider():
    prompt = ai_agent_groq.build_event_analysis_prompt(
        {
            "symbol": "GRAM",
            "market": {"chg_window_percent": -0.183, "chg24h_percent": -0.721},
        }
    )

    assert "Market decides; news alone never alerts" in prompt
    assert "LLM owns significance" in prompt
    assert "no invented thresholds" in prompt
    assert "Never claim a threshold unless supplied" in prompt
    assert "reason_for_no_alert set" in prompt
    assert "0.042=0.042%, not 4.2%" in prompt
    assert "no x100" in prompt
    assert "body interprets without extra numbers" in prompt
    assert "news coincident not causal" in prompt
    assert "action=conditional monitoring" in prompt
    assert "Facts only" in prompt
    assert "Routine/modest/stable=>false" in prompt
    assert "unless other market facts are noteworthy" in prompt
    assert "cw=window%" in prompt
    assert "cl=since prior alert%" in prompt
    assert "null/missing=unknown" in prompt
    assert "never derive cw from c24/cl" in prompt
    assert "consistent/persistent/throughout only if s supports it" in prompt
    assert "title uses cw when present" in prompt


@pytest.mark.parametrize(
    ("window_change", "day_change"),
    (
        (Decimal("0.042"), Decimal("0.246")),
        (Decimal("-0.042"), Decimal("-0.246")),
    ),
)
def test_event_analysis_prompt_preserves_subpercent_values_as_percentages(
    window_change, day_change
):
    prompt = ai_agent_groq.build_event_analysis_prompt(
        {
            "symbol": "BTC",
            "market": {
                "chg_window_percent": window_change,
                "chg24h_percent": day_change,
                "chg_since_msg_percent": Decimal("0.001"),
            },
        }
    )

    assert f'"cw":{window_change}' in prompt
    assert f'"c24":{day_change}' in prompt
    assert "0.042=0.042%, not 4.2%" in prompt
    assert "no x100" in prompt


def test_other_prompts_preserve_report_and_heartbeat_contracts():
    heartbeat = ai_agent_groq.build_market_heartbeat_prompt({"symbol": "SOL"})
    report = ai_agent_groq.build_market_report_prompt({"report_type": "weekly"})

    assert "Market Heartbeat, not an Event Alert" in heartbeat
    assert "0.042 means 0.042%, not 4.2%" in heartbeat
    assert "never multiply them by 100" in heartbeat
    assert "market_pulse" in report
    assert "title, market_pulse, why_it_matters, and watch_next must be non-empty text" in report
    assert "week_timeline" in report
    assert "exactly one object for each supplied active symbol" in report
    assert "symbol, summary, and watch fields" in report
    assert "For weekly reports" in report
    assert "next_week_focus must be non-empty" in report
    assert "all fields ending in _percent are already percentage values" in report
    assert "0.042 means 0.042%, not 4.2%" in report
    assert "never multiply them by 100" in report


def test_sanitize_alert_message_drops_backend_diagnostic_lines():
    message = ai_agent_groq.sanitize_alert_message(
        "Market update\nthreshold=2\ncurrent=1.35\nReview the market context."
    )

    assert message == "Market update\nReview the market context."


@pytest.mark.parametrize(
    ("raw_content", "expected"),
    [
        ('{"ok": true}', {"ok": True}),
        ('```json\n{"ok": true}\n```', {"ok": True}),
        ("not json", None),
        ("[]", None),
    ],
)
def test_parse_json_keeps_object_only_contract(raw_content, expected):
    assert ai_agent_groq._parse_json(raw_content) == expected


def test_event_analysis_raw_uses_strict_groq_schema_and_returns_provider_attribution(monkeypatch):
    captured = {}

    class FakeCompletions:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=(
                                '{"symbol":"BTC","should_alert":false,"event_key":null,'
                                '"title":null,"message_body":null,"related_news_ids":[],'
                                '"possible_action":null,"urgency":null,"confidence":null,'
                                '"reason_for_no_alert":"No material market event."}'
                            )
                        )
                    )
                ],
                usage=SimpleNamespace(prompt_tokens=12, completion_tokens=8, total_tokens=20),
                headers={},
            )

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    _set_groq_client(monkeypatch, fake_client)
    result = asyncio.run(ai_agent_groq.ask_event_analysis_raw({"symbol": "BTC"}))

    assert result[1]["should_alert"] is False
    assert result.provider == "groq"
    response_format = captured["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == "event_analysis"
    assert response_format["json_schema"]["strict"] is True
    schema = response_format["json_schema"]["schema"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "symbol",
        "should_alert",
        "event_key",
        "title",
        "message_body",
        "related_news_ids",
        "possible_action",
        "urgency",
        "confidence",
        "reason_for_no_alert",
    }
    assert schema["properties"]["related_news_ids"]["type"] == ["array", "null"]
    assert schema["properties"]["urgency"]["enum"] == [
        "low",
        "normal",
        "high",
        None,
    ]
    assert schema["properties"]["confidence"]["enum"] == [
        "low",
        "medium",
        "high",
        None,
    ]
    assert captured["max_tokens"] >= 300


def test_market_heartbeat_raw_uses_strict_groq_schema(monkeypatch):
    captured = {}

    class FakeCompletions:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=(
                                '{"symbol":"BTC","title":"BTC heartbeat",'
                                '"message_body":"Conditions remain orderly.",'
                                '"related_news_ids":[],"possible_action":"Watch the range.",'
                                '"confidence":"low"}'
                            )
                        )
                    )
                ],
                usage=SimpleNamespace(prompt_tokens=10, completion_tokens=7, total_tokens=17),
                headers={},
            )

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    _set_groq_client(monkeypatch, fake_client)

    result = asyncio.run(ai_agent_groq.ask_market_heartbeat_raw({"symbol": "BTC"}))

    assert result.provider == "groq"
    response_format = captured["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == "market_heartbeat"
    assert response_format["json_schema"]["strict"] is True
    schema = response_format["json_schema"]["schema"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "symbol",
        "title",
        "message_body",
        "related_news_ids",
        "possible_action",
        "confidence",
    }


def test_market_report_raw_uses_strict_groq_schema(monkeypatch):
    captured = {}

    class FakeCompletions:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=(
                                '{"report_type":"daily","title":"Daily Market Report",'
                                '"market_pulse":"Mixed market.","dashboard":["BTC is steady."],'
                                '"coin_cards":[{"symbol":"BTC","summary":"BTC is steady.",'
                                '"watch":"Watch the range."}],"market_catalysts":[],'
                                '"why_it_matters":"Confirmation matters.",'
                                '"watch_next":"Watch the range.","week_timeline":[],'
                                '"themes":[],"next_week_focus":""}'
                            )
                        )
                    )
                ],
                usage=SimpleNamespace(prompt_tokens=20, completion_tokens=12, total_tokens=32),
                headers={},
            )

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    _set_groq_client(monkeypatch, fake_client)

    result = asyncio.run(
        ai_agent_groq.ask_market_report_raw(
            {"report_type": "daily", "active_symbols": ["BTC"]}
        )
    )

    assert result.provider == "groq"
    response_format = captured["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == "market_report"
    assert response_format["json_schema"]["strict"] is True
    schema = response_format["json_schema"]["schema"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "report_type",
        "title",
        "market_pulse",
        "dashboard",
        "coin_cards",
        "market_catalysts",
        "why_it_matters",
        "watch_next",
        "week_timeline",
        "themes",
        "next_week_focus",
    }
    coin_card_schema = schema["properties"]["coin_cards"]["items"]
    assert coin_card_schema["additionalProperties"] is False
    assert set(coin_card_schema["required"]) == {"symbol", "summary", "watch"}


def test_market_report_unknown_groq_model_keeps_json_object_mode(monkeypatch):
    captured = {}
    monkeypatch.setenv("GROQ_REPORT_MODEL", "custom/unsupported-model")

    class FakeCompletions:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=(
                                '{"report_type":"daily","title":"Daily Market Report",'
                                '"market_pulse":"Mixed market.","dashboard":["BTC is steady."],'
                                '"coin_cards":[{"symbol":"BTC","summary":"BTC is steady.",'
                                '"watch":"Watch the range."}],"market_catalysts":[],'
                                '"why_it_matters":"Confirmation matters.",'
                                '"watch_next":"Watch the range.","week_timeline":[],'
                                '"themes":[],"next_week_focus":""}'
                            )
                        )
                    )
                ],
                usage=SimpleNamespace(prompt_tokens=20, completion_tokens=12, total_tokens=32),
                headers={},
            )

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    _set_groq_client(monkeypatch, fake_client)

    result = asyncio.run(
        ai_agent_groq.ask_market_report_raw(
            {"report_type": "daily", "active_symbols": ["BTC"]}
        )
    )

    assert result.provider == "groq"
    assert captured["response_format"] == {"type": "json_object"}


def test_event_analysis_unknown_groq_model_keeps_json_object_mode(monkeypatch):
    captured = {}
    monkeypatch.setenv("GROQ_EVENT_ANALYSIS_MODEL", "custom/unsupported-model")

    class FakeCompletions:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=(
                                '{"symbol":"BTC","should_alert":false,"event_key":null,'
                                '"title":null,"message_body":null,"related_news_ids":[],'
                                '"possible_action":null,"urgency":null,"confidence":null,'
                                '"reason_for_no_alert":"No material market event."}'
                            )
                        )
                    )
                ],
                usage=SimpleNamespace(prompt_tokens=12, completion_tokens=8, total_tokens=20),
                headers={},
            )

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    _set_groq_client(monkeypatch, fake_client)

    result = asyncio.run(ai_agent_groq.ask_event_analysis_raw({"symbol": "BTC"}))

    assert result.provider == "groq"
    assert captured["response_format"] == {"type": "json_object"}
