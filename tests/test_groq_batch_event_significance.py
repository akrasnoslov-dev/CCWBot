"""Offline Groq batch preparation, import and cost-approval safety tests."""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy

import pytest

from scripts import groq_batch_event_significance as batch
from scripts import live_event_significance_benchmark as live
from scripts.event_alert_benchmark import digest


def frozen():
    cases = []
    for i, (symbol, _label) in enumerate((
        ("BTC", "alert"), ("ETH", "no_alert"), ("GRAM", "alert"),
        ("SOL", "no_alert"), ("BTC", "ambiguous"),
    )):
        payload = {
            "symbol": symbol, "market": {
                "price": 100,
                "snapshots": [{"m": -180, "p": 99}, {"m": 0, "p": 100}],
                "chg_window_percent": 1,
                "analysed_window_minutes": 180,
            },
        }
        cases.append({
            "id": f"case_{i}", "symbol": symbol,
            "input": payload, "input_sha256": digest(payload),
            "observed": {"should_alert": False},
        })
    labels = {case["id"]: x for case, x in zip(
        cases, ("alert", "no_alert", "alert", "no_alert", "ambiguous"),
        strict=True,
    )}
    return {"cases": cases, "dataset_sha256": digest(cases)}, labels


def state(dataset):
    return {
        "dataset_sha256": dataset["dataset_sha256"],
        "attempted_requests": 227,
        "runs": {
            "market_signal_path": [
                {
                    "id": "case_0",
                    "input_sha256": dataset["cases"][0]["input_sha256"],
                    "status": "valid", "should_alert": True,
                },
                {
                    "id": "case_2",
                    "input_sha256": dataset["cases"][2]["input_sha256"],
                    "status": "provider_error", "http_status": 429,
                },
            ],
        },
    }


def test_pending_only_decisive_and_preserves_existing_valid_results():
    dataset, labels = frozen()
    pending = batch.pending_batch_cases(dataset, labels, state(dataset))
    assert [x["id"] for x in pending] == ["case_1", "case_2", "case_3"]
    source = state(dataset)
    source["runs"]["market_signal_path"][1]["http_status"] = 500
    with pytest.raises(ValueError, match="Unrecognized prior failure"):
        batch.pending_batch_cases(dataset, labels, source)


def test_batch_payload_matches_individual_groq_prompt_and_is_strict():
    dataset, labels = frozen()
    pending = batch.pending_batch_cases(dataset, labels, state(dataset))
    _, _, _, schema = batch.active_configuration()
    entries, manifest = batch.build_batch_entries(
        pending, model="openai/gpt-oss-120b", effort="medium",
        max_tokens=6300, schema=schema,
    )
    assert len(entries) == len(manifest) == 3
    assert len({x["custom_id"] for x in entries}) == len(entries)
    assert all(row["method"] == "POST" for row in entries)
    assert all(row["url"] == "/v1/chat/completions" for row in entries)
    assert all(row["body"]["temperature"] == 0 for row in entries)
    assert all(row["body"]["response_format"]["json_schema"]["strict"] for row in entries)
    assert all(row["body"]["reasoning_effort"] == "medium" for row in entries)
    assert all("case_" not in entry["custom_id"] for entry in entries)
    assert all("system" == entry["body"]["messages"][0]["role"] for entry in entries)


def test_import_batch_responses_can_retry_only_recorded_429():
    dataset, _ = frozen()
    current = state(dataset)
    original = deepcopy(current["runs"]["market_signal_path"][0])
    _, manifest = batch.build_batch_entries(
        [dataset["cases"][1], dataset["cases"][2]],
        model="openai/gpt-oss-120b", effort="medium",
        max_tokens=6300, schema={},
    )
    opaque_by_case = {x["id"]: key for key, x in manifest.items()}
    good = {
        "custom_id": opaque_by_case["case_2"],
        "response": {
            "status_code": 200,
            "body": {
                "choices": [{"message": {"content": json.dumps({
                    "symbol": "GRAM", "materiality": "routine",
                    "novelty": "unclear", "should_alert": False,
                    "reason_code": "routine_move", "confidence": "high",
                })}}],
                "usage": {"total_tokens": 2000},
            },
        },
    }
    result = batch._sanitized_answer(good, case=manifest[good["custom_id"]])
    assert result["status"] == "valid"
    completed, failures = batch.import_output(
        entries=json.dumps(good),
        manifest={"cases": manifest}, state=current,
    )
    assert (completed, failures) == (1, 0)
    assert len(current["runs"]["market_signal_path"]) == 2
    assert current["runs"]["market_signal_path"][0] == original
    assert current["runs"]["market_signal_path"][1]["status"] == "valid"
    with pytest.raises(ValueError, match="rate-limit failure"):
        batch.import_output(
            entries=json.dumps(good), manifest={"cases": manifest},
            state=current,
        )


