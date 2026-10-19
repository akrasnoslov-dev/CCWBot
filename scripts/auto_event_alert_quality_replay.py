"""Unattended resumable Event Alert discovery benchmarks. NEVER sends alerts.

The Windows Task Scheduler runs --once every ten minutes while logged in.
Each frozen model/prompt candidate has its own durable private ledger. If the
mathematical upper bound misses PR349 targets, automatically screen the next
candidate instead of wasting provider requests. Provider backoffs are enforced
by the leaf replay scripts, and production Groq capacity has a local cutoff.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.auto_event_significance_replay import exclusive_worker_lock  # noqa: E402
from scripts.event_alert_benchmark import load_frozen  # noqa: E402
from scripts.live_event_significance_benchmark import (  # noqa: E402
    load_reviewer_a,
    maximum_possible_quality,
)

PRIVATE = ROOT / "reports" / "event-alert-review-20261016"
LOGDIR = PRIVATE / "merged_pilots_private"
PROVIDER_SCRIPT = ROOT / "scripts" / "multi_provider_event_significance_benchmark.py"
GROQ_SCRIPT = ROOT / "scripts" / "live_event_significance_benchmark.py"
FROZEN = PRIVATE / "v2_private_sanitized.json"
LABELS = PRIVATE / "reviewer_A_significance_for_pr1.json"

# The order is exploratory, not an assertion that any variant works.
CANDIDATES = {
    "cloudflare": (
        "contextual_materiality", "market_event_evidence",
        "balanced_novelty", "global_prior_safe", "relative_displacement",
        "trajectory_evidence", "rebalanced_core", "production",
        "global_prior_no_family",
    ),
    "gemini": (
        "contextual_materiality", "market_event_evidence",
        "production", "balanced_novelty", "relative_displacement",
        "trajectory_evidence", "rebalanced_core", "path_facts",
        "global_prior_no_family",
    ),
}
GEMINI_MODEL = "gemini-3.5-flash-lite"


def select_candidate(provider: str, dataset: dict, labels: dict) -> tuple[str | None, str]:
    model_suffix = "_gemini-3.5-flash-lite" if provider == "gemini" else ""
    total = sum(value != "ambiguous" for value in labels.values())
    for variant in CANDIDATES[provider]:
        directory = LOGDIR / ("fallback_" + provider + "_" + variant + model_suffix)
        ledger = directory / "replay_state.json"
        if not ledger.exists():
            return variant, "new_candidate"
        state = json.loads(ledger.read_text(encoding="utf-8"))
        if state.get("dataset_sha256") != dataset["dataset_sha256"]:
            raise ValueError("Frozen data mismatch")
        measured = state["runs"][variant]
        if any(r.get("status") == "provider_error" and r.get("http_status")
               in (400, 401, 402, 403, 404) for r in measured):
            return None, "provider_configuration_error_needs_review"
        if not maximum_possible_quality(dataset, labels, state, variant)["can_meet_target"]:
            continue
        complete = sum(r.get("status") == "valid" and labels[r["id"]] != "ambiguous"
                       for r in measured) >= total
        if complete:
            return None, "candidate_fully_scored_needs_review"
        return variant, "resume_candidate"
    return None, "all_candidates_fail_quality_bound"


def make_commands(dataset: dict, labels: dict) -> tuple[list[tuple[str, list[str]]], dict]:
    cmds = []
    skipped = {}
    for provider in ("cloudflare", "gemini"):
        variant, reason = select_candidate(provider, dataset, labels)
        if variant is None:
            skipped[provider] = {"stop": reason}
            continue
        cmd = [
            str(sys.executable), str(PROVIDER_SCRIPT),
            "--provider", provider, "--variant", variant,
            "--max-requests", "32" if provider == "cloudflare" else "8",
            "--delay-seconds", "5" if provider == "cloudflare" else "10",
            "--approve-provider-requests",
        ]
        if provider == "gemini":
            cmd.extend(("--model-override", GEMINI_MODEL))
        cmds.append((provider, cmd))
    cmds.append(("groq", [
        str(sys.executable), str(GROQ_SCRIPT),
        "--benchmark", str(FROZEN), "--reviewer-a", str(LABELS),
        "--out", str(LOGDIR), "--variants", "path_facts",
        "--max-requests", "5", "--delay-seconds", "50",
        "--max-total-tokens", "5100000", "--approve-provider-requests",
        "--skip-ambiguous", "--retry-rate-limited",
        "--stop-on-impossible-gates", "--screen-positives-first",
    ]))
    return cmds, skipped


def production_reserved(provider: str) -> bool:
    if provider != "groq":
        return False
    path = LOGDIR / "quality_worker_policy.json"
    if not path.exists():
        return False
    policy = json.loads(path.read_text(encoding="utf-8"))
    deadline = datetime.fromisoformat(policy["stop_groq_at_utc"])
    if deadline.tzinfo is None:
        raise ValueError("Groq production reservation cutoff must be timezone-aware")
    return datetime.now(timezone.utc) >= deadline


def parse_benchmark_summary(output: str) -> dict:
    """Parse either JSON-lines fallbacks or Groq's final multiline JSON.

    Preserve only summary fields; never persist raw market inputs or errors.
    """
    stripped = output.strip()
    if not stripped:
        return {}
    try:
        candidate = json.loads(stripped)
        return candidate if isinstance(candidate, dict) else {}
    except json.JSONDecodeError:
        pass
    for line in reversed(stripped.splitlines()):
        try:
            candidate = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict) and (
            "stop" in candidate or "status" in candidate
        ):
            return candidate
    # Groq prints a JSON object across multiple lines after progress logs.
    marker = stripped.rfind("\n{\n")
    if marker >= 0:
        try:
            candidate = json.loads(stripped[marker + 1:])
            return candidate if isinstance(candidate, dict) else {}
        except json.JSONDecodeError:
            pass
    return {}


def run_once(*, dry_run: bool = False) -> dict:
    if not FROZEN.is_file() or not LABELS.is_file():
        return {"status": "private_dataset_missing"}
    LOGDIR.mkdir(parents=True, exist_ok=True)
    if dry_run:
        return {"status": "dry_run", "providers": ["cloudflare", "gemini", "groq"]}
    with exclusive_worker_lock(LOGDIR / ".quality_worker.lock"):
        dataset = load_frozen(FROZEN)
        labels = load_reviewer_a(LABELS, dataset)
        commands, results = make_commands(dataset, labels)
        for provider, command in commands:
            if production_reserved(provider):
                results[provider] = {"stop": "reserved_for_production"}
                continue
            completed = subprocess.run(
                command, cwd=ROOT, capture_output=True, text=True,
                timeout=540, check=False,
                **({"creationflags": subprocess.CREATE_NO_WINDOW}
                   if sys.platform == "win32" else {}),
            )
            # No credentials, raw errors or input payloads enter status logs.
            parsed = parse_benchmark_summary(completed.stdout)
            results[provider] = {
                "exit_code": completed.returncode,
                "stop": parsed.get("stop", parsed.get("status", "unknown")),
                "valid": parsed.get("valid"),
                "attempts": parsed.get("attempted_requests", parsed.get("attempts_total")),
            }
            if completed.returncode:
                results["status"] = "worker_error_needs_review"
                break
        results.setdefault("status", "completed")
        results["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
        path = LOGDIR / "quality_worker_status.json"
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        temp.replace(path)
        return results


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--once", required=True, action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    print(json.dumps(run_once(dry_run=args.dry_run), sort_keys=True))
