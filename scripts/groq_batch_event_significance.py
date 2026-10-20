"""One-shot Groq Batch API replay of all remaining reviewer-decisive events.

Private JSONL and metadata never leave the ignored report directory except
for an explicitly authorised provider upload. Batch processing is independent
of a Windows PC after submission. Submit is potentially billed: requires
--approve-billed-batch. No Telegram messages, deployment or production changes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from bot.alerting.event_analysis import validate_event_significance_output  # noqa: E402
from bot.services import ai_agent_groq  # noqa: E402
from bot.services.llm import config  # noqa: E402
from scripts.event_alert_benchmark import load_frozen  # noqa: E402
from scripts.event_significance_candidates import candidate_prompt  # noqa: E402
from scripts.live_event_significance_benchmark import (  # noqa: E402
    MAX_APPROVED_CALLS,
    VARIANTS,
    export_recorded_runs,
    fingerprint,
    load_reviewer_a,
    load_state,
    record_replay_result,
    save_state,
)
from scripts.score_event_significance_ab import (  # noqa: E402
    score,
    with_historical_baseline,
)

PRIVATE = ROOT / "reports" / "event-alert-review-20261016"
OUT = PRIVATE / "merged_pilots_private"
VARIANT = "market_signal_path"
API_BASE = "https://api.groq.com/openai/v1"
ENDPOINT = "/v1/chat/completions"
ACCEPTED_STATUSES = frozenset({
    "validating", "in_progress", "finalizing", "completed",
    "failed", "expired", "cancelling", "cancelled",
})
TERMINAL = frozenset({"completed", "failed", "expired", "cancelled"})


def private_write(path: Path, document: dict) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def load_inputs(directory: Path = PRIVATE) -> tuple[dict, dict]:
    dataset = load_frozen(directory / "v2_private_sanitized.json")
    labels = load_reviewer_a(
        directory / "reviewer_A_significance_for_pr1.json", dataset,
    )
    return dataset, labels


def active_configuration() -> tuple[str, str | None, int, dict]:
    load_dotenv(ROOT / ".env")
    model = config.model_for("groq", "event_analysis")
    effort = config.reasoning_effort_for(model, "event_analysis")
    max_tokens = config.effective_max_tokens_for(
        call_type="event_analysis", provider="groq", model=model,
    )
    schema = {
        "type": "json_schema",
        "json_schema": {
            "name": "event_significance", "strict": True,
            "schema": ai_agent_groq._EVENT_SIGNIFICANCE_JSON_SCHEMA,
        },
    }
    return model, effort, max_tokens, schema


def pending_batch_cases(dataset: dict, labels: dict, ledger: dict) -> list[dict]:
    existing = {r["id"]: r for r in ledger["runs"][VARIANT]}
    pending = []
    for case in dataset["cases"]:
        if labels[case["id"]] == "ambiguous":
            continue
        prior = existing.get(case["id"])
        if prior and prior["input_sha256"] != case["input_sha256"]:
            raise ValueError("Frozen input hash changed")
        if prior and prior["status"] == "valid":
            continue
        if prior and not (
            prior.get("status") == "provider_error"
            and prior.get("http_status") == 429
        ):
            raise ValueError("Unrecognized prior failure; manual review needed")
        pending.append(case)
    return pending


def build_batch_entries(
    pending: list[dict], *, model: str, effort: str | None,
    max_tokens: int, schema: dict,
) -> tuple[list[dict], dict]:
    entries = []
    manifest = {}
    for case in pending:
        opaque_id = hashlib.sha256(
            (VARIANT + ":" + case["id"]).encode("utf-8")
        ).hexdigest()[:32]
        if opaque_id in manifest:
            raise ValueError("Batch custom_id collision")
        manifest[opaque_id] = {
            "id": case["id"],
            "input_sha256": case["input_sha256"],
            "symbol": case["symbol"],
        }
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": ai_agent_groq.SYSTEM_PROMPT},
                {"role": "user", "content": candidate_prompt(case["input"], VARIANT)},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.0,
            "response_format": schema,
        }
        if effort is not None:
            body["reasoning_effort"] = effort
        entries.append({
            "custom_id": opaque_id, "method": "POST",
            "url": ENDPOINT, "body": body,
        })
    return entries, manifest


def prepare(*, directory: Path = PRIVATE) -> dict:
    out = directory / "merged_pilots_private"
    out.mkdir(parents=True, exist_ok=True)
    status_file = out / "groq_batch_status.json"
    if status_file.exists():
        saved = json.loads(status_file.read_text(encoding="utf-8"))
        if saved.get("phase") not in ("prepared", "denied"):
            raise RuntimeError("Batch already submitted/reserved; do not submit twice")
    dataset, labels = load_inputs(directory)
    model, effort, max_tokens, schema = active_configuration()
    configs = {v: fingerprint(v, model, max_tokens, effort) for v in VARIANTS}
    state = load_state(out / "replay_state.json", dataset["dataset_sha256"], model, configs)
    pending = pending_batch_cases(dataset, labels, state)
    if state["attempted_requests"] + len(pending) > MAX_APPROVED_CALLS:
        raise RuntimeError("Combined sync and batch would exceed 600 approved decisions")
    if len(pending) == 0:
        return {"status": "already_fully_scored", "pending": 0}
    entries, manifest = build_batch_entries(
        pending, model=model, effort=effort,
        max_tokens=max_tokens, schema=schema,
    )
    jsonl = out / "groq_batch_input.jsonl"
    jsonl.write_text(
        "".join(json.dumps(entry, separators=(",", ":")) + "\n" for entry in entries),
        encoding="utf-8",
    )
    digest = hashlib.sha256(jsonl.read_bytes()).hexdigest()
    private_write(out / "groq_batch_manifest.json", {
        "dataset_sha256": dataset["dataset_sha256"],
        "model": model,
        "variant": VARIANT,
        "variant_fingerprint": configs[VARIANT],
        "input_sha256": digest,
        "cases": manifest,
    })
    private_write(status_file, {
        "phase": "prepared", "pending": len(pending),
        "previous_attempts": state["attempted_requests"],
        "input_sha256": digest, "batch_id": None,
    })
    return {
        "status": "prepared", "pending": len(pending),
        "previous_attempts": state["attempted_requests"],
        "total_decisive": sum(v != "ambiguous" for v in labels.values()),
        "requires_billed_batch_approval": True,
    }


def authenticated_client() -> httpx.Client:
    load_dotenv(ROOT / ".env")
    key = os.getenv("GROQ_BENCHMARK_BATCH_API_KEY") or os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("No Groq API key is configured")
    return httpx.Client(
        base_url=API_BASE,
        headers={"Authorization": f"Bearer {key}"},
        timeout=30,
        follow_redirects=False,
    )


def safe_provider_status(response: httpx.Response) -> dict:
    try:
        data = response.json()
    except (ValueError, TypeError):
        data = {}
    error = data.get("error") if isinstance(data, dict) else None
    return {
        "http_status": response.status_code,
        "error_code": (
            error.get("code") if isinstance(error, dict)
            and error.get("code") in (
                "not_available_for_plan", "permission_denied", "insufficient_quota"
            ) else None
        ),
    }


def check_access() -> dict:
    with authenticated_client() as client:
        response = client.get("/batches", params={"limit": 1})
        if response.status_code == 200:
            return {"batch_available": True}
        return {"batch_available": False, **safe_provider_status(response)}


def submit(*, directory: Path = PRIVATE, explicit_billed_approval: bool) -> dict:
    if not explicit_billed_approval:
        raise PermissionError("Owner must explicitly approve potentially billed batch")
    out = directory / "merged_pilots_private"
    status_file = out / "groq_batch_status.json"
    saved = json.loads(status_file.read_text(encoding="utf-8"))
    if saved.get("phase") != "prepared":
        raise RuntimeError("Batch cannot be resubmitted")
    jsonl = out / "groq_batch_input.jsonl"
    if hashlib.sha256(jsonl.read_bytes()).hexdigest() != saved["input_sha256"]:
        raise ValueError("Batch JSONL modified after preparation")
    dataset, labels = load_inputs(directory)
    model, effort, max_tokens, _schema = active_configuration()
    configs = {v: fingerprint(v, model, max_tokens, effort) for v in VARIANTS}
    ledger_path = out / "replay_state.json"
    state = load_state(ledger_path, dataset["dataset_sha256"], model, configs)
    pending = pending_batch_cases(dataset, labels, state)
    if (
        len(pending) != saved["pending"]
        or state["attempted_requests"] != saved["previous_attempts"]
    ):
        raise ValueError("Recorded replay changed; batch must be regenerated")
    if state["attempted_requests"] + len(pending) > MAX_APPROVED_CALLS:
        raise RuntimeError("Approved 600 request ceiling would be exceeded")
    with authenticated_client() as client:
        access = client.get("/batches", params={"limit": 1})
        if access.status_code != 200:
            saved["phase"] = "denied"
            private_write(status_file, saved)
            return {"status": "batch_not_available", **safe_provider_status(access)}
        # Uploading the file isn't the provider workload; batch creation is.
        with jsonl.open("rb") as handle:
            upload = client.post(
                "/files", data={"purpose": "batch"},
                files={"file": ("event_significance.jsonl", handle, "application/jsonl")},
            )
        if upload.status_code not in (200, 201):
            return {"status": "upload_failed", **safe_provider_status(upload)}
        file_id = upload.json().get("id")
        if not isinstance(file_id, str) or not file_id.startswith("file_"):
            raise ValueError("Provider did not return a file ID")
        # Reserve the entire batch budget BEFORE create. Unknown POST outcomes
        # are never automatically reissued, preventing duplicate paid runs.
        saved.update(phase="creating", input_file_id=file_id)
        private_write(status_file, saved)
        state["attempted_requests"] += len(pending)
        save_state(ledger_path, state)
        result = client.post(
            "/batches",
            json={
                "input_file_id": file_id, "endpoint": ENDPOINT,
                "completion_window": "24h",
            },
        )
        if result.status_code not in (200, 201):
            saved["phase"] = "creation_failed_manual_review"
            private_write(status_file, saved)
            return {"status": "batch_creation_failed", **safe_provider_status(result)}
        obj = result.json()
        batch_id = obj.get("id")
        if not isinstance(batch_id, str) or not batch_id.startswith("batch_"):
            raise ValueError("Batch creation response did not have batch_id")
        saved.update(phase="submitted", batch_id=batch_id)
        private_write(status_file, saved)
        return {"status": "submitted", "requests": len(pending)}


def batch_status(*, directory: Path = PRIVATE) -> dict:
    saved = json.loads(
        (directory / "merged_pilots_private" / "groq_batch_status.json")
        .read_text(encoding="utf-8")
    )
    if saved.get("phase") not in ("submitted", "collected", "partial"):
        return {"status": saved.get("phase"), "batch_available": False}
    with authenticated_client() as client:
        response = client.get("/batches/" + saved["batch_id"])
        if response.status_code != 200:
            return {"status": "status_check_failed", **safe_provider_status(response)}
        meta = response.json()
        return {
            "status": meta.get("status"),
            "counts": meta.get("request_counts"),
        }


def _sanitized_answer(raw: dict, *, case: dict) -> dict:
    row = {"id": case["id"], "input_sha256": case["input_sha256"]}
    response = raw.get("response") or {}
    if raw.get("error") or response.get("status_code") != 200:
        row.update(status="provider_error", error_type="BatchRequestFailed")
        code = response.get("status_code")
        if type(code) is int:
            row["http_status"] = code
        return row
    body = response.get("body") or {}
    usage = body.get("usage") or {}
    for key in ("total_tokens", "prompt_tokens", "completion_tokens"):
        value = usage.get(key)
        if type(value) is int and value >= 0:
            row[key] = value
    try:
        message = body["choices"][0]["message"]["content"]
        parsed = json.loads(message)
        result = validate_event_significance_output(
            parsed, expected_symbol=case["symbol"],
        )
        row.update(
            status="valid",
            should_alert=result.should_alert,
            materiality=result.materiality,
            novelty=result.novelty,
            reason_code=result.reason_code,
        )
    except (KeyError, IndexError, TypeError, ValueError):
        row.update(status="schema_error", error_type="InvalidBatchResponse")
    return row


def import_output(
    *, entries: str, manifest: dict, state: dict,
) -> tuple[int, int]:
    """Exact opaque-ID reconciliation; no raw responses, reasons or news are stored."""
    mapped = manifest["cases"]
    completed = 0
    failures = 0
    seen = set()
    for line in entries.splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        custom_id = raw.get("custom_id")
        if custom_id not in mapped or custom_id in seen:
            raise ValueError("Unknown or duplicated result custom_id")
        seen.add(custom_id)
        row = _sanitized_answer(raw, case=mapped[custom_id])
        previous = next(
            (item for item in state["runs"][VARIANT] if item["id"] == row["id"]),
            None,
        )
        retrying = previous is not None
        record_replay_result(state, VARIANT, row, retrying=retrying)
        if row["status"] == "valid":
            completed += 1
        else:
            failures += 1
    return completed, failures


def collect(*, directory: Path = PRIVATE) -> dict:
    out = directory / "merged_pilots_private"
    status_file = out / "groq_batch_status.json"
    saved = json.loads(status_file.read_text(encoding="utf-8"))
    if saved.get("phase") != "submitted":
        raise RuntimeError("Only an uncollected submitted batch can be imported")
    manifest = json.loads(
        (out / "groq_batch_manifest.json").read_text(encoding="utf-8")
    )
    with authenticated_client() as client:
        response = client.get("/batches/" + saved["batch_id"])
        response.raise_for_status()
        info = response.json()
        if info.get("status") not in TERMINAL:
            return {"status": info.get("status"), "ready": False}
        output_file_id = info.get("output_file_id")
        error_file_id = info.get("error_file_id")
        success_lines = ""
        error_lines = ""
        if output_file_id:
            answer = client.get("/files/" + output_file_id + "/content")
            answer.raise_for_status()
            success_lines = answer.text
        if error_file_id:
            failed = client.get("/files/" + error_file_id + "/content")
            failed.raise_for_status()
            error_lines = failed.text
    model, effort, max_tokens, _schema = active_configuration()
    dataset, labels = load_inputs(directory)
    configs = {v: fingerprint(v, model, max_tokens, effort) for v in VARIANTS}
    ledger_path = out / "replay_state.json"
    state = load_state(ledger_path, dataset["dataset_sha256"], model, configs)
    if manifest["dataset_sha256"] != state["dataset_sha256"]:
        raise ValueError("Frozen reference no longer matches batch")
    if manifest["variant_fingerprint"] != state["fingerprints"][VARIANT]:
        raise ValueError("Prompt changed after batch submission")
    # Never append duplicates on restarts, including incomplete imports.
    completed, failures = import_output(
        entries=success_lines + "\n" + error_lines,
        manifest=manifest, state=state,
    )
    save_state(ledger_path, state)
    export_recorded_runs(out, state)
    report = score(
        dataset, labels, with_historical_baseline(dataset, state),
        variants=("historical", VARIANT),
    )
    candidate = report["variants"][VARIANT]
    decisive_total = sum(label != "ambiguous" for label in labels.values())
    fully_scored = candidate["valid_answers"] == decisive_total
    gates_met = bool(
        fully_scored and candidate["precision"] is not None
        and candidate["precision"] >= 0.85
        and candidate["recall"] is not None
        and candidate["recall"] >= 0.90
    )
    summary = {
        "status": info.get("status"),
        "imported_valid": completed, "imported_failed": failures,
        "not_returned": len(manifest["cases"]) - completed - failures,
        "decisive_valid": candidate["valid_answers"],
        "decisive_total": decisive_total,
        "precision": candidate["precision"] if fully_scored else None,
        "recall": candidate["recall"] if fully_scored else None,
        "quality_gates_met": gates_met,
    }
    saved.update(phase="collected", imported=completed, failures=failures)
    private_write(status_file, saved)
    private_write(out / "groq_batch_quality_summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--prepare", action="store_true")
    modes.add_argument("--check-access", action="store_true")
    modes.add_argument("--submit", action="store_true")
    modes.add_argument("--status", action="store_true")
    modes.add_argument("--collect", action="store_true")
    parser.add_argument("--approve-billed-batch", action="store_true")
    args = parser.parse_args()
    if args.prepare:
        result = prepare()
    elif args.check_access:
        result = check_access()
    elif args.submit:
        result = submit(explicit_billed_approval=args.approve_billed_batch)
    elif args.status:
        result = batch_status()
    else:
        result = collect()
    print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
