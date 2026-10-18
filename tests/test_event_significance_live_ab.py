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


def test_new_holdout_never_reuses_examined_events():
    dataset, labels = fixture_data()
    selected = live.eligible_replay_cases(
        dataset, labels,
        excluded_case_ids=frozenset({"case_0", "case_2"}),
        skip_ambiguous=True,
    )
    assert [case["id"] for case in selected] == ["case_1"]


def test_positive_screen_is_stable_and_keeps_all_decisive_cases():
    dataset, labels = fixture_data()
    default = live.eligible_replay_cases(
        dataset, labels, excluded_case_ids=frozenset(), skip_ambiguous=True,
    )
    screened = live.eligible_replay_cases(
        dataset, labels, excluded_case_ids=frozenset(), skip_ambiguous=True,
        screen_positives_first=True,
    )
    assert [case["id"] for case in default] == ["case_0", "case_1", "case_2"]
    assert [case["id"] for case in screened] == ["case_1", "case_2", "case_0"]
    assert {case["id"] for case in default} == {case["id"] for case in screened}
    assert len(screened) == len({case["id"] for case in screened})


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


def test_old_pinned_replay_can_add_candidate_without_replaying_existing_answers(tmp_path):
    dataset, _ = fixture_data()
    ledger = tmp_path / "old.json"
    earlier = live.load_state(
        ledger, dataset["dataset_sha256"], "gpt-oss-test",
        {"production": "fixed", "materiality_first": "fixed-two"},
    )
    earlier["runs"]["production"].append({
        "id": "case_0", "status": "valid", "should_alert": True,
    })
    live.save_state(ledger, earlier)
    resumed = live.load_state(
        ledger, dataset["dataset_sha256"], "gpt-oss-test",
        {
            "production": "fixed", "materiality_first": "fixed-two",
            "trajectory_evidence": "new",
        },
    )
    assert resumed["runs"]["production"] == earlier["runs"]["production"]
    assert resumed["runs"]["trajectory_evidence"] == []
    with pytest.raises(ValueError, match="configuration mismatch"):
        live.load_state(
            ledger, dataset["dataset_sha256"], "gpt-oss-test",
            {"production": "changed", "materiality_first": "fixed-two"},
        )


def test_unused_candidate_fingerprint_may_be_refreshed_only_explicitly(tmp_path):
    dataset, _ = fixture_data()
    path = tmp_path / "old.json"
    original = live.load_state(
        path, dataset["dataset_sha256"], "model",
        {"production": "original", "global_prior_no_family": "draft-v1"},
    )
    original["runs"]["production"].append({
        "id": "case_0", "input_sha256": dataset["cases"][0]["input_sha256"],
        "status": "valid", "should_alert": False,
    })
    live.save_state(path, original)
    new_config = {"production": "original", "global_prior_no_family": "draft-v2"}
    with pytest.raises(ValueError, match="configuration mismatch"):
        live.load_state(path, dataset["dataset_sha256"], "model", new_config)
    resumed = live.load_state(
        path, dataset["dataset_sha256"], "model", new_config,
        refresh_unused_config=True,
    )
    assert resumed["fingerprints"]["global_prior_no_family"] == "draft-v2"
    assert len(resumed["runs"]["production"]) == 1
    assert original["fingerprints"]["global_prior_no_family"] == "draft-v1"
    with pytest.raises(ValueError, match="configuration mismatch"):
        live.load_state(
            path, dataset["dataset_sha256"], "model",
            {"production": "changed", "global_prior_no_family": "draft-v2"},
            refresh_unused_config=True,
        )


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


def test_historical_baseline_reuses_frozen_decisions_without_provider_calls():
    dataset, labels = fixture_data()
    recorded = {
        "dataset_sha256": dataset["dataset_sha256"],
        "attempted_requests": 3,
        "runs": {"rebalanced_core": [
            {
                "id": case["id"], "input_sha256": case["input_sha256"],
                "status": "valid", "should_alert": labels[case["id"]] == "alert",
            }
            for case in dataset["cases"][:3]
        ]},
    }
    merged = scoring.with_historical_baseline(dataset, recorded)
    assert "historical" not in recorded["runs"]
    assert merged["attempted_requests"] == 3
    result = scoring.score(
        dataset, labels, merged, variants=("historical", "rebalanced_core"),
    )
    assert result["paired_unambiguous_cases"] == 3
    assert result["variants"]["historical"]["fp"] == 1
    assert result["variants"]["historical"]["fn"] == 1
    assert result["variants"]["rebalanced_core"]["tp"] == 2
    assert result["candidate_significance_gates_met"]["rebalanced_core"]