def test_import_rejects_duplicate_or_unmapped_custom_ids_without_leaking():
    dataset, _ = frozen()
    current = state(dataset)
    _, mapping = batch.build_batch_entries(
        [dataset["cases"][1]], model="model", effort=None,
        max_tokens=6300, schema={},
    )
    opaque = next(iter(mapping))
    error = {"custom_id": opaque, "response": {"status_code": 500}}
    with pytest.raises(ValueError, match="duplicated"):
        batch.import_output(
            entries=json.dumps(error) + "\n" + json.dumps(error),
            manifest={"cases": mapping}, state=deepcopy(current),
        )
    with pytest.raises(ValueError, match="Unknown"):
        batch.import_output(
            entries=json.dumps({"custom_id": "foreign-id"}),
            manifest={"cases": mapping}, state=deepcopy(current),
        )


def test_prepare_is_local_and_never_calls_groq(tmp_path, monkeypatch):
    dataset, labels = frozen()
    out = tmp_path / "merged_pilots_private"
    out.mkdir(parents=True)
    model, effort, max_tokens, _schema = batch.active_configuration()
    configs = {
        v: live.fingerprint(v, model, max_tokens, effort) for v in live.VARIANTS
    }
    ledger = live.load_state(out / "replay_state.json", dataset["dataset_sha256"], model, configs)
    ledger["attempted_requests"] = 227
    ledger["runs"]["market_signal_path"] = state(dataset)["runs"]["market_signal_path"]
    live.save_state(out / "replay_state.json", ledger)
    monkeypatch.setattr(batch, "load_inputs", lambda _directory: (dataset, labels))
    monkeypatch.setattr(
        batch, "authenticated_client",
        lambda: (_ for _ in ()).throw(AssertionError("No network in --prepare")),
    )
    summary = batch.prepare(directory=tmp_path)
    assert summary["pending"] == 3
    assert summary["previous_attempts"] == 227
    document = (out / "groq_batch_input.jsonl").read_text(encoding="utf-8")
    assert len(document.splitlines()) == 3
    assert hashlib.sha256((out / "groq_batch_input.jsonl").read_bytes()).hexdigest() == json.loads(
        (out / "groq_batch_manifest.json").read_text(encoding="utf-8")
    )["input_sha256"]
    assert not any("case_" in json.loads(line)["custom_id"] for line in document.splitlines())
    assert not any("GROQ_API_KEY" in line for line in document.splitlines())
    assert batch.prepare(directory=tmp_path)["pending"] == 3


def test_submit_is_explicitly_billed_and_denied_without_approval(tmp_path):
    with pytest.raises(PermissionError, match="explicitly approve"):
        batch.submit(directory=tmp_path, explicit_billed_approval=False)

def test_inaccessible_free_plan_never_uploads_or_creates_batch(tmp_path, monkeypatch):
    dataset, labels = frozen()
    out = tmp_path / "merged_pilots_private"
    out.mkdir(parents=True)
    model, effort, max_tokens, _schema = batch.active_configuration()
    configs = {
        v: live.fingerprint(v, model, max_tokens, effort) for v in live.VARIANTS
    }
    ledger = live.load_state(out / "replay_state.json", dataset["dataset_sha256"], model, configs)
    ledger["attempted_requests"] = 227
    ledger["runs"]["market_signal_path"] = state(dataset)["runs"]["market_signal_path"]
    live.save_state(out / "replay_state.json", ledger)
    monkeypatch.setattr(batch, "load_inputs", lambda _directory: (dataset, labels))
    assert batch.prepare(directory=tmp_path)["pending"] == 3

    class AccessDenied:
        status_code = 403

        def json(self):
            return {"error": {"type": "permissions_error", "code": "not_available_for_plan"}}

    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def get(self, path, **_kwargs):
            assert path == "/batches"
            return AccessDenied()

        def post(self, *_args, **_kwargs):
            raise AssertionError("Must never upload on a free account")

    monkeypatch.setattr(batch, "authenticated_client", Client)
    result = batch.submit(directory=tmp_path, explicit_billed_approval=True)
    assert result == {
        "status": "batch_not_available", "http_status": 403,
        "error_code": "not_available_for_plan",
    }
    assert json.loads(
        (out / "replay_state.json").read_text(encoding="utf-8")
    )["attempted_requests"] == 227
    assert json.loads(
        (out / "groq_batch_status.json").read_text(encoding="utf-8")
    )["phase"] == "denied"


