"""No network requests: integrity, budget and paired-score contracts."""
from __future__ import annotations

import pytest

from scripts import live_event_significance_benchmark as live
from scripts import score_event_significance_ab as scoring
from scripts.event_alert_benchmark import digest


def fixture_data():
    cases = []
    for i, (symbol, observed) in enumerate((
        ("BTC", True), ("ETH", False), ("GRAM", True), ("SOL", False)
    )):
        payload = {
            "symbol": symbol,
            "market": {
                "price": 100,
                "snapshots": [{"m": -180, "p": 99}, {"m": 0, "p": 100}],
                "chg_window_percent": 1,
                "analysed_window_minutes": 180,
            },
        }
        cases.append({
            "id": f"case_{i}", "symbol": symbol, "input": payload,
            "input_sha256": digest(payload), "observed": {"should_alert": observed},
        })
    dataset = {"cases": cases, "dataset_sha256": digest(cases)}
    a = {
        "case_0": "no_alert", "case_1": "alert",
        "case_2": "alert", "case_3": "ambiguous",
    }
    return dataset, a


def test_ordering_interleaves_historic_error_types_and_has_no_duplicates():
    dataset, labels = fixture_data()
    arranged = live.ordering(dataset, labels)
    assert [row["id"] for row in arranged] == [
        "case_0", "case_1", "case_2", "case_3"
    ]
    assert len({row["id"] for row in arranged}) == len(dataset["cases"])


def test_replay_state_rejects_changed_model_input_or_configuration(tmp_path):
    dataset, _ = fixture_data()
    ledger = tmp_path / "run.json"
    state = live.load_state(
        ledger, dataset["dataset_sha256"], "gpt-oss-test", {"production": "hash"}
    )
    assert state["attempted_requests"] == 0
    live.save_state(ledger, state)
    assert live.load_state(
        ledger, dataset["dataset_sha256"], "gpt-oss-test", {"production": "hash"}
    ) == state
    with pytest.raises(ValueError, match="configuration mismatch"):
        live.load_state(ledger, dataset["dataset_sha256"], "another", {})


def test_paired_score_excludes_incomplete_and_ambiguous_cases():
    dataset, a = fixture_data()
    state = {
        "dataset_sha256": dataset["dataset_sha256"],
        "attempted_requests": 11,
        "runs": {v: [] for v in live.VARIANTS},
    }
    for variant in live.VARIANTS:
        for index, pred in enumerate((False, True, True, False)):
            case = dataset["cases"][index]
            row = {
                "id": case["id"],
                "input_sha256": case["input_sha256"],
                "status": "valid", "should_alert": pred,
                "total_tokens": 100,
            }
            if variant == "balanced_novelty" and index == 2:
                continue
            state["runs"][variant].append(row)
    report = scoring.score(dataset, a, state)
    assert report["paired_unambiguous_cases"] == 2
    assert report["paired_cohort_not_population_estimate"] is True
    for variant in live.VARIANTS:
        stats = report["variants"][variant]
        assert (stats["tp"], stats["fp"], stats["fn"], stats["tn"]) == (1, 0, 0, 1)
        assert stats["precision"] == 1.0
        assert stats["recall"] == 1.0


def test_pairwise_cohort_does_not_require_dropped_third_candidate():
    dataset, labels = fixture_data()
    rows = {}
    for name in live.VARIANTS:
        rows[name] = []
        for case in dataset["cases"][:3]:
            rows[name].append({
                "id": case["id"], "input_sha256": case["input_sha256"],
                "status": "valid", "should_alert": case["observed"]["should_alert"],
            })
    # The discontinued third candidate has no valid answer on case 1.
    rows["balanced_novelty"] = rows["balanced_novelty"][:1]
    state = {
        "dataset_sha256": dataset["dataset_sha256"],
        "attempted_requests": 7,
        "runs": rows,
    }
    triple = scoring.score(dataset, labels, state)
    pair = scoring.score(
        dataset, labels, state,
        variants=("production", "materiality_first"),
    )
    assert triple["paired_unambiguous_cases"] == 1
    assert pair["paired_unambiguous_cases"] == 3
    assert set(pair["variants"]) == {"production", "materiality_first"}


def test_paired_score_rejects_mismatched_input_hash():
    dataset, a = fixture_data()
    row = {
        "id": "case_0", "input_sha256": "not-frozen", "status": "valid",
        "should_alert": True,
    }
    state = {
        "dataset_sha256": dataset["dataset_sha256"],
        "attempted_requests": 1,
        "runs": {"production": [row], "materiality_first": [], "balanced_novelty": []},
    }
    with pytest.raises(ValueError, match="input hash mismatch"):
        scoring.score(dataset, a, state)


def test_paired_score_requires_boolean_on_valid_output():
    dataset, a = fixture_data()
    state = {"dataset_sha256": dataset["dataset_sha256"],
             "attempted_requests": 3, "runs": {}}
    for variant in live.VARIANTS:
        state["runs"][variant] = [{
            "id": "case_0", "input_sha256": dataset["cases"][0]["input_sha256"],
            "status": "valid", "should_alert": "false",
        }]
    with pytest.raises(ValueError, match="boolean"):
        scoring.score(dataset, a, state)


def test_records_export_private_decisions_not_raw_prompts(tmp_path):
    dataset, _ = fixture_data()
    state = {
        "dataset_sha256": dataset["dataset_sha256"], "model": "test-model",
        "fingerprints": {variant: variant + "-hash" for variant in live.VARIANTS},
        "attempted_requests": 1,
        "runs": {v: [] for v in live.VARIANTS},
    }
    state["runs"]["production"].append({
        "id": "case_0",
        "input_sha256": dataset["cases"][0]["input_sha256"],
        "status": "valid", "should_alert": False,
        "error_type": "none",
    })
    live.export_recorded_runs(tmp_path, state)
    output = (tmp_path / "recorded_production.json").read_text(encoding="utf-8")
    assert "error_type" not in output
    assert "should_alert" in output
    assert "messages" not in output


def test_token_safety_counts_uncertain_and_interrupted_attempts():
    state = {
        "attempted_requests": 3,
        "runs": {
            "production": [{"total_tokens": 1800}],
            "materiality_first": [{"status": "provider_error"}],
            "balanced_novelty": [],
        },
    }
    assert live.estimated_spent_tokens(state, 6300) == 1800 + 8300 + 8300


def test_reference_labels_must_match_original_frozen_dataset(tmp_path):
    dataset, _ = fixture_data()
    path = tmp_path / "reference.json"
    path.write_text('{"dataset_sha256":"bad","labels":[]}', encoding="utf-8")
    with pytest.raises(ValueError, match="do not match"):
        live.load_reviewer_a(path, dataset)
