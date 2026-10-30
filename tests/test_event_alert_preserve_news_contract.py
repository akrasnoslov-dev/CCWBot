"""Preserve-first Event Alert and incident-aware news regression contracts.

Synthetic evidence only. No private production records.
"""
from datetime import datetime, timezone
from html import unescape
from types import SimpleNamespace

import pytest

from bot import alerts
from bot.alerting.event_analysis import (
    EventAnalysisDecision,
    EventAnalysisValidationError,
    validate_event_analysis_output,
)
from bot.alerting.news_context import classify_news_relevance, filter_news_for_symbol
from bot.news import _news_row_rank
from bot.services.news_intelligence_service import build_post_llm_dedup_group_id


def _market():
    return {
        "price": 100.0,
        "chg_window_percent": -2.0,
        "chg24h_percent": -3.0,
        "analysed_window_minutes": 180,
        "snapshots": [
            {"m": -90, "p": 104.0},
            {"m": -60, "p": 103.0},
            {"m": -30, "p": 101.0},
            {"m": 0, "p": 100.0},
        ],
    }


def _decision(situation, action):
    return EventAnalysisDecision(
        symbol="BTC", should_alert=True, event_key=None, title=None,
        message_body=situation, related_news_ids=[], possible_action=action,
        urgency="normal", confidence="high", reason_for_no_alert=None,
    )


def test_long_valid_render_sections_are_preserved_in_every_format():
    situation = (
        "BTC fell through successive verified observations, with each observed "
        "step lower than the previous one. This movement aligns with the wider "
        "24-hour decline, but the observations alone cannot establish whether "
        "the decline will continue. The latest observation is at the low of "
        "the supplied range and no rebound has yet been observed. "
    ) * 2
    action = (
        "If the next observation recovers above the earlier observed high, "
        "that would weaken the short-term decline case. If it stays below "
        "the latest observed low, the downward interpretation would remain "
        "intact. A risk-management response should depend on the holder's "
        "own time horizon rather than an assumed outcome. "
    ) * 2
    result = alerts._build_event_alert_payload(
        decision=_decision(situation, action),
        input_payload={"market": _market()}, related_news=[],
    )
    for key in ("plain_text", "html_text", "rich_html"):
        assert situation.strip() in unescape(result[key])
        assert action.strip() in unescape(result[key])
        assert "Not financial advice." in result[key]


def test_trading_vocabulary_is_not_replaced_by_backend():
    situation = "BTC declined in each supplied interval and aligns with the 24-hour down move."
    action = (
        "If the range breaks, a trader may reduce exposure, "
        "sell, or hold based on their risk plan."
    )
    result = alerts._build_event_alert_payload(
        decision=_decision(situation, action),
        input_payload={"market": _market()}, related_news=[],
    )
    assert action in result["plain_text"]


def test_no_generated_generic_situation_or_action():
    situation = "The latest observed price is the lowest in the supplied sequence."
    action = "A recovery above the previous high would weaken the downward interpretation."
    result = alerts._build_event_alert_payload(
        decision=_decision(situation, action),
        input_payload={"market": _market()}, related_news=[],
    )
    assert situation in result["plain_text"]
    assert action in result["plain_text"]
    assert "Watch for a sustained move above the observed" not in result["plain_text"]


@pytest.mark.parametrize("symbol", ["btc", "eth", "sol", "gram"])
def test_major_exchange_hack_can_be_market_wide_for_multiple_assets(symbol):
    incident = {
        "title": "Major Binance exchange hack drains $6 billion",
        "summary": (
            "Multi-billion-dollar breach rattles the broader crypto "
            "market and exchange liquidity."
        ),
        "category": "security", "impact_level": "critical", "impact_score": 90,
        "primary_symbol": None, "related_symbols": ["btc", "eth"],
    }
    assert classify_news_relevance(symbol, incident) in {"direct", "market_wide"}


def test_unrelated_security_and_regulatory_headlines_remain_irrelevant():
    for item in [
        {"title": "Local retail exchange updates parking rules", "summary": ""},
        {"title": "Canadian fraud trial goes to jury", "summary": "Digital asset investor case."},
        {"title": "Tech firm reports small database breach", "summary": ""},
    ]:
        assert classify_news_relevance("sol", item) == "irrelevant"
        assert classify_news_relevance("gram", item) == "irrelevant"


