"""Regressions from 2026-10-13 delivered Event Alerts.

These assertions inspect the Telegram-ready payload, not just provider JSON.
"""
from decimal import Decimal

import pytest

from bot import alerts
from bot.alerting.event_analysis import EventAnalysisDecision
from bot.alerting.event_text import final_event_alert_quality_flags
from bot.alerting.news_context import classify_news_relevance


def _decision(situation: str, action: str, symbol: str = "BTC"):
    return EventAnalysisDecision(
        symbol=symbol, should_alert=True, event_key=f"{symbol.lower()}_price_downtrend",
        title="ignored", message_body=situation, related_news_ids=[],
        possible_action=action, urgency="normal", confidence="high",
        reason_for_no_alert=None,
    )


def _market(window, day):
    return {
        "price": Decimal("100"), "chg_window_percent": Decimal(window),
        "chg24h_percent": Decimal(day), "analysed_window_minutes": 180,
        "snapshots": [{"m": -180, "p": Decimal("102")},
                      {"m": -90, "p": Decimal("101")},
                      {"m": 0, "p": Decimal("100")}],
    }


def _render(situation, action, market=None, symbol="BTC", last_msg=None):
    return alerts._build_event_alert_payload(
        decision=_decision(situation, action, symbol),
        input_payload={"market": market or _market("-2", "3"),
                       "timestamp_utc": "2026-10-13T16:00:00+00:00",
                       "last_msg": last_msg or {}},
        related_news=[],
    )["plain_text"]


def test_grounded_llm_explanation_is_not_replaced_by_vocabulary_filter():
    situation = ("Although the shorter decline contrasts with the 24-hour rise, "
                 "the divergence leaves two different directions to compare.")
    action = ("Check whether the next 1h observation maintains the divergence "
              "or returns toward the 24-hour direction.")
    delivered = _render(situation, action)
    assert situation in delivered
    assert action in delivered
    assert not final_event_alert_quality_flags(delivered)["generic_action"]


def test_distinct_grounded_event_explanations_survive_final_render():
    sol = _render(
        "The short-term decline contrasts with the 24-hour rise, creating divergence.",
        "Check whether the next 1h reading extends the decline or turns toward the daily rise.",
        symbol="SOL",
    )
    eth = _render(
        "The supplied snapshots show a persistent decline despite a rising 24-hour direction.",
        "Check whether the next snapshot extends the decline or breaks the sequence.",
        symbol="ETH",
    )
    sol_situation = sol.split("Situation:\n")[1].split("\n\n")[0]
    eth_situation = eth.split("Situation:\n")[1].split("\n\n")[0]
    assert sol_situation != eth_situation


@pytest.mark.parametrize("situation", [
    "BlackRock announced an ETF launch; the short-term decline diverges from the daily rise.",
    "Liquidations drove the move while the short-term decline diverges from the daily rise.",
    "The market fell 15% due to an exchange hack.",
])
def test_unsupported_claims_do_not_reach_delivered_text(situation):
    delivered = _render(
        situation,
        "Check whether the next 1h observation extends the divergence or reverses.",
    )
    assert situation not in delivered
    assert "BlackRock" not in delivered
    assert "Liquidations" not in delivered
    assert "exchange hack" not in delivered


def test_generic_action_quality_uses_final_delivered_message():
    delivered = _render(
        "The supplied snapshot direction is the only available trajectory.",
        "Review the risk plan.",
        market={"price": Decimal("100"), "chg_window_percent": Decimal("-2"),
                "analysed_window_minutes": 180},
    )
    assert final_event_alert_quality_flags(delivered)["generic_action"] is True
    assert "Review the risk plan." not in delivered
    assert "Possible action:" in delivered