def test_prepared_batch_rejects_changes_to_ledger(tmp_path, monkeypatch):
    dataset, labels = frozen()
    out = tmp_path / "merged_pilots_private"
    out.mkdir(parents=True)
    model, effort, max_tokens, _schema = batch.active_configuration()
    configs = {
        v: live.fingerprint(v, model, max_tokens, effort) for v in live.VARIANTS
    }
    ledger = live.load_state(out / "replay_state.json", dataset["dataset_sha256"], model, configs)
    ledger["attempted_requests"] = 227
    ledger["runs"]["market_signal_path"] = state(dataset)["runs"]["market_signal_path"]
    live.save_state(out / "replay_state.json", ledger)
    monkeypatch.setattr(batch, "load_inputs", lambda _directory: (dataset, labels))
    assert batch.prepare(directory=tmp_path)["pending"] == 3
    ledger["attempted_requests"] = 228
    live.save_state(out / "replay_state.json", ledger)
    with pytest.raises(ValueError, match="replay changed"):
        batch.submit(directory=tmp_path, explicit_billed_approval=True)

def test_collect_imports_entire_offline_batch_and_scores_full_reference(
    tmp_path, monkeypatch,
):
    dataset, labels = frozen()
    out = tmp_path / "merged_pilots_private"
    out.mkdir(parents=True)
    model, effort, max_tokens, _schema = batch.active_configuration()
    configs = {
        v: live.fingerprint(v, model, max_tokens, effort) for v in live.VARIANTS
    }
    ledger = live.load_state(
        out / "replay_state.json", dataset["dataset_sha256"], model, configs,
    )
    ledger["attempted_requests"] = 227
    ledger["runs"]["market_signal_path"] = state(dataset)["runs"]["market_signal_path"]
    live.save_state(out / "replay_state.json", ledger)
    monkeypatch.setattr(batch, "load_inputs", lambda _directory: (dataset, labels))
    assert batch.prepare(directory=tmp_path)["pending"] == 3
    metadata = json.loads(
        (out / "groq_batch_status.json").read_text(encoding="utf-8")
    )
    metadata.update(phase="submitted", batch_id="batch_mock")
    batch.private_write(out / "groq_batch_status.json", metadata)
    ledger["attempted_requests"] += 3
    live.save_state(out / "replay_state.json", ledger)
    manifest = json.loads(
        (out / "groq_batch_manifest.json").read_text(encoding="utf-8")
    )
    output = []
    for key, item in manifest["cases"].items():
        should = labels[item["id"]] == "alert"
        output.append({
            "custom_id": key,
            "response": {
                "status_code": 200,
                "body": {
                    "choices": [{"message": {"content": json.dumps({
                        "symbol": item["symbol"],
                        "should_alert": should,
                        "materiality": "material" if should else "routine",
                        "novelty": "new" if should else "unclear",
                        "reason_code": "fast_move" if should else "routine_move",
                        "confidence": "medium",
                    })}}],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
                },
            },
        })

    class Response:
        status_code = 200

        def __init__(self, *, body=None, text=""):
            self.body, self.text = body, text

        def json(self):
            return self.body

        def raise_for_status(self):
            return None

    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def get(self, path):
            if path == "/batches/batch_mock":
                return Response(body={
                    "status": "completed", "output_file_id": "file_results",
                    "error_file_id": None,
                })
            if path == "/files/file_results/content":
                return Response(text="\n".join(json.dumps(row) for row in reversed(output)))
            raise AssertionError(f"Unexpected provider endpoint {path}")

    monkeypatch.setattr(batch, "authenticated_client", Client)
    result = batch.collect(directory=tmp_path)
    assert result["decisive_valid"] == 4
    assert result["decisive_total"] == 4
    assert result["quality_gates_met"] is True
    assert result["precision"] == result["recall"] == 1.0
    assert result["imported_valid"] == 3
    assert result["not_returned"] == 0
    after = json.loads((out / "replay_state.json").read_text(encoding="utf-8"))
    assert after["attempted_requests"] == 230
    assert len(after["runs"]["market_signal_path"]) == 4
    assert all(x["status"] == "valid" for x in after["runs"]["market_signal_path"])
    with pytest.raises(RuntimeError, match="uncollected"):
        batch.collect(directory=tmp_path)
