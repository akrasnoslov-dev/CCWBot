"""Grounded Event Alert copy: test scenarios without recipient or LLM calls."""

from decimal import Decimal

import pytest

from bot.alerting.event_text import (
    compact_event_alert_situation,
    event_alert_presentation_fallback,
)


@pytest.mark.parametrize(
    ("symbol", "change", "thirty", "hour", "prices", "expected"),
    [
        ("BTC", "-5.0", "-1.0", "-3.0", ("100", "98", "95"), "picked up pace"),
        ("ETH", "4.0", "0.25", "0.97", ("100", "103", "104"), "slower per minute"),
        ("GRAM", "4.0", "0.95", "1.98", ("100", "101", "103"), "picked up pace"),
        ("SOL", "-4.0", "-0.5", "-1.03", ("100", "97", "96"), "slower per minute"),
    ],
)
def test_short_window_pace_is_a_provable_snapshot_relationship(
    symbol, change, thirty, hour, prices, expected
):
    market = {
        "analysed_window_minutes": 180,
        "chg_window_percent": Decimal(change),
        "chg30m_percent": Decimal(thirty),
        "chg1h_percent": Decimal(hour),
        "snapshots": [
            {"m": -120, "p": Decimal(prices[0])},
            {"m": -60, "p": Decimal(prices[1])},
            {"m": 0, "p": Decimal(prices[2])},
        ],
    }
    situation, watch = event_alert_presentation_fallback(market, [])
    assert expected in situation, (symbol, situation)
    assert "next observed interval" in watch
    assert "%" not in situation
    assert "historic" not in situation.lower()
    assert not any(
        item in (situation + watch).lower()
        for item in ("buy now", "sell now", "risk plan")
    )


@pytest.mark.parametrize(
    ("overrides", "invalid_reason"),
    [
        ({"chg1h_percent": None}, "missing hour"),
        ({"chg30m_percent": 1}, "opposite 30m direction"),
        ({"analysed_window_minutes": 30}, "short analysed window"),
        ({"chg30m_percent": "NaN"}, "invalid number"),
        ({"snapshots": []}, "missing snapshots"),
        ({"snapshots": [
            {"m": -120, "p": 100},
            {"m": -60, "p": 98},
            {"m": -10, "p": 95},
        ]}, "no current snapshot"),
        ({"snapshots": [
            {"m": -120, "p": 100},
            {"m": -60, "p": 98},
            {"m": 0, "p": "NaN"},
        ]}, "nonfinite snapshot"),
    ],
)
def test_missing_or_conflicting_window_evidence_does_not_claim_pace(
    overrides, invalid_reason
):
    market = {
        "analysed_window_minutes": 180,
        "chg_window_percent": Decimal("-5"),
        "chg30m_percent": Decimal("-1"),
        "chg1h_percent": Decimal("-3"),
        "snapshots": [
            {"m": -120, "p": Decimal("100")},
            {"m": -60, "p": Decimal("98")},
            {"m": 0, "p": Decimal("95")},
        ],
    }
    market.update(overrides)
    situation, watch = event_alert_presentation_fallback(market, [])
    assert "picked up pace" not in situation, invalid_reason
    assert "per minute" not in situation, invalid_reason
    assert "next observed interval" not in watch, invalid_reason


def test_actual_snapshot_duration_prevents_false_pace_claim():
    market = {
        "analysed_window_minutes": 180,
        "chg_window_percent": Decimal("5"),
        "chg30m_percent": Decimal("0.4"),
        "chg1h_percent": Decimal("2.8"),
        "snapshots": [
            {"m": -90, "p": Decimal("100")},
            {"m": -60, "p": Decimal("102")},
            {"m": 0, "p": Decimal("105")},
        ],
    }
    # Latest absolute change is bigger, but it takes twice as long.
    situation, watch = event_alert_presentation_fallback(market, [])
    assert "slower per minute" in situation
    assert "next observed interval" in watch



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
        "The analysed-window rise is smaller in magnitude than the broader 24-hour "
        "trend's net rise."
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
                "snapshots": [
                    {"m": -120, "p": Decimal("100")},
                    {"m": -60, "p": Decimal("98")},
                    {"m": 0, "p": Decimal("95")},
                ],
            }
        },
        related_news=[],
    )["plain_text"]
    assert "BTC Event Alert" in text
    assert "BTC Event Alert: -3.00%" in text
    assert "Price (now): $65,000" in text or "Price (now): $65000" in text
    assert "3h market move:" in text
    assert "Situation:\nMarket movement is noteworthy." in text
    assert "Possible action:\nReview risk plan if the move continues." in text
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
        "The supplied snapshots show positive short-term movement against the "
        "broader 24-hour direction.",
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


