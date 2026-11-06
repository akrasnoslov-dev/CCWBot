"""Synthetic regression coverage for 2026-11-06 Render direction failures.

Only sanitized failure categories are known, not the rejected production prose.
These cases must not be presented as a reproduction of the raw BTC/ETH output.
"""
import json

import pytest

import bot.alerts as alerts
from bot.alerting.event_analysis import EventAnalysisValidationError
from bot.services import ai_agent_groq
from bot.services.llm.base_provider import ProviderResult
from bot.services.llm.errors import AISchemaValidationError
from bot.services.llm.router import LLMRouter


def _payload(symbol="BTC"):
    return {
        "symbol": symbol,
        "timestamp_utc": "2026-11-06T15:00:00+00:00",
        "market": {
            "price": 100.0,
            "analysed_window_minutes": 180,
            "chg_window_percent": -1.4,
            "chg30m_percent": 0.4,
            "chg1h_percent": -0.5,
            "chg24h_percent": 2.4,
            "chg_since_msg_percent": None,
            "snapshots": [{"m": -180, "p": 101.42}, {"m": 0, "p": 100.0}],
        },
        "last_msg": {"time": None, "price": None},
        "news": [],
    }


def _render(body):
    return {"message_body": body, "related_news_ids": [],
            "possible_action": "Watch the next observed interval."}


@pytest.mark.parametrize("symbol", ["BTC", "ETH"])
def test_synthetic_period_direction_rejection_matches_incident_category(symbol):
    market = _payload(symbol)["market"]
    valid = "The 30-minute price rose. The 1-hour price fell. The 24-hour price rose."
    invalid = (
        "The 30-minute price fell. The 1-hour price rose. "
        "The 24-hour price fell."
    )
    original = _render(valid)
    alerts._validate_event_alert_render_causality(original, market_data=market)
    assert original["message_body"] == valid  # Never mutate accepted model prose.

    with pytest.raises(EventAnalysisValidationError) as error:
        alerts._validate_event_alert_render_causality(
            _render(invalid), market_data=market
        )
    assert alerts._event_alert_render_validation_reason(error.value) == (
        "period_direction_mismatch"
    )


def test_render_prompt_supplies_each_independent_period_direction():
    prompt = ai_agent_groq.build_event_alert_render_prompt(_payload())
    facts = json.loads(prompt.split("Input JSON:\\n", 1)[1])
    assert facts["market_directions"] == {
        "window": "down", "30m": "up", "1h": "down", "24h": "up"
    }
    assert "30m" in prompt and "1h" in prompt


def test_render_directions_are_only_present_for_supported_market_metrics():
    payload = _payload()
    payload["market"]["chg30m_percent"] = None
    payload["market"]["chg1h_percent"] = "not a number"
    payload["market"]["chg24h_percent"] = 0
    facts = json.loads(
        ai_agent_groq.build_event_alert_render_prompt(payload)
        .split("Input JSON:\\n", 1)[1]
    )
    assert facts["market_directions"] == {"window": "down", "24h": "flat"}
    assert "change_30m_percent" not in facts["market_metrics"]
    assert "change_1h_percent" not in facts["market_metrics"]


class _FakeProvider:
    def __init__(self, name, raw):
        self.name = name
        self.raw = raw
        self.calls = []

    async def chat_completion(self, *, model, messages, **kwargs):
        self.calls.append(messages)
        return ProviderResult(
            provider=self.name, model=model, raw_content=self.raw, input_chars=42
        )


def _real_direction_schema_check(market):
    def check(data):
        try:
            alerts._validate_event_alert_render_causality(data, market_data=market)
        except EventAnalysisValidationError as error:
            raise AISchemaValidationError(
                alerts._event_alert_render_validation_reason(error)
            ) from error
    return check


@pytest.mark.asyncio
async def test_invalid_direction_advances_only_to_configured_provider(monkeypatch):
    monkeypatch.setenv("LLM_EVENT_RENDER_PROVIDERS", "groq,cloudflare")
    monkeypatch.setenv("GROQ_API_KEY", "fake")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "fake")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "fake")
    monkeypatch.setenv("LLM_BREAKER_ENABLED", "false")
    bad = _FakeProvider("groq", json.dumps(_render("The 30-minute price fell.")))
    good = _FakeProvider("cloudflare", json.dumps(_render("The 30-minute price rose.")))
    monkeypatch.setattr(
        ai_agent_groq, "get_router",
        lambda: LLMRouter(registry={"groq": bad, "cloudflare": good}),
    )
    result = await ai_agent_groq.ask_event_alert_render_raw(
        _payload(), schema_check=_real_direction_schema_check(_payload()["market"])
    )
    assert result[1]["message_body"] == "The 30-minute price rose."
    assert len(bad.calls) == len(good.calls) == 1
    assert "period_direction_mismatch" in good.calls[0][-1]["content"]
    assert "30-minute price fell" not in good.calls[0][-1]["content"]


@pytest.mark.asyncio
async def test_invalid_direction_is_terminal_in_luna_only_policy(monkeypatch):
    monkeypatch.setenv("LLM_EVENT_RENDER_PROVIDERS", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "fake")
    monkeypatch.setenv("OPENAI_ENABLED", "true")
    monkeypatch.setenv("LLM_BREAKER_ENABLED", "false")
    provider = _FakeProvider("openai", json.dumps(_render("The 24-hour price fell.")))
    monkeypatch.setattr(
        ai_agent_groq, "get_router", lambda: LLMRouter(registry={"openai": provider})
    )
    with pytest.raises(AISchemaValidationError) as error:
        await ai_agent_groq.ask_event_alert_render_raw(
            _payload("ETH"),
            schema_check=_real_direction_schema_check(_payload("ETH")["market"]),
        )
    assert str(error.value) == "period_direction_mismatch"
    assert len(provider.calls) == 1  # No unauthorized second request.
