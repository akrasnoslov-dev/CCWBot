from decimal import Decimal

import pytest

from bot.alerting.event_identity import _build_exact_event_context_fingerprint, _json_dumps


def _payload() -> dict:
    return {
        "analysis_id": "runtime-id-a",
        "timestamp_utc": "2026-09-17T10:00:00+00:00",
        "symbol": "BTC",
        "display_symbol": "BTC",
        "coin_name": "Bitcoin",
        "market": {
            "price": Decimal("1.3500"),
            "snapshots": [{"m": 30, "p": Decimal("1.3500")}],
            "payload_points": 6,
            "analysed_window_minutes": 30,
            "chg_window": Decimal("-0.183"),
            "chg24h": Decimal("-0.721"),
            "chg_since_msg": None,
        },
        "last_msg": {"time": None, "type": None, "price": None},
        "news": [
            {
                "news_id": "n1",
                "title": "Market update",
                "source": "Example",
                "time": "2026-09-17T09:00:00+00:00",
                "summary": "Market conditions changed.",
                "relevance_label": "high",
                "material": True,
            }
        ],
        "policy": {"language": "English"},
    }


def test_exact_context_ignores_runtime_metadata_and_normalizes_decimal_representation():
    original = _payload()
    equivalent = _payload()
    equivalent["analysis_id"] = "runtime-id-b"
    equivalent["timestamp_utc"] = "2026-09-17T11:00:00+00:00"
    equivalent["last_msg"]["time"] = "2026-09-17T11:00:00+00:00"
    equivalent["previous_event_alert"] = {
        "created_at": "2026-09-17T11:00:00+00:00",
        "canonical_event_key": "btc_market_move",
        "semantic_family": "market_move",
    }
    original["previous_event_alert"] = {
        "created_at": "2026-09-17T10:00:00+00:00",
        "canonical_event_key": "btc_market_move",
        "semantic_family": "market_move",
    }
    equivalent["market"]["price"] = Decimal("1.35")
    assert _build_exact_event_context_fingerprint(
        original
    ) == _build_exact_event_context_fingerprint(equivalent)


def test_exact_context_ignores_nested_timestamps_but_not_semantic_previous_context():
    original = _payload()
    original["last_msg"] = {"time": "2026-09-17T10:00:00+00:00", "type": "event", "price": 1.35}
    original["previous_event_alert"] = {
        "created_at": "2026-09-17T10:00:00+00:00",
        "canonical_event_key": "btc_market_move",
        "semantic_family": "market_move",
        "title": "BTC market move",
    }
    timestamp_only = _payload()
    timestamp_only["last_msg"] = {
        "time": "2026-09-17T11:00:00+00:00",
        "type": "event",
        "price": 1.35,
    }
    timestamp_only["previous_event_alert"] = {
        **original["previous_event_alert"],
        "created_at": "2026-09-17T11:00:00+00:00",
    }
    changed_semantics = _payload()
    changed_semantics["last_msg"] = timestamp_only["last_msg"]
    changed_semantics["previous_event_alert"] = {
        **timestamp_only["previous_event_alert"],
        "semantic_family": "market_breakout",
    }

    assert _build_exact_event_context_fingerprint(
        original
    ) == _build_exact_event_context_fingerprint(timestamp_only)
    assert _build_exact_event_context_fingerprint(
        original
    ) != _build_exact_event_context_fingerprint(changed_semantics)


def test_exact_context_invalidates_any_real_market_or_news_change():
    original = _payload()
    changed_market = _payload()
    changed_market["market"]["chg_window"] = Decimal("-0.184")
    changed_news = _payload()
    changed_news["news"][0]["title"] = "Different market update"
    fingerprint = _build_exact_event_context_fingerprint(original)
    assert fingerprint != _build_exact_event_context_fingerprint(changed_market)
    assert fingerprint != _build_exact_event_context_fingerprint(changed_news)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("news_id", "n2"),
        ("title", "Corrected market update"),
        ("source", "Corrected publisher"),
        ("time", "2026-09-17T09:01:00+00:00"),
        ("summary", "Corrected market conditions."),
        ("relevance_label", "medium"),
        ("material", False),
    ],
)
def test_exact_context_invalidates_every_semantic_event_news_field(field, replacement):
    original = _payload()
    changed = _payload()
    changed["news"][0][field] = replacement

    assert _build_exact_event_context_fingerprint(
        original
    ) != _build_exact_event_context_fingerprint(changed)


def test_decimal_json_is_full_precision_json_number_not_float_or_string():
    assert (
        _json_dumps({"price": Decimal("1.3500"), "move": Decimal("-0.183")})
        == '{"move":-0.183,"price":1.35}'
    )
