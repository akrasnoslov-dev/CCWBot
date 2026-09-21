import pytest

from bot.alerting.event_analysis import (
    EventAnalysisValidationError,
    validate_event_analysis_output,
)


def event_analysis_result(**overrides):
    result = {
        "symbol": "SOL",
        "should_alert": False,
        "event_key": None,
        "title": None,
        "message_body": None,
        "related_news_ids": None,
        "possible_action": None,
        "urgency": None,
        "confidence": None,
        "reason_for_no_alert": "No significant market event requires user attention.",
    }
    result.update(overrides)
    return result


def alert_analysis_result(**overrides):
    result = event_analysis_result(
        should_alert=True,
        event_key="sol_market_event_2026_05_20",
        title="SOL market conditions changed",
        message_body="SOL moved sharply while market context remains mixed.",
        related_news_ids=["n1"],
        possible_action="Review exposure and avoid reacting impulsively.",
        urgency="normal",
        confidence="medium",
        reason_for_no_alert=None,
    )
    result.update(overrides)
    return result


def factual_market_input(**overrides):
    market = {
        "price": 108.20942528957224,
        "snapshots": [{"m": 0, "p": 108.20942528957224}],
        "analysed_window_minutes": 180,
        "chg_window_percent": None,
        "chg24h_percent": -3.5813502370649672,
        "chg_since_msg_percent": -3.2583878312836735,
    }
    market.update(overrides)
    return market


def validate_factual_alert(result, market=None, *, last_msg=None, timestamp_utc=None):
    return validate_event_analysis_output(
        result,
        expected_symbol="sol",
        candidate_news_ids={"n1"},
        market_data=market or factual_market_input(),
        last_msg=last_msg
        or {
            "time": "2026-09-19T11:45:01+00:00",
            "type": "event_alert",
            "price": 111.85406451657656,
        },
        timestamp_utc=timestamp_utc or "2026-09-20T09:14:01+00:00",
    )


def test_no_alert_accepts_null_urgency_confidence_and_null_related_news_ids():
    decision = validate_event_analysis_output(
        event_analysis_result(),
        expected_symbol="sol",
        candidate_news_ids={"n1"},
    )

    assert decision.should_alert is False
    assert decision.related_news_ids == []
    assert decision.urgency is None
    assert decision.confidence is None


def test_no_alert_accepts_empty_related_news_ids():
    decision = validate_event_analysis_output(
        event_analysis_result(related_news_ids=[]),
        expected_symbol="sol",
        candidate_news_ids={"n1"},
    )

    assert decision.should_alert is False
    assert decision.related_news_ids == []
    assert decision.urgency is None
    assert decision.confidence is None


def test_no_alert_accepts_confidence_value():
    decision = validate_event_analysis_output(
        event_analysis_result(related_news_ids=[], confidence="low"),
        expected_symbol="sol",
        candidate_news_ids={"n1"},
    )

    assert decision.should_alert is False
    assert decision.urgency is None
    assert decision.confidence == "low"


@pytest.mark.parametrize("reason", [None, "", "   "])
def test_no_alert_rejects_missing_or_empty_reason_for_no_alert(reason):
    with pytest.raises(
        EventAnalysisValidationError,
        match="reason_for_no_alert is required for no-alert result",
    ):
        validate_event_analysis_output(
            event_analysis_result(reason_for_no_alert=reason),
            expected_symbol="sol",
            candidate_news_ids={"n1"},
        )


def test_alert_rejects_null_urgency():
    with pytest.raises(EventAnalysisValidationError, match="invalid urgency"):
        validate_event_analysis_output(
            alert_analysis_result(urgency=None),
            expected_symbol="sol",
            candidate_news_ids={"n1"},
        )


def test_alert_rejects_invalid_urgency():
    with pytest.raises(EventAnalysisValidationError, match="invalid urgency"):
        validate_event_analysis_output(
            alert_analysis_result(urgency="urgent"),
            expected_symbol="sol",
            candidate_news_ids={"n1"},
        )


def test_alert_rejects_null_confidence():
    with pytest.raises(EventAnalysisValidationError, match="invalid confidence"):
        validate_event_analysis_output(
            alert_analysis_result(confidence=None),
            expected_symbol="sol",
            candidate_news_ids={"n1"},
        )


def test_alert_rejects_unmapped_related_news_ids():
    with pytest.raises(
        EventAnalysisValidationError,
        match="related_news_ids contains unknown news ids",
    ):
        validate_event_analysis_output(
            alert_analysis_result(related_news_ids=["n999"]),
            expected_symbol="sol",
            candidate_news_ids={"n1"},
        )


