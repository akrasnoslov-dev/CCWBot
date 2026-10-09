"""Grounded Event Alert copy: test scenarios without recipient or LLM calls."""

from decimal import Decimal

import pytest

from bot.alerting.event_text import (
    compact_event_alert_situation,
    event_alert_presentation_fallback,
)


@pytest.mark.parametrize(
    ("symbol", "change", "thirty", "hour", "expected", "next_signal"),
    [
        ("BTC", "-3.0", "-1.8", "-2.2", "picked up pace", "30-minute"),
        ("ETH", "2.4", "0.25", "1.8", "slower", "30-minute"),
        ("GRAM", "4.0", "1.6", "2.0", "picked up pace", "30-minute"),
        ("SOL", "-3.0", "-0.3", "-1.8", "slower", "30-minute"),
    ],
)
def test_short_window_pace_is_a_provable_current_market_relationship(
    symbol, change, thirty, hour, expected, next_signal
):
    market = {
        "analysed_window_minutes": 180,
        "chg_window_percent": Decimal(change),
        "chg30m_percent": Decimal(thirty),
        "chg1h_percent": Decimal(hour),
    }
    situation, watch = event_alert_presentation_fallback(market, [])
    assert expected in situation, (symbol, situation)
    assert next_signal in watch
    assert "%" not in situation
    assert "historic" not in situation.lower()
    assert not any(x in (situation + watch).lower() for x in ("buy now", "sell now", "risk plan"))


@pytest.mark.parametrize(
    ("market", "unverified"),
    [
        ({"chg_window_percent": 2, "chg30m_percent": 1, "chg1h_percent": None,
          "analysed_window_minutes": 180}, "missing hour"),
        ({"chg_window_percent": 2, "chg30m_percent": -1, "chg1h_percent": 1.5,
          "analysed_window_minutes": 180}, "opposite 30m direction"),
        ({"chg_window_percent": 2, "chg30m_percent": 1, "chg1h_percent": 1.5,
          "analysed_window_minutes": 30}, "overlapping short window"),
        ({"chg_window_percent": 2, "chg30m_percent": "NaN", "chg1h_percent": 1.5,
          "analysed_window_minutes": 180}, "invalid number"),
        ({"chg_window_percent": 2, "chg30m_percent": 1, "chg1h_percent": 2,
          "analysed_window_minutes": 180}, "equal pace"),
    ],
)
def test_missing_contradictory_or_equal_short_windows_make_no_pace_claim(
    market, unverified
):
    situation, watch = event_alert_presentation_fallback(market, [])
    assert "picked up pace" not in situation, unverified
    assert "slower" not in situation, unverified
    assert "30-minute" not in watch, unverified


def test_latest_snapshot_countermove_takes_priority_over_hourly_pace():
    market = {
        "analysed_window_minutes": 180,
        "chg_window_percent": 1,
        "chg30m_percent": 0.8,
        "chg1h_percent": 1,
        "snapshots": [
            {"m": -180, "p": Decimal("100")},
            {"m": -90, "p": Decimal("104")},
            {"m": 0, "p": Decimal("101")},
        ],
    }
    situation, watch = event_alert_presentation_fallback(market, [])
    assert "reverses part of the earlier path" in situation
    assert "further reversal" in watch
    assert "picked up pace" not in situation


@pytest.mark.parametrize(
    "claim",
    [
        "SEC approved an ETF; the move aligns with the broader 24-hour direction.",
        "Rumors of an exchange hack accompany the broader 24-hour alignment.",
        "Following a new listing, the short-term move aligns with the broader 24-hour trend.",
        "Momentum accelerated on rising volume; the move aligns with the broader 24-hour trend.",
        "BlackRock filed a new trust; the move aligns with the broader 24-hour direction.",
        "An unnamed central bank intervened while the 24-hour direction remains aligned.",
    ],
)
def test_unverified_news_catalysts_and_unverified_market_metrics_never_survive(claim):
    situation = compact_event_alert_situation(
        claim,
        significance_reason=None,
        market_data={"chg_window_percent": 2, "chg24h_percent": 3},
        related_news=[{"news_id": "n1", "title": "Market-related article"}],
    )
    assert situation == (
        "The short-term move continues the same direction as the broader 24-hour trend, "
        "giving the event broader-trend context."
    )


