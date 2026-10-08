from __future__ import annotations

from decimal import Decimal

import pytest

import bot.services.ai_agent_groq as ai_agent_groq
from bot.alerting.event_analysis import (
    EventAnalysisValidationError,
    empirical_absolute_move_percentile,
    validate_event_significance_output,
)


def _payload() -> dict:
    return {
        "symbol": "SOL",
        "timestamp_utc": "2026-10-02T05:15:00+00:00",
        "market": {
            "price": Decimal("150.0"),
            "snapshots": [
                {"m": -180, "p": Decimal("144.2")},
                {"m": -90, "p": Decimal("146.1")},
                {"m": 0, "p": Decimal("150.0")},
            ],
            "analysed_window_minutes": 180,
            "chg_window_percent": Decimal("4.0275"),
            "chg30m_percent": Decimal("1.1"),
            "chg1h_percent": Decimal("2.2"),
            "chg24h_percent": Decimal("3.5347"),
            "chg_since_msg_percent": Decimal("5.1"),
            "relative_window_percentile_30d": Decimal("99.2"),
            "relative_24h_percentile_30d": Decimal("91.3"),
        },
        "news": [
            {
                "news_id": "n1",
                "source": "Wire A",
                "title": "Solana activity increases during the session",
                "summary": "Long summary that the always-on decision prompt should not need.",
                "relevance_label": "asset_specific",
                "material": True,
                "time": "2026-10-02T04:40:00+00:00",
            },
            {
                "news_id": "n2",
                "source": "Wire B",
                "title": "Crypto market advances",
                "summary": "Another verbose summary.",
                "relevance_label": "market_wide",
                "material": False,
                "time": "2026-10-02T04:00:00+00:00",
            },
            {
                "news_id": "n3",
                "source": "Wire C",
                "title": "Third candidate should be excluded from stage one",
                "summary": "Not needed.",
                "relevance_label": "supporting",
                "material": False,
                "time": "2026-10-02T03:00:00+00:00",
            },
        ],
        "previous_event_alert": {
            "canonical_event_key": "sol_price_uptrend",
            "semantic_family": "price_uptrend",
            "analysed_window_move": Decimal("1.2"),
            "created_at": "2026-09-30T10:00:00+00:00",
            "age_minutes": 2595,
        },
        "recent_event_counts": {"h6": 2, "h24": 5},
    }


def test_empirical_absolute_move_percentile_uses_relative_magnitude_not_direction():
    history = [Decimal(str(value)) for value in range(1, 101)]

    assert empirical_absolute_move_percentile(Decimal("95"), history, min_samples=100) == 95.0
    assert empirical_absolute_move_percentile(Decimal("-95"), history, min_samples=100) == 95.0


def test_empirical_absolute_move_percentile_returns_none_for_insufficient_or_missing_data():
    assert empirical_absolute_move_percentile(Decimal("4"), [1, 2, 3], min_samples=4) is None
    assert empirical_absolute_move_percentile(None, range(1, 101), min_samples=100) is None


def test_event_significance_prompt_contains_relative_context_without_numeric_gate():
    payload = _payload()
    compact = ai_agent_groq._event_significance_prompt_payload(payload)

    assert compact["sym"] == "SOL"
    assert compact["m"] == {
        "s": [
            [-180, Decimal("144.2")],
            [-90, Decimal("146.1")],
            [0, Decimal("150.0")],
        ],
        "w": 180,
        "c30": Decimal("1.1"),
        "c60": Decimal("2.2"),
        "cw": Decimal("4.0275"),
        "c24": Decimal("3.5347"),
        "cl": Decimal("5.1"),
        "pw": Decimal("99.2"),
        "p24": Decimal("91.3"),
    }
    assert len(compact["n"]) == 2
    assert compact["n"][0]["t"] == payload["news"][0]["title"]
    assert compact["n"][0]["r"] == "asset_specific"
    assert compact["n"][0]["mat"] is True
    assert "x" not in compact["n"][0]
    assert "src" not in compact["n"][0]
    assert compact["prev"] == {"min": 2595, "f": "price_uptrend", "cw": Decimal("1.2")}
    assert compact["cnt"] == {"h6": 2, "h24": 5}

    prompt = ai_agent_groq.build_event_significance_prompt(payload)
    lowered = prompt.lower()
    assert "context, not" in lowered
    assert "threshold" in lowered
    assert "no fixed numeric cutoff" in lowered
    assert "default=>no alert" in lowered
    assert "q1 materiality" in lowered
    assert "q2 novelty" in lowered
    assert "q3 should_alert" in lowered
    assert "large c24/p24" in lowered
    assert "previous/recent events can only reduce novelty" in lowered
    assert "only after q1/q2/q3 choose reason_code" in lowered
    assert "calibration examples are not thresholds" in lowered
    assert "materiality=material" in lowered
    assert "novelty=new" in lowered
    assert "should_alert=true" in lowered
    assert "should_alert=false" in lowered
    assert len(prompt) <= 2600

