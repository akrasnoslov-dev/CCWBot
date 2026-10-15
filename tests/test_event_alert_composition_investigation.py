"""Synthetic regressions for the October alert-composition investigation."""

from decimal import Decimal

import pytest

from bot import alerts
from bot.alerting.event_analysis import (
    EventAnalysisDecision,
    EventAnalysisValidationError,
    _validate_positive_market_claims,
)
from bot.alerting.event_text import final_event_alert_quality_flags


def market(prices=(100, 101, 102), window="2", day="-1"):
    return {
        "price": Decimal(str(prices[-1])),
        "chg_window_percent": Decimal(window),
        "chg24h_percent": Decimal(day),
        "analysed_window_minutes": 180,
        "snapshots": [
            {"m": minute, "p": Decimal(str(price))}
            for minute, price in zip((-180, -90, 0), prices, strict=True)
        ],
    }


def validate(
    situation, data, action="Watch whether the next observed interval extends the move or turns."
):
    _validate_positive_market_claims(
        title="",
        message_body=situation,
        possible_action=action,
        market_data=data,
        last_msg={},
        timestamp_utc=None,
    )


@pytest.mark.parametrize(
    "situation",
    [
        (
            "The rising move persisted across supplied snapshots. "
            "The broader 24-hour trend remains lower."
        ),
        (
            "The rising move persisted across supplied snapshots while "
            "the broader 24-hour trend remains lower."
        ),
    ],
)
def test_snapshot_trajectory_direction_is_scoped_to_its_own_period(situation):
    validate(situation, market())


def test_consistent_with_describes_alignment_not_snapshot_persistence():
    validate(
        "The current rise is consistent with the broader positive trend.",
        market((100, 101, 100.5), "0.5", "1"),
    )


@pytest.mark.parametrize(
    ("situation", "prices"),
    [
        ("The rise persisted across supplied snapshots.", (100, 102, 101)),
        ("The decline persisted across supplied snapshots.", (100, 101, 102)),
    ],
)
def test_unsupported_snapshot_trajectories_remain_rejected(situation, prices):
    with pytest.raises(EventAnalysisValidationError, match="trajectory is unsupported"):
        validate(situation, market(prices))


@pytest.mark.parametrize(
    ("situation", "data"),
    [
        ("The short-term rise contrasts with the broader 24-hour decline.", market()),
        (
            "The short-term decline contrasts with the broader 24-hour rise.",
            market((102, 101, 100), "-2", "1"),
        ),
    ],
)
def test_grounded_opposite_periods_survive_final_telegram_assembly(situation, data):
    decision = EventAnalysisDecision(
        symbol="ETH",
        should_alert=True,
        event_key="eth_market_event",
        title="ignored",
        message_body=situation,
        related_news_ids=[],
        urgency="normal",
        confidence="medium",
        possible_action="Watch whether the next observed interval extends the divergence or turns.",
        reason_for_no_alert=None,
    )
    final = alerts._build_event_alert_payload(
        decision=decision,
        input_payload={"market": data},
        related_news=[],
    )["plain_text"]
    assert f"Situation:\n{situation}\n\n" in final
    assert final.count("Not financial advice.") == 1


@pytest.mark.parametrize(
    "action",
    [
        "Watch whether the next short-term snapshots continue or reverse.",
        "Check whether the next snapshots continue or reverse.",
    ],
)
def test_generic_snapshot_diagnostic_matches_real_message_newlines(action):
    final = (
        "ETH Event Alert\n\nSituation:\nVerified context.\n\n"
        f"Possible action:\n{action}\n\nNot financial advice."
    )
    assert final_event_alert_quality_flags(final)["generic_action"]


def test_specific_next_observation_is_not_generic():
    final = (
        "Situation:\nVerified context.\n\nPossible action:\n"
        "Watch whether the next snapshots extend the divergence from the broader direction."
        "\n\nNot financial advice."
    )
    assert not final_event_alert_quality_flags(final)["generic_action"]


def test_alignment_without_monotonic_snapshots_survives_compaction():
    from bot.alerting.event_text import compact_event_alert_situation

    situation = "The short-term rise is consistent with the broader positive trend."
    assert (
        compact_event_alert_situation(
            situation,
            significance_reason=None,
            market_data=market((100, 101, 100.5), "0.5", "1"),
        )
        == situation
    )


@pytest.mark.parametrize(
    "situation",
    [
        "The short-term decline contrasts with the broader 24-hour rise.",
        "The short-term rise contrasts with the broader 24-hour rise.",
        "The short-term rise is consistent with the broader negative trend.",
    ],
)
def test_incorrect_direction_or_divergence_still_uses_evidence_fallback(situation):
    from bot.alerting.event_text import compact_event_alert_situation

    assert (
        compact_event_alert_situation(
            situation,
            significance_reason=None,
            market_data=market(),
        )
        != situation
    )


@pytest.mark.parametrize("wrong_direction", ["weakness", "weaker", "bearish", "selloff", "crash"])
def test_scoped_direction_guard_preserves_older_downward_vocabulary(wrong_direction):
    from bot.alerting.event_analysis import market_direction_claims_supported

    assert not market_direction_claims_supported(
        f"The short-term {wrong_direction} contrasts with the broader negative trend.", market()
    )


@pytest.mark.parametrize("wrong_direction", ["strength", "stronger", "bullish", "surge"])
def test_scoped_direction_guard_preserves_older_upward_vocabulary(wrong_direction):
    from bot.alerting.event_analysis import market_direction_claims_supported

    assert not market_direction_claims_supported(
        f"The short-term {wrong_direction} contrasts with the broader positive trend.",
        market((102, 101, 100), "-2", "1"),
    )


@pytest.mark.parametrize(
    ("window", "day", "direction", "comparison"),
    [
        ("0.443", "0.402", "rise", "larger"),
        ("0.556", "0.809", "rise", "smaller"),
        ("-0.337", "-0.134", "decline", "larger"),
        ("0.05", "3.622", "rise", "smaller"),
        ("-1", "-1", "decline", "equal"),
    ],
)
def test_alignment_fallback_names_direction_and_verified_size_relationship(
    window, day, direction, comparison
):
    from bot.alerting.event_text import event_alert_presentation_fallback

    situation, _ = event_alert_presentation_fallback(
        {"chg_window_percent": Decimal(window), "chg24h_percent": Decimal(day)}, []
    )
    assert direction in situation
    assert comparison in situation
    assert "%" not in situation
    assert "faster" not in situation and "material" not in situation
