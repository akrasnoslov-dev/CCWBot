from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from scripts.ccw41_reviewer_c_audit import (
    _narrative_findings,
    compare_reviewers,
    import_results,
    prepare_review,
)
from scripts.event_alert_benchmark import digest

SYMBOLS = ("BTC", "ETH", "GRAM", "SOL")


def _case(index: int, symbol: str) -> dict:
    facts = {
        "analysis_id": f"source-analysis-{index}",
        "symbol": symbol,
        "coin_name": symbol,
        "display_symbol": symbol,
        "timestamp_utc": "2026-01-01T00:00:00Z",
        "market": {
            "price": 100 + index,
            "chg_window_percent": (index % 7) - 3,
            "analysed_window_minutes": 180,
            "snapshots": [
                {"timestamp": "2025-12-31T21:00:00Z", "price": 100 + index},
                {"timestamp": "2026-01-01T00:00:00Z", "price": 101 + index},
            ],
        },
        "news": [],
        "policy": {"market_first": True},
        "previous_event_alert": None,
        "recent_event_counts": {"6h": 0, "24h": 0},
        "last_msg": None,
    }
    return {
        "id": f"case-{index:03}",
        "symbol": symbol,
        "scenario_type": "routine",
        "tags": ["routine", "news_absent"],
        "source_type": "approved_read_only",
        "input": facts,
        "input_sha256": digest(facts),
        "observed": {"should_alert": index % 2 == 0},
    }


