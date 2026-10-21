"""CCW-16: isolated, quota-bounded scheduler tick for a pre-staged pilot.

Never reads production config, model prompts, DB or Telegram state. Invokes
only the already-staged private runner, at most once per provider per tick.
Install/run as ccwbot_ops. Do not revive the cancelled CCW-28 timers.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

BASE = Path("/home/ccwbot_ops/ccw16_replay")
LEDGER = BASE / "pilot-ledger.json"
STAGED = BASE / "private_calls.json"
RUNNER = BASE / "runner.py"
LOCK = BASE / "scheduler.lock"
SHA256 = "ed126380369014e6522cee49009b880cf0350aa7565269d50641c3f1bbdc3bee"
PROMPTS = frozenset({"production", "ccw15_materiality_evidence_v1", "ccw15_novelty_independent_v1"})
PROVIDERS = ("groq", "cloudflare")
DEFER_STOPS = frozenset({
    "conservative_daily_cap", "min_provider_spacing",
    "max_provider_attempts", "max_pilot_attempts",
})


def check_identity() -> None:
    if os.name != "posix":
        raise RuntimeError("CCW-16 server scheduler requires Linux")
    import pwd

    if os.geteuid() == 0 or pwd.getpwuid(os.geteuid()).pw_name != "ccwbot_ops":
        raise RuntimeError("Must run only as unprivileged ccwbot_ops")
    if Path.home() != Path("/home/ccwbot_ops"):
        raise RuntimeError("Isolated CCW-16 home mismatch")


def load_json(path: Path) -> dict:
    if not path.is_file():
        raise RuntimeError("Required private state not found")
    if path.stat().st_mode & 0o077:
        raise RuntimeError("Private state permissions not restrictive")
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if data.get("version") != 1 or data.get("dataset_sha256") != SHA256:
        raise RuntimeError("Frozen dataset/ledger identity changed")
    return data


def inspect(base: Path = BASE) -> dict:
    """Return counts only. Never expose raw contexts, prompts or case IDs."""
    staged = load_json(base / STAGED.name)
    jobs = staged.get("calls")
    if not isinstance(jobs, list) or len(jobs) != 120:
        raise RuntimeError("Staged pilot not 20 cases x 3 prompts x 2 providers")
    expected = Counter({(p, v): 20 for p in PROVIDERS for v in PROMPTS})
    if Counter((x.get("provider"), x.get("prompt")) for x in jobs) != expected:
        raise RuntimeError("Unbalanced staged pilot")
    staged_keys = {(x["id"], x["prompt"], x["provider"]) for x in jobs}
    if len(staged_keys) != 120:
        raise RuntimeError("Duplicate staged request")
    state_path = base / LEDGER.name
    ledger = load_json(state_path) if state_path.exists() else {
        "version": 1, "dataset_sha256": SHA256, "attempts": [],
    }
    attempts = ledger.get("attempts")
    if not isinstance(attempts, list) or len(attempts) > 120:
        raise RuntimeError("Too many pilot attempts")
    keys = [(x.get("id"), x.get("prompt"), x.get("provider")) for x in attempts]
    if len(keys) != len(set(keys)) or any(x not in staged_keys for x in keys):
        raise RuntimeError("Ledger divergence/duplicate attempts")
    per_provider = Counter(x["provider"] for x in attempts)
    if any(n > 60 for n in per_provider.values()):
        raise RuntimeError("Provider request cap exceeded")
    statuses = Counter(x.get("status", x.get("state", "unknown")) for x in attempts)
    blocked = any(x.get("status") not in ("valid", None)
                  or x.get("state") == "reserved" for x in attempts)
    complete = len(attempts) == 120 and statuses == {"valid": 120}
    return {
        "total": len(attempts),
        "by_provider": {p: per_provider[p] for p in PROVIDERS},
        "by_status": dict(statuses),
        "completed": complete,
        "blocked": blocked,
    }


def invoke_provider(provider: str, base: Path = BASE, python: str = sys.executable) -> dict:
    result = subprocess.run(
        [python, str(base / RUNNER.name), "--provider", provider, "--count", "1"],
        cwd=str(base), capture_output=True, text=True, timeout=155, check=False,
    )
    if result.returncode:
        # Never show stderr: raw provider/host errors could contain sensitive data.
        raise RuntimeError("Private runner failed; manual inspection required")
    try:
        data = json.loads(result.stdout)
    except (ValueError, TypeError):
        raise RuntimeError("Invalid runner summary") from None
    if data.get("provider") != provider or data.get("new_attempts", 0) not in (0, 1):
        raise RuntimeError("Runner violated finite-call contract")
    if data.get("stop") and data["stop"] not in DEFER_STOPS:
        raise RuntimeError("Unsafe runner stop reason")
    if any(x.get("status") != "valid" for x in data.get("cases", [])):
        raise RuntimeError("Invalid provider output; auto-run stopped")
    return {
        "new_attempts": data.get("new_attempts", 0),
        "deferred": data.get("stop") in DEFER_STOPS,
    }


def tick(base: Path = BASE, *, dry_run: bool = False) -> dict:
    """At most one attempt per provider; fail closed on errors or quota stops."""
    check_identity()
    import fcntl
    if not (base / RUNNER.name).is_file():
        raise RuntimeError("Private runner missing")
    os.umask(0o077)
    with (base / LOCK.name).open("a+", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"state": "already_running"}
        before = inspect(base)
        if before["blocked"]:
            return {"state": "halted_for_manual_review", "progress": before}
        if before["completed"]:
            return {"state": "complete", "progress": before}
        if dry_run:
            return {"state": "dry_run", "progress": before}
        # Alternate first provider to keep paired coverage as even as possible.
        providers = sorted(
            PROVIDERS, key=lambda p: (before["by_provider"][p], PROVIDERS.index(p)),
        )
        results = {}
        for provider in providers:
            try:
                results[provider] = invoke_provider(provider, base)
            except RuntimeError:
                return {"state": "halted_for_manual_review",
                        "provider": provider, "progress": inspect(base)}
            after = inspect(base)
            if after["blocked"]:
                return {"state": "halted_for_manual_review", "progress": after}
        final = inspect(base)
        return {"state": "complete" if final["completed"] else "running",
                "progress": final, "tick": results}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--tick", action="store_true")
    choice.add_argument("--status", action="store_true")
    choice.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    check_identity()
    result = inspect(BASE) if args.status else tick(dry_run=args.dry_run)
    print(json.dumps(result, separators=(",", ":"), sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
