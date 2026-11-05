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


@pytest.mark.parametrize("body, valid", [
    ("BTC rose 1% over 1 hour.", True),
    ("BTC fell 0.4% over 30 minutes.", True),
    ("BTC rose 2% over 1 hour.", False),
    ("BTC fell 1% over 1 hour.", False),
    ("BTC rose 0.4% over 30 minutes.", False),
    ("BTC rose 1% over 2 hours.", False),
])
def test_render_short_period_claims_validate_against_their_own_metric(body, valid):
    payload = _payload()
    payload["market"].update(chg1h_percent=1, chg30m_percent=-0.4)
    parsed = {"message_body": body, "related_news_ids": [],
              "possible_action": "Watch subsequent observations."}
    result = alerts._event_alert_render_result_for_validation(
        parsed, input_payload=payload, expected_symbol="BTC", confidence="high",
        candidate_news_ids=set(),
    )
    def check():
        alerts._validate_event_alert_render_causality(parsed, market_data=payload["market"])
        validate_event_analysis_output(
            result, expected_symbol="BTC", candidate_news_ids=set(),
            market_data=payload["market"], last_msg=payload["last_msg"],
            timestamp_utc=payload["timestamp_utc"],
        )
    if valid:
        check()
    else:
        with pytest.raises(EventAnalysisValidationError):
            check()


def test_short_period_source_requires_data_and_prefers_exact_metric():
    from bot.alerting.event_analysis import _market_claim_source, _market_claim_value

    text = "rose 1% over 1 hour"
    market = {"analysed_window_minutes": 180, "chg_window_percent": 1}
    with pytest.raises(EventAnalysisValidationError):
        _market_claim_source(text, 5, market, None, None)
    market.update(analysed_window_minutes=60, chg1h_percent=-1)
    source = _market_claim_source(text, 5, market, None, None)
    assert source == "1h"
    assert _market_claim_value(source, market) == -1
    del market["chg1h_percent"]
    assert _market_claim_value(source, market) == 1


@pytest.mark.parametrize("left,right", [
    ("30-minute", "1-hour"), ("1-hour", "30-minute"),
    ("30-minute", "analysed-window"), ("analysed-window", "30-minute"),
    ("30-minute", "24-hour"), ("24-hour", "30-minute"),
    ("1-hour", "analysed-window"), ("analysed-window", "1-hour"),
    ("1-hour", "24-hour"), ("24-hour", "1-hour"),
    ("analysed-window", "24-hour"), ("24-hour", "analysed-window"),
])
@pytest.mark.parametrize("case", ["valid", "reversed", "missing", "opposite", "equal"])
@pytest.mark.parametrize("trend", ["rise", "decline"])
def test_render_period_comparison_checks_both_operands_end_to_end(left, right, case, trend):
    payload = _payload()
    fields = {"30-minute": "chg30m_percent", "1-hour": "chg1h_percent",
              "analysed-window": "chg_window_percent", "24-hour": "chg24h_percent"}
    market = payload["market"]
    market.update(chg30m_percent=0.5, chg1h_percent=1, chg_window_percent=1.5,
                  chg24h_percent=2)
    if trend == "decline":
        for field in fields.values():
            market[field] *= -1
    if case == "missing":
        market[fields[left]] = None
    elif case == "opposite":
        market[fields[left]] *= -1
    elif case == "equal":
        market[fields[left]] = market[fields[right]]
    comparison = "weaker" if market.get(fields[left]) is not None and (
        abs(market[fields[left]]) < abs(market[fields[right]])
    ) else "stronger"
    if case == "reversed":
        comparison = "stronger" if comparison == "weaker" else "weaker"
    parsed = {"message_body": f"The {left} {trend} is {comparison} than the {right} {trend}.",
              "related_news_ids": [], "possible_action": "Watch subsequent observations."}
    result = alerts._event_alert_render_result_for_validation(
        parsed, input_payload=payload, expected_symbol="BTC", confidence="high",
        candidate_news_ids=set(),
    )
    def check():
        alerts._validate_event_alert_render_causality(parsed, market_data=market)
        validate_event_analysis_output(
            result, expected_symbol="BTC", candidate_news_ids=set(), market_data=market,
            last_msg=payload["last_msg"], timestamp_utc=payload["timestamp_utc"],
        )
    if case == "valid":
        check()
    else:
        with pytest.raises(EventAnalysisValidationError):
            check()


