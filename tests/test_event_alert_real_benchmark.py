"""Offline benchmark and historical alert diagnostics; all constructed cases are TEST-ONLY."""
import json
from copy import deepcopy

import pytest

from scripts.event_alert_benchmark import (
    blind_packet,
    compare_recorded_run,
    digest,
    load_frozen,
    reconcile,
    report,
)


def _case(case_id, symbol="BTC", decision=True, recipients=12):
    context = {
        "symbol": symbol,
        "timestamp_utc": "2026-10-16T05:30:00+00:00",
        "market": {
            "price": 100,
            "chg_window_percent": 0.16,
            "chg24h_percent": 1.2,
            "analysed_window_minutes": 180,
            "snapshots": [{"m": -180, "p": 99.84}, {"m": 0, "p": 100}],
        },
        "news": [],
        "recent_event_counts": {"h6": 1, "h24": 2},
    }
    return {
        "id": case_id,
        "symbol": symbol,
        "scenario_type": "delivered" if decision else "no_alert",
        "source_type": "approved_read_only",
        "input": context,
        "input_sha256": digest(context),
        "observed": {
            "should_alert": decision,
            "eligible_recipients": recipients,
            "delivered_count": recipients if decision else 0,
            "final_message": "Situation:\nA verified relationship.\n\n"
                             "Possible action:\nWatch the next observed interval.\n\n"
                             "Not financial advice." if decision else None,
            "llm_calls": 1,
            "provider_attempts": 2,
            "total_tokens": 800,
            "rate_limit_attempts": 1,
        },
    }


def _dataset(*cases):
    rows = list(cases)
    return {
        "schema_version": 1,
        "version": "test-only-never-production",
        "provenance": "real_market_sanitized",
        "dataset_sha256": digest(rows),
        "cases": rows,
    }


