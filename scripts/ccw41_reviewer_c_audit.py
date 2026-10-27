"""Offline blinded Reviewer-C preparation, import, and comparison for CCW-41.

The tool makes no network/provider calls. Private case data and reviewer records stay in a
caller-selected gitignored directory. Tracked fixtures and tests contain synthetic data only.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import random
import re
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.event_alert_benchmark import WARRANT, _read_evaluations, load_frozen
except ModuleNotFoundError:  # Direct `python scripts/...` execution.
    from event_alert_benchmark import WARRANT, _read_evaluations, load_frozen

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_ROOT = ROOT / "benchmarks" / "ccw41-v1"
RUBRIC_PATH = PROTOCOL_ROOT / "reviewer-c-rubric.md"
SCHEMA_PATH = PROTOCOL_ROOT / "reviewer-c-result.schema.json"
CANONICAL_DATASET_SHA256 = "ed126380369014e6522cee49009b880cf0350aa7565269d50641c3f1bbdc3bee"
EXPECTED_SYMBOLS = {"BTC": 50, "ETH": 50, "GRAM": 50, "SOL": 50}
EXPECTED_A = {"alert": 41, "no_alert": 112, "ambiguous": 47}
EXPECTED_AB_CONFLICTS = 99
FROZEN_RUBRIC_SHA256 = "2615ebb4d4bd0fd53f41f0fe4db260f092a2e7ea7d430e857d9bfbaf102027b0"
FROZEN_SCHEMA_SHA256 = "e2acbfdc878d71071fcf95e93017035200860e4839dac2941a1bd84b4334cc40"
FROZEN_PROMPT_SHA256 = "d5169b9a87442da61807cbb9841c865b3c134d9df3b79485c24e56d4749199c2"
CONFIDENCE = {"low", "medium", "high"}
RUN_METADATA_FIELDS = {
    "provider", "model", "reasoning_effort", "interface", "data_transfer_approval",
    "model_identity_verification",
}


def _require_gitignored_private_dir(private_dir: Path) -> Path:
    resolved = private_dir.resolve()
    reports_root = (ROOT / "reports" / "event-alert-review-20261016").resolve()
    if reports_root not in resolved.parents:
        raise ValueError(
            "Private CCW-41 artifacts must stay under the canonical gitignored reports directory"
        )
    return resolved


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _write_new_or_same(path: Path, value: object) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != payload:
            raise ValueError(f"Refusing to overwrite changed frozen artifact: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8", newline="\n")


def _write_text_new_or_same(path: Path, text: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise ValueError(f"Refusing to overwrite changed frozen artifact: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _opaque_id(seed: str, dataset_sha256: str, source_id: str) -> str:
    material = f"{seed}\0{dataset_sha256}\0{source_id}".encode()
    return "rc_" + hashlib.sha256(material).hexdigest()[:16]


def _model_input(source: dict) -> dict:
    """Remove non-semantic source identity while preserving the original significance evidence."""
    result = copy.deepcopy(source)
    result.pop("analysis_id", None)
    previous = result.get("previous_event_alert")
    if isinstance(previous, dict):
        # Keep timing and market-move context used for novelty, but exclude prior generated copy,
        # provider-derived classification, and technical identity hashes from the reviewer packet.
        for key in (
            "title", "possible_action", "canonical_event_key", "semantic_family",
            "stable_related_news_ids_hash",
        ):
            previous.pop(key, None)
    news = result.get("news")
    if isinstance(news, list):
        for item in news:
            if isinstance(item, dict):
                item.pop("news_id", None)
    return result


def _label_counts(labels: dict) -> dict[str, int]:
    return dict(sorted(Counter(row["warrant"] for row in labels.values()).items()))


def _operator_prompt(rubric: str, schema: str) -> str:
    return (
        "# CCW-41 Reviewer C operator prompt\n\n"
        "You are the independent, blinded Reviewer C. Read only the assigned batch JSON, this "
        "prompt, and the schema below. Do not inspect repository files, human reviews, prior model "
        "outputs, comparison reports, or other batches. Assess every case independently and return "
        "one JSON object matching the schema. Keep exact case_id and input_sha256 values.\n\n"
        "## Frozen rubric\n\n" + rubric.rstrip() + "\n\n"
        "## Frozen output schema\n\n```json\n" + schema.rstrip() + "\n```\n"
    )


def prepare_review(
    benchmark: Path,
    reviewer_a: Path,
    reviewer_b: Path,
    private_dir: Path,
    *,
    seed: str = "ccw41-reviewer-c-v1",
    batch_size: int = 20,
    enforce_canonical: bool = True,
    enforce_private_location: bool = True,
) -> dict:
    if enforce_private_location:
        private_dir = _require_gitignored_private_dir(private_dir)
    if not seed or not 1 <= batch_size <= 20:
        raise ValueError("Seed is required and batch size must be between 1 and 20")
    dataset = load_frozen(benchmark)
    if len(dataset["cases"]) != 200:
        raise ValueError("Expected exactly 200 distinct cases")
    symbol_counts = dict(sorted(Counter(case["symbol"] for case in dataset["cases"]).items()))
    if symbol_counts != EXPECTED_SYMBOLS:
        raise ValueError("Expected exactly 50 cases per supported symbol")
    if enforce_canonical and dataset["dataset_sha256"] != CANONICAL_DATASET_SHA256:
        raise ValueError("Not the owner-selected immutable CCW-41 dataset")

    evaluator_a, labels_a = _read_evaluations(reviewer_a, dataset)
    evaluator_b, labels_b = _read_evaluations(reviewer_b, dataset)
    source_ids = {case["id"] for case in dataset["cases"]}
    if not evaluator_a or not evaluator_b or evaluator_a == evaluator_b:
        raise ValueError("Two distinct existing human reviewer records are required")
    if set(labels_a) != source_ids or set(labels_b) != source_ids:
        raise ValueError("Reviewer A/B case coverage does not match the frozen dataset")
    a_counts = _label_counts(labels_a)
    conflicts = sum(labels_a[key]["warrant"] != labels_b[key]["warrant"] for key in source_ids)
    if enforce_canonical and (a_counts != EXPECTED_A or conflicts != EXPECTED_AB_CONFLICTS):
        raise ValueError("Canonical Reviewer A/B evidence differs from the approved baseline")

    rubric = RUBRIC_PATH.read_text(encoding="utf-8")
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    schema_json = json.loads(schema)
    if schema_json.get("title") != "CCW-41 Reviewer C batch result":
        raise ValueError("Unexpected Reviewer C schema")
    prompt = _operator_prompt(rubric, schema)
    prompt_sha256 = hashlib.sha256(prompt.encode()).hexdigest()
    if (
        _sha256_file(RUBRIC_PATH) != FROZEN_RUBRIC_SHA256
        or _sha256_file(SCHEMA_PATH) != FROZEN_SCHEMA_SHA256
        or prompt_sha256 != FROZEN_PROMPT_SHA256
    ):
        raise ValueError("Frozen CCW-41 v1 protocol differs from approved fingerprints")

    ordered = list(dataset["cases"])
    random_seed = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
    random.Random(random_seed).shuffle(ordered)
    mapping = []
    packets = []
    seen_opaque = set()
    for offset in range(0, len(ordered), batch_size):
        batch_number = len(packets) + 1
        batch_id = f"batch_{batch_number:02}"
        cards = []
        for case in ordered[offset:offset + batch_size]:
            opaque = _opaque_id(seed, dataset["dataset_sha256"], case["id"])
            if opaque in seen_opaque:
                raise ValueError("Opaque case ID collision")
            seen_opaque.add(opaque)
            cards.append({
                "case_id": opaque,
                "input_sha256": case["input_sha256"],
                "symbol": case["symbol"],
                "input": _model_input(case["input"]),
            })
            mapping.append({
                "opaque_id": opaque,
                "source_case_id": case["id"],
                "input_sha256": case["input_sha256"],
                "symbol": case["symbol"],
                "scenario_type": case["scenario_type"],
                "tags": case.get("tags", []),
                "batch_id": batch_id,
            })
        packet = {
            "protocol_version": "ccw41-v1",
            "batch_id": batch_id,
            "dataset_sha256": dataset["dataset_sha256"],
            "rubric_sha256": _sha256_file(RUBRIC_PATH),
            "result_schema_sha256": _sha256_file(SCHEMA_PATH),
            "cases": cards,
        }
        packets.append((batch_id, packet))

    packet_summaries = []
    for batch_id, packet in packets:
        path = private_dir / "packets" / f"{batch_id}.json"
        _write_new_or_same(path, packet)
        packet_summaries.append({
            "batch_id": batch_id,
            "case_count": len(packet["cases"]),
            "packet_sha256": _sha256_file(path),
            "opaque_ids": [case["case_id"] for case in packet["cases"]],
        })
    _write_text_new_or_same(private_dir / "operator_prompt.md", prompt)
    _write_text_new_or_same(private_dir / "reviewer-c-rubric.md", rubric)
    _write_text_new_or_same(private_dir / "reviewer-c-result.schema.json", schema)

    manifest = {
        "protocol_version": "ccw41-v1",
        "dataset_sha256": dataset["dataset_sha256"],
        "case_count": 200,
        "symbol_counts": symbol_counts,
        "shuffle_seed_sha256": hashlib.sha256(seed.encode()).hexdigest(),
        "batch_size": batch_size,
        "rubric_sha256": _sha256_file(RUBRIC_PATH),
        "result_schema_sha256": _sha256_file(SCHEMA_PATH),
        "operator_prompt_sha256": prompt_sha256,
        "sources": {
            "benchmark": {"path": str(benchmark.resolve()), "sha256": _sha256_file(benchmark)},
            "reviewer_a": {"path": str(reviewer_a.resolve()), "sha256": _sha256_file(reviewer_a)},
            "reviewer_b": {"path": str(reviewer_b.resolve()), "sha256": _sha256_file(reviewer_b)},
        },
        "verified_private_evidence": {
            "reviewer_a_distribution": a_counts,
            "reviewer_b_distribution": _label_counts(labels_b),
            "a_b_conflicts": conflicts,
        },
        "batches": packet_summaries,
        "cases": sorted(mapping, key=lambda row: row["opaque_id"]),
    }
    _write_new_or_same(private_dir / "manifest.json", manifest)
    return {
        "dataset_sha256": dataset["dataset_sha256"],
        "case_count": 200,
        "symbol_counts": symbol_counts,
        "batch_count": len(packets),
        "a_b_conflicts": conflicts,
        "provider_requests": 0,
    }


def _load_manifest(private_dir: Path) -> dict:
    path = private_dir / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("protocol_version") != "ccw41-v1" or manifest.get("case_count") != 200:
        raise ValueError("Invalid CCW-41 manifest")
    pinned = {
        "rubric_sha256": FROZEN_RUBRIC_SHA256,
        "result_schema_sha256": FROZEN_SCHEMA_SHA256,
        "operator_prompt_sha256": FROZEN_PROMPT_SHA256,
    }
    if any(manifest.get(field) != value for field, value in pinned.items()):
        raise ValueError("Frozen CCW-41 v1 protocol fingerprint mismatch")
    for name in ("rubric", "result_schema", "operator_prompt"):
        filename = {
            "rubric": "reviewer-c-rubric.md",
            "result_schema": "reviewer-c-result.schema.json",
            "operator_prompt": "operator_prompt.md",
        }[name]
        if _sha256_file(private_dir / filename) != manifest[f"{name}_sha256"]:
            raise ValueError(f"Frozen {name} fingerprint mismatch")
    return manifest


def _verified_packets(private_dir: Path, manifest: dict) -> tuple[dict, dict]:
    packets: dict[str, dict] = {}
    expected_by_batch: dict[str, set[str]] = {}
    mapped = {row["opaque_id"]: row for row in manifest["cases"]}
    if len(mapped) != 200:
        raise ValueError("Duplicate or missing cases in the frozen manifest")
    seen: set[str] = set()
    for batch in manifest["batches"]:
        batch_id = batch["batch_id"]
        if batch_id in packets:
            raise ValueError("Duplicate frozen batch")
        path = private_dir / "packets" / f"{batch_id}.json"
        if _sha256_file(path) != batch["packet_sha256"]:
            raise ValueError("Frozen review packet fingerprint mismatch")
        packet = json.loads(path.read_text(encoding="utf-8"))
        if (
            packet.get("batch_id") != batch_id
            or packet.get("protocol_version") != "ccw41-v1"
            or packet.get("dataset_sha256") != manifest["dataset_sha256"]
            or packet.get("rubric_sha256") != manifest["rubric_sha256"]
            or packet.get("result_schema_sha256") != manifest["result_schema_sha256"]
        ):
            raise ValueError("Frozen packet protocol mismatch")
        cards = {row["case_id"]: row for row in packet["cases"]}
        ids = set(cards)
        if (
            len(cards) != len(packet["cases"])
            or len(cards) != batch["case_count"]
            or len(cards) != len(batch["opaque_ids"])
            or ids != set(batch["opaque_ids"])
            or ids & seen
        ):
            raise ValueError("Frozen packet has missing, repeated, or misbucketed cases")
        for case_id, card in cards.items():
            if (
                case_id not in mapped
                or mapped[case_id]["batch_id"] != batch_id
                or card["input_sha256"] != mapped[case_id]["input_sha256"]
                or card["symbol"] != mapped[case_id]["symbol"]
            ):
                raise ValueError("Frozen packet case mapping mismatch")
        packets[batch_id] = cards
        expected_by_batch[batch_id] = ids
        seen.update(ids)
    if seen != set(mapped):
        raise ValueError("Frozen packet coverage mismatch")
    return packets, expected_by_batch


def _verify_run_metadata(run: dict) -> None:
    if (
        not isinstance(run, dict)
        or not RUN_METADATA_FIELDS.issubset(run)
        or any(not isinstance(run[key], str) or not run[key].strip()
               for key in RUN_METADATA_FIELDS)
    ):
        raise ValueError("Complete Reviewer C output requires verified run metadata")
    for name in ("request_errors", "measured_tokens"):
        value = run.get(name)
        if value is not None and (
            type(value) is not int or value < 0
        ):
            raise ValueError(f"Invalid Reviewer C {name}")
    cost = run.get("measured_cost_usd")
    if cost is not None and (
        type(cost) not in (int, float) or not 0 <= cost < float("inf")
    ):
        raise ValueError("Invalid Reviewer C measured cost")


def _verify_sealed_record(private_dir: Path, manifest: dict, sealed: dict) -> None:
    run = json.loads((private_dir / "run_manifest.json").read_text(encoding="utf-8"))
    _verify_run_metadata(run)
    expected = {
        "protocol_version": "ccw41-v1",
        "dataset_sha256": manifest["dataset_sha256"],
        "rubric_sha256": manifest["rubric_sha256"],
        "result_schema_sha256": manifest["result_schema_sha256"],
        "operator_prompt_sha256": manifest["operator_prompt_sha256"],
        "batch_count": len(manifest["batches"]),
        "result_count": 200,
        "reviewer_c_sha256": _sha256_file(private_dir / "reviewer_c_sealed.json"),
    }
    if any(run.get(key) != value for key, value in expected.items()):
        raise ValueError("Sealed Reviewer C provenance/hash mismatch")
    if not isinstance(run.get("sealed_at"), str) or not run["sealed_at"].strip():
        raise ValueError("Missing Reviewer C seal timestamp")
    if (
        sealed.get("protocol_version") != "ccw41-v1"
        or sealed.get("dataset_sha256") != manifest["dataset_sha256"]
        or sealed.get("result_count") != 200
        or not isinstance(sealed.get("results"), list)
        or len(sealed["results"]) != 200
    ):
        raise ValueError("Reviewer C output is incomplete or from the wrong dataset")
    packets, _ = _verified_packets(private_dir, manifest)
    mapped = {row["opaque_id"]: row for row in manifest["cases"]}
    seen: set[str] = set()
    for row in sealed["results"]:
        case_id = row.get("case_id") if isinstance(row, dict) else None
        if case_id not in mapped or case_id in seen:
            raise ValueError("Duplicate or unknown sealed Reviewer C case")
        seen.add(case_id)
        expected_case = mapped[case_id]
        if any(row.get(key) != expected_case[key] for key in
               ("source_case_id", "symbol", "batch_id")):
            raise ValueError("Sealed Reviewer C case provenance mismatch")
        pure = {key: value for key, value in row.items()
                if key not in {"source_case_id", "symbol", "batch_id"}}
        validated = _validate_result(
            pure, expected_case, packets[expected_case["batch_id"]][case_id]
        )
        if pure != validated:
            raise ValueError("Invalid sealed Reviewer C schema")
    if seen != set(mapped):
        raise ValueError("Sealed Reviewer C cases are incomplete")


REFERENCE_PART = re.compile(r"^(?P<key>[A-Za-z0-9_]+)(?:\[(?P<index>[0-9]+)\])?$")


def _walk_reference(case_input: dict, reference: str) -> Any:
    if not reference.startswith("input."):
        raise KeyError(reference)
    current: Any = case_input
    for part in reference.split(".")[1:]:
        match = REFERENCE_PART.fullmatch(part)
        if not match or not isinstance(current, dict) or match.group("key") not in current:
            raise KeyError(reference)
        current = current[match.group("key")]
        if match.group("index") is not None:
            index = int(match.group("index"))
            if not isinstance(current, list) or index >= len(current):
                raise KeyError(reference)
            current = current[index]
    return current


def _field_exists(case_input: dict, reference: str) -> bool:
    try:
        _walk_reference(case_input, reference)
    except KeyError:
        return False
    return True


def _validate_result(row: dict, expected: dict, packet_case: dict) -> dict:
    allowed = {
        "case_id", "input_sha256", "warrant", "confidence", "rationale",
        "evidence_references", "missing_evidence", "reason_category",
    }
    required = allowed - {"reason_category"}
    if not isinstance(row, dict) or not required.issubset(row) or set(row) - allowed:
        raise ValueError("Reviewer C result fields do not match the frozen schema")
    if row["case_id"] != expected["opaque_id"]:
        raise ValueError("Unknown Reviewer C case")
    if row["input_sha256"] != expected["input_sha256"]:
        raise ValueError("Reviewer C input hash mismatch")
    if row["warrant"] not in WARRANT or row["confidence"] not in CONFIDENCE:
        raise ValueError("Invalid Reviewer C warrant or confidence")
    rationale = row["rationale"]
    if not isinstance(rationale, str) or not 1 <= len(rationale.strip()) <= 1200:
        raise ValueError("Reviewer C rationale is missing or too long")
    evidence = row["evidence_references"]
    missing = row["missing_evidence"]
    if (
        not isinstance(evidence, list) or not evidence
        or any(not isinstance(item, str) or not item for item in evidence)
        or not isinstance(missing, list)
        or any(not isinstance(item, str) or not item for item in missing)
    ):
        raise ValueError("Invalid Reviewer C evidence or missing-evidence list")
    if any(not _field_exists(packet_case["input"], item) for item in evidence):
        raise ValueError("Reviewer C cited evidence outside the supplied case")
    if row["warrant"] == "ambiguous" and not missing:
        raise ValueError("Ambiguous Reviewer C result must identify missing evidence")
    category = row.get("reason_category")
    if category is not None and (not isinstance(category, str) or len(category) > 80):
        raise ValueError("Invalid Reviewer C reason category")
    return {key: row.get(key) for key in sorted(allowed) if key in row}


def import_results(
    private_dir: Path,
    results_dir: Path,
    *,
    run_metadata: dict | None = None,
    enforce_private_location: bool = True,
) -> dict:
    if enforce_private_location:
        private_dir = _require_gitignored_private_dir(private_dir)
        if results_dir.resolve() != (private_dir / "results").resolve():
            raise ValueError("Reviewer C results must stay inside the private audit directory")
    manifest = _load_manifest(private_dir)
    expected = {row["opaque_id"]: row for row in manifest["cases"]}
    packets, expected_by_batch = _verified_packets(private_dir, manifest)

    journal_path = private_dir / "reviewer_c_partial.json"
    accepted = {}
    if journal_path.exists():
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
        if (
            not isinstance(journal, dict)
            or set(journal) != {"protocol_version", "dataset_sha256", "results"}
            or journal["protocol_version"] != "ccw41-v1"
            or journal["dataset_sha256"] != manifest["dataset_sha256"]
            or not isinstance(journal["results"], list)
        ):
            raise ValueError("Partial Reviewer C journal belongs to another protocol/dataset")
        for row in journal["results"]:
            case_id = row.get("case_id") if isinstance(row, dict) else None
            if case_id not in expected or case_id in accepted:
                raise ValueError("Duplicate or unknown partial Reviewer C case")
            batch_id = expected[case_id]["batch_id"]
            if case_id not in expected_by_batch[batch_id]:
                raise ValueError("Partial Reviewer C case in wrong batch")
            accepted[case_id] = _validate_result(
                row, expected[case_id], packets[batch_id][case_id]
            )

    seen_in_import = set()
    for path in sorted(results_dir.glob("batch_*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or set(payload) != {"batch_id", "results"}:
            raise ValueError("Reviewer C batch root fields do not match frozen schema")
        batch_id = payload.get("batch_id")
        if batch_id not in packets or path.stem != batch_id:
            raise ValueError("Unknown or misnamed Reviewer C batch")
        rows = payload.get("results")
        if not isinstance(rows, list):
            raise ValueError("Reviewer C batch results must be a list")
        for row in rows:
            case_id = row.get("case_id") if isinstance(row, dict) else None
            if case_id in seen_in_import:
                raise ValueError("Duplicate Reviewer C case in import")
            seen_in_import.add(case_id)
            if case_id not in expected_by_batch[batch_id]:
                raise ValueError("Reviewer C case appears in the wrong batch")
            validated = _validate_result(row, expected[case_id], packets[batch_id][case_id])
            prior = accepted.get(case_id)
            if prior is not None and prior != validated:
                raise ValueError("Refusing to overwrite an existing Reviewer C decision")
            accepted[case_id] = validated
    _write_atomic(journal_path, {
        "protocol_version": "ccw41-v1",
        "dataset_sha256": manifest["dataset_sha256"],
        "results": [accepted[key] for key in sorted(accepted)],
    })

    missing = set(expected) - set(accepted)
    if missing:
        return {"accepted": len(accepted), "missing": len(missing), "sealed": False}
    _verify_run_metadata(run_metadata)
    sealed_path = private_dir / "reviewer_c_sealed.json"
    enriched = []
    for case_id in sorted(accepted):
        mapping = expected[case_id]
        enriched.append({
            **accepted[case_id],
            "source_case_id": mapping["source_case_id"],
            "symbol": mapping["symbol"],
            "batch_id": mapping["batch_id"],
        })
    sealed = {
        "protocol_version": "ccw41-v1",
        "dataset_sha256": manifest["dataset_sha256"],
        "result_count": 200,
        "results": enriched,
    }
    if sealed_path.exists() and json.loads(sealed_path.read_text(encoding="utf-8")) != sealed:
        raise ValueError("Refusing to overwrite sealed Reviewer C output")
    _write_new_or_same(sealed_path, sealed)
    run = {
        **run_metadata,
        "protocol_version": "ccw41-v1",
        "dataset_sha256": manifest["dataset_sha256"],
        "reviewer_c_sha256": _sha256_file(sealed_path),
        "rubric_sha256": manifest["rubric_sha256"],
        "result_schema_sha256": manifest["result_schema_sha256"],
        "operator_prompt_sha256": manifest["operator_prompt_sha256"],
        "batch_count": len(manifest["batches"]),
        "result_count": 200,
        "request_errors": run_metadata.get("request_errors", 0),
        "measured_tokens": run_metadata.get("measured_tokens"),
        "measured_cost_usd": run_metadata.get("measured_cost_usd"),
        "sealed_at": run_metadata.get("sealed_at") or datetime.now(timezone.utc).isoformat(),
    }
    _write_new_or_same(private_dir / "run_manifest.json", run)
    return {"accepted": 200, "missing": 0, "sealed": True}


def _pairwise(left: dict[str, str], right: dict[str, str]) -> dict:
    table = {a: {b: 0 for b in sorted(WARRANT)} for a in sorted(WARRANT)}
    for case_id in left:
        table[left[case_id]][right[case_id]] += 1
    total = len(left)
    agreement = sum(table[value][value] for value in WARRANT)
    left_counts = Counter(left.values())
    right_counts = Counter(right.values())
    expected = sum(left_counts[value] * right_counts[value] for value in WARRANT) / (total * total)
    observed = agreement / total
    kappa = None if expected == 1 else (observed - expected) / (1 - expected)
    return {
        "total": total,
        "agreement": agreement,
        "agreement_rate": observed,
        "disagreement": total - agreement,
        "confusion": table,
        "cohen_kappa": kappa,
    }


def _group_metrics(case_ids: list[str], labels: dict[str, dict[str, str]]) -> dict:
    return {
        name: {
            "total": len(case_ids),
            "agreement": sum(labels[left][key] == labels[right][key] for key in case_ids),
            "disagreement": sum(labels[left][key] != labels[right][key] for key in case_ids),
        }
        for name, left, right in (("A-C", "A", "C"), ("B-C", "B", "C"), ("A-B", "A", "B"))
    }


def _resolve_reference(case_input: dict, reference: str) -> Any:
    return _walk_reference(case_input, reference)


def _aggregate_markdown(aggregate: dict) -> str:
    """Publishable, aggregate-only exploratory report; never include case identity."""
    lines = [
        "# CCW-41 exploratory Reviewer-C agreement/disagreement",
        "",
        "Reviewer A remains the authoritative reference for CCW-16/29. Reviewer C is an "
        "independent AI audit, not an adjudicator or majority vote.",
        "",
        f"Dataset: {aggregate['case_count']} frozen cases. "
        f"Original A/B conflicts: {aggregate['a_b_conflict_subset']['count']}.",
        "",
        "## Overall distributions",
        "",
        "| Reviewer | alert | no_alert | ambiguous |",
        "|---|---:|---:|---:|",
    ]
    for reviewer, counts in aggregate["distributions"].items():
        lines.append(
            f"| {reviewer} | {counts['alert']} | {counts['no_alert']} | "
            f"{counts['ambiguous']} |"
        )
    lines += [
        "",
        "## Pairwise agreement (all 200 cases)",
        "",
        "| Pair | Agreed | Disagreed | Rate |",
        "|---|---:|---:|---:|",
    ]
    for name, values in aggregate["pairwise"].items():
        lines.append(
            f"| {name} | {values['agreement']}/{values['total']} | "
            f"{values['disagreement']} | {values['agreement_rate']:.1%} |"
        )
    conflicts = aggregate["a_b_conflict_subset"]
    lines += [
        "",
        "## Original A/B disagreement subset",
        "",
        f"Of {conflicts['count']} original disagreements: "
        f"C agrees with A in {conflicts.get('c_agrees_a', 0)}, "
        f"with B in {conflicts.get('c_agrees_b', 0)}, "
        f"with neither in {conflicts.get('c_agrees_neither', 0)}, "
        f"and selected ambiguous in {conflicts.get('c_ambiguous', 0)}.",
        "These are descriptive categories, not votes or corrections to human labels.",
        "",
        "## Reviewer A decisive vs ambiguous",
        "",
    ]
    for name, key in (("A decisive", "a_decisive"), ("A ambiguous", "a_ambiguous")):
        values = aggregate[key]["A-C"]
        lines.append(
            f"- {name}: A/C agreement {values['agreement']}/{values['total']}; "
            f"disagreement {values['disagreement']}/{values['total']}"
        )
    lines += [
        "",
        "## Differences by symbol (A vs C)",
        "",
        "| Symbol | Disagreements | Denominator |",
        "|---|---:|---:|",
    ]
    for symbol in ("BTC", "ETH", "GRAM", "SOL"):
        values = aggregate["breakdowns"][f"symbol:{symbol}"]["A-C"]
        lines.append(f"| {symbol} | {values['disagreement']} | {values['total']} |")
    lines += ["", "## Observed scenario and tag splits (A vs C)", ""]
    for group, metrics in aggregate["breakdowns"].items():
        if not group.startswith(("scenario_type:", "tag:")):
            continue
        values = metrics["A-C"]
        lines.append(
            f"- {group}: {values['disagreement']}/{values['total']} disagreements"
        )
    impact = aggregate["high_impact_counts"]
    lines += [
        "",
        "## High-impact disagreement counts",
        "",
        f"- A=alert, C=no_alert: {impact['a_alert_c_no_alert']}",
        f"- A=no_alert, C=alert: {impact['a_no_alert_c_alert']}",
        f"- A=ambiguous, C=decisive: {impact['a_ambiguous_c_decisive']}",
        "",
        "## Confirmed observations",
        "",
    ]
    lines += [f"- {item}" for item in aggregate["confirmed_patterns"]]
    lines += ["", "## Hypotheses requiring owner judgment", ""]
    lines += [f"- {item}" for item in aggregate["hypotheses_for_owner_review"]]
    lines += ["", "## Limitations and decisions", ""]
    lines += [f"- {item}" for item in aggregate["limitations"]]
    lines += [
        "- Review the restricted private shortlist against original market evidence and "
        "the independent rationales before deciding whether labels need a new protocol.",
        "- Any benchmark relabeling, evaluation-policy change, or CCW-16/29 acceptance "
        "change requires separate owner approval and versioning.",
        "- Cohen's kappa and all subgroup rates in the aggregate JSON are descriptive "
        "only; small groups and three-class ambiguity limit inference.",
        "",
    ]
    return "\n".join(lines)


def _narrative_findings(
    distributions: dict,
    a_decisive: dict,
    a_ambiguous: dict,
    breakdowns: dict,
) -> tuple[list[str], list[str]]:
    confirmed = []
    hypotheses = []
    if (
        distributions["C"]["no_alert"]
        > max(distributions["A"]["no_alert"], distributions["B"]["no_alert"])
        and distributions["C"]["ambiguous"]
        < min(distributions["A"]["ambiguous"], distributions["B"]["ambiguous"])
    ):
        confirmed.append(
            "Reviewer C selected no_alert more often and ambiguous less often than either "
            "human reviewer."
        )
        hypotheses.extend([
            "The frozen rubric may have induced a conservative materiality/novelty "
            "interpretation in Reviewer C; this is a hypothesis, not a demonstrated "
            "human-label defect.",
            "Reviewer C's low ambiguous rate may indicate over-resolution of incomplete "
            "evidence rather than stronger certainty.",
        ])
    decisive_rate = a_decisive["A-C"]["agreement"] / a_decisive["A-C"]["total"]
    ambiguous_rate = a_ambiguous["A-C"]["agreement"] / a_ambiguous["A-C"]["total"]
    if decisive_rate > ambiguous_rate:
        confirmed.append(
            "Reviewer C agreed with Reviewer A more often on A-decisive cases than on "
            "A-ambiguous cases."
        )
    symbol_disagreements = [
        breakdowns[f"symbol:{symbol}"]["A-C"]["disagreement"]
        for symbol in ("BTC", "ETH", "GRAM", "SOL")
    ]
    if all(
        left < right
        for left, right in zip(symbol_disagreements, symbol_disagreements[1:], strict=False)
    ):
        confirmed.append(
            "Reviewer A/C disagreement increased from BTC through ETH and GRAM to SOL in "
            "this frozen sample."
        )
        hypotheses.append(
            "Higher GRAM/SOL disagreement may reflect asset-specific context gaps or reviewer "
            "calibration and requires case-level owner review."
        )
    return confirmed, hypotheses


def compare_reviewers(private_dir: Path, *, enforce_private_location: bool = True) -> dict:
    if enforce_private_location:
        private_dir = _require_gitignored_private_dir(private_dir)
    manifest = _load_manifest(private_dir)
    sealed_path = private_dir / "reviewer_c_sealed.json"
    run_path = private_dir / "run_manifest.json"
    if not sealed_path.exists() or not run_path.exists():
        raise ValueError("Reviewer C must be complete and sealed before unblinding")
    sealed = json.loads(sealed_path.read_text(encoding="utf-8"))
    _verify_sealed_record(private_dir, manifest, sealed)

    sources = manifest["sources"]
    for source in sources.values():
        if _sha256_file(Path(source["path"])) != source["sha256"]:
            raise ValueError("A frozen source file changed after packet preparation")
    dataset = load_frozen(Path(sources["benchmark"]["path"]))
    if dataset["dataset_sha256"] != manifest["dataset_sha256"]:
        raise ValueError("Frozen dataset fingerprint mismatch")
    _, labels_a_raw = _read_evaluations(Path(sources["reviewer_a"]["path"]), dataset)
    _, labels_b_raw = _read_evaluations(Path(sources["reviewer_b"]["path"]), dataset)
    labels = {
        "A": {key: value["warrant"] for key, value in labels_a_raw.items()},
        "B": {key: value["warrant"] for key, value in labels_b_raw.items()},
        "C": {row["source_case_id"]: row["warrant"] for row in sealed["results"]},
    }
    source_ids = {case["id"] for case in dataset["cases"]}
    if any(set(values) != source_ids for values in labels.values()):
        raise ValueError("Reviewer coverage changed before comparison")

    distributions = {
        reviewer: {value: Counter(values.values())[value] for value in sorted(WARRANT)}
        for reviewer, values in labels.items()
    }
    pairwise = {
        "A-C": _pairwise(labels["A"], labels["C"]),
        "B-C": _pairwise(labels["B"], labels["C"]),
        "A-B": _pairwise(labels["A"], labels["B"]),
    }
    conflicts = sorted(key for key in source_ids if labels["A"][key] != labels["B"][key])
    conflict_split = Counter()
    for key in conflicts:
        if labels["C"][key] == "ambiguous":
            conflict_split["c_ambiguous"] += 1
        elif labels["C"][key] == labels["A"][key]:
            conflict_split["c_agrees_a"] += 1
        elif labels["C"][key] == labels["B"][key]:
            conflict_split["c_agrees_b"] += 1
        else:
            conflict_split["c_agrees_neither"] += 1

    cases_by_id = {case["id"]: case for case in dataset["cases"]}
    groups: dict[str, list[str]] = {}
    for case in dataset["cases"]:
        categories = {
            f"symbol:{case['symbol']}",
            f"scenario_type:{case['scenario_type']}",
            *(f"tag:{tag}" for tag in case.get("tags", [])),
        }
        for category in categories:
            groups.setdefault(category, []).append(case["id"])
    breakdowns = {
        group: _group_metrics(case_ids, labels)
        for group, case_ids in sorted(groups.items())
    }

    a_decisive = _group_metrics(
        [key for key in source_ids if labels["A"][key] != "ambiguous"], labels,
    )
    a_ambiguous = _group_metrics(
        [key for key in source_ids if labels["A"][key] == "ambiguous"], labels,
    )
    confirmed_patterns, hypotheses = _narrative_findings(
        distributions, a_decisive, a_ambiguous, breakdowns,
    )
    aggregate = {
        "label": "exploratory Reviewer-C agreement/disagreement",
        "protocol_version": "ccw41-v1",
        "dataset_sha256": manifest["dataset_sha256"],
        "case_count": 200,
        "distributions": distributions,
        "pairwise": pairwise,
        "a_decisive": a_decisive,
        "a_ambiguous": a_ambiguous,
        "a_b_conflict_subset": {"count": len(conflicts), **dict(sorted(conflict_split.items()))},
        "high_impact_counts": {
            "a_alert_c_no_alert": sum(
                labels["A"][key] == "alert" and labels["C"][key] == "no_alert"
                for key in source_ids
            ),
            "a_no_alert_c_alert": sum(
                labels["A"][key] == "no_alert" and labels["C"][key] == "alert"
                for key in source_ids
            ),
            "a_ambiguous_c_decisive": sum(
                labels["A"][key] == "ambiguous" and labels["C"][key] != "ambiguous"
                for key in source_ids
            ),
        },
        "breakdowns": breakdowns,
        "confirmed_patterns": confirmed_patterns,
        "hypotheses_for_owner_review": hypotheses,
        "limitations": [
            "Reviewer C is exploratory and is not adjudicated truth.",
            "Agreement with either human reviewer does not establish correctness.",
            "Small subgroup denominators are descriptive and must not be generalized.",
            "No majority-vote relabeling or production policy change is authorized.",
        ],
    }

    c_by_source = {row["source_case_id"]: row for row in sealed["results"]}
    discrepancies = []
    for source_id in sorted(source_ids):
        c = c_by_source[source_id]
        if labels["A"][source_id] == labels["C"][source_id]:
            continue
        case = cases_by_id[source_id]
        discrepancies.append({
            "source_case_id": source_id,
            "symbol": case["symbol"],
            "scenario_type": case["scenario_type"],
            "reviewer_a": labels["A"][source_id],
            "reviewer_b": labels["B"][source_id],
            "reviewer_c": c["warrant"],
            "reviewer_c_confidence": c["confidence"],
            "reviewer_c_rationale": c["rationale"],
            "reviewer_c_missing_evidence": c["missing_evidence"],
            "supporting_evidence": {
                reference: _resolve_reference(_model_input(case["input"]), reference)
                for reference in c["evidence_references"]
            },
        })
    priority = {
        ("alert", "no_alert"): 0,
        ("no_alert", "alert"): 1,
    }
    confidence_priority = {"high": 0, "medium": 1, "low": 2}
    shortlist_candidates = sorted(
        discrepancies,
        key=lambda row: (
            priority.get((row["reviewer_a"], row["reviewer_c"]), 2),
            confidence_priority[row["reviewer_c_confidence"]],
            row["symbol"],
            row["source_case_id"],
        ),
    )
    shortlist = []
    per_symbol = Counter()
    for row in shortlist_candidates:
        if per_symbol[row["symbol"]] >= 6:
            continue
        shortlist.append(row)
        per_symbol[row["symbol"]] += 1
        if len(shortlist) == 24:
            break
    private_report = {
        "label": "restricted private Reviewer-C discrepancies",
        "dataset_sha256": manifest["dataset_sha256"],
        "count": len(discrepancies),
        "owner_review_shortlist_count": len(shortlist),
        "owner_review_shortlist": shortlist,
        "cases": discrepancies,
    }
    _write_atomic(private_dir / "aggregate_summary.json", aggregate)
    _write_text_atomic(private_dir / "aggregate_summary.md", _aggregate_markdown(aggregate))
    _write_atomic(private_dir / "private_discrepancies.json", private_report)
    return aggregate


def _cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--benchmark", type=Path, required=True)
    prepare.add_argument("--reviewer-a", type=Path, required=True)
    prepare.add_argument("--reviewer-b", type=Path, required=True)
    prepare.add_argument("--private-dir", type=Path, required=True)
    prepare.add_argument("--seed", default="ccw41-reviewer-c-v1")
    prepare.add_argument("--batch-size", type=int, default=20)

    import_parser = subparsers.add_parser("import-results")
    import_parser.add_argument("--private-dir", type=Path, required=True)
    import_parser.add_argument("--results-dir", type=Path, required=True)
    import_parser.add_argument("--run-metadata", type=Path)

    compare = subparsers.add_parser("compare")
    compare.add_argument("--private-dir", type=Path, required=True)
    return parser


def main() -> None:
    args = _cli().parse_args()
    if args.command == "prepare":
        result = prepare_review(
            args.benchmark, args.reviewer_a, args.reviewer_b, args.private_dir,
            seed=args.seed, batch_size=args.batch_size,
        )
    elif args.command == "import-results":
        metadata = None
        if args.run_metadata:
            metadata = json.loads(args.run_metadata.read_text(encoding="utf-8"))
        result = import_results(args.private_dir, args.results_dir, run_metadata=metadata)
    else:
        result = compare_reviewers(args.private_dir)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