def test_alert_accepts_gram_display_symbol_for_backend_gram():
    decision = validate_event_analysis_output(
        alert_analysis_result(
            symbol="GRAM",
            event_key="gram_price_downtrend",
            title="GRAM market conditions changed",
            message_body="GRAM moved sharply while market context remains mixed.",
        ),
        expected_symbol="gram",
        candidate_news_ids={"n1"},
    )

    assert decision.symbol == "GRAM"


def test_alert_possible_action_advice_like_wording_no_longer_blocks_schema():
    decision = validate_event_analysis_output(
        alert_analysis_result(
            possible_action=(
                "Buy, sell, adjust your portfolio, and review exposure if it fits your plan."
            )
        ),
        expected_symbol="sol",
        candidate_news_ids={"n1"},
    )

    assert "adjust your portfolio" in decision.possible_action


def test_unknown_extra_field_is_stripped_not_rejected():
    # Reproduces the production GRAM failure: strict validation rejected the whole
    # analysis over an extra display_symbol field. Unknown fields are now dropped.
    decision = validate_event_analysis_output(
        alert_analysis_result(
            symbol="GRAM",
            event_key="gram_price_downtrend",
            title="GRAM market conditions changed",
            message_body="GRAM moved sharply while market context remains mixed.",
            display_symbol="GRAM",
        ),
        expected_symbol="gram",
        candidate_news_ids={"n1"},
    )

    assert decision.symbol == "GRAM"
    assert decision.should_alert is True


def test_missing_required_field_is_still_rejected():
    result = event_analysis_result()
    result.pop("confidence")

    with pytest.raises(EventAnalysisValidationError, match="missing fields"):
        validate_event_analysis_output(
            result,
            expected_symbol="sol",
            candidate_news_ids={"n1"},
        )


def test_wrong_type_required_field_is_still_rejected():
    with pytest.raises(EventAnalysisValidationError, match="should_alert must be boolean"):
        validate_event_analysis_output(
            event_analysis_result(should_alert="yes"),
            expected_symbol="sol",
            candidate_news_ids={"n1"},
        )


def test_alert_still_rejects_invalid_related_news_ids_shape():
    with pytest.raises(
        EventAnalysisValidationError,
        match="related_news_ids must be a string array",
    ):
        validate_event_analysis_output(
            alert_analysis_result(related_news_ids=[1]),
            expected_symbol="sol",
            candidate_news_ids={"n1"},
        )


@pytest.mark.parametrize(
    "title",
    (
        "SOL falls ~3% in the last 3 hours",
        "SOL down 3.58% over a 3-hour window",
        "SOL down ~3.26% over the last three hours",
    ),
)
def test_positive_analysis_rejects_missing_or_misattributed_analysed_window_claim(title):
    with pytest.raises(EventAnalysisValidationError, match="window"):
        validate_factual_alert(alert_analysis_result(title=title))


def test_positive_analysis_rejects_single_snapshot_persistent_trajectory_claim():
    with pytest.raises(EventAnalysisValidationError, match="trajectory"):
        validate_factual_alert(
            alert_analysis_result(
                title="SOL market event",
                message_body="The price declined consistently across the last three hours.",
            )
        )


def test_positive_analysis_rejects_unquantified_analysed_window_claim_when_unavailable():
    with pytest.raises(EventAnalysisValidationError, match="window"):
        validate_factual_alert(
            alert_analysis_result(
                title="SOL market event",
                message_body="SOL fell over the last three hours.",
            )
        )


def test_positive_analysis_rejects_unquantified_analysed_window_claim_with_wrong_direction():
    with pytest.raises(EventAnalysisValidationError, match="direction"):
        validate_factual_alert(
            alert_analysis_result(
                title="SOL market event",
                message_body="SOL fell over the last three hours.",
            ),
            factual_market_input(
                snapshots=[{"m": -180, "p": 100}, {"m": 0, "p": 101}],
                chg_window_percent=1.0,
            ),
        )


def test_positive_analysis_rejects_zig_zag_snapshots_as_consistent_decline():
    with pytest.raises(EventAnalysisValidationError, match="trajectory"):
        validate_factual_alert(
            alert_analysis_result(
                title="SOL market event",
                message_body="SOL declined consistently across the supplied snapshots.",
            ),
            factual_market_input(
                snapshots=[
                    {"m": -180, "p": 100},
                    {"m": -90, "p": 101},
                    {"m": 0, "p": 100},
                ],
                chg_window_percent=-0.1,
            ),
        )


