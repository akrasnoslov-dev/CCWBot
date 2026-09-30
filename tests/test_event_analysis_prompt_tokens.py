# ruff: noqa: E501
"""Regression measurements for the Event Analysis prompt's compact representation."""

from decimal import Decimal
from math import ceil

import pytest

import bot.services.ai_agent_groq as ai_agent_groq
from bot.alerting.event_identity import _canonical_event_analysis_context

# Exact instruction block from dev before the compact prompt change.  This is a sanitized,
# fixture-only reconstruction: production payloads are neither needed nor used by this test.
_BEFORE_INSTRUCTIONS = """Return valid JSON only. Write English.
Use exactly: symbol, should_alert, event_key, title, message_body, related_news_ids, possible_action, urgency, confidence, reason_for_no_alert.
urgency: low, normal, high. confidence: low, medium, high.
Analyze one symbol. Event Alerts are market-event-first: market facts and snapshots are primary; news supports interpretation but news alone must not set should_alert=true.
LLM owns market significance. Do not invent backend price thresholds. Time-window facts are distinct: market.chg_window_percent is the price change over market.analysed_window_minutes; market.chg24h_percent is the 24-hour price change; market.chg_since_msg_percent is the change since last_msg.time/last_msg.price, not the analysed-window change unless those timestamps coincide. snapshots are the only supplied observations for an analysed-window trajectory. A null metric is unavailable or unknown: never infer it from another metric, substitute chg_since_msg_percent or chg24h_percent for chg_window_percent, or claim an analysed-window move when chg_window_percent is null. One current snapshot does not establish an analysed-window trajectory. analysed_window_minutes describes the intended analysis window, not proof that a change for that window is available. All Event Analysis change fields (chg_window_percent, chg24h_percent, chg_since_msg_percent) are already percentage values / percentage points, never decimal fractions: 0.042 means 0.042%, not 4.2%. Never multiply a supplied change value by 100. Use qualitative significance reasoning from the supplied market evidence; never say a move did not meet a threshold unless an explicit threshold is present in the input.
should_alert=true means you judge this supplied market event noteworthy enough to interrupt the user with an Event Alert. Keep that boolean and your qualitative reasoning internally consistent: if you describe the state as routine, ordinary, modest, stable, insignificant, or otherwise not meaningfully noteworthy, normally return should_alert=false. You may return true despite a modest individual metric only when other supplied market evidence clearly makes the event noteworthy; state that market-evidence reason. News alone must never make a routine market state alertable.
When should_alert=true use a stable non-random event_key. When false, event_key/title/message_body/possible_action are empty or null, related_news_ids is [], urgency is null, and reason_for_no_alert is non-empty.
For should_alert=true, make title concise and centered on the verified analysed-window move when chg_window_percent is available; otherwise use only verified available context. Do not repeat 24h change in the title when that move is available. message_body must be a short, useful interpretation, not a restatement of supplied price or percentage values. Use only supplied evidence: describe news as coincident context, never as proven cause. possible_action must be concise, conditional monitoring of supplied snapshots, trend, or selected news; do not give trading commands or generic risk-plan advice.
Use news.news_id only for related_news_ids. Be cautious; no guaranteed outcomes or hard trading commands.
In snapshots, m is minutes before timestamp_utc and p is USD price.

Input JSON:
"""


