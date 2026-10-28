"""Evidence-backed Stage-2 Render guards and final-copy regression tests.

All cases use synthetic snapshots and no provider/Telegram/DB calls.
"""

import json
from decimal import Decimal

import bot.alerts as alerts
from bot.alerting.event_analysis import EventAnalysisDecision
from bot.alerting.event_text import (
    compact_event_alert_situation,
    verified_event_alert_render_context,
)
from bot.services.ai_agent_groq import build_event_alert_render_prompt


def market_down():
    return {
        "price": Decimal("100.00"),
        "snapshots": [
            {"m": -90, "p": Decimal("102.00")},
            {"m": -60, "p": Decimal("101.00")},
            {"m": -30, "p": Decimal("102.00")},
            {"m": 0, "p": Decimal("100.00")},
        ],
        "analysed_window_minutes": 90,
        "chg_window_percent": Decimal("-1.96"),
        "chg24h_percent": Decimal("2.0"),
    }


def decision_for(action):
    return EventAnalysisDecision(
        symbol="BTC",
        should_alert=True,
        event_key="btc_price_move",
        title="ignored",
        message_body=(
            "The last observed step reversed the brief recovery and ended at "
            "the lowest price in the supplied recent range."
        ),
        related_news_ids=[],
        possible_action=action,
        urgency="normal",
        confidence="high",
        reason_for_no_alert=None,
    )


def final_action(market, action):
    message = alerts._build_event_alert_payload(
        decision=decision_for(action),
        input_payload={"market": market},
        related_news=[],
    )["plain_text"]
    return message.split("Possible action:\n", 1)[1].split(
        "\n\nNot financial advice.", 1
    )[0]


def test_when_two_sided_conditions_do_not_inherit_the_observed_down_direction():
    action = (
        "When price moves above the observed $102.00 high, the rebound case "
        "would strengthen; when it falls below $100.00, that case would weaken."
    )
    assert final_action(market_down(), action) == action


def test_when_without_dollar_levels_remains_a_future_conditional():
    action = (
        "When the next observed interval rises, it could recover part of the "
        "decline; when it falls again, the decline would extend."
    )
    assert final_action(market_down(), action) == action


def test_conditionals_do_not_hide_false_observed_direction():
    action = (
        "The current analysed window shows a rally; when price falls below "
        "$100.00, the rebound would weaken."
    )
    assert final_action(market_down(), action) != action


def test_unverified_dollar_level_is_still_rejected():
    action = (
        "When price moves above $999.00, the rebound would strengthen; "
        "when it falls below $100.00, the case would weaken."
    )
    assert final_action(market_down(), action) != action


def test_render_evidence_exposes_grounded_recent_path_not_only_direction():
    market = market_down()
    evidence = verified_event_alert_render_context(market)
    assert evidence["recent_price_path"] == {
        "step_directions": ["down", "up", "down"],
        "step_durations_minutes": [30, 30, 30],
        "current_range_position": "at_low",
    }
    assert evidence["observed_price_band"]["high"] == "$102.00"
    prompt = build_event_alert_render_prompt(
        {"symbol": "BTC", "market": market, "news": []}
    )
    compact = json.loads(prompt.split("Input JSON:\n", 1)[1])
    assert compact["evidence"]["recent_price_path"] == evidence["recent_price_path"]
    assert "step_directions" in prompt


def test_render_does_not_invent_a_path_from_missing_or_gapped_snapshots():
    market = market_down()
    market["snapshots"][1]["m"] = -250
    assert "recent_price_path" not in verified_event_alert_render_context(market)
    market["snapshots"] = [{"m": 0, "p": Decimal("100")}]
    assert "recent_price_path" not in verified_event_alert_render_context(market)


def test_verified_pace_description_is_not_discarded_as_unsubstantiated():
    market = {
        "price": Decimal("104"),
        "snapshots": [
            {"m": -120, "p": Decimal("100")},
            {"m": -60, "p": Decimal("101")},
            {"m": 0, "p": Decimal("104")},
        ],
        "analysed_window_minutes": 120,
        "chg_window_percent": Decimal("4"),
        "chg24h_percent": Decimal("5"),
        "chg30m_percent": Decimal("1"),
        "chg1h_percent": Decimal("3"),
    }
    situation = (
        "The latest observed snapshot interval accelerated while the "
        "short-term rise aligned with the 24-hour direction."
    )
    assert compact_event_alert_situation(
        situation, significance_reason=None, market_data=market
    ) == situation


def test_same_conditional_copy_is_not_forced_on_distinct_paths():
    down = market_down()
    action_down = (
        "When price moves above the observed $102.00 high, the rebound case "
        "would strengthen; when it falls below $100.00, that case would weaken."
    )
    up = {
        "price": Decimal("103"),
        "snapshots": [
            {"m": -90, "p": Decimal("100")},
            {"m": -60, "p": Decimal("100.5")},
            {"m": -30, "p": Decimal("102")},
            {"m": 0, "p": Decimal("103")},
        ],
        "analysed_window_minutes": 90,
        "chg_window_percent": Decimal("3"),
        "chg24h_percent": Decimal("4"),
    }
    action_up = (
        "When price holds above the observed $103.00 high, the advance would "
        "extend; when it drops below $100.00, the recent advance would unwind."
    )
    assert final_action(down, action_down) == action_down
    assert final_action(up, action_up) == action_up
    assert final_action(down, action_down) != final_action(up, action_up)