def test_critical_market_wide_outweighs_routine_direct_news():
    def row(title, impact, relevance, primary, related):
        return SimpleNamespace(
            title=title, impact_score=impact, relevance_score=relevance, id=1,
            primary_symbol=primary, related_symbols=related,
            published_at=datetime(2026, 10, 30, tzinfo=timezone.utc),
            category="security", impact_level="critical",
            llm_summary=title, raw_summary=title, source="News source",
            url="https://example.org/story", dedup_group_id="test:story",
            llm_status="success",
        )
    routine = row("Bitcoin chart analysis", 20, 80, "btc", ["btc"])
    critical = row(
        "Major Binance exchange hack drains $6 billion; crypto markets tumble",
        90, 95, None, [],
    )
    assert _news_row_rank(critical, "btc") > _news_row_rank(routine, "btc")


def test_high_impact_news_not_displaced_by_newer_routine_item():
    critical = {
        "title": "Binance hack drains $6 billion; crypto markets and exchange liquidity hit",
        "summary": "Record breach triggers crypto-wide withdrawal pressure.",
        "category": "security", "impact_level": "critical", "impact_score": 90,
        "published_at": "2026-10-29T21:12:45+00:00",
    }
    routine = {
        "title": "Bitcoin traders discuss a chart pattern",
        "summary": "Routine analysis", "impact_score": 20,
        "published_at": "2026-10-30T08:00:00+00:00",
    }
    selected = filter_news_for_symbol("btc", [routine, critical])
    assert selected[0]["title"] == critical["title"]


def test_render_rejects_unsupported_quoted_price_and_mixed_sections():
    with pytest.raises(EventAnalysisValidationError, match="unsupported observed USD price"):
        alerts._validate_event_alert_render_prices(
            {"message_body": "The observed price was $999.00", "possible_action": "Monitor"},
            _market(),
        )
    alerts._validate_event_alert_render_prices(
        {"message_body": "The observed high was $104.00", "possible_action": "Monitor"},
        _market(),
    )
    with pytest.raises(EventAnalysisValidationError, match="mixed render sections"):
        alerts._validate_event_alert_render_causality(
            {"message_body": "Situation: Price changed. Possible action: Watch levels."}
        )


def test_unknown_news_ids_are_not_silently_removed():
    normalized = alerts._event_alert_render_result_for_validation(
        {
            "message_body": "BTC declined within the observed sequence.",
            "related_news_ids": ["n999"],
            "possible_action": "Watch for a change in the next observation.",
        },
        input_payload={"market": _market()}, expected_symbol="btc",
        confidence="high", candidate_news_ids={"n1"},
    )
    assert normalized["related_news_ids"] == ["n999"]
    with pytest.raises(EventAnalysisValidationError):
        validate_event_analysis_output(
            normalized, expected_symbol="btc", candidate_news_ids={"n1"}
        )


def test_telegram_hard_limit_fails_instead_of_truncating():
    with pytest.raises(EventAnalysisValidationError, match="telegram_message_too_long"):
        alerts._build_event_alert_payload(
            decision=_decision("The observed price declined. " * 180, "Watch the range."),
            input_payload={"market": _market()}, related_news=[],
        )


def test_incident_followups_have_distinct_dedup_developments():
    initial = build_post_llm_dedup_group_id(
        "binance hack", "unrelated", title="Binance hack confirmed",
        primary_symbol=None, category="security",
    )
    recovery = build_post_llm_dedup_group_id(
        "binance hack", "unrelated", title="Binance hack recovery funding confirmed",
        primary_symbol=None, category="security",
    )
    repeat = build_post_llm_dedup_group_id(
        "binance hack", "unrelated", title="Binance hack confirmed",
        primary_symbol=None, category="security",
    )
    assert initial != recovery
    assert initial == repeat


def test_market_wide_news_survives_final_related_context_validation():
    incident = {
        "title": "Binance hack drains $6 billion from a major exchange",
        "summary": "The breach affects exchange liquidity across the crypto market.",
        "source": "Independent Crypto News",
        "url": "https://example.org/major-exchange-hack",
    }
    decision = EventAnalysisDecision(
        symbol="SOL", should_alert=True, event_key=None, title=None,
        message_body="The current observations show a lower short-term range.",
        related_news_ids=["n1"],
        possible_action="The next observation may clarify whether the move continues.",
        urgency="normal", confidence="high", reason_for_no_alert=None,
    )
    payload = alerts._build_event_alert_payload(
        decision=decision,
        input_payload={"market": _market()}, related_news=[incident],
    )
    for key in ("plain_text", "html_text", "rich_html"):
        assert "Binance hack drains" in payload[key]


def test_legacy_combined_database_message_does_not_leak_multiple_sections():
    mixed = (
        "Situation: BTC has a verified lower path. "
        "Possible action: Watch the observed range."
    )
    with pytest.raises(EventAnalysisValidationError, match="mixed render sections"):
        alerts._build_event_alert_payload(
            decision=_decision(mixed, "Observe the range."),
            input_payload={"market": _market()}, related_news=[],
        )