def test_generic_snapshot_consistency_requires_all_steps_to_agree():
    market = {
        "chg_window_percent": Decimal("-10"),
        "snapshots": [
            {"m": -180, "p": Decimal("100")},
            {"m": -120, "p": Decimal("110")},
            {"m": -60, "p": Decimal("100")},
            {"m": 0, "p": Decimal("90")},
        ],
    }
    situation = compact_event_alert_situation(
        "The supplied snapshots show consistent movement in the same direction.",
        significance_reason=None,
        market_data=market,
        related_news=[],
    )
    fallback, _ = event_alert_presentation_fallback(market, [])
    assert situation == fallback
    assert "consistent movement" not in situation


@pytest.mark.parametrize(
    "prices",
    [
        ("100", "105", "115.7625"),
        ("100", "95", "85.7375"),
    ],
)
def test_equal_compounded_per_minute_rate_does_not_claim_pace_change(prices):
    market = {
        "analysed_window_minutes": 180,
        "chg_window_percent": Decimal("4") if Decimal(prices[2]) > 100 else Decimal("-4"),
        "chg30m_percent": Decimal("1") if Decimal(prices[2]) > 100 else Decimal("-1"),
        "chg1h_percent": Decimal("2") if Decimal(prices[2]) > 100 else Decimal("-2"),
        "snapshots": [
            {"m": -90, "p": Decimal(prices[0])},
            {"m": -60, "p": Decimal(prices[1])},
            {"m": 0, "p": Decimal(prices[2])},
        ],
    }
    # 30m factor 1.05 (or 0.95), 60m factor its exact square.
    situation, watch = event_alert_presentation_fallback(market, [])
    assert "picked up pace" not in situation
    assert "slower per minute" not in situation
    assert "next observed interval" not in watch


def test_ccw349_persistent_snapshot_path_must_agree_with_window_direction():
    market = {
        "chg_window_percent": Decimal("-3"),
        "chg24h_percent": Decimal("-4"),
        "snapshots": [
            {"m": -120, "p": Decimal("100")},
            {"m": -60, "p": Decimal("102")},
            {"m": 0, "p": Decimal("104")},
        ],
    }
    situation, _ = event_alert_presentation_fallback(market, [])
    assert "persistent" not in situation.lower()
    assert "24-hour" in situation
    llm_text = compact_event_alert_situation(
        "The supplied snapshots show persistent short-term weakness "
        "aligned with the broader 24-hour direction.",
        significance_reason=None, market_data=market, related_news=[],
    )
    assert "persistent" not in llm_text.lower()


def test_ccw349_aligned_latest_counterstep_must_not_claim_fading():
    market = {
        "chg_window_percent": Decimal("-2"),
        "chg24h_percent": Decimal("-4"),
        "snapshots": [
            {"m": -120, "p": Decimal("100")},
            {"m": -60, "p": Decimal("105")},
            {"m": 0, "p": Decimal("101")},
        ],
    }
    situation, action = event_alert_presentation_fallback(market, [])
    assert "reverses part of the earlier path" in situation
    assert "fading" not in situation
    assert "latest decline aligns with the analysed-window direction" in situation
    assert "extends the decline" in action


def test_ccw20_counterstep_fallback_names_direction_and_next_observation():
    market = {
        "chg_window_percent": Decimal("1"),
        "chg24h_percent": Decimal("2"),
        "snapshots": [
            {"m": -120, "p": Decimal("100")},
            {"m": -60, "p": Decimal("104")},
            {"m": 0, "p": Decimal("101")},
        ],
    }
    situation, action = event_alert_presentation_fallback(market, [])
    assert "latest decline runs against the net analysed-window rise" in situation
    assert "further reversal toward the decline" in action
    assert "analysed-window rise" in action
    assert "%" not in situation and "$" not in situation