def _fixture(*, news: bool = False, previous: bool = False) -> dict:
    payload = {
        "analysis_id": "event_analysis_btc_fixture",
        "symbol": "BTC",
        "display_symbol": "BTC",
        "coin_name": "Bitcoin",
        "timestamp_utc": "2026-09-29T10:00:00+00:00",
        "market": {
            "price": Decimal("112345.678901234567"),
            "snapshots": [
                {"m": 30, "p": Decimal("111900.123456789012")},
                {"m": 15, "p": Decimal("112100.543210987654")},
                {"m": 0, "p": Decimal("112345.678901234567")},
            ],
            "payload_points": 6,
            "analysed_window_minutes": 30,
            "chg_window_percent": Decimal("0.398172635491"),
            "chg24h_percent": Decimal("-0.184276519"),
            "chg_since_msg_percent": Decimal("0.201234567"),
        },
        "last_msg": {
            "time": "2026-09-29T06:00:00+00:00",
            "type": "event_alert",
            "price": Decimal("112120.123456789012"),
        },
        "news": [],
        "policy": {
            "language": "English",
            "audience": "General retail crypto holder.",
            "noise": "Prefer fewer useful alerts; avoid repetitive low-value alerts.",
        },
    }
    if news:
        payload["news"] = [
            {
                "news_id": "btc-etf-flow",
                "source": "Example Wire",
                "title": "Bitcoin ETF flows reverse after volatile session",
                "time": "2026-09-29T09:15:00+00:00",
                "summary": "Sanitized representative summary of reported fund-flow context and market reaction.",
                "relevance_label": "market_context",
                "material": True,
            },
            {
                "news_id": "btc-options",
                "source": "Example Desk",
                "title": "Options positioning remains elevated into month end",
                "time": "2026-09-29T08:40:00+00:00",
                "summary": "Sanitized representative summary of derivatives positioning; it is context, not a proven cause.",
                "relevance_label": "supporting",
                "material": False,
            },
        ]
    if previous:
        payload["previous_event_alert"] = {
            "title": "Bitcoin volatility expands",
            "canonical_event_key": "btc_volatility_expansion",
            "semantic_family": "volatility",
            "analysed_window_move": Decimal("0.4219"),
            "stable_related_news_ids_hash": "0e6a2b5c84ddf40f9a38b163beeb0a20",
            "possible_action": "Monitor whether the supplied range holds.",
            "created_at": "2026-09-29T06:00:00+00:00",
        }
    return payload


def _production_shape_fixture() -> dict:
    payload = _fixture(news=True, previous=True)
    payload["market"]["snapshots"] = [
        {"m": 150, "p": Decimal("111500.123456789012")},
        {"m": 120, "p": Decimal("111700.223456789012")},
        {"m": 90, "p": Decimal("111850.323456789012")},
        {"m": 60, "p": Decimal("112000.423456789012")},
        {"m": 30, "p": Decimal("112150.523456789012")},
        {"m": 0, "p": Decimal("112345.678901234567")},
    ]
    payload["news"].append(
        {
            "news_id": "btc-policy",
            "source": "Example News",
            "title": "Policy discussion adds broad crypto context into the session",
            "time": "2026-09-29T07:05:00+00:00",
            "summary": (
                '<p style="float:right"><img alt="Policy discussion adds broad crypto context" '
                'src="https://example.invalid/image.png"></p>'
            ),
            "relevance_label": "market_wide",
            "material": False,
        }
    )
    return payload


def _estimate_tokens(text: str) -> int:
    """Deterministic, clearly labeled fallback: one token per four UTF-8 characters."""
    return ceil(len(text.encode("utf-8")) / 4)


def _measurement(payload: dict, *, before: bool) -> dict:
    if before:
        static = ai_agent_groq.SYSTEM_PROMPT + "\n" + _BEFORE_INSTRUCTIONS
        serialized_payload = ai_agent_groq._json_dumps(payload)
    else:
        static = ai_agent_groq.SYSTEM_PROMPT + "\n" + ai_agent_groq._EVENT_ANALYSIS_INSTRUCTIONS + "\nInput JSON:\n"
        serialized_payload = ai_agent_groq._json_dumps(
            ai_agent_groq._event_analysis_prompt_payload(payload)
        )
    message = static + serialized_payload
    return {
        "method": (
            "deterministic message characters plus a UTF-8/4 proxy; "
            "provider prompt tokens require post-deploy telemetry"
        ),
        "static_message_chars": len(static),
        "serialized_payload_chars": len(serialized_payload),
        "total_message_chars": len(message),
        "token_proxy_utf8_div4": _estimate_tokens(message),
    }


@pytest.mark.parametrize(
    ("case", "payload"),
    [
        ("no_news", _fixture()),
        ("candidate_news", _fixture(news=True)),
        ("previous_event_alert", _fixture(previous=True)),
    ],
)
def test_event_analysis_prompt_measurement_reduces_each_sanitized_fixture(case, payload):
    before = _measurement(payload, before=True)
    after = _measurement(payload, before=False)

    assert after["static_message_chars"] < before["static_message_chars"], case
    assert after["serialized_payload_chars"] < before["serialized_payload_chars"], case
    assert after["total_message_chars"] < before["total_message_chars"], case


