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
