"""Regression contracts for production Event Alert Render rejection categories.

Provider response patterns come from the five sanitized categories reported on
2026-10-09; no raw production output was available in the local checkout.
"""
import json
from unittest.mock import AsyncMock

import pytest

import bot.alerts as alerts
from bot.alerting.event_analysis import EventAnalysisValidationError, validate_event_analysis_output
from bot.services import ai_agent_groq
from bot.services.llm.errors import AIInvalidJsonError, AISchemaValidationError


def _payload():
    return {
        "symbol": "BTC",
        "timestamp_utc": "2026-10-09T09:00:00+00:00",
        "market": {
            "price": 105.0,
            "snapshots": [{"m": -180, "p": 108.0}, {"m": 0, "p": 105.0}],
            "analysed_window_minutes": 180,
            "chg_window_percent": -3.1,
            "chg24h_percent": 2.4,
            "chg_since_msg_percent": None,
        },
        "last_msg": {"time": None, "price": None},
        "news": [],
    }


@pytest.mark.parametrize(
    ("body", "expected_category"),
    [
        ("BTC fell 4.8% over 3 hours.", "market_claim_mismatch"),
        ("BTC has moved 7.8%.", "market_percentage_mismatch"),
        ("BTC rose over the last 3 hours.", "market_claim_direction_mismatch"),
        ("BTC fell 3.1% over the last 2 hours.", "window_duration_mismatch"),
    ],
)
def test_unverified_render_market_assertions_still_fail_closed(body, expected_category):
    payload = _payload()
    result = alerts._event_alert_render_result_for_validation(
        {"message_body": body, "related_news_ids": [],
         "possible_action": "Monitor the next observations.", "urgency": "normal"},
        input_payload=payload,
        expected_symbol="BTC",
        confidence="high",
        candidate_news_ids=set(),
    )
    with pytest.raises(EventAnalysisValidationError) as error:
        validate_event_analysis_output(
            result, expected_symbol="BTC", candidate_news_ids=set(),
            market_data=payload["market"], last_msg=payload["last_msg"],
            timestamp_utc=payload["timestamp_utc"],
        )
    assert alerts._event_alert_render_validation_reason(error.value) == expected_category


def test_render_cannot_invent_or_escalate_urgency():
    payload = _payload()
    result = alerts._event_alert_render_result_for_validation(
        {"message_body": "The supplied market conditions deserve monitoring.",
         "related_news_ids": [], "possible_action": "Watch subsequent observations.",
         "urgency": "critical"},
        input_payload=payload,
        expected_symbol="BTC",
        confidence="high",
        candidate_news_ids=set(),
    )
    decision = validate_event_analysis_output(
        result, expected_symbol="BTC", candidate_news_ids=set(),
        market_data=payload["market"], last_msg=payload["last_msg"],
        timestamp_utc=payload["timestamp_utc"],
    )
    assert decision.urgency == "normal"
    assert decision.should_alert is True


def test_render_prompt_includes_actual_primary_market_metrics():
    payload = _payload()
    prompt = ai_agent_groq.build_event_alert_render_prompt(payload)
    compact = json.loads(prompt.split("Input JSON:\n", 1)[1])
    assert compact["sym"] == "BTC"
    assert compact["market_directions"] == {"window": "down", "24h": "up"}
    assert compact["market_metrics"] == {
        "price_now_usd": 105.0,
        "analysed_window_minutes": 180,
        "analysed_window_change_percent": -3.1,
        "change_24h_percent": 2.4,
    }
    assert "snapshots" not in json.dumps(compact)
    assert "Do not repeat" in prompt
    assert set(ai_agent_groq._EVENT_ALERT_RENDER_JSON_SCHEMA["required"]) == {
        "message_body", "related_news_ids", "possible_action"
    }



def test_ccw20_render_copy_asks_for_meaningful_price_scenarios():
    payload = _payload()
    prompt = ai_agent_groq.build_event_alert_render_prompt(payload)
    compact = json.loads(prompt.split("Input JSON:\n", 1)[1])

    assert compact["evidence"]["window_vs_24h"] == "opposite_direction"
    assert "explain the verified observed trajectory" in prompt
    assert "Do not force both the observed high and low" in prompt
    assert "observed price band" in prompt
    assert compact["market_directions"] == {"window": "down", "24h": "up"}
    # Insufficient snapshots must not invent price levels.
    assert "observed_price_band" not in compact["evidence"]
    assert set(compact) == {"sym", "market_directions", "market_metrics", "evidence", "n", "sig"}


def test_ccw20_render_prompt_missing_context_fails_closed():
    payload = _payload()
    payload["market"] = {"price": 105.0}
    prompt = ai_agent_groq.build_event_alert_render_prompt(payload)
    compact = json.loads(prompt.split("Input JSON:\n", 1)[1])
    assert compact["evidence"] == {}
    assert compact["market_directions"] == {}
    assert compact["market_metrics"] == {"price_now_usd": 105.0}
    assert "Do not force both the observed high and low" in prompt




