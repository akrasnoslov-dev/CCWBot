"""Owner-approved Event Alert final-copy regressions (no provider/network calls)."""

from bot import alerts
from bot.alerting.event_analysis import EventAnalysisDecision
from bot.alerting.event_text import (
    compact_event_alert_possible_action,
    compact_event_alert_situation,
)
from bot.alerting.news_context import classify_news_relevance
from bot.services.llm import config as llm_config


def _market():
    return {
        "price": 100.0,
        "chg_window_percent": -2.0,
        "chg24h_percent": -3.0,
        "analysed_window_minutes": 180,
        "snapshots": [
            {"m": -90, "p": 99.0},
            {"m": -60, "p": 101.0},
            {"m": -30, "p": 104.0},
            {"m": 0, "p": 100.0},
        ],
    }


def _decision(action):
    return EventAnalysisDecision(
        symbol="BTC", should_alert=True, event_key=None, title=None,
        message_body=(
            "After two upward steps, the latest snapshot declined and left price "
            "at the recent observed low. The short-term decline aligns with the "
            "broader 24-hour direction."
        ),
        related_news_ids=[], possible_action=action,
        urgency="normal", confidence="high", reason_for_no_alert=None,
    )


def test_realistic_llm_two_scenario_action_with_would_is_preserved():
    action = (
        "A sustained move above the observed $104.00 high would strengthen the "
        "short-term recovery attempt. A move below $100.00 would weaken the "
        "rebound case after the latest decline."
    )
    assert compact_event_alert_possible_action(
        action, fallback="generic", market_data=_market()
    ) == action


def test_unproven_support_resistance_disclaimer_does_not_erase_scenarios():
    action = (
        "A sustained move above the observed $104.00 high would strengthen the "
        "rebound case. A move below $100.00 would undermine it. "
        "These are not established support or resistance levels."
    )
    assert compact_event_alert_possible_action(
        action, fallback="generic", market_data=_market()
    ) == action


def test_action_with_asserted_support_or_unobserved_price_still_fails_closed():
    unsupported = (
        "If price rises above the confirmed $104.00 support, it would guarantee "
        "a profitable trade; or a decline below $100.00 would suggest weakness."
    )
    wrong_price = (
        "If price rises above the observed $999.00 high it would strengthen "
        "the rebound; or if it falls below $100.00 it would weaken the rebound."
    )
    for action in (unsupported, wrong_price):
        assert compact_event_alert_possible_action(
            action, fallback="generic", market_data=_market()
        ) == "generic"


def test_temporal_after_between_observed_steps_is_not_news_causation():
    situation = _decision("Watch the next observed interval.").message_body
    assert compact_event_alert_situation(
        situation, significance_reason=None, market_data=_market(),
    ) == situation


def test_metadata_only_ethereum_tag_cannot_turn_bitcoin_news_into_eth_news():
    wrongly_tagged = {
        "title": "Bitcoin reaches a new range after US economic data",
        "summary": "BTC price and the Bitcoin network were discussed.",
        "primary_symbol": "eth",
        "related_symbols": ["eth"],
    }
    assert classify_news_relevance("eth", wrongly_tagged) == "irrelevant"
    assert classify_news_relevance("btc", wrongly_tagged) == "direct"
    assert classify_news_relevance(
        "eth", {"title": "Ethereum staking update", "summary": ""}
    ) == "direct"


def test_related_context_is_present_in_all_formats_when_no_news_are_selected():
    action = (
        "A sustained move above the observed $104.00 high would strengthen the "
        "rebound. A move below $100.00 would undermine that recovery attempt."
    )
    payload = alerts._build_event_alert_payload(
        decision=_decision(action),
        input_payload={"market": _market()},
        related_news=[],
    )
    for fmt in ("plain_text", "html_text", "rich_html"):
        assert "Related context" in payload[fmt]
        assert "No relevant news linked to this market move." in payload[fmt]
        assert payload[fmt].index("Related context") < payload[fmt].index("Possible action")


def test_explicit_event_provider_overrides_select_only_openai_luna(monkeypatch):
    monkeypatch.setenv("LLM_EVENT_PROVIDERS", "openai")
    monkeypatch.setenv("LLM_EVENT_RENDER_PROVIDERS", "openai")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-6-luna")
    assert llm_config.provider_attempts("event_analysis") == [
        ("openai", "gpt-6-luna")
    ]
    assert llm_config.provider_attempts("event_alert_render") == [
        ("openai", "gpt-6-luna")
    ]
