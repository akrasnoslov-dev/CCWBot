"""Offline prompt-pack regressions; no inference or private benchmark fixtures."""
import copy
import hashlib
import json

import pytest

from bot.services.ai_agent_groq import (
    _EVENT_SIGNIFICANCE_JSON_SCHEMA,
    build_event_significance_prompt,
)
from scripts.ccw15_prompt_pack import (
    PROMPTS,
    build_prompt,
    check_production_parity,
    instruction,
)


def _input():
    return {
        "symbol": "BTC",
        "market": {
            "snapshots": [
                {"m": -120, "p": 100.0},
                {"m": -60, "p": 100.5},
                {"m": 0, "p": 100.7},
            ],
            "analysed_window_minutes": 120,
            "chg_window_percent": 0.7,
            "chg24h_percent": -1.1,
            "chg30m_percent": 0.11,
            "chg1h_percent": 0.2,
            "relative_window_percentile_30d": 62.5,
        },
        "news": [],
        "recent_event_counts": {"h6": 2, "h24": 5},
        "previous_event_alert": {
            "age_minutes": 200,
            "semantic_family": "price_uptrend",
            "analysed_window_move": 0.25,
        },
    }


def test_baseline_instructions_match_exact_production_prompt():
    check_production_parity()
    payload = _input()
    assert build_prompt(payload, "production") == build_event_significance_prompt(payload)


def test_candidate_prompts_are_full_deterministic_instructions_only():
    initial = _input()
    original = copy.deepcopy(initial)
    rendered = {name: build_prompt(initial, name) for name in PROMPTS}
    assert initial == original
    assert len(rendered) == 3
    for name, text in rendered.items():
        assert text.startswith(instruction("production"))
        prod_payload = build_event_significance_prompt(initial).split("\nInput JSON:\n", 1)[1]
        assert text.endswith(prod_payload)
        assert json.loads(text.split("\nInput JSON:\n", 1)[1]) == json.loads(
            rendered["production"].split("\nInput JSON:\n", 1)[1]
        )
        assert len(hashlib.sha256(instruction(name).encode("utf-8")).hexdigest()) == 64
    assert len(set(rendered.values())) == 3


def test_json_schema_remains_exactly_six_fields():
    expected = {"symbol", "materiality", "novelty", "should_alert", "reason_code", "confidence"}
    assert set(_EVENT_SIGNIFICANCE_JSON_SCHEMA["required"]) == expected
    assert set(_EVENT_SIGNIFICANCE_JSON_SCHEMA["properties"]) == expected
    assert _EVENT_SIGNIFICANCE_JSON_SCHEMA["additionalProperties"] is False


def test_unregistered_candidate_fails_closed():
    with pytest.raises(ValueError, match="Unregistered"):
        build_prompt(_input(), "unapproved_fourth_candidate")