@pytest.mark.asyncio
@pytest.mark.parametrize("render_error", [
    AISchemaValidationError("market_claim_mismatch"),
    AISchemaValidationError("invalid_urgency"),
    AIInvalidJsonError("malformed JSON"),
])
async def test_invalid_provider_chain_exhaustion_fails_without_fabricated_prose(
    monkeypatch, render_error
):
    significance = {
        "symbol": "BTC", "should_alert": True, "confidence": "high",
        "materiality": "material", "novelty": "new", "reason_code": "unusual_move",
    }
    render_error._llm_all_exhausted_attempts_invalid_output = True
    significance_llm = AsyncMock(return_value=("significance-json", significance))
    render_llm = AsyncMock(side_effect=render_error)
    render_outcome = AsyncMock()
    save_analysis = AsyncMock(return_value=400)
    delivery_outcome = AsyncMock()
    monkeypatch.setattr(alerts, "ask_event_significance_raw", significance_llm)
    monkeypatch.setattr(alerts, "ask_event_alert_render_raw", render_llm)
    monkeypatch.setattr(alerts, "_save_event_alert_render_outcome", render_outcome)
    monkeypatch.setattr(alerts, "_save_event_analysis_attempt", save_analysis)
    monkeypatch.setattr(alerts, "_record_alert_delivery_outcome", delivery_outcome)
    monkeypatch.setattr(alerts, "_get_previous_event_alert_id", AsyncMock(return_value=None))
    decision, analysis_id = await alerts._create_event_analysis_decision(_payload())
    assert decision is None and analysis_id is None
    assert render_outcome.await_args.kwargs["status"] == "llm_error"
    assert save_analysis.await_args.kwargs["status"] == "llm_error"
    assert delivery_outcome.await_args.kwargs["status"] == alerts.OUTCOME_FAILED
    assert delivery_outcome.await_args.kwargs["reason_code"] == alerts.REASON_LLM_INVALID_RESPONSE
    significance_llm.assert_awaited_once()
    render_llm.assert_awaited_once()

@pytest.mark.parametrize("claim", [
    "The move was caused by news coverage.",
    "BTC fell due to a large liquidation wave.",
    "The market was driven by whale activity.",
])
def test_render_rejects_unsourced_causality_before_delivery(claim):
    with pytest.raises(EventAnalysisValidationError, match="unverified causal claim"):
        alerts._validate_event_alert_render_causality({
            "message_body": claim,
            "possible_action": "Monitor the next observations.",
        })


@pytest.mark.asyncio
async def test_untrusted_deterministic_fallback_cannot_bypass_validation(monkeypatch):
    significance = {
        "symbol": "BTC", "should_alert": True, "confidence": "high",
        "materiality": "material", "novelty": "new", "reason_code": "unusual_move",
    }
    monkeypatch.setattr(
        alerts, "ask_event_significance_raw",
        AsyncMock(return_value=("significance-json", significance)),
    )
    monkeypatch.setattr(
        alerts, "ask_event_alert_render_raw",
        AsyncMock(side_effect=AISchemaValidationError("market_claim_mismatch")),
    )
    monkeypatch.setattr(
        alerts, "event_alert_presentation_fallback",
        lambda market, news: ("BTC fell 99% over the last 2 hours.", "Monitor the market."),
    )
    render_outcome = AsyncMock()
    analysis = AsyncMock(return_value=321)
    delivery_outcome = AsyncMock()
    monkeypatch.setattr(alerts, "_save_event_alert_render_outcome", render_outcome)
    monkeypatch.setattr(alerts, "_save_event_analysis_attempt", analysis)
    monkeypatch.setattr(alerts, "_record_alert_delivery_outcome", delivery_outcome)
    monkeypatch.setattr(alerts, "_get_previous_event_alert_id", AsyncMock(return_value=None))

    decision, analysis_id = await alerts._create_event_analysis_decision(_payload())

    assert decision is None and analysis_id is None
    assert render_outcome.await_args.kwargs["status"] == "llm_error"
    assert analysis.await_args.kwargs["status"] == "llm_error"
    assert delivery_outcome.await_args.kwargs["status"] == alerts.OUTCOME_FAILED


@pytest.mark.asyncio
async def test_mixed_transport_and_invalid_output_does_not_claim_success(monkeypatch):
    significance = {
        "symbol": "BTC", "should_alert": True, "confidence": "high",
        "materiality": "material", "novelty": "new", "reason_code": "unusual_move",
    }
    mixed_error = AISchemaValidationError("invalid_json_from_one_provider")
    mixed_error._llm_all_exhausted_attempts_invalid_output = False
    monkeypatch.setattr(alerts, "ask_event_significance_raw",
                        AsyncMock(return_value=("significance", significance)))
    monkeypatch.setattr(alerts, "ask_event_alert_render_raw",
                        AsyncMock(side_effect=mixed_error))
    render_outcome = AsyncMock()
    save_analysis = AsyncMock(return_value=401)
    delivery_outcome = AsyncMock()
    monkeypatch.setattr(alerts, "_save_event_alert_render_outcome", render_outcome)
    monkeypatch.setattr(alerts, "_save_event_analysis_attempt", save_analysis)
    monkeypatch.setattr(alerts, "_record_alert_delivery_outcome", delivery_outcome)
    monkeypatch.setattr(alerts, "_get_previous_event_alert_id", AsyncMock(return_value=None))
    decision, analysis_id = await alerts._create_event_analysis_decision(_payload())
    assert decision is None and analysis_id is None
    assert render_outcome.await_args.kwargs["status"] == "llm_error"
    assert delivery_outcome.await_args.kwargs["status"] == alerts.OUTCOME_FAILED