def _dataset() -> dict:
    cases = [_case(i, SYMBOLS[i // 50]) for i in range(200)]
    return {
        "schema_version": 1,
        "version": "synthetic-test-only",
        "provenance": "real_market_sanitized",
        "cases": cases,
        "dataset_sha256": digest(cases),
    }


def _labels(dataset: dict, evaluator: str, offset: int = 0) -> dict:
    warrants = ("alert", "no_alert", "ambiguous")
    return {
        "dataset_sha256": dataset["dataset_sha256"],
        "evaluator_id": evaluator,
        "labels": [
            {
                "id": case["id"],
                "warrant": warrants[(i + offset) % 3],
                "useful": None,
                "factual": None,
            }
            for i, case in enumerate(dataset["cases"])
        ],
    }


def _write(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


@pytest.fixture
def prepared(tmp_path: Path) -> dict:
    dataset = _dataset()
    benchmark = _write(tmp_path / "dataset.json", dataset)
    reviewer_a = _write(tmp_path / "a.json", _labels(dataset, "human-a"))
    reviewer_b = _write(tmp_path / "b.json", _labels(dataset, "human-b", 1))
    private_dir = tmp_path / "private"
    summary = prepare_review(
        benchmark, reviewer_a, reviewer_b, private_dir,
        seed="fixed-test-seed", batch_size=20, enforce_canonical=False,
        enforce_private_location=False,
    )
    return {"dataset": dataset, "private": private_dir, "summary": summary}


def _result_rows(prepared: dict, batch_index: int, *, reverse: bool = False) -> dict:
    packet = json.loads(
        (prepared["private"] / "packets" / f"batch_{batch_index:02}.json").read_text()
    )
    cases = list(packet["cases"])
    if reverse:
        cases.reverse()
    return {
        "batch_id": packet["batch_id"],
        "results": [
            {
                "case_id": case["case_id"],
                "input_sha256": case["input_sha256"],
                "warrant": "ambiguous" if i % 7 == 0 else ("alert" if i % 2 else "no_alert"),
                "confidence": "medium",
                "rationale": "The supplied market path is insufficiently novel or material.",
                "evidence_references": [
                    "input.market.snapshots[0].price",
                    "input.market.chg_window_percent",
                ],
                "missing_evidence": ["longer context"] if i % 7 == 0 else [],
                "reason_category": "routine_or_unclear",
            }
            for i, case in enumerate(cases)
        ],
    }


def test_prepare_is_deterministic_and_blinds_source_ids_and_decisions(prepared: dict) -> None:
    private_dir = prepared["private"]
    manifest = json.loads((private_dir / "manifest.json").read_text())
    packet_text = "\n".join(
        path.read_text() for path in sorted((private_dir / "packets").glob("*.json"))
    )
    assert manifest["case_count"] == 200
    assert manifest["symbol_counts"] == {symbol: 50 for symbol in SYMBOLS}
    assert len(manifest["batches"]) == 10
    assert "source-analysis-" not in packet_text
    assert '"observed"' not in packet_text
    assert '"baseline_provider"' not in packet_text
    assert all(row["opaque_id"].startswith("rc_") for row in manifest["cases"])
    assert len({row["opaque_id"] for row in manifest["cases"]}) == 200


def test_prepare_removes_prior_generated_copy_and_identity_metadata(tmp_path: Path) -> None:
    dataset = _dataset()
    for case in dataset["cases"]:
        case["input"]["previous_event_alert"] = {
            "age_minutes": 60,
            "analysed_window_minutes": 180,
            "analysed_window_move": 2.5,
            "created_at": "2025-12-31T23:00:00Z",
            "title": "generated message copy",
            "possible_action": "generated action copy",
            "canonical_event_key": "provider-derived-key",
            "semantic_family": "provider-derived-family",
            "stable_related_news_ids_hash": "technical-hash",
        }
        case["input"]["news"] = [{"news_id": "source-id", "title": "Public headline"}]
        case["input_sha256"] = digest(case["input"])
    dataset["dataset_sha256"] = digest(dataset["cases"])
    benchmark = _write(tmp_path / "dataset.json", dataset)
    a = _write(tmp_path / "a.json", _labels(dataset, "human-a"))
    b = _write(tmp_path / "b.json", _labels(dataset, "human-b", 1))
    private = tmp_path / "private"
    prepare_review(
        benchmark, a, b, private,
        enforce_canonical=False, enforce_private_location=False,
    )
    packet_text = (private / "packets" / "batch_01.json").read_text()
    assert "generated message copy" not in packet_text
    assert "provider-derived" not in packet_text
    assert "technical-hash" not in packet_text
    assert "source-id" not in packet_text
    assert '"age_minutes"' in packet_text
    assert "Public headline" in packet_text


def test_prepare_rejects_changed_input_hash(tmp_path: Path) -> None:
    dataset = _dataset()
    dataset["cases"][0]["input"]["market"]["price"] = 999
    dataset["dataset_sha256"] = digest(dataset["cases"])
    benchmark = _write(tmp_path / "dataset.json", dataset)
    a = _write(tmp_path / "a.json", _labels(dataset, "human-a"))
    b = _write(tmp_path / "b.json", _labels(dataset, "human-b", 1))
    with pytest.raises(ValueError, match="changed canonical replay input"):
        prepare_review(
            benchmark, a, b, tmp_path / "private",
            enforce_canonical=False, enforce_private_location=False,
        )


def test_partial_import_resumes_without_overwriting(prepared: dict) -> None:
    results_dir = prepared["private"] / "results"
    results_dir.mkdir()
    _write(results_dir / "batch_01.json", _result_rows(prepared, 1))
    first = import_results(prepared["private"], results_dir, enforce_private_location=False)
    second = import_results(prepared["private"], results_dir, enforce_private_location=False)
    assert first["accepted"] == 20
    assert first["missing"] == 180
    assert second["accepted"] == 20
    assert second["sealed"] is False


def test_import_rejects_duplicate_and_wrong_hash(prepared: dict) -> None:
    results_dir = prepared["private"] / "results"
    results_dir.mkdir()
    payload = _result_rows(prepared, 1)
    payload["results"].append(dict(payload["results"][0]))
    _write(results_dir / "batch_01.json", payload)
    with pytest.raises(ValueError, match="Duplicate Reviewer C case"):
        import_results(prepared["private"], results_dir, enforce_private_location=False)
    payload = _result_rows(prepared, 1)
    payload["results"][0]["input_sha256"] = "0" * 64
    _write(results_dir / "batch_01.json", payload)
    with pytest.raises(ValueError, match="input hash mismatch"):
        import_results(prepared["private"], results_dir, enforce_private_location=False)


def test_complete_import_is_order_independent_and_seals(prepared: dict) -> None:
    results_dir = prepared["private"] / "results"
    results_dir.mkdir()
    for index in range(10, 0, -1):
        _write(results_dir / f"batch_{index:02}.json", _result_rows(prepared, index, reverse=True))
    summary = import_results(
        prepared["private"], results_dir,
        run_metadata={
            "provider": "OpenAI Codex",
            "model": "gpt-test",
            "reasoning_effort": "test",
            "interface": "synthetic-test",
            "data_transfer_approval": "synthetic",
            "model_identity_verification": "synthetic-test",
        },
        enforce_private_location=False,
    )
    sealed = json.loads((prepared["private"] / "reviewer_c_sealed.json").read_text())
    assert summary == {"accepted": 200, "missing": 0, "sealed": True}
    assert len(sealed["results"]) == 200
    assert Counter(row["symbol"] for row in sealed["results"]) == Counter({s: 50 for s in SYMBOLS})


def test_compare_counts_ambiguous_and_original_conflicts(prepared: dict) -> None:
    results_dir = prepared["private"] / "results"
    results_dir.mkdir()
    for index in range(1, 11):
        _write(results_dir / f"batch_{index:02}.json", _result_rows(prepared, index))
    import_results(
        prepared["private"], results_dir,
        run_metadata={
            "provider": "OpenAI Codex", "model": "gpt-test",
            "reasoning_effort": "test", "interface": "synthetic-test",
            "data_transfer_approval": "synthetic",
            "model_identity_verification": "synthetic-test",
        },
        enforce_private_location=False,
    )
    aggregate = compare_reviewers(prepared["private"], enforce_private_location=False)
    assert aggregate["case_count"] == 200
    assert aggregate["pairwise"]["A-B"]["total"] == 200
    assert aggregate["a_b_conflict_subset"]["count"] > 0
    assert sum(aggregate["distributions"]["C"].values()) == 200
    assert "case_id" not in json.dumps(aggregate)


def test_narrative_does_not_claim_patterns_absent_from_metrics() -> None:
    distributions = {
        "A": {"alert": 10, "no_alert": 80, "ambiguous": 10},
        "B": {"alert": 10, "no_alert": 80, "ambiguous": 10},
        "C": {"alert": 20, "no_alert": 70, "ambiguous": 10},
    }
    decisive = {"A-C": {"agreement": 5, "total": 10}}
    ambiguous = {"A-C": {"agreement": 6, "total": 10}}
    breakdowns = {
        f"symbol:{symbol}": {"A-C": {"disagreement": disagreement}}
        for symbol, disagreement in zip(
            ("BTC", "ETH", "GRAM", "SOL"), (9, 7, 5, 3), strict=True,
        )
    }
    assert _narrative_findings(distributions, decisive, ambiguous, breakdowns) == ([], [])


def test_private_artifacts_are_rejected_outside_reports(tmp_path: Path) -> None:
    dataset = _dataset()
    benchmark = _write(tmp_path / "dataset.json", dataset)
    a = _write(tmp_path / "a.json", _labels(dataset, "human-a"))
    b = _write(tmp_path / "b.json", _labels(dataset, "human-b", 1))
    with pytest.raises(ValueError, match="gitignored reports directory"):
        prepare_review(
            benchmark, a, b, Path(__file__).resolve().parents[1] / "benchmarks"
            / "ccw41-unsafe-private", enforce_canonical=False,
        )


def test_complete_import_rejects_empty_approval_metadata(prepared: dict) -> None:
    results_dir = prepared["private"] / "results"
    results_dir.mkdir()
    for index in range(1, 11):
        _write(results_dir / f"batch_{index:02}.json", _result_rows(prepared, index))
    with pytest.raises(ValueError, match="verified run metadata"):
        import_results(
            prepared["private"],
            results_dir,
            run_metadata={
                "provider": "OpenAI Codex",
                "model": "gpt-test",
                "reasoning_effort": "test",
                "interface": "synthetic-test",
                "data_transfer_approval": "",
                "model_identity_verification": "synthetic-test",
            },
            enforce_private_location=False,
        )


def test_results_directory_must_be_inside_private_audit(tmp_path: Path) -> None:
    private = (
        Path(__file__).resolve().parents[1]
        / "reports" / "event-alert-review-20261016" / "ccw41-path-test"
    )
    with pytest.raises(ValueError, match="inside the private audit directory"):
        import_results(private, tmp_path)


def _seal_synthetic(prepared: dict) -> Path:
    results_dir = prepared["private"] / "results"
    results_dir.mkdir(exist_ok=True)
    for index in range(1, 11):
        _write(results_dir / f"batch_{index:02}.json", _result_rows(prepared, index))
    import_results(
        prepared["private"],
        results_dir,
        run_metadata={
            "provider": "synthetic", "model": "synthetic-test",
            "reasoning_effort": "synthetic", "interface": "synthetic",
            "data_transfer_approval": "synthetic",
            "model_identity_verification": "synthetic-test",
        },
        enforce_private_location=False,
    )
    return results_dir


def test_resume_rejects_corrupt_existing_partial_journal(prepared: dict) -> None:
    private = prepared["private"]
    results_dir = private / "results"
    results_dir.mkdir()
    _write(results_dir / "batch_01.json", _result_rows(prepared, 1))
    import_results(private, results_dir, enforce_private_location=False)
    journal_path = private / "reviewer_c_partial.json"
    journal = json.loads(journal_path.read_text())
    journal["results"][0]["input_sha256"] = "0" * 64
    _write(journal_path, journal)
    with pytest.raises(ValueError, match="input hash mismatch"):
        import_results(private, results_dir, enforce_private_location=False)


def test_resume_rejects_duplicate_existing_partial_journal(prepared: dict) -> None:
    private = prepared["private"]
    results_dir = private / "results"
    results_dir.mkdir()
    _write(results_dir / "batch_01.json", _result_rows(prepared, 1))
    import_results(private, results_dir, enforce_private_location=False)
    journal_path = private / "reviewer_c_partial.json"
    journal = json.loads(journal_path.read_text())
    journal["results"].append(dict(journal["results"][0]))
    _write(journal_path, journal)
    with pytest.raises(ValueError, match="Duplicate or unknown partial"):
        import_results(private, results_dir, enforce_private_location=False)


def test_import_rejects_unexpected_root_result_fields(prepared: dict) -> None:
    private = prepared["private"]
    results_dir = private / "results"
    results_dir.mkdir()
    payload = _result_rows(prepared, 1)
    payload["extra"] = "unapproved"
    _write(results_dir / "batch_01.json", payload)
    with pytest.raises(ValueError, match="batch root fields"):
        import_results(private, results_dir, enforce_private_location=False)


def test_compare_rejects_tampered_sealed_file(prepared: dict) -> None:
    _seal_synthetic(prepared)
    path = prepared["private"] / "reviewer_c_sealed.json"
    record = json.loads(path.read_text())
    record["results"][0]["warrant"] = "alert"
    _write(path, record)
    with pytest.raises(ValueError, match="provenance/hash mismatch"):
        compare_reviewers(prepared["private"], enforce_private_location=False)


def test_compare_rejects_tampered_run_fingerprint(prepared: dict) -> None:
    _seal_synthetic(prepared)
    path = prepared["private"] / "run_manifest.json"
    record = json.loads(path.read_text())
    record["rubric_sha256"] = "0" * 64
    _write(path, record)
    with pytest.raises(ValueError, match="provenance/hash mismatch"):
        compare_reviewers(prepared["private"], enforce_private_location=False)


def test_compare_rejects_tampered_sealed_case_even_with_rehashed_run(prepared: dict) -> None:
    import hashlib

    _seal_synthetic(prepared)
    sealed_path = prepared["private"] / "reviewer_c_sealed.json"
    record = json.loads(sealed_path.read_text())
    record["results"][0]["source_case_id"] = "forged-source-id"
    _write(sealed_path, record)
    run_path = prepared["private"] / "run_manifest.json"
    run = json.loads(run_path.read_text())
    run["reviewer_c_sha256"] = hashlib.sha256(sealed_path.read_bytes()).hexdigest()
    _write(run_path, run)
    with pytest.raises(ValueError, match="case provenance mismatch"):
        compare_reviewers(prepared["private"], enforce_private_location=False)


def test_frozen_protocol_rejects_edited_rubric(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts import ccw41_reviewer_c_audit as audit

    dataset = _dataset()
    benchmark = _write(tmp_path / "dataset.json", dataset)
    a = _write(tmp_path / "a.json", _labels(dataset, "human-a"))
    b = _write(tmp_path / "b.json", _labels(dataset, "human-b", 1))
    fake_rubric = tmp_path / "changed-rubric.md"
    fake_rubric.write_text("# CCW-41 Reviewer C significance rubric v1\nCHANGED\n")
    monkeypatch.setattr(audit, "RUBRIC_PATH", fake_rubric)
    with pytest.raises(ValueError, match="Frozen CCW-41 v1 protocol"):
        prepare_review(
            benchmark, a, b, tmp_path / "private",
            enforce_canonical=False, enforce_private_location=False,
        )


def test_complete_import_rejects_missing_identity_verification(prepared: dict) -> None:
    results_dir = prepared["private"] / "results"
    results_dir.mkdir()
    for index in range(1, 11):
        _write(results_dir / f"batch_{index:02}.json", _result_rows(prepared, index))
    with pytest.raises(ValueError, match="verified run metadata"):
        import_results(
            prepared["private"], results_dir,
            run_metadata={
                "provider": "OpenAI", "model": "gpt-6.1-sol",
                "reasoning_effort": "ultra", "interface": "local Codex",
                "data_transfer_approval": "owner approved",
            },
            enforce_private_location=False,
        )