def test_historical_baseline_missing_recorded_decisions_never_padding():
    dataset, labels = fixture_data()
    dataset["cases"][0]["observed"].pop("should_alert")
    original_state = {
        "dataset_sha256": dataset["dataset_sha256"],
        "attempted_requests": 3,
        "runs": {"rebalanced_core": [
            {
                "id": case["id"], "input_sha256": case["input_sha256"],
                "status": "valid", "should_alert": True,
            }
            for case in dataset["cases"][:3]
        ]},
    }
    state = scoring.with_historical_baseline(dataset, original_state)
    report = scoring.score(
        dataset, labels, state, variants=("historical", "rebalanced_core"),
    )
    assert report["paired_cases_missing"] == 1
    assert not report["candidate_significance_gates_met"]["rebalanced_core"]


def test_significance_release_gate_requires_complete_paired_reference():
    dataset, labels = fixture_data()
    variants = ("production", "relative_displacement")
    runs = {
        name: [
            {
                "id": case["id"],
                "input_sha256": case["input_sha256"],
                "status": "valid",
                "should_alert": labels[case["id"]] == "alert",
            }
            for case in dataset["cases"][:3]
        ]
        for name in variants
    }
    state = {
        "dataset_sha256": dataset["dataset_sha256"],
        "attempted_requests": 6,
        "runs": runs,
    }
    complete = scoring.score(dataset, labels, state, variants=variants)
    assert complete["decisive_reference_cases"] == 3
    assert complete["paired_cases_missing"] == 0
    assert complete["candidate_significance_gates_met"]["relative_displacement"]
    runs["relative_displacement"].pop()
    incomplete = scoring.score(dataset, labels, state, variants=variants)
    assert incomplete["paired_cases_missing"] == 1
    assert not incomplete["candidate_significance_gates_met"]["relative_displacement"]


def test_best_case_gate_fails_as_soon_as_existing_false_negatives_make_recall_impossible():
    dataset, labels = fixture_data()
    rows = {
        "production": [],
        "global_prior_no_family": [],
    }
    for case in dataset["cases"]:
        if labels[case["id"]] == "ambiguous":
            continue
        prediction = False  # two missed positives; best recall is now zero
        row = {
            "id": case["id"], "input_sha256": case["input_sha256"],
            "status": "valid", "should_alert": prediction,
        }
        for variant in rows:
            rows[variant].append(dict(row))
    state = {
        "dataset_sha256": dataset["dataset_sha256"],
        "attempted_requests": 6, "runs": rows,
    }
    report = scoring.score(
        dataset, labels, state, variants=("production", "global_prior_no_family"),
    )
    info = report["candidate_best_case_feasibility"]["global_prior_no_family"]
    assert report["paired_cases_missing"] == 0
    assert info["best_possible_recall"] == 0
    assert not info["can_still_meet_gates"]


def test_best_case_gate_can_pass_with_unseen_positive_examples():
    dataset, labels = fixture_data()
    case = dataset["cases"][0]
    state = {
        "dataset_sha256": dataset["dataset_sha256"],
        "attempted_requests": 1,
        "runs": {"global_prior_no_family": [{
            "id": case["id"], "input_sha256": case["input_sha256"],
            "status": "valid", "should_alert": False,
        }]},
    }
    report = scoring.score(
        dataset, labels, state, variants=("global_prior_no_family",),
    )
    info = report["candidate_best_case_feasibility"]["global_prior_no_family"]
    assert info["best_possible_recall"] == 1.0
    assert info["best_possible_precision"] == 1.0
    assert info["remaining_positives"] == 2
    assert info["can_still_meet_gates"]
    assert not report["candidate_significance_gates_met"]["global_prior_no_family"]


