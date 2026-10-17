"""Offline, paired scoring for private Groq Event Alert A/B results.

Score only cases with validated decisions for ALL compared variants.
Incomplete or ambiguous cases never become negatives; no provider calls.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.event_alert_benchmark import load_frozen  # noqa: E402
from scripts.live_event_significance_benchmark import (  # noqa: E402
    VARIANTS,
    load_reviewer_a,
)


def score(
    dataset: dict, a_labels: dict, state: dict,
    *, variants: tuple[str, ...] = VARIANTS,
) -> dict:
    by_id = {case["id"]: case for case in dataset["cases"]}
    if state["dataset_sha256"] != dataset["dataset_sha256"]:
        raise ValueError("Mismatching frozen inputs")
    observed = {}
    for variant in variants:
        records = state["runs"].get(variant, [])
        if any(row.get("id") not in by_id for row in records):
            raise ValueError("Unknown case")
        if len({row["id"] for row in records}) != len(records):
            raise ValueError("Duplicate run result")
        if any(
            row.get("input_sha256") != by_id[row["id"]]["input_sha256"]
            for row in records
        ):
            raise ValueError("Candidate input hash mismatch")
        observed[variant] = {row["id"]: row for row in records}
    completed = [
        case for case in dataset["cases"]
        if a_labels[case["id"]] in ("alert", "no_alert")
        and all(
            observed[variant].get(case["id"], {}).get("status") == "valid"
            for variant in variants
        )
    ]
    results = {}
    for variant in variants:
        cm = Counter()
        for case in completed:
            pred = observed[variant][case["id"]]["should_alert"]
            label = a_labels[case["id"]]
            if type(pred) is not bool:
                raise ValueError("Invalid purportedly valid boolean response")
            cm["tp" if pred and label == "alert" else
               "fp" if pred else "fn" if label == "alert" else "tn"] += 1
        tp, fp, fn = cm["tp"], cm["fp"], cm["fn"]
        rows = state["runs"][variant]
        measured_tokens = [
            row["total_tokens"] for row in rows if isinstance(row.get("total_tokens"), int)
        ]
        results[variant] = {
            "recorded_attempts": len(rows),
            "valid_answers": sum(row.get("status") == "valid" for row in rows),
            "provider_failures": sum(
                row.get("status") == "provider_error" for row in rows
            ),
            "invalid_or_schema": sum(
                row.get("status") in ("schema_error", "invalid_json") for row in rows
            ),
            "paired_scored": len(completed),
            "tp": tp, "fp": fp, "fn": fn, "tn": cm["tn"],
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
            "total_tokens_measured": sum(measured_tokens) if measured_tokens else None,
            "token_coverage": len(measured_tokens),
            "by_symbol": {},
        }
        for symbol in ("BTC", "ETH", "GRAM", "SOL"):
            cases = [c for c in completed if c["symbol"] == symbol]
            sub = Counter()
            for case in cases:
                pred = observed[variant][case["id"]]["should_alert"]
                lab = a_labels[case["id"]]
                sub["tp" if pred and lab == "alert" else
                    "fp" if pred else "fn" if lab == "alert" else "tn"] += 1
            results[variant]["by_symbol"][symbol] = {
                "n": len(cases), "tp": sub["tp"], "fp": sub["fp"],
                "fn": sub["fn"], "tn": sub["tn"],
            }
    decisive_total = sum(
        a_labels[case["id"]] in ("alert", "no_alert")
        for case in dataset["cases"]
    )
    complete_reference = len(completed) == decisive_total
    candidate_gates = {
        name: (
            complete_reference
            and stats["precision"] is not None
            and stats["precision"] >= 0.85
            and stats["recall"] is not None
            and stats["recall"] >= 0.90
        )
        for name, stats in results.items()
        if name != "production"
    }
    return {
        "decisive_reference_cases": decisive_total,
        "paired_cases_missing": decisive_total - len(completed),
        "complete_paired_reference": complete_reference,
        "candidate_significance_gates_met": candidate_gates,
        "frozen_cases": len(dataset["cases"]),
        "reference": "reviewer_A_owner_designated",
        "benchmark_sha256": dataset["dataset_sha256"],
        "paired_unambiguous_cases": len(completed),
        "paired_ids_count_only": len(completed),
        "paired_cohort_not_population_estimate": True,
        "requests_attempted": state["attempted_requests"],
        "variants": results,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--benchmark", type=Path, required=True)
    p.add_argument("--reviewer-a", type=Path, required=True)
    p.add_argument("--run-state", type=Path, required=True)
    p.add_argument("--variants", nargs="+", choices=VARIANTS, default=VARIANTS)
    args = p.parse_args()
    dataset = load_frozen(args.benchmark)
    labels = load_reviewer_a(args.reviewer_a, dataset)
    state = json.loads(args.run_state.read_text(encoding="utf-8"))
    print(json.dumps(
        score(dataset, labels, state, variants=tuple(dict.fromkeys(args.variants))),
        indent=2,
    ))


if __name__ == "__main__":
    main()