@pytest.mark.parametrize("minutes,label,field", [
    (30, "30-minute", "chg30m_percent"),
    (60, "1-hour", "chg1h_percent"),
    (1440, "24-hour", "chg24h_percent"),
])
def test_render_rejects_comparing_same_market_period_as_distinct(minutes, label, field):
    payload = _payload()
    market = payload["market"]
    market.update(analysed_window_minutes=minutes, chg_window_percent=1)
    market[field] = 2
    parsed = {"message_body": f"The analysed-window rise is weaker than the {label} rise.",
              "related_news_ids": [], "possible_action": "Watch subsequent observations."}
    with pytest.raises(EventAnalysisValidationError):
        alerts._validate_event_alert_render_causality(parsed, market_data=market)


@pytest.mark.parametrize("short_change,day_change,valid", [
    (0.5, 2, True), (3, 2, False), (-0.5, -2, False),
])
@pytest.mark.parametrize("section", ["message_body", "possible_action"])
def test_render_compares_30m_and_broader_day_in_both_sections(
    short_change, day_change, valid, section
):
    payload = _payload()
    market = payload["market"]
    market.update(chg30m_percent=short_change, chg24h_percent=day_change, chg_window_percent=1)
    text = "The 30-minute rise is weaker than the broader 24-hour rise."
    parsed = {"message_body": "The market conditions warrant attention.", "related_news_ids": [],
              "possible_action": "Watch subsequent observations."}
    parsed[section] = text
    result = alerts._event_alert_render_result_for_validation(
        parsed, input_payload=payload, expected_symbol="BTC", confidence="high",
        candidate_news_ids=set(),
    )
    def check():
        alerts._validate_event_alert_render_causality(parsed, market_data=market)
        validate_event_analysis_output(
            result, expected_symbol="BTC", candidate_news_ids=set(), market_data=market,
            last_msg=payload["last_msg"], timestamp_utc=payload["timestamp_utc"],
        )
    if valid:
        check()
    else:
        with pytest.raises(EventAnalysisValidationError):
            check()


@pytest.mark.parametrize("short_change,valid", [(0.5, True), (3, False)])
def test_reverse_order_30m_comparison_with_broader_day(short_change, valid):
    payload = _payload()
    market = payload["market"]
    market.update(chg30m_percent=short_change, chg24h_percent=2, chg_window_percent=1)
    parsed = {"message_body": "The 24-hour rise remains stronger than the 30-minute rise.",
              "related_news_ids": [], "possible_action": "Watch subsequent observations."}
    result = alerts._event_alert_render_result_for_validation(
        parsed, input_payload=payload, expected_symbol="BTC", confidence="high",
        candidate_news_ids=set(),
    )
    def check():
        alerts._validate_event_alert_render_causality(parsed, market_data=market)
        validate_event_analysis_output(
            result, expected_symbol="BTC", candidate_news_ids=set(), market_data=market,
            last_msg=payload["last_msg"], timestamp_utc=payload["timestamp_utc"],
        )
    if valid:
        check()
    else:
        with pytest.raises(EventAnalysisValidationError):
            check()


@pytest.mark.parametrize("section", ["message_body", "possible_action"])
@pytest.mark.parametrize("comparison", [
    "is larger than", "is greater than", "outpaced", "exceeded", "was smaller than",
])
@pytest.mark.parametrize("case", ["valid", "contradictory", "missing"])
def test_historical_magnitude_comparisons_validate_both_periods(section, comparison, case):
    payload = _payload()
    market = payload["market"]
    smaller = "smaller" in comparison
    short_change = 0.5 if (case == "valid") == smaller else 3
    market.update(chg30m_percent=None if case == "missing" else short_change,
                  chg24h_percent=2, chg_window_percent=1)
    parsed = {"message_body": "The market conditions warrant attention.", "related_news_ids": [],
              "possible_action": "Watch subsequent observations."}
    parsed[section] = f"The 30-minute rise {comparison} the 24-hour rise."
    result = alerts._event_alert_render_result_for_validation(
        parsed, input_payload=payload, expected_symbol="BTC", confidence="high",
        candidate_news_ids=set(),
    )
    def check():
        alerts._validate_event_alert_render_causality(parsed, market_data=market)
        validate_event_analysis_output(
            result, expected_symbol="BTC", candidate_news_ids=set(), market_data=market,
            last_msg=payload["last_msg"], timestamp_utc=payload["timestamp_utc"],
        )
    if case == "valid":
        check()
    else:
        with pytest.raises(EventAnalysisValidationError):
            check()