def test_event_significance_schema_generates_reasoning_before_decision():
    schema = ai_agent_groq._EVENT_SIGNIFICANCE_JSON_SCHEMA

    assert list(schema["properties"]) == [
        "symbol",
        "materiality",
        "novelty",
        "should_alert",
        "reason_code",
        "confidence",
    ]
    assert schema["required"] == [
        "symbol",
        "materiality",
        "novelty",
        "should_alert",
        "reason_code",
        "confidence",
    ]


def test_event_significance_output_is_small_and_constrained():
    decision = validate_event_significance_output(
        {
            "symbol": "SOL",
            "should_alert": True,
            "confidence": "high",
            "materiality": "material",
            "novelty": "new",
            "reason_code": "unusual_move",
        },
        expected_symbol="SOL",
    )

    assert decision.should_alert is True
    assert decision.confidence == "high"
    assert decision.materiality == "material"
    assert decision.novelty == "new"
    assert decision.reason_code == "unusual_move"

    with pytest.raises(EventAnalysisValidationError, match="reason_code"):
        validate_event_significance_output(
            {
                "symbol": "SOL",
                "should_alert": False,
                "confidence": "medium",
                "materiality": "routine",
                "novelty": "new",
                "reason_code": "four_percent_threshold",
            },
            expected_symbol="SOL",
        )


@pytest.mark.parametrize(
    ("should_alert", "reason_code"),
    (
        (False, "unusual_move"),
        (False, "fast_move"),
        (False, "reversal"),
        (False, "trend_acceleration"),
        (False, "market_news_alignment"),
        (True, "routine_move"),
        (True, "unclear"),
    ),
)
def test_event_significance_rejects_internally_inconsistent_reason_polarity(
    should_alert, reason_code
):
    with pytest.raises(EventAnalysisValidationError, match="inconsistent significance decision"):
        validate_event_significance_output(
            {
                "symbol": "BTC",
                "should_alert": should_alert,
                "confidence": "medium",
                "materiality": "material" if should_alert else "routine",
                "novelty": "new",
                "reason_code": reason_code,
            },
            expected_symbol="BTC",
        )


def test_event_significance_rejects_true_news_only_as_inconsistent():
    with pytest.raises(EventAnalysisValidationError, match="inconsistent significance decision"):
        validate_event_significance_output(
            {
                "symbol": "BTC",
                "should_alert": True,
                "confidence": "medium",
                "materiality": "material",
                "novelty": "new",
                "reason_code": "news_only",
            },
            expected_symbol="BTC",
        )


@pytest.mark.parametrize(
    ("materiality", "novelty"),
    (
        ("routine", "new"),
        ("unclear", "new"),
        ("material", "continuation"),
        ("material", "repeated"),
        ("material", "unclear"),
    ),
)
def test_event_significance_true_requires_material_and_new(materiality, novelty):
    with pytest.raises(EventAnalysisValidationError, match="materiality and novelty"):
        validate_event_significance_output(
            {
                "symbol": "ETH",
                "should_alert": True,
                "confidence": "high",
                "materiality": materiality,
                "novelty": novelty,
                "reason_code": "fast_move",
            },
            expected_symbol="ETH",
        )


def test_event_significance_false_allows_material_and_new_with_no_alert_reason():
    decision = validate_event_significance_output(
        {
            "symbol": "ETH",
            "should_alert": False,
            "confidence": "medium",
            "materiality": "material",
            "novelty": "new",
            "reason_code": "routine_move",
        },
        expected_symbol="ETH",
    )

    assert decision.should_alert is False
    assert decision.materiality == "material"
    assert decision.novelty == "new"
    assert decision.reason_code == "routine_move"
