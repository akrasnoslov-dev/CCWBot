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


@pytest.mark.parametrize(
    "variant",
    (*candidates.CANDIDATE_ADDITIONS, *candidates.CANDIDATE_REPLACEMENTS),
)
def test_candidate_changes_only_instructions_not_input_or_schema(variant):
    payload = _dataset()["cases"][0]["input"]
    before = deepcopy(payload)
    production = candidates.candidate_prompt(payload, "production")
    candidate = candidates.candidate_prompt(payload, variant)

    assert candidate != production
    if variant not in (
        "global_prior_no_family", "path_facts", "market_signal_path",
        "market_event_evidence",
        "contextual_materiality",
    ):
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
        "production", "materiality_first", "balanced_novelty",
        "trajectory_evidence", "relative_displacement", "rebalanced_core",
        "global_prior_safe", "global_prior_no_family", "path_facts",
        "market_signal_path", "market_event_evidence",
        "contextual_materiality",
    }
    assert len({
        value["aggregate_prompt_fingerprint"] for value in output["candidates"].values()
    }) == 12
    for stats in output["candidates"].values():
        assert stats["measured_significance_precision"] is None
        assert stats["measured_significance_recall"] is None
        assert stats["provider_requests"] == 0


def test_market_signal_path_never_treats_global_alert_counts_as_own_history():
    import json

    payload = deepcopy(_dataset()["cases"][0]["input"])
    payload["previous_event_alert"] = {
        "semantic_family": "price_downtrend", "age_minutes": 30,
    }
    before = deepcopy(payload)
    body = candidates.candidate_prompt(payload, "market_signal_path")
    compact = json.loads(body.split("\nInput JSON:\n")[-1])
    assert "prev" not in compact and "cnt" not in compact
    assert "path" in compact
    assert "independently noteworthy" in body
    assert "per-recipient semantic cooldown" in body
    assert payload == before


def test_path_facts_are_grounded_in_sampled_prices_without_changing_input():
    import json

    payload = deepcopy(_dataset()["cases"][0]["input"])
    payload["previous_event_alert"] = {
        "semantic_family": "price_downtrend", "age_minutes": 30,
        "analysed_window_move": -1.0,
    }
    before = deepcopy(payload)
    result = candidates.candidate_prompt(payload, "path_facts")
    actual = json.loads(result.split("\nInput JSON:\n")[-1])
    assert "f" not in actual["prev"]
    assert actual["path"]["eff"] == 1.0
    assert actual["path"]["up"] > 0
    assert actual["path"]["down"] == 0
    assert actual["path"]["from_hi"] == 0
    assert actual["path"]["from_lo"] > 0
    assert "No fixed numeric cutoff" in result
    assert payload == before
    assert "path" not in json.loads(
        candidates.candidate_prompt(payload, "production")
        .split("\nInput JSON:\n")[-1]
    )


def test_verified_path_facts_reversal_is_not_mistaken_for_trending_motion():
    facts = candidates.verified_path_facts({
        "s": [[-120, 100], [-60, 95], [0, 100]],
    })
    assert facts["eff"] == 0.0
    assert facts["up"] > 0
    assert facts["down"] == -5
    assert facts["from_lo"] > 0
    assert candidates.verified_path_facts({"s": [[0, 0], [1, 100]]}) == {}
    assert candidates.verified_path_facts({"s": [[0, 100]]}) == {}


def test_global_prior_no_family_only_omits_unreliable_semantic_family():
    import json

    payload = deepcopy(_dataset()["cases"][0]["input"])
    payload["previous_event_alert"] = {
        "age_minutes": 37,
        "semantic_family": "price_downtrend",
        "analysed_window_move": -1.8,
    }
    before = deepcopy(payload)
    baseline = json.loads(
        candidates.candidate_prompt(payload, "production").split("\nInput JSON:\n")[-1]
    )
    candidate = json.loads(
        candidates.candidate_prompt(payload, "global_prior_no_family")
        .split("\nInput JSON:\n")[-1]
    )
    assert "f" in baseline["prev"] and "f" not in candidate["prev"]
    instructions = candidates.candidate_prompt(payload, "global_prior_no_family")
    assert "prev={min,cw}" in instructions
    assert "prev={min,f,cw}" not in instructions
    assert candidate["prev"]["min"] == 37
    assert candidate["prev"]["cw"] == -1.8
    assert baseline["prev"].pop("f") == "price_downtrend"
    assert baseline == candidate
    assert payload == before


def test_global_prior_candidate_does_not_confuse_shared_previous_with_per_user_delivery():
    payload = _dataset()["cases"][0]["input"]
    prompt = candidates.candidate_prompt(payload, "global_prior_safe")
    assert "ANY recipient" in prompt
    assert "four-hour per-user" in prompt
    assert "Matching prev.f" in prompt
    assert "No fixed numeric cutoff" in prompt
    assert candidates.candidate_prompt(payload, "production") == (
        ai_agent_groq.build_event_significance_prompt(payload)
    )


def test_missing_or_mutated_input_hash_fails_closed():
    dataset = _dataset()
    dataset["cases"][0]["input_sha256"] = "wrong"
    with pytest.raises(ValueError, match="Frozen case input changed"):
        candidates.offline_inventory(dataset)


def test_unknown_candidate_is_rejected():
    with pytest.raises(ValueError, match="Unknown candidate"):
        candidates.candidate_prompt(_dataset()["cases"][0]["input"], "not_a_candidate")


def test_market_event_evidence_preserves_observed_path_without_global_family():
    import json

    payload = deepcopy(_dataset()["cases"][0]["input"])
    payload["previous_event_alert"] = {
        "age_minutes": 35, "semantic_family": "price_uptrend",
        "analysed_window_move": 0.4,
    }
    original = deepcopy(payload)
    prompt = candidates.candidate_prompt(payload, "market_event_evidence")
    compact = json.loads(prompt.split("\nInput JSON:\n")[-1])
    assert compact["sym"] == "BTC"
    assert compact["prev"]["min"] == 35
    assert "f" not in compact["prev"]
    assert compact["path"]["eff"] == 1.0
    assert "cnt" in compact
    assert "partial" in prompt
    assert "No fixed numeric cutoff" in prompt
    assert payload == original