def test_event_analysis_prompt_measurement_targets_production_message_budget():
    payloads = (
        _fixture(),
        _fixture(news=True),
        _fixture(previous=True),
        _production_shape_fixture(),
    )
    measurements = [_measurement(payload, before=False) for payload in payloads]
    average_chars = sum(item["total_message_chars"] for item in measurements) / len(
        measurements
    )

    # Production replay showed the real pre-change payload mix was materially larger than the
    # original synthetic fixtures. Keep this as a deterministic message-size guard only;
    # provider prompt-token usage must still be measured after deployment.
    assert average_chars <= 1450
    assert measurements[-1]["total_message_chars"] <= 1850


def test_compact_event_analysis_payload_preserves_decision_and_grounding_facts():
    payload = _fixture(news=True, previous=True)
    compact = ai_agent_groq._event_analysis_prompt_payload(payload)

    assert compact["sym"] == "BTC"
    assert "at" not in compact
    assert "p" not in compact["m"]
    assert compact["m"]["s"] == [
        [30, Decimal("111900.123456789012")],
        [15, Decimal("112100.543210987654")],
        [0, Decimal("112345.678901234567")],
    ]
    assert compact["m"]["cw"] == Decimal("0.398172635491")
    assert compact["m"]["c24"] == Decimal("-0.184276519")
    assert compact["m"]["cl"] == Decimal("0.201234567")
    assert "lm" not in compact
    assert compact["n"][0] == {
        "i": "btc-etf-flow",
        "src": "Example Wire",
        "t": "Bitcoin ETF flows reverse after volatile session",
        "x": "Sanitized representative summary of reported fund-flow context and market reaction.",
        "r": "market_context",
        "mat": True,
        "h": 0,
    }
    assert compact["n"][1]["h"] == 1
    assert compact["prev"] == {
        "k": "btc_volatility_expansion",
        "f": "volatility",
        "cw": Decimal("0.4219"),
    }
    assert "analysis_id" not in compact
    assert "policy" not in compact


def test_exact_context_tracks_the_compact_model_contract_not_redundant_input_fields():
    context = _canonical_event_analysis_context(_fixture(news=True, previous=True))

    assert context["schema_version"] == 8
    assert context["symbol"] == "btc"
    assert context["market"]["price"] == Decimal("112345.678901234567")
    assert context["last_msg"] == {
        "time": "2026-09-29T06:00:00+00:00",
        "price": Decimal("112120.123456789012"),
    }
    assert "display_symbol" not in context
    assert "coin_name" not in context
    assert "payload_points" not in context["market"]
    news_by_id = {item["news_id"]: item for item in context["news"]}
    assert all("time" not in item for item in context["news"])
    assert news_by_id["btc-etf-flow"]["relevance_label"] == "market_context"
    assert news_by_id["btc-etf-flow"]["age_hours"] == 0
    assert news_by_id["btc-options"]["relevance_label"] == "supporting"
    assert news_by_id["btc-options"]["age_hours"] == 1
    assert "title" not in context["previous_event_alert"]
    assert "stable_related_news_ids_hash" not in context["previous_event_alert"]
    assert "possible_action" not in context["previous_event_alert"]
    assert "policy" not in context


def test_compact_news_drops_truncated_rss_markup_but_keeps_freshness():
    payload = _fixture(previous=True)
    payload["news"] = [
        {
            "news_id": "n1",
            "source": "Example Feed",
            "title": "Market update",
            "time": "2026-09-29T07:05:00+00:00",
            "summary": (
                '<p style="float:right"><img alt="Market update" '
                'src="https://example.invalid/truncated'
            ),
            "relevance_label": "market_wide",
            "material": False,
        }
    ]

    compact = ai_agent_groq._event_analysis_prompt_payload(payload)

    assert compact["n"][0]["h"] == 2
    assert "x" not in compact["n"][0]
