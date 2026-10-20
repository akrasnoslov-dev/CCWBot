"""Combine approved Event Alert replay ledgers without repeating paid/provider calls.

No provider, Telegram or database calls. The output directory must not exist.
Inputs remain private and must never be committed to Git.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.event_alert_benchmark import load_frozen  # noqa: E402
from scripts.live_event_significance_benchmark import (  # noqa: E402
    MAX_APPROVED_CALLS,
    VARIANTS,
    export_recorded_runs,
    save_state,
)

_ALLOWED_FIELDS = frozenset({
    "id", "input_sha256", "status", "should_alert", "materiality",
    "novelty", "reason_code", "provider_attempts", "total_tokens",
    "prompt_tokens", "completion_tokens", "http_status", "error_type",
    "retry_after_seconds", "rate_limit_at_utc",
    "rate_limit_daily_requests", "rate_limit_remaining_requests",
    "rate_limit_minute_tokens", "rate_limit_remaining_tokens",
    "rate_limit_dimension",
})
_VALID_STATUSES = frozenset({"valid", "schema_error", "invalid_json", "provider_error"})


def combine_states(dataset: dict, states: list[dict]) -> dict:
    """Strict union; never convert failed calls into no-alert decisions."""
    if len(states) < 2:
        raise ValueError("At least two recorded states are required")
    known = {case["id"]: case["input_sha256"] for case in dataset["cases"]}
    merged = {
        "dataset_sha256": dataset["dataset_sha256"],
        "model": None,
        "fingerprints": {},
        "attempted_requests": 0,
        "runs": {variant: [] for variant in VARIANTS},
    }
    seen = set()
    for state in states:
        if state.get("dataset_sha256") != dataset["dataset_sha256"]:
            raise ValueError("Mismatched frozen benchmark digest")
        if not isinstance(state.get("model"), str) or not state["model"]:
            raise ValueError("Missing model identifier")
        if merged["model"] is None:
            merged["model"] = state["model"]
        elif merged["model"] != state["model"]:
            raise ValueError("Different model configurations cannot be pooled")
        fingerprints = state.get("fingerprints", {})
        if not isinstance(fingerprints, dict):
            raise ValueError("Invalid config fingerprints")
        for variant, fingerprint in fingerprints.items():
            if variant not in VARIANTS or not isinstance(fingerprint, str) or not fingerprint:
                raise ValueError("Unrecognized/empty prompt fingerprint")
            existing = merged["fingerprints"].get(variant)
            if existing is not None and existing != fingerprint:
                raise ValueError("Conflicting prompt fingerprints")
            merged["fingerprints"][variant] = fingerprint
        runs = state.get("runs", {})
        if not isinstance(runs, dict) or any(v not in VARIANTS for v in runs):
            raise ValueError("Unknown run variant")
        count = 0
        for variant, rows in runs.items():
            if rows and variant not in fingerprints:
                raise ValueError("Responses without pinned prompt configuration")
            if not isinstance(rows, list):
                raise ValueError("Malformed run responses")
            for row in rows:
                if not isinstance(row, dict) or not set(row).issubset(_ALLOWED_FIELDS):
                    raise ValueError("Unexpected potentially private response fields")
                case_id = row.get("id")
                if case_id not in known or row.get("input_sha256") != known[case_id]:
                    raise ValueError("Unknown case or changed input hash")
                key = (variant, case_id)
                if key in seen:
                    raise ValueError("Overlapping provider attempts; refuse double counting")
                seen.add(key)
                if row.get("status") not in _VALID_STATUSES:
                    raise ValueError("Unrecognized result status")
                if row["status"] == "valid":
                    if type(row.get("should_alert")) is not bool:
                        raise ValueError("Valid response needs a boolean decision")
                elif row.get("should_alert") is not None:
                    raise ValueError("Failed response must not be scored")
                merged["runs"][variant].append(dict(row))
                count += 1
        attempts = state.get("attempted_requests")
        if type(attempts) is not int or attempts < count:
            raise ValueError("Attempt counter smaller than recorded responses")
        merged["attempted_requests"] += attempts
    if merged["attempted_requests"] > MAX_APPROVED_CALLS:
        raise ValueError("Cumulative replay safety ceiling exceeded")
    return merged


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--states", type=Path, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if len(args.states) < 2:
        parser.error("Supply two or more private replay_state.json files")
    dataset = load_frozen(args.benchmark)
    state = combine_states(
        dataset,
        [json.loads(path.read_text(encoding="utf-8")) for path in args.states],
    )
    args.out.mkdir(parents=True, exist_ok=False)
    save_state(args.out / "replay_state.json", state)
    export_recorded_runs(args.out, state)
    print(json.dumps({
        "merged_requests": state["attempted_requests"],
        "records": {name: len(rows) for name, rows in state["runs"].items()},
        "model": state["model"],
        "dataset_sha256": state["dataset_sha256"],
        "output": str(args.out),
    }, indent=2))


if __name__ == "__main__":
    main()