def test_ccw20_action_rejects_unsupported_future_divergence_or_convergence():
    from bot.alerting.event_text import compact_event_alert_possible_action

    safe = (
        "Watch the next observed interval for further reversal toward the decline "
        "or a return to the analysed-window rise."
    )
    invalid = [
        "If the next observed step extends this counter-move, it may further "
        "diverge from the 24h downward direction.",
        "If the next step extends this counter-move, it may further diverge "
        "from the 24h downtrend.",
        "If the next interval continues the decline, it may further converge "
        "with the 24-hour trend.",
    ]
    for action in invalid:
        assert compact_event_alert_possible_action(action, fallback=safe) == safe

    # A conditional *question* presenting two possibilities is not a prediction.
    valid = (
        "Watch whether upcoming snapshots begin aligning with the broader "
        "24-hour direction or continue diverging."
    )
    assert compact_event_alert_possible_action(valid, fallback=safe) == valid


def test_ccw20_frozen_eth_and_sol_errors_are_removed_at_final_assembly():
    from bot import alerts
    cases = [
        ("ETH", "If the next observed step extends this counter-move, it may further "
         "diverge from the 24h downward direction."),
        ("SOL", "If the next step extends this counter-move, it may further diverge "
         "from the 24h downtrend."),
    ]
    for _symbol, incorrect_action in cases:
        # Unsupported cross-period prediction now fails schema checking,
        # rather than being rewritten into another statement by Python.
        with pytest.raises(alerts.EventAnalysisValidationError,
                           match="unsupported action market claim"):
            alerts._validate_event_alert_render_causality(
                {"message_body": "The latest observation reversed the prior step.",
                 "possible_action": incorrect_action}
            )

def test_ccw20_verified_eth_levels_and_useful_conditional_action():
    import json

    from bot import alerts
    from bot.alerting.event_analysis import EventAnalysisDecision
    from bot.alerting.event_text import observed_event_alert_price_band
    from bot.services.ai_agent_groq import build_event_alert_render_prompt

    market = {
        "price": 2474.518857885452,
        "chg_window_percent": 0.26286988218543744,
        "chg24h_percent": -3.7848709953819224,
        "analysed_window_minutes": 180,
        "snapshots": [
            {"m": -210, "p": 2468.031147316202},
            {"m": -180, "p": 2472.899094100193},
            {"m": -120, "p": 2477.822953902561},
            {"m": -90, "p": 2471.8461459408736},
            {"m": -30, "p": 2477.5362414138694},
            {"m": 0, "p": 2474.518857885452},
        ],
    }
    band = observed_event_alert_price_band(market)
    assert band == {
        "low": "$2,472", "high": "$2,478",
        "observations": 4, "high_visits": 2,
    }
    prompt = build_event_alert_render_prompt({"symbol": "ETH", "market": market})
    input_json = json.loads(prompt.split("Input JSON:\n", 1)[1])
    assert input_json["evidence"]["observed_price_band"] == band

    correct_action = (
        "If price holds above the observed $2,478 high, it would strengthen the "
        "short-term recovery attempt; if it falls below $2,472, the rebound "
        "would look weaker."
    )
    decision = EventAnalysisDecision(
        symbol="ETH", should_alert=True, event_key=None, title=None,
        message_body="The short-term rebound opposes the broader 24-hour decline. "
        "Two recent snapshots approached the same high, but the latest move "
        "pulled back; the recovery remains unproven.",
        related_news_ids=[], possible_action=correct_action,
        urgency="normal", confidence="high", reason_for_no_alert=None,
    )
    assembled = alerts._build_event_alert_payload(
        decision=decision, input_payload={"market": market}, related_news=[]
    )["plain_text"]
    assert decision.message_body in assembled
    assert "Possible action:\n" + correct_action in assembled
    assert "$2,478" in assembled and "$2,472" in assembled
    assert "buy now" not in assembled.lower()

    wrong_decision = EventAnalysisDecision(
        symbol="ETH", should_alert=True, event_key=None, title=None,
        message_body=decision.message_body, related_news_ids=[],
        possible_action=correct_action.replace("$2,478", "$2,999"),
        urgency="normal", confidence="high", reason_for_no_alert=None,
    )
    with pytest.raises(alerts.EventAnalysisValidationError,
                       match="unsupported observed USD price"):
        alerts._validate_event_alert_render_prices(
            {"message_body": wrong_decision.message_body,
             "possible_action": wrong_decision.possible_action},
            market,
        )

    false_relation_decision = EventAnalysisDecision(
        symbol="ETH", should_alert=True, event_key=None, title=None,
        message_body=decision.message_body, related_news_ids=[],
        possible_action=(
            "If price holds above $2,478, it would align the rebound with the "
            "24-hour decline."
        ),
        urgency="normal", confidence="high", reason_for_no_alert=None,
    )
    with pytest.raises(alerts.EventAnalysisValidationError,
                       match="unsupported action market claim"):
        alerts._validate_event_alert_render_causality(
            {"message_body": decision.message_body,
             "possible_action": false_relation_decision.possible_action},
            market_data=market,
        )