@pytest.mark.parametrize("section", ["message_body", "possible_action"])
@pytest.mark.parametrize("condition", [
    "If the next 30-minute rise is greater than the 24-hour rise",
    "If a 30-minute rise is greater than the 24-hour rise",
    "When the 30-minute rise exceeds the 24-hour rise",
    "Unless the 30-minute rise outpaces the 24-hour rise",
    "Should the 30-minute rise outpace the 24-hour rise",
    "Watch if the 30-minute rise is greater than the 24-hour rise",
    "Monitor when the 30-minute rise outpaces the 24-hour rise",
    "Watch unless the 30-minute rise exceeds the 24-hour rise",
    "If the next 30-minute rise outpaced the 24-hour rise",
    "Should the next 30-minute rise have exceeded the 24-hour rise",
    "When the upcoming 30-minute rise was greater than the 24-hour rise",
])
def test_future_comparison_remains_conditional(section, condition):
    payload = _payload()
    market = payload["market"]
    market.update(chg30m_percent=-0.5, chg24h_percent=2, chg_window_percent=1)
    parsed = {"message_body": "The market conditions warrant attention.", "related_news_ids": [],
              "possible_action": "Watch subsequent observations."}
    parsed[section] = f"{condition}, watch for a change in the observed direction."
    result = alerts._event_alert_render_result_for_validation(
        parsed, input_payload=payload, expected_symbol="BTC", confidence="high",
        candidate_news_ids=set(),
    )
    alerts._validate_event_alert_render_causality(parsed, market_data=market)
    validate_event_analysis_output(
        result, expected_symbol="BTC", candidate_news_ids=set(), market_data=market,
        last_msg=payload["last_msg"], timestamp_utc=payload["timestamp_utc"],
    )


@pytest.mark.parametrize("section", ["message_body", "possible_action"])
@pytest.mark.parametrize("statement", [
    "The 30-minute rise is larger in magnitude than the 24-hour rise.",
    "The 30-minute trend's net rise outstripped the 24-hour rise.",
    "The 30-minute rise dominated the 24-hour rise.",
    "The 30-minute rise swamped the 24-hour rise.",
    "The 30-minute rise outpaced the last hour rise.",
    "The 30-minute rise outpaced the prior hour rise.",
    "The 30-minute rise was twice the 24-hour rise.",
    "The 30-minute rise is greater when compared to the 24-hour rise.",
    "The 30-minute rise is greater when compared with the 24-hour rise.",
    "The 30-minute rise is greater while compared with the 24-hour rise.",
    "The 30-minute rise is greater when directly compared to the 24-hour rise.",
    "The 30-minute rise is greater when comparing it to the 24-hour rise.",
    "The 30-minute rise is greater when set against the 24-hour rise.",
    "The 30-minute rise is greater when measured against the 24-hour rise.",
    "When compared to the 24-hour rise, the 30-minute rise is greater.",
    "Compared to the 24-hour rise, the 30-minute rise is greater.",
    "Relative to the 24-hour rise, the 30-minute rise is greater.",
    "Against the 24-hour rise, the 30-minute rise is greater.",
    "Measured against the 24-hour rise, the 30-minute rise is greater.",
    "Set against the 24-hour rise, the 30-minute rise is greater.",
    "In comparison with the 24-hour rise, the 30-minute rise is greater.",
    "In contrast with the 24-hour rise, the 30-minute rise is greater.",
    "In contrast with the 24-hour rise, the 30-minute rise is higher.",
    "In comparison with the 24-hour rise, the 30-minute rise is higher.",
    "The 30-minute rise is higher, versus the 24-hour rise.",
    "The 30-minute rise is weaker than the 1-hour rise and surpassed the 24-hour rise.",
    "The 30-minute rise outpaced the 24-hour rise and if the next observation rises, watch it.",
    "Watch if the 30-minute rise was greater than the 24-hour rise.",
])
def test_unparsed_or_historical_comparisons_fail_closed(section, statement):
    payload = _payload()
    market = payload["market"]
    market.update(chg30m_percent=0.5, chg1h_percent=1, chg24h_percent=2,
                  chg_window_percent=1.5)
    parsed = {"message_body": "The market conditions warrant attention.", "related_news_ids": [],
              "possible_action": "Watch subsequent observations."}
    parsed[section] = statement
    result = alerts._event_alert_render_result_for_validation(
        parsed, input_payload=payload, expected_symbol="BTC", confidence="high",
        candidate_news_ids=set(),
    )
    with pytest.raises(EventAnalysisValidationError):
        alerts._validate_event_alert_render_causality(parsed, market_data=market)
        validate_event_analysis_output(
            result, expected_symbol="BTC", candidate_news_ids=set(), market_data=market,
            last_msg=payload["last_msg"], timestamp_utc=payload["timestamp_utc"],
        )