def test_feasibility_uses_all_valid_candidate_rows_not_only_paired_intersection():
    dataset, labels = fixture_data()
    first, missed = dataset["cases"][0], dataset["cases"][1]
    state = {
        "dataset_sha256": dataset["dataset_sha256"],
        "attempted_requests": 2,
        "runs": {
            "production": [{
                "id": first["id"], "input_sha256": first["input_sha256"],
                "status": "valid", "should_alert": False,
            }],
            "market_signal_path": [{
                "id": missed["id"], "input_sha256": missed["input_sha256"],
                "status": "valid", "should_alert": False,
            }],
        },
    }
    report = scoring.score(
        dataset, labels, state, variants=("production", "market_signal_path"),
    )
    assert report["paired_unambiguous_cases"] == 0
    feasibility = report["candidate_best_case_feasibility"]["market_signal_path"]
    assert feasibility["observed_decisive_cases"] == 1
    assert feasibility["observed_false_negatives"] == 1
    assert feasibility["remaining_positives"] == 1
    assert feasibility["best_possible_recall"] == 0.5
    assert not feasibility["can_still_meet_gates"]


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



def test_explicit_rate_limit_retry_keeps_one_case_and_counts_both_calls():
    dataset, _ = fixture_data()
    case = dataset["cases"][0]
    original = {
        "id": case["id"], "input_sha256": case["input_sha256"],
        "status": "provider_error", "http_status": 429,
    }
    state = {
        "attempted_requests": 2,
        "runs": {"global_prior_safe": [dict(original)]},
    }
    assert not live.can_retry_rate_limit(original, approved=False)
    assert live.can_retry_rate_limit(original, approved=True)
    success = {
        "id": case["id"], "input_sha256": case["input_sha256"],
        "status": "valid", "should_alert": True, "total_tokens": 1760,
    }
    live.record_replay_result(state, "global_prior_safe", success, retrying=True)
    assert state["attempted_requests"] == 2
    assert len(state["runs"]["global_prior_safe"]) == 1
    assert state["runs"]["global_prior_safe"][0]["should_alert"] is True
    # The earlier unknown-usage attempt still conservatively costs a full budget.
    assert live.estimated_spent_tokens(state, 6300) == 1760 + 8300


def test_rate_limit_retry_rejects_non_429_failures_duplicate_and_changed_input():
    case = fixture_data()[0]["cases"][0]
    failed = {
        "id": case["id"], "input_sha256": case["input_sha256"],
        "status": "provider_error", "http_status": 503,
    }
    state = {"attempted_requests": 1, "runs": {"production": [failed]}}
    assert not live.can_retry_rate_limit(failed, approved=True)
    with pytest.raises(ValueError, match="rate-limit failure"):
        live.record_replay_result(state, "production", failed, retrying=True)
    with pytest.raises(ValueError, match="Duplicate scored response"):
        live.record_replay_result(state, "production", failed, retrying=False)
    state["runs"]["production"][0]["http_status"] = 429
    mismatched = dict(failed, input_sha256="different")
    with pytest.raises(ValueError, match="frozen input"):
        live.record_replay_result(state, "production", mismatched, retrying=True)



def test_live_best_case_bound_matches_complete_reference_and_ignores_errors():
    dataset, labels = fixture_data()
    rows = [{
        "id": dataset["cases"][i]["id"],
        "status": "valid",
        "should_alert": False,
    } for i in (0, 1)]
    rows.append({
        "id": dataset["cases"][2]["id"], "status": "provider_error",
        "http_status": 429,
    })
    state = {"runs": {"global_prior_no_family": rows}}
    result = live.maximum_possible_quality(
        dataset, labels, state, "global_prior_no_family",
    )
    assert result["false_negative"] == 1
    assert result["false_positive"] == 0
    assert result["max_recall"] == 0.5
    assert not result["can_meet_target"]
    rows[1]["should_alert"] = True
    recovered = live.maximum_possible_quality(
        dataset, labels, state, "global_prior_no_family",
    )
    assert recovered["can_meet_target"]
    assert recovered["max_recall"] == 1.0


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
