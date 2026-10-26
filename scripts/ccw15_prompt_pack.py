"""CCW-15: offline, read-only frozen-input and Reviewer A audit.

No live inference, network requests, production writes, or private case output.
Use --benchmark and --reviewer-a only on an authorized isolated workstation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPT_ROOT = ROOT / "benchmarks" / "ccw15-v1"
PROMPTS = {
    "production": "production.txt",
    "ccw15_materiality_evidence_v1": "materiality-evidence.txt",
    "ccw15_novelty_independent_v1": "novelty-independent.txt",
}
FROZEN_DATASET_SHA256 = "ed126380369014e6522cee49009b880cf0350aa7565269d50641c3f1bbdc3bee"
EXPECTED_LABELS = {"alert": 41, "no_alert": 112, "ambiguous": 47}
EXPECTED_CONFUSION = {"tp": 21, "fp": 53, "fn": 20, "tn": 59}
EXPECTED_SYMBOL_CONFUSION = {
    "BTC": {"tp": 2, "fp": 21, "fn": 4, "tn": 20},
    "ETH": {"tp": 3, "fp": 13, "fn": 3, "tn": 17},
    "GRAM": {"tp": 8, "fp": 11, "fn": 8, "tn": 10},
    "SOL": {"tp": 8, "fp": 8, "fn": 5, "tn": 12},
}


def instruction(name: str) -> str:
    if name not in PROMPTS:
        raise ValueError("Unregistered CCW-15 candidate")
    raw = (PROMPT_ROOT / PROMPTS[name]).read_bytes()
    if not raw.endswith(b"\n") or b"\r" in raw:
        raise ValueError("Prompt file must use UTF-8 LF and trailing newline")
    return raw.decode("utf-8")[:-1]


def check_production_parity() -> None:
    from bot.services.ai_agent_groq import _EVENT_SIGNIFICANCE_INSTRUCTIONS
    if instruction("production") != _EVENT_SIGNIFICANCE_INSTRUCTIONS:
        raise ValueError("Production instructions drifted; do not compare unmatched baseline")


def build_prompt(
    input_payload: dict, candidate: str, *, require_current_parity: bool = True
) -> str:
    """Build historical prompt; require current parity unless explicitly replaying an archive."""
    from bot.alerting.event_identity import _json_dumps
    from bot.services.ai_agent_groq import _event_significance_prompt_payload

    frozen_instruction = instruction(candidate)
    if require_current_parity:
        check_production_parity()
    compact = _event_significance_prompt_payload(input_payload)
    return frozen_instruction + "\nInput JSON:\n" + _json_dumps(compact)


def inspect_private_frozen(benchmark: Path, reviewer_a: Path) -> dict:
    """Fail closed: never print original cases, labels, evaluator identity, or case IDs."""
    from scripts.event_alert_benchmark import _read_evaluations, load_frozen, report

    dataset = load_frozen(benchmark)
    if dataset["dataset_sha256"] != FROZEN_DATASET_SHA256:
        raise ValueError("Not the owner-selected immutable 200-case dataset")
    cases = dataset["cases"]
    if len(cases) != 200:
        raise ValueError("Expected exactly 200 real-market cases")
    symbols = Counter(c["symbol"] for c in cases)
    if dict(symbols) != {"BTC": 50, "ETH": 50, "GRAM": 50, "SOL": 50}:
        raise ValueError("Expected 50 cases per symbol")

    evaluator_id, labels = _read_evaluations(reviewer_a, dataset)
    ids = {c["id"] for c in cases}
    if not evaluator_id or set(labels) != ids:
        raise ValueError("Reviewer A case IDs do not exactly match frozen inputs")
    count = Counter(row["warrant"] for row in labels.values())
    if dict(count) != EXPECTED_LABELS:
        raise ValueError("Reviewer A label totals differ from frozen baseline")
    baseline = report(dataset, labels)
    scored = baseline["overall"]["event_level"]
    if any(scored[k] != v for k, v in EXPECTED_CONFUSION.items()):
        raise ValueError("Reviewer A mapping/baseline scorer mismatch")
    for symbol, expected in EXPECTED_SYMBOL_CONFUSION.items():
        actual = baseline["by_symbol"][symbol]["event_level"]
        if any(actual[k] != value for k, value in expected.items()):
            raise ValueError("Reviewer A per-symbol scorer mismatch")
    if scored["scored_cases"] != 153 or scored["ambiguous_cases"] != 47:
        raise ValueError("Unexpected decisive/ambiguous partition")

    # Rebuild all model-visible inputs without calls, persistent files or case dumps.
    # The production serialization and original inputs are identical for all variants.
    aggregate = {}
    for name in PROMPTS:
        fingerprints = [
            hashlib.sha256(
                build_prompt(case["input"], name, require_current_parity=False).encode("utf-8")
            ).hexdigest()
            for case in cases
        ]
        aggregate[name] = hashlib.sha256("\n".join(fingerprints).encode("ascii")).hexdigest()
    return {
        "dataset_sha256": dataset["dataset_sha256"],
        "case_count": len(cases),
        "reviewer_a_case_id_matches": True,
        "reviewer_a_warrants": dict(sorted(count.items())),
        "baseline_confusion": {k: scored[k] for k in EXPECTED_CONFUSION},
        "candidate_aggregate_prompt_sha256": aggregate,
        "provider_requests": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path)
    parser.add_argument("--reviewer-a", type=Path)
    args = parser.parse_args()
    if bool(args.benchmark) != bool(args.reviewer_a):
        parser.error("--benchmark and --reviewer-a must be provided together")
    # CCW-15 remains a frozen 2026-10 benchmark; current dev adopted
    # Refined v2 in CCW-47. Never silently label the old prompt "live".
    from bot.services.ai_agent_groq import _EVENT_SIGNIFICANCE_INSTRUCTIONS

    summary = {
        "version": "ccw15-v1",
        "scope": "OFFLINE_PREPARATION_ONLY",
        "production_source": "historical CCW-15 frozen production.txt",
        "matches_current_dev_instructions": (
            instruction("production") == _EVENT_SIGNIFICANCE_INSTRUCTIONS
        ),
        "prompt_instruction_sha256": {
            name: hashlib.sha256(instruction(name).encode("utf-8")).hexdigest()
            for name in PROMPTS
        },
        "schema_and_model": (
            "Use unchanged production strict event_significance JSON schema; "
            "Groq GPT-OSS-120B medium, effective cap 6300"
        ),
        "provider_requests": 0,
    }
    if args.benchmark:
        summary["frozen_audit"] = inspect_private_frozen(args.benchmark, args.reviewer_a)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
