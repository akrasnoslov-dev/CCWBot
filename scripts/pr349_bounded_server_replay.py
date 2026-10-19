"""Finite, isolated, no-delivery model replay for approved PR 349 benchmark."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.event_alert_benchmark import load_frozen  # noqa: E402
from scripts.live_event_significance_benchmark import (  # noqa: E402
    load_reviewer_a,
    maximum_possible_quality,
)

PRIVATE = ROOT / "reports" / "event-alert-review-20261016"
LEDGERS = PRIVATE / "merged_pilots_private"
CONFIG = LEDGERS / "vps_bounded_plan.json"
STATUS = LEDGERS / "vps_bounded_status.json"
REPLAY = ROOT / "scripts" / "multi_provider_event_significance_benchmark.py"
CANDIDATES = (
    ("cloudflare", "rebalanced_core", None),
    ("gemini", "rebalanced_core", "gemini-3.5-flash-lite"),
    ("gemini", "global_prior_no_family", "gemini-3.5-flash-lite"),
)


def model_ledger(provider: str, variant: str, model: str | None) -> Path:
    suffix = "_" + model.replace("/", "_").replace("@", "") if model else ""
    return LEDGERS / f"fallback_{provider}_{variant}{suffix}" / "replay_state.json"


def summary(dataset: dict, labels: dict, provider: str, variant: str,
            model: str | None) -> dict:
    path = model_ledger(provider, variant, model)
    status = {"provider": provider, "variant": variant, "model": model,
              "valid": 0, "remaining": 153, "attempts": 0,
              "possible": True, "complete": False}
    if not path.exists():
        return status
    saved = json.loads(path.read_text(encoding="utf-8"))
    if saved["dataset_sha256"] != dataset["dataset_sha256"]:
        raise RuntimeError("Frozen dataset fingerprint mismatch")
    rows = saved["runs"][variant]
    scored = [r for r in rows if r["status"] == "valid"
              and labels[r["id"]] != "ambiguous"]
    status.update(valid=len(scored), remaining=153-len(scored),
                  attempts=saved["attempted_requests"],
                  possible=maximum_possible_quality(
                      dataset, labels, saved, variant)["can_meet_target"],
                  complete=len(scored) == 153)
    return status


def run_once(*, dry_run: bool) -> dict:
    plan = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert plan["candidates"] == [list(c) for c in CANDIDATES], "Unpinned plan"
    now = datetime.now(timezone.utc)
    deadline = datetime.fromisoformat(plan["deadline_utc"])
    if deadline.tzinfo is None:
        raise ValueError("Deadline must include timezone")
    dataset = load_frozen(PRIVATE / "v2_private_sanitized.json")
    labels = load_reviewer_a(PRIVATE / "reviewer_A_significance_for_pr1.json", dataset)
    results = [summary(dataset, labels, *c) for c in CANDIDATES]
    state = {"at_utc": now.isoformat(), "deadline_utc": deadline.isoformat(),
             "candidates": results, "dry_run": dry_run, "state": "waiting"}
    if now >= deadline:
        state["state"] = "deadline_reached"
    elif any(r["complete"] and r["possible"] for r in results):
        state["state"] = "candidate_full_pass"
    elif all(not r["possible"] or r["complete"] for r in results):
        state["state"] = "all_three_exhausted"
    elif not dry_run:
        for provider in ("cloudflare", "gemini"):
            selected = next((r for r in results if r["provider"] == provider
                             and r["possible"] and not r["complete"]), None)
            if selected is None:
                continue
            cmd = [sys.executable, str(REPLAY), "--provider", provider,
                   "--variant", selected["variant"], "--max-requests", "6",
                   "--delay-seconds", "10", "--approve-provider-requests"]
            if selected["model"]:
                cmd.extend(["--model-override", selected["model"]])
            try:
                child = subprocess.run(cmd, cwd=ROOT, text=True,
                                       capture_output=True, timeout=460,
                                       check=False)
                parsed = {}
                for line in reversed(child.stdout.splitlines()):
                    try:
                        parsed = json.loads(line)
                        break
                    except (ValueError, TypeError):
                        continue
                selected["last_stop"] = parsed.get("stop", "no_summary")
                selected["last_exit"] = child.returncode
            except subprocess.TimeoutExpired:
                selected["last_stop"] = "request_batch_timeout"
            refreshed = summary(dataset, labels, selected["provider"],
                                selected["variant"], selected["model"])
            selected.update(refreshed)
        state["state"] = "replayed"
    LEDGERS.mkdir(parents=True, exist_ok=True)
    temporary = STATUS.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    temporary.replace(STATUS)
    return state


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = run_once(dry_run=args.dry_run)
    print(json.dumps({"state": result["state"], "candidates":
        [{k:r[k] for k in ("provider", "variant", "valid", "remaining", "possible")}
         for r in result["candidates"]]}))
