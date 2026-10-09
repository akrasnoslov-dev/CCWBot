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


def test_render_prompt_contains_only_verified_directions_not_raw_metrics():
    payload = _payload()
    prompt = ai_agent_groq.build_event_alert_render_prompt(payload)
    compact = json.loads(prompt.split("Input JSON:\n", 1)[1])
    assert compact["sym"] == "BTC"
    assert compact["market_directions"] == {"window": "down", "24h": "up"}
    assert "105.0" not in prompt
    assert "3.1" not in prompt
    assert "2.4" not in prompt
    assert "snapshots" not in prompt
    assert set(ai_agent_groq._EVENT_ALERT_RENDER_JSON_SCHEMA["required"]) == {
        "message_body", "related_news_ids", "possible_action"
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("render_error", [
    AISchemaValidationError("market_claim_mismatch"),
    AISchemaValidationError("invalid_urgency"),
    AIInvalidJsonError("malformed JSON"),
])
async def test_invalid_provider_chain_exhaustion_uses_validated_evidence_fallback(
    monkeypatch, render_error
):
    significance = {
        "symbol": "BTC", "should_alert": True, "confidence": "high",
        "materiality": "material", "novelty": "new", "reason_code": "unusual_move",
    }
    significance_llm = AsyncMock(return_value=("significance-json", significance))
    # The mocked router exception must represent a fully invalid-output chain.
    render_error._llm_all_exhausted_attempts_invalid_output = True
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
    monkeypatch.setattr(alerts.event_analysis_health, "record_success", lambda: None)

    payload = _payload()
    decision, analysis_id = await alerts._create_event_analysis_decision(payload)

    assert analysis_id == 400
    assert decision is not None and decision.should_alert
    assert decision.urgency == "normal"
    assert decision.related_news_ids == []
    assert "4.8%" not in decision.message_body
    assert render_outcome.await_args.kwargs["status"] == "success"
    assert render_outcome.await_args.kwargs["error_reason"].startswith(
        "deterministic_fallback_from_"
    )
    assert save_analysis.await_args.kwargs["status"] == "success"
    assert delivery_outcome.await_args.kwargs["status"] == alerts.OUTCOME_ALLOWED
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