def test_selected_news_does_not_create_a_market_explanation_or_urgency():
    situation, watch = event_alert_presentation_fallback(
        {"chg_window_percent": Decimal("1.4")},
        [{"news_id": "n1", "title": "Rumored ETF approval"}],
    )
    assert "only confirmed signal" in situation
    assert "ETF" not in situation
    assert "urgent" not in (situation + watch).lower()


def test_historical_percentile_without_sample_provenance_not_presented_as_rarity():
    situation, _ = event_alert_presentation_fallback(
        {
            "chg_window_percent": Decimal("-1.4"),
            "relative_window_percentile_30d": Decimal("99"),
        },
        [],
    )
    assert "99" not in situation
    assert "rare" not in situation.lower()
    assert "unusual" not in situation.lower()


def test_full_event_alert_keeps_shared_message_structure_and_disclaimer():
    from bot import alerts
    from bot.alerting.event_analysis import EventAnalysisDecision

    decision = EventAnalysisDecision(
        symbol="BTC",
        should_alert=True,
        event_key="btc_price_downtrend",
        title="Backend owned",
        message_body="Market movement is noteworthy.",
        related_news_ids=[],
        possible_action="Review risk plan if the move continues.",
        urgency="normal",
        confidence="high",
        reason_for_no_alert=None,
    )
    text = alerts._build_event_alert_payload(
        decision=decision,
        input_payload={
            "market": {
                "price": Decimal("65000"),
                "analysed_window_minutes": 180,
                "chg_window_percent": Decimal("-3.0"),
                "chg30m_percent": Decimal("-1.8"),
                "chg1h_percent": Decimal("-2.2"),
            }
        },
        related_news=[],
    )["plain_text"]
    assert "BTC Event Alert" in text
    assert "BTC down ~3.0% in the last 3 hours" in text
    assert "Price: $65,000" in text or "Price: $65000" in text
    assert "3h market move:" in text
    assert "Situation:\nThe latest 30-minute change is steeper" in text
    assert "Possible action:\nWatch whether the next 30-minute observation" in text
    assert text.endswith("Not financial advice.")
    assert text.count("Not financial advice.") == 1
    situation = text.split("Situation:\n", 1)[1].split("\n\nPossible action:", 1)[0]
    assert "%" not in situation


def test_countermovement_cannot_be_described_as_persistent_direction():
    situation = compact_event_alert_situation(
        "The supplied snapshots show persistent short-term weakness against the broader direction.",
        significance_reason=None,
        market_data={
            "chg_window_percent": Decimal("-2"),
            "chg24h_percent": Decimal("2"),
            "snapshots": [
                {"m": -180, "p": Decimal("100")},
                {"m": -90, "p": Decimal("103")},
                {"m": 0, "p": Decimal("98")},
            ],
        },
        related_news=[],
    )
    assert "persistent" not in situation
    assert "reverses part of the earlier path" in situation


def test_short_term_polarity_cannot_be_borrowed_from_opposite_24h_trend():
    situation = compact_event_alert_situation(
        "The supplied snapshots show positive short-term movement against the broader 24-hour direction.",
        significance_reason=None,
        market_data={
            "chg_window_percent": Decimal("-2"),
            "chg24h_percent": Decimal("2"),
            "snapshots": [
                {"m": -180, "p": Decimal("100")},
                {"m": -90, "p": Decimal("99")},
                {"m": 0, "p": Decimal("98")},
            ],
        },
        related_news=[],
    )
    assert "positive short-term" not in situation
    assert "short-term snapshots" in situation