def test_positive_analysis_rejects_unsupported_time_window_claim_in_possible_action():
    with pytest.raises(EventAnalysisValidationError, match="window"):
        validate_factual_alert(
            alert_analysis_result(
                title="SOL market event",
                message_body="Use the supplied market context.",
                possible_action="Review downside risk if SOL's three-hour decline continues.",
            )
        )


def test_positive_analysis_accepts_rounded_analysed_window_claim():
    decision = validate_factual_alert(
        alert_analysis_result(
            title="SOL down ~3.3% over the last 3 hours",
            message_body="The supplied market move is notable.",
        ),
        factual_market_input(
            snapshots=[{"m": -180, "p": 111.85}, {"m": 0, "p": 108.21}],
            chg_window_percent=-3.2583878312836735,
        ),
    )

    assert decision.should_alert is True


def test_positive_analysis_accepts_24h_claim_without_analysed_window_change():
    decision = validate_factual_alert(
        alert_analysis_result(
            title="SOL down ~3.6% over 24 hours",
            message_body="The broader market move is the available context.",
        )
    )

    assert decision.should_alert is True


def test_positive_analysis_keeps_distinct_valid_window_and_24h_claims():
    decision = validate_factual_alert(
        alert_analysis_result(
            title="SOL down ~3.1% over the last 3 hours",
            message_body="SOL is down ~3.6% over 24 hours.",
        ),
        factual_market_input(
            snapshots=[{"m": -180, "p": 111.67}, {"m": 0, "p": 108.21}],
            chg_window_percent=-3.1,
            chg24h_percent=-3.6,
        ),
    )

    assert decision.should_alert is True


def test_positive_analysis_keeps_same_sentence_since_and_24h_claims_distinct():
    decision = validate_factual_alert(
        alert_analysis_result(
            title=(
                "SOL down ~3.3% since the previous alert and down ~3.6% over 24 hours"
            ),
            message_body="The supplied market evidence is notable.",
        )
    )

    assert decision.should_alert is True


def test_positive_analysis_keeps_mixed_direction_claims_in_one_sentence_distinct():
    decision = validate_factual_alert(
        alert_analysis_result(
            title="SOL up 3% over 24 hours, but fell 1% over the last 3 hours",
            message_body="The supplied market evidence is notable.",
        ),
        factual_market_input(
            snapshots=[{"m": -180, "p": 101}, {"m": 0, "p": 100}],
            chg_window_percent=-1,
            chg24h_percent=3,
        ),
    )

    assert decision.should_alert is True


def test_positive_analysis_accepts_since_previous_alert_claim_with_matching_elapsed_context():
    decision = validate_factual_alert(
        alert_analysis_result(
            title="SOL down ~3.3% since the previous alert",
            message_body="The prior alert provides the comparison.",
        )
    )

    assert decision.should_alert is True


def test_positive_analysis_rejects_explicit_since_previous_alert_duration():
    with pytest.raises(EventAnalysisValidationError, match="duration"):
        validate_factual_alert(
            alert_analysis_result(
                title="SOL down ~3.3% since the previous alert over 3 hours",
                message_body="The prior alert provides the comparison.",
            )
        )


def test_positive_analysis_accepts_matching_explicit_since_previous_alert_duration():
    decision = validate_factual_alert(
        alert_analysis_result(
            title="SOL down ~3.3% since the previous alert over 21 hours",
            message_body="The prior alert provides the comparison.",
        ),
        last_msg={
            "time": "2026-09-19T12:14:01+00:00",
            "type": "event_alert",
            "price": 111.85406451657656,
        },
    )

    assert decision.should_alert is True


def test_future_conditional_possible_action_is_not_a_historical_market_claim():
    decision = validate_factual_alert(
        alert_analysis_result(
            title="SOL market event",
            message_body="Use the supplied market context.",
            possible_action="If SOL falls in the next three hours, review downside risk.",
        )
    )

    assert decision.should_alert is True


def test_future_conditional_action_cannot_hide_a_separate_unsupported_market_claim():
    with pytest.raises(EventAnalysisValidationError, match="window"):
        validate_factual_alert(
            alert_analysis_result(
                title="SOL market event",
                message_body="Use the supplied market context.",
                possible_action=(
                    "If SOL falls in the next three hours, compare it with the 3% fall "
                    "in the last three hours."
                ),
            )
        )