@pytest.mark.asyncio
async def test_flat_news_led_input_cannot_be_recovered_as_market_alert(monkeypatch):
    significance = {
        "symbol": "BTC", "should_alert": True, "confidence": "high",
        "materiality": "material", "novelty": "new",
        "reason_code": "market_news_alignment",
    }
    render_error = AISchemaValidationError("invalid_json")
    render_error._llm_all_exhausted_attempts_invalid_output = True
    payload = _payload()
    payload["market"].update({
        "chg_window_percent": 0.0, "chg_since_msg_percent": 0.0,
        "snapshots": [{"m": -180, "p": 105.0}, {"m": 0, "p": 105.0}],
    })
    payload["news"] = [{"news_id": "n1", "title": "ETF filing", "source": "Example"}]
    monkeypatch.setattr(alerts, "ask_event_significance_raw",
                        AsyncMock(return_value=("significance", significance)))
    monkeypatch.setattr(alerts, "ask_event_alert_render_raw",
                        AsyncMock(side_effect=render_error))
    render_outcome = AsyncMock()
    save_analysis = AsyncMock(return_value=402)
    delivery_outcome = AsyncMock()
    monkeypatch.setattr(alerts, "_save_event_alert_render_outcome", render_outcome)
    monkeypatch.setattr(alerts, "_save_event_analysis_attempt", save_analysis)
    monkeypatch.setattr(alerts, "_record_alert_delivery_outcome", delivery_outcome)
    monkeypatch.setattr(alerts, "_get_previous_event_alert_id", AsyncMock(return_value=None))
    decision, analysis_id = await alerts._create_event_analysis_decision(payload)
    assert decision is None and analysis_id is None
    assert render_outcome.await_args.kwargs["status"] != "success"
    assert delivery_outcome.await_args.kwargs["status"] != alerts.OUTCOME_ALLOWED


def test_render_metrics_match_published_alert_inputs_and_optional_lookbacks():
    from bot import alerts

    payload = _payload()
    payload["market"].update({
        "price": 105.257,
        "chg30m_percent": -0.41234567,
        "chg1h_percent": -0.8754321,
        "chg_since_msg_percent": -1.17234567,
    })
    payload["timestamp_utc"] = "2026-10-09T09:00:00+00:00"
    payload["last_msg"] = {
        "time": "2026-10-09T06:31:00+00:00",
        "price": 106.5,
        "type": "event_alert",
    }

    compact = json.loads(
        ai_agent_groq.build_event_alert_render_prompt(payload).split("Input JSON:\n", 1)[1]
    )
    metrics = compact["market_metrics"]
    assert metrics == {
        "price_now_usd": 105.257,
        "analysed_window_minutes": 180,
        "analysed_window_change_percent": -3.1,
        "change_24h_percent": 2.4,
        "change_30m_percent": -0.412346,
        "change_1h_percent": -0.875432,
        "since_previous_notification": {
            "change_percent": -1.172346,
            "elapsed": "2h 29m ago",
        },
    }
    # The independently assembled Telegram header uses the same source fields.
    lines = alerts._event_alert_market_context_lines(
        symbol="BTC",
        price=payload["market"]["price"],
        change_since_message=payload["market"]["chg_since_msg_percent"],
        last_message_at=payload["last_msg"]["time"],
        last_message_price=payload["last_msg"]["price"],
        last_message_type=payload["last_msg"]["type"],
        current_at=payload["timestamp_utc"],
        analysed_window_minutes=payload["market"]["analysed_window_minutes"],
        analysed_window_change=payload["market"]["chg_window_percent"],
    )
    assert "Price (now): $105.26" in lines
    assert "Since previous alert (2h 29m ago): -1.17%" in lines
    assert "3h market move: -3.10%" in lines


def test_render_metrics_never_invent_missing_prior_notification_or_invalid_numbers():
    payload = _payload()
    payload["market"].update({
        "price": float("nan"),
        "chg_window_percent": float("inf"),
        "chg24h_percent": "not a number",
        "chg30m_percent": None,
        "chg1h_percent": "1e10000",
        "chg_since_msg_percent": 3.0,
    })
    # A change without an attributed last notification must not be relabeled.
    payload["last_msg"] = {"time": None, "price": None}
    compact = json.loads(
        ai_agent_groq.build_event_alert_render_prompt(payload).split("Input JSON:\n", 1)[1]
    )
    assert compact["market_metrics"] == {"analysed_window_minutes": 180}
    assert "since_previous_notification" not in compact["market_metrics"]
    assert compact["market_directions"] == {}