@pytest.mark.parametrize("section", ["message_body", "possible_action"])
@pytest.mark.parametrize("label", ["current", "latest", "window", "analysed move", "snapshot"])
def test_window_alias_comparisons_do_not_bypass_validation(section, label):
    payload = _payload()
    market = payload["market"]
    market.update(chg_window_percent=0.5, chg24h_percent=2)
    parsed = {"message_body": "The market conditions warrant attention.", "related_news_ids": [],
              "possible_action": "Watch subsequent observations."}
    parsed[section] = f"The {label} rise is larger than the 24-hour rise."
    result = alerts._event_alert_render_result_for_validation(
        parsed, input_payload=payload, expected_symbol="BTC", confidence="high",
        candidate_news_ids=set(),
    )
    with pytest.raises(EventAnalysisValidationError):
        alerts._validate_event_alert_render_causality(parsed, market_data=market)
        validate_event_analysis_output(
            result, expected_symbol="BTC", candidate_news_ids=set(), market_data=market,
            last_msg=payload["last_msg"], timestamp_utc=payload["timestamp_utc"],
        )


@pytest.mark.parametrize("section", ["message_body", "possible_action"])
@pytest.mark.parametrize("statement", [
    "The 30-minute rise remains positive while the 24-hour rise is also positive.",
    "The 30-minute trend rose, the 24-hour trend rose.",
    "The 30-minute rise increased, the 24-hour rise increased.",
    "The 30-minute gain continued, the 24-hour gain continued.",
    "The 30-minute rise is positive, and the 24-hour rise is positive.",
    "The 30-minute rise continued, and the 24-hour rise remained positive.",
])
def test_separate_period_facts_remain_valid_without_magnitude_comparison(section, statement):
    payload = _payload()
    market = payload["market"]
    market.update(chg30m_percent=0.5, chg24h_percent=2, chg_window_percent=1)
    parsed = {"message_body": "The market conditions warrant attention.", "related_news_ids": [],
              "possible_action": "Watch subsequent observations."}
    parsed[section] = statement
    result = alerts._event_alert_render_result_for_validation(
        parsed, input_payload=payload, expected_symbol="BTC", confidence="high",
        candidate_news_ids=set(),
    )
    alerts._validate_event_alert_render_causality(parsed, market_data=market)
    validate_event_analysis_output(
        result, expected_symbol="BTC", candidate_news_ids=set(), market_data=market,
        last_msg=payload["last_msg"], timestamp_utc=payload["timestamp_utc"],
    )


@pytest.mark.parametrize("phrase", [
    "an hour", "one hour", "60 minutes", "0.5 hours", "the last hour", "the past hour",
    "the past half-hour", "the last half an hour",
])
def test_short_period_aliases_cannot_use_opposite_window_direction(phrase):
    from bot.alerting.event_analysis import market_direction_claims_supported

    market = {"chg_window_percent": -2, "chg24h_percent": -3,
              "chg1h_percent": 1, "chg30m_percent": 1}
    assert not market_direction_claims_supported(f"BTC fell over {phrase}.", market)
    assert market_direction_claims_supported(f"BTC rose over {phrase}.", market)


