from datetime import datetime, timedelta, timezone

import pytest

from bot import alerts
from bot.alerting.event_analysis import EventAnalysisDecision
from bot.alerting.event_significance import evaluate_event_significance
from bot.alerting.event_text import (
    compact_elapsed_since,
    ensure_useful_situation,
    soften_possible_action,
)


def payload(*, window, day=0.0, since=0.0, prices=None):
    return {
        "market": {
            "chg_window": window,
            "chg24h": day,
            "chg_since_msg": since,
            "snapshots": [{"p": price} for price in (prices or [])],
        }
    }


@pytest.mark.parametrize("movement", [0.01, -0.05, 0.1, -0.2, 0.49])
def test_isolated_small_moves_are_rejected(movement):
    result = evaluate_event_significance(payload(window=movement), urgency="normal")

    assert result.is_significant is False
    assert result.reason == "insufficient_market_significance"


def test_news_and_unsupported_urgency_do_not_rescue_tiny_move():
    result = evaluate_event_significance(
        payload(window=0.05, day=0.2),
        urgency="high",
        related_news=[{"relevance_label": "direct_symbol", "material": True}],
    )

    assert result.is_significant is False
    assert result.reason == "unsupported_urgency"


def test_small_steps_accumulating_into_persistent_trend_can_alert():
    result = evaluate_event_significance(
        payload(window=2.1, prices=[100.0, 100.4, 100.9, 101.5, 102.1]),
        urgency="normal",
    )

    assert result.is_significant is True
    assert result.reason == "persistent_cumulative_trend"


def test_material_acceleration_can_alert():
    result = evaluate_event_significance(
        payload(window=0.75, prices=[100.0, 100.1, 100.2, 100.75]),
        urgency="normal",
    )

    assert result.is_significant is True
    assert result.reason == "material_acceleration"


def test_modest_move_with_aligned_broader_context_can_alert():
    result = evaluate_event_significance(
        payload(window=-0.4, day=-4.2, prices=[100.0, 99.8, 99.6]),
        urgency="normal",
    )

    assert result.is_significant is True
    assert result.reason == "broader_24h_trend_continuation"


def test_relevant_news_only_supports_meaningful_market_reaction():
    generic = [{"relevance_label": "direct_symbol", "material": False}]
    material = [{"relevance_label": "direct_symbol", "material": True}]
    weak = evaluate_event_significance(
        payload(window=0.2, day=4.0), urgency="normal", related_news=material
    )
    supported = evaluate_event_significance(
        payload(window=0.55, day=1.5), urgency="normal", related_news=material
    )
    generic_result = evaluate_event_significance(
        payload(window=0.55, day=1.5), urgency="normal", related_news=generic
    )

    assert weak.is_significant is False
    assert generic_result.is_significant is False
    assert supported.is_significant is True
    assert supported.reason == "relevant_context_supports_market_move"


@pytest.mark.parametrize("symbol", ["BTC", "ETH", "GRAM", "SOL"])
def test_significance_policy_has_no_btc_only_branch(symbol):
    input_payload = payload(
        window=1.2,
        prices=[0.005, 0.00501, 0.005025, 0.00504, 0.00506],
    )
    input_payload["symbol"] = symbol

    assert evaluate_event_significance(input_payload, urgency="normal").is_significant


def test_low_priced_gram_trajectory_preserves_acceleration_evidence():
    input_payload = payload(
        window=0.8,
        prices=[0.005, 0.005002, 0.005004, 0.00504],
    )
    input_payload["symbol"] = "GRAM"

    result = evaluate_event_significance(input_payload, urgency="normal")

    assert result.is_significant is True
    assert result.reason == "material_acceleration"


def test_compact_elapsed_formats_required_boundaries():
    now = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)

    assert compact_elapsed_since(now - timedelta(minutes=12), now) == "12m ago"
    assert compact_elapsed_since(now - timedelta(hours=1, minutes=25), now) == "1h 25m ago"
    assert compact_elapsed_since(now - timedelta(days=1, hours=3), now) == "1d 3h ago"


def test_message_quality_guards_preserve_conditional_advice_and_replace_hard_commands():
    assert soften_possible_action(
        "Consider reducing exposure if momentum weakens.", urgency="normal"
    ) == "Consider reducing exposure if momentum weakens."
    assert soften_possible_action("Buy now.", urgency="high").startswith(
        "Consider a cautious entry"
    )
    assert soften_possible_action("You should sell now.", urgency="normal").startswith(
        "Consider reducing exposure"
    )
    assert soften_possible_action("Immediately close the position.", urgency="normal").startswith(
        "Consider reducing or closing"
    )
    assert soften_possible_action("You need to sell now.", urgency="normal").startswith(
        "Consider reducing exposure"
    )
    assert soften_possible_action("Please buy now.", urgency="normal").startswith(
        "Consider a cautious entry"
    )
    assert soften_possible_action("Go long now.", urgency="normal").startswith(
        "Consider a cautious entry"
    )
    assert soften_possible_action("Take profit immediately.", urgency="normal").startswith(
        "Consider reducing exposure"
    )
    assert soften_possible_action("Selling pressure has eased.", urgency="normal") == (
        "Selling pressure has eased."
    )
    assert ensure_useful_situation(
        "BTC fell 1.2% after a confirmed protocol exploit.",
        significance_reason="material_analysed_window_move",
    ) == "BTC fell 1.2% after a confirmed protocol exploit."
    assert "meaningful market change" in ensure_useful_situation(
        "ETH moved lower by -0.05%.", significance_reason="material_analysed_window_move"
    )


def test_event_message_elapsed_uses_payload_reference_record():
    now = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)
    decision = EventAnalysisDecision(
        symbol="ETH",
        should_alert=True,
        event_key="eth_price_downtrend",
        title="ETH trend extends",
        message_body="The decline extends a persistent analysed-window trend.",
        related_news_ids=[],
        possible_action="Consider reducing exposure if momentum keeps weakening.",
        urgency="normal",
        confidence="medium",
        reason_for_no_alert=None,
    )

    rendered = alerts._build_event_alert_payload(
        decision=decision,
        input_payload={
            "timestamp_utc": now.isoformat(),
            "last_msg": {
                "time": (now - timedelta(hours=1, minutes=25)).isoformat(),
                "price": 100.0,
            },
            "market": {
                "price": 98.0,
                "chg_since_msg": -2.0,
                "chg_window": -1.2,
                "analysed_window_minutes": 180,
            },
            "backend_significance": {"reason": "material_analysed_window_move"},
        },
        related_news=[],
    )["plain_text"]

    assert "Since last alert/message (1h 25m ago): -2.00%" in rendered
    assert "Possible action:\nConsider reducing exposure if" in rendered
    assert rendered.count("Not financial advice.") == 1