def test_since_previous_reference_identifies_source_and_time():
    delivered = _render(
        "The short-term decline diverges from the 24-hour rise.",
        "Check whether the next 1h reading extends the decline or turns.",
        last_msg={"time": "2026-10-13T11:00:00+00:00",
                  "type": "market_heartbeat", "price": Decimal("103")},
        market={**_market("-2", "3"), "chg_since_msg_percent": Decimal("-2.912621")},
    )
    assert "Since previous BTC Market Heartbeat" in delivered
    assert "13 Oct 11:00 UTC" in delivered
    assert "5h ago" in delivered
    assert "3h market move:" in delivered


@pytest.mark.parametrize("headline", [
    "Exchange CEO buys a yacht",
    "Federal Reserve official meets local bankers",
    "Bitcoin mining firm reports quarterly revenue",
])
def test_unrelated_headlines_not_promoted_to_gram_market_news(headline):
    assert classify_news_relevance("GRAM", {"title": headline}) == "irrelevant"


def test_clearly_broad_crypto_market_news_is_eligible_context():
    assert classify_news_relevance(
        "GRAM", {"title": "Broad crypto market selloff follows major exchange outage"}
    ) == "market_wide"



def test_render_model_receives_grounded_relationships_not_price_numbers():
    from bot.services.ai_agent_groq import _event_alert_render_prompt_payload
    context = _event_alert_render_prompt_payload({
        "symbol": "SOL", "market": _market("-2", "3"),
        "significance_decision": {"confidence": "high", "reason_code": "reversal"},
    })
    assert context["evidence"]["window_vs_24h"] == "opposite_direction"
    assert context["evidence"]["snapshot_path"] == "consecutive_steps_same_direction"
    assert context["market_directions"] == {"window": "down", "24h": "up"}
    assert "100" not in str(context["evidence"])


@pytest.mark.parametrize(("symbol", "window", "percentile", "recent"), [
    ("BTC", "-0.27", 49, 0),
    ("BTC", "-0.29", 51, 2),
    ("GRAM", "0.35", 48, 5),
    ("ETH", "-5.7", 99, 0),
    ("SOL", "6.2", 98, 0),
])
def test_significance_model_receives_routine_and_material_context(
    symbol, window, percentile, recent
):
    # These are prompt-contract fixtures, not deterministic alert decisions.
    # The model must still judge materiality/novelty at runtime.
    from bot.services.ai_agent_groq import _event_significance_prompt_payload
    context = _event_significance_prompt_payload({
        "symbol": symbol,
        "market": {**_market(window, "3"),
                   "relative_window_percentile_30d": percentile},
        "recent_event_counts": {"h6": recent, "h24": recent},
        "previous_event_alert": {"age_minutes": 55,
                                 "semantic_family": "price_downtrend",
                                 "analysed_window_move": window},
    })
    assert context["m"]["cw"] == Decimal(window)
    assert context["m"]["pw"] == percentile
    assert context["cnt"]["h6"] == recent
    assert context["prev"]["min"] == 55


@pytest.mark.parametrize("action", [
    "Watch the next short-term snapshots for confirmation or reversal.",
    "Watch whether the next short-term snapshots continue or reverse.",
    "Monitor market developments.",
])
def test_generic_possible_action_detector_looks_at_delivered_copy(action):
    body = (
        "BTC Event Alert\\n\\nSituation:\\nMarket evidence remains limited."
        f"\\n\\nPossible action:\\n{action}\\n\\nNot financial advice."
    )
    assert final_event_alert_quality_flags(body)["generic_action"] is True


def test_selected_unrelated_article_omitted_from_delivered_alert():
    decision = _decision(
        "The short-term decline diverges from the broader 24-hour rise.",
        "Check whether the next 1h observation extends the divergence or turns.",
    )
    from dataclasses import replace
    decision = replace(decision, related_news_ids=["n1"])
    message = alerts._build_event_alert_payload(
        decision=decision,
        input_payload={"market": _market("-2", "3")},
        related_news=[{
            "news_id": "n1", "title": "Exchange CEO buys a yacht",
            "source": "Wire", "url": "https://example.com/story",
        }],
    )["plain_text"]
    assert "Related context:" not in message
    assert "yacht" not in message.lower()
