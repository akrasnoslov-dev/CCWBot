"""Prepare cost-conscious Event Alert significance candidates; OFFLINE ONLY.

Run: python scripts/event_significance_candidates.py --benchmark <private-frozen.json>
No API calls, prompt/response dumps, production changes or inferred accuracy scores.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bot.alerting.event_identity import _json_dumps  # noqa: E402
from bot.services.ai_agent_groq import (  # noqa: E402
    _EVENT_SIGNIFICANCE_INSTRUCTIONS,
    _event_significance_prompt_payload,
    build_event_significance_prompt,
)

# Additions are hypotheses to compare with the current production prompt.
# Neither changes the schema, model, facts, or the LLM's exclusive authority.
CANDIDATE_ADDITIONS = {
    "materiality_first": (
        "Calibration focus: before considering news, c24, prev or cnt, explain to "
        "yourself whether the present cw over w merits a notification for this "
        "specific asset. Inspect same-window pw and actual s path for evidence "
        "of unusual size, persistence or acceleration. A short-lived wobble or "
        "a counter-move inside a larger c24 direction is not automatically "
        "a reversal. Missing c30/c60 or sparse s never proves rapid motion. "
        "Do not transform these observations into fixed cutoffs."
    ),
    "balanced_novelty": (
        "Calibration focus: keep Q1 materiality and Q2 novelty strictly separate. "
        "A demonstrably noteworthy present move may be material even if recent "
        "market events were frequent; cnt and prev reduce novelty only when "
        "the present path merely continues or repeats their described move. "
        "A genuinely changed current path may be new despite earlier alerts. "
        "But a fresh timestamp, headline or counter-move alone is not a new "
        "market event. Use pw and s as supporting evidence, never thresholds."
    ),
}


def candidate_prompt(input_payload: dict, candidate: str) -> str:
    if candidate == "production":
        return build_event_significance_prompt(input_payload)
    if candidate not in CANDIDATE_ADDITIONS:
        raise ValueError(f"Unknown candidate: {candidate}")
    # Preserve production message shape and validation schema, changing only
    # short materiality/novelty guidance for an isolated counterfactual replay.
    instructions = (
        _EVENT_SIGNIFICANCE_INSTRUCTIONS + "\n" + CANDIDATE_ADDITIONS[candidate]
    )
    payload_json = _json_dumps(_event_significance_prompt_payload(input_payload))
    return f"{instructions}\nInput JSON:\n{payload_json}"


def offline_inventory(dataset: dict) -> dict:
    from scripts.event_alert_benchmark import digest

    cases = dataset["cases"]
    variants = ("production", *CANDIDATE_ADDITIONS)
    results = {}
    for variant in variants:
        size = []
        fingerprints = []
        for case in cases:
            # Don't print or persist private model inputs.
            if case["input_sha256"] != digest(case["input"]):
                raise ValueError("Frozen case input changed")
            prompt = candidate_prompt(case["input"], variant)
            size.append(len(prompt))
            fingerprints.append(hashlib.sha256(prompt.encode("utf-8")).hexdigest())
        results[variant] = {
            "min_prompt_characters": min(size) if size else None,
            "max_prompt_characters": max(size) if size else None,
            "aggregate_prompt_fingerprint": hashlib.sha256(
                "\n".join(fingerprints).encode("ascii")
            ).hexdigest(),
            "measured_significance_precision": None,
            "measured_significance_recall": None,
            "provider_requests": 0,
        }
    return {
        "provenance": "OFFLINE_PREPARATION_ONLY",
        "dataset_sha256": dataset["dataset_sha256"],
        "cases": len(cases),
        "by_symbol": dict(sorted(Counter(c["symbol"] for c in cases).items())),
        "candidates": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, required=True)
    arguments = parser.parse_args()
    from scripts.event_alert_benchmark import load_frozen

    dataset = load_frozen(arguments.benchmark)
    print(json.dumps(offline_inventory(dataset), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