@pytest.mark.parametrize("body", [
    "The hourly decline continues.",
    "The half-hourly decline continues.",
    "BTC fell in the previous hour.",
])
def test_short_period_aliases_fail_closed_through_full_validation(body):
    payload = _payload()
    payload["market"].update(chg1h_percent=1, chg30m_percent=1)
    parsed = {"message_body": body, "related_news_ids": [],
              "possible_action": "Watch subsequent observations."}
    result = alerts._event_alert_render_result_for_validation(
        parsed, input_payload=payload, expected_symbol="BTC", confidence="high",
        candidate_news_ids=set(),
    )
    with pytest.raises(EventAnalysisValidationError):
        alerts._validate_event_alert_render_causality(parsed, market_data=payload["market"])
        validate_event_analysis_output(
            result, expected_symbol="BTC", candidate_news_ids=set(),
            market_data=payload["market"], last_msg=payload["last_msg"],
            timestamp_utc=payload["timestamp_utc"],
        )


def test_matching_leading_render_labels_are_normalized_but_cross_sections_remain_rejected():
    normalized = alerts._normalize_render_section_labels({
        "message_body": "Situation: The latest observed step slowed.",
        "possible_action": "Possible action: Watch the next observed interval for reversal.",
    })
    assert normalized["message_body"] == "The latest observed step slowed."
    assert normalized["possible_action"] == "Watch the next observed interval for reversal."
    with pytest.raises(EventAnalysisValidationError, match="mixed render sections"):
        alerts._validate_event_alert_render_causality({
            "message_body": "The latest step slowed. Possible action: watch it.",
            "possible_action": "Watch the next observed interval.",
        })


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
    assert "bind the observation to a supplied relationship" in prompt
    assert "generic descriptions of pace" in prompt
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

@pytest.mark.parametrize("statement,valid", [
    ("The final snapshot fell after the previous snapshot rose.", True),
    ("The final snapshot rose after the previous snapshot fell.", False),
    ("The final snapshot fell after the previous snapshot fell.", False),
    ("The final snapshot fell after the previous snapshot rose, "
     "while the 24-hour trend fell.", False),
    ("The last snapshot fell following the previous snapshot rose.", True),
])
@pytest.mark.parametrize("section", ["message_body", "possible_action"])
def test_mixed_snapshot_steps_are_checked_against_their_own_observations(
    statement, valid, section
):
    payload = _payload()
    payload["symbol"] = "SOL"
    payload["market"].update(
        price=99, chg_window_percent=-1, chg24h_percent=2,
        snapshots=[{"m": -180, "p": 100}, {"m": -120, "p": 98},
                   {"m": -60, "p": 101}, {"m": 0, "p": 99}],
    )
    parsed = {"message_body": "The short-term decline contrasts with the 24-hour rise.",
              "related_news_ids": [],
              "possible_action": "Watch the next observed interval."}
    parsed[section] = statement
    def check():
        alerts._validate_event_alert_render_causality(parsed, market_data=payload["market"])
        result = alerts._event_alert_render_result_for_validation(
            parsed, input_payload=payload, expected_symbol="SOL", confidence="high",
            candidate_news_ids=set(),
        )
        validate_event_analysis_output(
            result, expected_symbol="SOL", candidate_news_ids=set(),
            market_data=payload["market"], last_msg=payload["last_msg"],
            timestamp_utc=payload["timestamp_utc"],
        )
    if valid:
        check()
    else:
        with pytest.raises(EventAnalysisValidationError):
            check()


@pytest.mark.parametrize("snapshots", [
    [],
    [{"m": -120, "p": 98}, {"m": -60, "p": 101}, {"m": -1, "p": 99}],
    [{"m": -60, "p": 98}, {"m": -60, "p": 101}, {"m": 0, "p": 99}],
    [{"m": -120, "p": 101}, {"m": -60, "p": 101}, {"m": 0, "p": 99}],
])
def test_snapshot_step_claim_requires_unambiguous_current_observations(snapshots):
    assert not alerts.market_direction_claims_supported(
        "The final snapshot fell after the previous snapshot rose.",
        {"snapshots": snapshots, "chg_window_percent": -1},
    )


def test_future_snapshot_step_scenario_is_not_treated_as_a_historical_fact():
    from bot.alerting.event_analysis import _validate_action_market_claims

    _validate_action_market_claims(
        "If the final snapshot rose after the previous snapshot fell, watch the next interval.",
        market_data={"snapshots": []}, last_msg=None, timestamp_utc=None,
    )