def test_ccw20_sparse_or_stale_market_input_cannot_produce_price_levels():
    from bot.alerting.event_text import observed_event_alert_price_band

    observations = [
        {"m": -120, "p": 100},
        {"m": -90, "p": 102},
        {"m": -30, "p": 104},
        {"m": 0, "p": 101},
    ]
    assert observed_event_alert_price_band({"price": 101, "snapshots": observations})
    assert observed_event_alert_price_band({"price": 120, "snapshots": observations}) == {}
    assert observed_event_alert_price_band({"price": 101, "snapshots": observations[:3]}) == {}
    assert observed_event_alert_price_band({
        "price": 101, "snapshots": [
            {"m": -220, "p": 100}, *observations[1:]
        ]
    }) == {}


def test_release_rejects_unproven_repeated_high_claim():
    from bot.alerting.event_text import (
        compact_event_alert_situation,
        observed_event_alert_price_band,
    )

    market = {
        "price": 10000,
        "chg_window_percent": -9.09,
        "chg24h_percent": -4,
        "analysed_window_minutes": 90,
        "snapshots": [
            {"m": -90, "p": 11000},
            {"m": -60, "p": 10700},
            {"m": -30, "p": 10400},
            {"m": 0, "p": 10000},
        ],
    }
    assert observed_event_alert_price_band(market)["high_visits"] == 1
    false_claim = (
        "The observed high was approached twice, leaving the recent "
        "range unbroken."
    )
    guarded = compact_event_alert_situation(
        false_claim, significance_reason=None, market_data=market,
        related_news=[],
    )
    assert guarded != false_claim
    assert "twice" not in guarded.lower()


def test_release_conditional_levels_cannot_mask_false_observed_direction():
    from bot import alerts
    from bot.alerting.event_analysis import EventAnalysisDecision

    market = {
        "price": 10000,
        "chg_window_percent": -9.09,
        "chg24h_percent": -4,
        "analysed_window_minutes": 90,
        "snapshots": [
            {"m": -90, "p": 11000},
            {"m": -60, "p": 10700},
            {"m": -30, "p": 10400},
            {"m": 0, "p": 10000},
        ],
    }
    invalid = (
        "The current window shows a rally; watch whether price holds "
        "above the observed $11,000 high or falls below $10,000."
    )
    decision = EventAnalysisDecision(
        symbol="BTC", should_alert=True, event_key=None, title=None,
        message_body="The recent price snapshots continue lower.",
        related_news_ids=[], possible_action=invalid,
        urgency="normal", confidence="high", reason_for_no_alert=None,
    )
    # Source guard rejects the false observed direction, rather than rewriting
    # the validated Stage-2 action after provider acceptance.
    assert alerts._guard_event_text_against_market_data(
        invalid, field_name="possible_action", symbol="BTC", market_data=market
    ) != invalid

    # Legitimate conditional upside/downside scenarios must remain accepted.
    valid = (
        "If price holds above the observed $11,000 high, the recent range "
        "could shift upward; if it falls below $10,000, the decline "
        "would extend."
    )
    accepted = alerts._build_event_alert_payload(
        decision=EventAnalysisDecision(
            symbol="BTC", should_alert=True, event_key=None, title=None,
            message_body=decision.message_body,
            related_news_ids=[], possible_action=valid,
            urgency="normal", confidence="high", reason_for_no_alert=None,
        ),
        input_payload={"market": market}, related_news=[],
    )["plain_text"]
    assert "Possible action:\n" + valid in accepted
