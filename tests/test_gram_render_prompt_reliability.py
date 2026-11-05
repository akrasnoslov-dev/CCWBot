"""Offline regressions for GRAM Render grounding and separate health telemetry."""

import time
from datetime import datetime, timezone

import pytest

from bot import alerts, health
from bot.observability.logical_llm_health import LogicalHealth
from bot.services.ai_agent_groq import build_event_alert_render_prompt


def _gram_market():
    return {
        "analysed_window_minutes": 180,
        "chg_window_percent": -0.42,
        "chg24h_percent": 2.1,
        "chg_since_msg_percent": 0.1,
        "snapshots": [
            {"m": -180, "p": 1.14},
            {"m": -90, "p": 1.135},
            {"m": 0, "p": 1.132},
        ],
    }


def test_gram_render_prompt_separates_window_day_and_earlier_steps():
    prompt = build_event_alert_render_prompt(
        {"symbol": "GRAM", "market": _gram_market(), "news": []}
    )
    assert '"window":"down"' in prompt
    assert '"24h":"up"' in prompt
    assert "market_directions.window" in prompt
    assert "market_directions.24h" in prompt
    assert "net analysed-window" in prompt
    assert "opposite" in prompt
    assert "individual snapshot" in prompt
    assert "do not invent" in prompt.lower()


def test_gram_render_validator_preserves_direction_safety():
    market = _gram_market()
    with pytest.raises(alerts.EventAnalysisValidationError):
        alerts._validate_event_alert_render_causality(
            {"message_body": "The short-term rise follows the broader 24-hour rise."},
            market_data=market,
        )
    alerts._validate_event_alert_render_causality(
        {
            "message_body": (
                "The short-term decline contrasts with the broader 24-hour rise."
            )
        },
        market_data=market,
    )


@pytest.mark.asyncio
async def test_health_exposes_render_failures_separately_without_flipping_container(monkeypatch):
    monkeypatch.setattr(health, "DB_ENABLED", False)
    monkeypatch.setattr(health, "load_state", lambda: {})

    async def recent_success():
        return datetime.now(timezone.utc)

    async def analysis_health():
        return LogicalHealth("event_analysis", "ok", 100, 100, 0, 0, 0, 100.0)

    async def render_health():
        return LogicalHealth("event_alert_render", "unknown", 6, 2, 4, 0, 0, 33.3)

    monkeypatch.setattr(health, "_read_last_event_analysis_success_at", recent_success)
    monkeypatch.setattr(health, "_read_event_analysis_logical_health", analysis_health)
    monkeypatch.setattr(health, "_read_event_alert_render_logical_health", render_health)

    response = await health.health_response(time.monotonic())

    assert response["status"] == "ok"
    assert response["event_analysis"]["state"] == "ok"
    assert response["event_analysis"]["logical_24h"]["successes"] == 100
    assert response["event_analysis"]["render_24h"] == {
        "state": "unknown",
        "operations": 6,
        "successes": 2,
        "terminal_failures": 4,
        "missing_outcomes": 0,
        "success_rate_percent": 33.3,
    }
