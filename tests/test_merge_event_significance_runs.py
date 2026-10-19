"""Replay merging is offline, conservative and safe for the frozen benchmark."""
from __future__ import annotations

from copy import deepcopy

import pytest

from scripts import merge_event_significance_runs as merging
from scripts.event_alert_benchmark import digest


def sample_dataset():
    cases = []
    for i, symbol in enumerate(("BTC", "ETH", "GRAM", "SOL")):
        market = {"symbol": symbol, "market": {"chg_window_percent": i + 1}}
        cases.append({
            "id": f"case-{i}", "symbol": symbol,
            "input_sha256": digest(market), "input": market,
        })
    return {"dataset_sha256": digest(cases), "cases": cases}


def state(dataset, *, case_ids, prompt="production", model="m1"):
    by_id = {item["id"]: item["input_sha256"] for item in dataset["cases"]}
    return {
        "dataset_sha256": dataset["dataset_sha256"],
        "model": model,
        "fingerprints": {prompt: f"fingerprint-{prompt}"},
        "attempted_requests": len(case_ids),
        "runs": {
            prompt: [{
                "id": case_id,
                "input_sha256": by_id[case_id],
                "status": "valid", "should_alert": True,
                "total_tokens": 200,
            } for case_id in case_ids],
        },
    }


def test_merge_disjoint_runs_preserves_results_and_total_request_budget():
    dataset = sample_dataset()
    first = state(dataset, case_ids=["case-0", "case-1"])
    second = state(dataset, case_ids=["case-2"], prompt="trajectory_evidence")
    result = merging.combine_states(dataset, [first, second])
    assert result["attempted_requests"] == 3
    assert len(result["runs"]["production"]) == 2
    assert len(result["runs"]["trajectory_evidence"]) == 1
    assert result["fingerprints"]["production"] == "fingerprint-production"
    assert result["fingerprints"]["trajectory_evidence"] == (
        "fingerprint-trajectory_evidence"
    )
    assert len(first["runs"]["production"]) == 2  # inputs not mutated


def test_same_case_with_different_variants_is_allowed_for_paired_comparison():
    dataset = sample_dataset()
    a = state(dataset, case_ids=["case-0"], prompt="production")
    b = state(dataset, case_ids=["case-0"], prompt="trajectory_evidence")
    result = merging.combine_states(dataset, [a, b])
    assert len(result["runs"]["production"]) == 1
    assert len(result["runs"]["trajectory_evidence"]) == 1
    assert result["attempted_requests"] == 2


def test_merge_rejects_double_counted_provider_decision():
    dataset = sample_dataset()
    recorded = state(dataset, case_ids=["case-0"])
    with pytest.raises(ValueError, match="Overlapping provider attempts"):
        merging.combine_states(dataset, [recorded, deepcopy(recorded)])


@pytest.mark.parametrize("mutation,expected", [
    (lambda s: s.update(dataset_sha256="wrong"), "benchmark"),
    (lambda s: s.update(model="another"), "model"),
    (lambda s: s["fingerprints"].update(production="changed"), "fingerprints"),
    (lambda s: s["runs"]["production"][0].update(input_sha256="wrong"), "input hash"),
    (lambda s: s["runs"]["production"][0].update(messages="secret"), "private"),
    (lambda s: s.update(attempted_requests=0), "counter"),
    (lambda s: s["runs"]["production"][0].update(should_alert="yes"), "boolean"),
])
def test_merge_rejects_incompatible_or_unsafe_ledgers(mutation, expected):
    dataset = sample_dataset()
    first = state(dataset, case_ids=["case-0"])
    second = state(dataset, case_ids=["case-1"])
    mutation(second)
    with pytest.raises(ValueError, match=expected):
        merging.combine_states(dataset, [first, second])


def test_failed_provider_attempt_remains_unknown_not_negative():
    dataset = sample_dataset()
    first = state(dataset, case_ids=["case-0"])
    second = state(dataset, case_ids=["case-1"], prompt="trajectory_evidence")
    second["runs"]["trajectory_evidence"][0].update(
        status="provider_error", should_alert=None,
    )
    combined = merging.combine_states(dataset, [first, second])
    assert combined["runs"]["trajectory_evidence"][0]["should_alert"] is None
    assert combined["attempted_requests"] == 2


def test_incomplete_attempt_counter_cannot_bypass_replay_safety_ceiling():
    dataset = sample_dataset()
    first = state(dataset, case_ids=["case-0"])
    second = state(dataset, case_ids=["case-1"])
    first["attempted_requests"] = merging.MAX_APPROVED_CALLS - 180
    second["attempted_requests"] = 181
    with pytest.raises(ValueError, match="replay safety ceiling"):
        merging.combine_states(dataset, [first, second])