def _write(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _labels(dataset, evaluator_id, labels):
    return {
        "dataset_sha256": dataset["dataset_sha256"],
        "evaluator_id": evaluator_id,
        "labels": labels,
    }


def test_versioned_bootstrap_has_no_fabricated_market_events():
    from pathlib import Path

    path = Path(__file__).parent / "fixtures/event_alert_benchmark/v1.json"
    dataset = load_frozen(path)
    scored = report(dataset)
    assert scored["real_market_usable_cases"] == 0
    assert scored["overall"]["event_level"]["precision"] is None
    assert scored["overall"]["event_level"]["recall"] is None
    assert scored["overall"]["technical_observations"]["total_tokens"]["total"] is None
    assert set(scored["by_symbol"]) == {"BTC", "ETH", "GRAM", "SOL"}


def test_blind_packets_hide_bot_decision_and_delivery_evidence():
    dataset = _dataset(_case("btc-case-001"))
    significance = blind_packet(dataset, "significance")["cases"][0]
    assert "observed" not in significance
    assert "final_message" not in significance
    assert "should_alert" not in json.dumps(significance)
    message = blind_packet(dataset, "message")["cases"][0]
    assert "Not financial advice." in message["final_message"]
    assert "delivered_count" not in message
    assert "should_alert" not in message


def test_frozen_hash_rejects_modified_market_facts(tmp_path):
    dataset = _dataset(_case("btc-case-001"))
    path = _write(tmp_path / "cases.json", dataset)
    assert len(load_frozen(path)["cases"]) == 1
    dataset["cases"][0]["input"]["market"]["chg_window_percent"] = 0.17
    with pytest.raises(ValueError, match="integrity"):
        load_frozen(_write(path, dataset))


@pytest.mark.parametrize("private_value", [
    {"telegram_chat_id": 12345678},
    {"news": [{"title": "Reach me at person@example.com"}]},
    {"news": [{"link": "https://t.me/private_account"}]},
])
def test_private_identifiers_cannot_enter_frozen_inputs(tmp_path, private_value):
    case = _case("btc-case-001")
    case["input"].update(private_value)
    case["input_sha256"] = digest(case["input"])
    with pytest.raises(ValueError, match="private|forbidden|contact"):
        load_frozen(_write(tmp_path / "private.json", _dataset(case)))


def test_independent_disagreement_requires_explicit_reconciliation(tmp_path):
    dataset = _dataset(_case("btc-case-001"), _case("sol-case-001", "SOL", False))
    a = _write(tmp_path / "a.json", _labels(dataset, "human-a", [
        {"id": "btc-case-001", "warrant": "no_alert", "useful": False, "factual": True},
        {"id": "sol-case-001", "warrant": "alert", "useful": None, "factual": None},
    ]))
    b = _write(tmp_path / "b.json", _labels(dataset, "human-b", [
        {"id": "btc-case-001", "warrant": "alert", "useful": False, "factual": True},
        {"id": "sol-case-001", "warrant": "alert", "useful": None, "factual": None},
    ]))
    labels, agreement = reconcile(dataset, a, b)
    assert agreement["reviewed_by_both"] == 2
    assert agreement["unresolved_disagreements"] == 1
    assert labels["btc-case-001"]["warrant"] is None
    assert report(dataset, labels)["overall"]["event_level"]["scored_cases"] == 1

    resolution = _write(tmp_path / "resolve.json", _labels(dataset, "human-judge", [
        {"id": "btc-case-001", "warrant": "no_alert", "useful": False, "factual": True},
    ]))
    labels, agreement = reconcile(dataset, a, b, resolution)
    scored = report(dataset, labels, agreement)["overall"]
    assert agreement["unresolved_disagreements"] == 0
    assert scored["event_level"]["fp"] == 1
    assert scored["event_level"]["fn"] == 1
    assert scored["event_level"]["precision"] == 0
    assert scored["event_level"]["recall"] == 0
    assert scored["recipient_eligible_weighted"]["fp"] == 12
    assert scored["final_text"]["usefulness_rate"] == 0
    assert scored["final_text"]["factual_errors"] == 0


def test_evaluator_cannot_be_duplicated_under_same_identity(tmp_path):
    dataset = _dataset(_case("btc-case-001"))
    x = _write(tmp_path / "a.json", _labels(dataset, "one-model-twice", [
        {"id": "btc-case-001", "warrant": "alert"},
    ]))
    with pytest.raises(ValueError, match="Two different"):
        reconcile(dataset, x, x)


def test_ambiguous_and_missing_eligibility_are_not_false_negatives():
    first = _case("btc-case-001")
    first["observed"].pop("eligible_recipients")
    second = _case("sol-case-001", "SOL", False)
    dataset = _dataset(first, second)
    labels = {
        "btc-case-001": {"warrant": "ambiguous"},
        "sol-case-001": {"warrant": "alert"},
    }
    scored = report(dataset, labels)["overall"]
    assert scored["event_level"]["ambiguous_cases"] == 1
    assert scored["event_level"]["fn"] == 1
    assert scored["event_level"]["recall"] == 0
    assert scored["recipient_eligible_weighted"]["scored_cases"] == 1


def test_pinned_candidate_run_never_inherits_baseline_deliveries(tmp_path):
    case = _case("btc-case-001")
    dataset = _dataset(case)
    run = _write(tmp_path / "run.json", {
        "dataset_sha256": dataset["dataset_sha256"],
        "model": "test-offline-model",
        "config_fingerprint": "test-frozen-config-sha",
        "run_name": "test-only",
        "results": [{
            "id": case["id"],
            "input_sha256": case["input_sha256"],
            "status": "valid",
            "should_alert": False,
            "llm_calls": 1,
            "total_tokens": 50,
        }],
    })
    compared = compare_recorded_run(dataset, run, {"btc-case-001": {"warrant": "alert"}})
    assert compared["paired_decision_changes"] == 1
    assert compared["baseline"]["overall"]["event_level"]["tp"] == 1
    assert compared["candidate"]["overall"]["event_level"]["fn"] == 1
    assert compared["candidate"]["overall"]["technical_observations"]["delivered_count"][
        "total"
    ] is None


def test_failed_candidate_attempt_not_scored_as_no_alert(tmp_path):
    case = _case("btc-case-001")
    dataset = _dataset(case)
    run = _write(tmp_path / "run.json", {
        "dataset_sha256": dataset["dataset_sha256"],
        "model": "test-model",
        "config_fingerprint": "test-config",
        "results": [{
            "id": case["id"],
            "input_sha256": case["input_sha256"],
            "status": "schema_error",
            "should_alert": None,
            "total_tokens": 121,
        }],
    })
    compared = compare_recorded_run(dataset, run, {"btc-case-001": {"warrant": "alert"}})
    candidate = compared["candidate"]["overall"]
    assert candidate["event_level"]["fn"] == 0
    assert candidate["event_level"]["scored_cases"] == 0
    assert candidate["technical_observations"]["total_tokens"]["total"] == 121


def test_no_duplicate_cases_or_synthetic_provenance(tmp_path):
    case = _case("btc-case-001")
    duplicate = deepcopy(case)
    with pytest.raises(ValueError, match="Duplicate"):
        load_frozen(_write(tmp_path / "cases.json", _dataset(case, duplicate)))
    dataset = _dataset(case)
    dataset["provenance"] = "synthetic"
    with pytest.raises(ValueError, match="real-market"):
        load_frozen(_write(tmp_path / "cases.json", dataset))
