"""Counterfactual prompt candidates are offline hypotheses, never production gates."""
from __future__ import annotations

from copy import deepcopy

import pytest

from bot.services import ai_agent_groq
from scripts import event_significance_candidates as candidates
from scripts.event_alert_benchmark import digest


def _dataset():
    payload = {
        "symbol": "BTC",
        "timestamp_utc": "2026-10-16T08:00:00+00:00",
        "market": {
            "price": 123,
            "snapshots": [{"m": -180, "p": 121}, {"m": -90, "p": 122}, {"m": 0, "p": 123}],
            "analysed_window_minutes": 180,
            "chg_window_percent": 1.6529,
            "chg24h_percent": -1.3,
            "relative_window_percentile_30d": 93,
        },
        "news": [{"title": "Relevant headline", "relevance_label": "asset_specific",
                  "material": False}],
        "recent_event_counts": {"h6": 4, "h24": 9},
    }
    return {
        "dataset_sha256": digest([payload]),
        "cases": [
            {"id": "btc_test_only", "symbol": "BTC", "input": payload,
             "input_sha256": digest(payload)}
        ],
    }


def test_production_prompt_is_byte_identical_to_live_production_builder():
    payload = _dataset()["cases"][0]["input"]
    assert candidates.candidate_prompt(payload, "production") == (
        ai_agent_groq.build_event_significance_prompt(payload)
    )


@pytest.mark.parametrize("variant", candidates.CANDIDATE_ADDITIONS)
def test_candidate_changes_only_instructions_not_input_or_schema(variant):
    payload = _dataset()["cases"][0]["input"]
    before = deepcopy(payload)
    production = candidates.candidate_prompt(payload, "production")
    candidate = candidates.candidate_prompt(payload, variant)

    assert candidate != production
    assert candidate.split("\nInput JSON:\n")[-1] == production.split("\nInput JSON:\n")[-1]
    assert payload == before
    assert "No fixed numeric cutoff" in candidate
    assert "should_alert=true" in candidate
    assert "materiality=material AND novelty=new" in candidate


def test_offline_inventory_never_infers_accuracy_or_provider_spend(monkeypatch):
    dataset = _dataset()

    def forbidden(*args, **kwargs):
        raise AssertionError("No provider/router calls allowed")

    monkeypatch.setattr(ai_agent_groq, "get_router", forbidden)
    output = candidates.offline_inventory(dataset)
    assert output["cases"] == 1
    assert output["by_symbol"] == {"BTC": 1}
    assert set(output["candidates"]) == {
        "production", "materiality_first", "balanced_novelty", "trajectory_evidence"
    }
    assert len({
        value["aggregate_prompt_fingerprint"] for value in output["candidates"].values()
    }) == 4
    for stats in output["candidates"].values():
        assert stats["measured_significance_precision"] is None
        assert stats["measured_significance_recall"] is None
        assert stats["provider_requests"] == 0


def test_missing_or_mutated_input_hash_fails_closed():
    dataset = _dataset()
    dataset["cases"][0]["input_sha256"] = "wrong"
    with pytest.raises(ValueError, match="Frozen case input changed"):
        candidates.offline_inventory(dataset)


def test_unknown_candidate_is_rejected():
    with pytest.raises(ValueError, match="Unknown candidate"):
        candidates.candidate_prompt(_dataset()["cases"][0]["input"], "not_a_candidate")
