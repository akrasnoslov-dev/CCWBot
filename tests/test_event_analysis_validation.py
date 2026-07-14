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
