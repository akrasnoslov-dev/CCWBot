"""Unattended, quota-conservative, single-attempt Event Alert benchmark worker.

This does NOT modify production, send Telegram messages or run unless invoked.
Designed for a once-per-hour LOCAL task on the authorized workstation.
All result and scheduling state remain in the gitignored private report directory.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.event_alert_benchmark import load_frozen  # noqa: E402
from scripts.live_event_significance_benchmark import (  # noqa: E402
    MAX_APPROVED_CALLS,
    estimated_spent_tokens,
    load_reviewer_a,
    maximum_possible_quality,
    remaining_rate_limit_backoff,
    replay,
)

PRIVATE = ROOT / "reports" / "event-alert-review-20261016"
LEDGER_DIR = PRIVATE / "merged_pilots_private"
VARIANT = "market_signal_path"
HOURLY_REQUESTS = 1
WINDOW = timedelta(hours=24)
# Free-tier gpt-oss-120b publicly lists 200K TPD, shared with production.
# Cap this offline benchmark below half of that for any rolling 24h window.
MAX_24H_REQUESTS = 8
MAX_24H_RESERVED_TOKENS = 60_000
RESERVATION_TOKENS = 8_300
MAX_TOTAL_SAFETY_TOKENS = 5_100_000
MAX_CONSECUTIVE_429 = 3


@contextmanager
def exclusive_worker_lock(path: Path):
    """OS-released file lock: a crash cannot leave a permanent stale lock."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        stream.seek(0)
        try:
            existing = stream.read(1)
        except PermissionError as exc:
            # Windows may deny reads of the byte locked by another process.
            raise RuntimeError("Benchmark worker already running") from exc
        if not existing:
            stream.seek(0)
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        if os.name == "nt":
            import msvcrt

            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise RuntimeError("Benchmark worker already running") from exc
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise RuntimeError("Benchmark worker already running") from exc
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def read_private_status(path: Path) -> dict:
    if not path.exists():
        return {"history": [], "rate_limit_streak": 0, "not_before": None}
    state = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(state, dict) or not isinstance(state.get("history"), list):
        raise ValueError("Malformed private automation status")
    return state


def record_status(path: Path, state: dict, *, reason: str, attempts: int) -> dict:
    state["status"] = reason
    state["total_provider_attempts"] = attempts
    state["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    return {"status": reason, "attempts": attempts}


def recent_reservations(history: list, now: datetime) -> list:
    recent = []
    for row in history:
        stamp = datetime.fromisoformat(row["at"])
        if stamp.tzinfo is None:
            raise ValueError("Private automation timestamps must be offset-aware")
        if now - WINDOW < stamp <= now:
            recent.append(row)
    return recent


def compute_next_eligible(
    state: dict, replay_state: dict, *, now: datetime,
) -> tuple[bool, str]:
    if replay_state["attempted_requests"] >= MAX_APPROVED_CALLS:
        return False, "replay_call_safety_ceiling"
    if estimated_spent_tokens(replay_state, 6300) + RESERVATION_TOKENS > MAX_TOTAL_SAFETY_TOKENS:
        return False, "total_token_safety_ceiling"
    if remaining_rate_limit_backoff(replay_state, now=now) > 0:
        return False, "provider_retry_after_active"
    until = state.get("not_before")
    if until and now < datetime.fromisoformat(until):
        return False, "consecutive_rate_limit_backoff"
    if state.get("rate_limit_streak", 0) >= MAX_CONSECUTIVE_429:
        return False, "repeated_429_manual_review_required"
    history = recent_reservations(state.get("history", []), now)
    if history and any(
        now - datetime.fromisoformat(row["at"]) < timedelta(hours=1)
        for row in history
    ):
        return False, "minimum_hourly_interval"
    if len(history) >= MAX_24H_REQUESTS:
        return False, "rolling_24h_request_reserve"
    if (
        sum(row["reserved_tokens"] for row in history) + RESERVATION_TOKENS
        > MAX_24H_RESERVED_TOKENS
    ):
        return False, "rolling_24h_token_reserve"
    return True, "eligible"


def run_once(*, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be offset-aware")
    if not (PRIVATE / "v2_private_sanitized.json").is_file():
        return {"status": "private_frozen_cases_unavailable"}
    if not (PRIVATE / "reviewer_A_significance_for_pr1.json").is_file():
        return {"status": "private_reviewer_labels_unavailable"}
    ledger = LEDGER_DIR / "replay_state.json"
    if not ledger.exists():
        return {"status": "existing_private_replay_ledger_unavailable"}
    with exclusive_worker_lock(LEDGER_DIR / ".hourly_replay.lock"):
        status_file = LEDGER_DIR / "hourly_replay_status.json"
        private = read_private_status(status_file)
        recorded = json.loads(ledger.read_text(encoding="utf-8"))
        dataset = load_frozen(PRIVATE / "v2_private_sanitized.json")
        labels = load_reviewer_a(
            PRIVATE / "reviewer_A_significance_for_pr1.json", dataset,
        )
        if recorded.get("dataset_sha256") != dataset["dataset_sha256"]:
            raise ValueError("Frozen market reference has changed")
        prior = recorded["attempted_requests"]
        candidate_rows = recorded["runs"].get(VARIANT, [])
        decisive = [
            r for r in candidate_rows
            if r.get("status") == "valid" and labels[r["id"]] != "ambiguous"
        ]
        if len(decisive) >= sum(v != "ambiguous" for v in labels.values()):
            return record_status(
                status_file, private, reason="candidate_fully_scored_review_required",
                attempts=prior,
            )
        if not maximum_possible_quality(
            dataset, labels, recorded, VARIANT,
        )["can_meet_target"]:
            return record_status(
                status_file, private, reason="candidate_cannot_meet_quality_gates",
                attempts=prior,
            )
        allowed, reason = compute_next_eligible(private, recorded, now=now)
        private["history"] = recent_reservations(private.get("history", []), now)
        if not allowed:
            return record_status(status_file, private, reason=reason, attempts=prior)

        # Reserve quota BEFORE issuing HTTP. Even after process interruption, the
        # local hourly budget treats an uncertain request as fully spent.
        private["history"].append({
            "at": now.isoformat(), "reserved_tokens": RESERVATION_TOKENS,
        })
        record_status(
            status_file, private, reason="provider_attempt_reserved",
            attempts=prior,
        )
        try:
            result = asyncio.run(replay(
                dataset, labels, LEDGER_DIR,
                max_requests=HOURLY_REQUESTS,
                delay=45,
                max_total_tokens=MAX_TOTAL_SAFETY_TOKENS,
                selected_variants=(VARIANT,),
                skip_ambiguous=True,
                retry_rate_limited=True,
                stop_on_impossible_gates=True,
                screen_positives_first=True,
            ))
        except Exception:
            # Never persist exception bodies or secrets; the run ledger is
            # independently durable and can be inspected in a manual review.
            record_status(
                status_file, private, reason="worker_error_needs_review",
                attempts=prior,
            )
            raise

        newer = json.loads(ledger.read_text(encoding="utf-8"))
        if result.get("stop") == "provider_http_429":
            streak = int(private.get("rate_limit_streak", 0)) + 1
            private["rate_limit_streak"] = streak
            latest = [
                row for row in newer["runs"][VARIANT]
                if row.get("http_status") == 429
            ]
            dimension = latest[-1].get("rate_limit_dimension") if latest else None
            private["last_rate_limit_dimension"] = dimension or "unknown"
            delay_hours = 24 if dimension in ("tokens_per_day", "requests_per_day") else 2 ** streak
            wait = max(
                timedelta(hours=delay_hours),
                timedelta(seconds=remaining_rate_limit_backoff(newer)),
            )
            private["not_before"] = (now + wait).isoformat()
        elif result.get("attempts_this_invocation", 0) > 0:
            private["rate_limit_streak"] = 0
            private["not_before"] = None

        return record_status(
            status_file, private, reason=str(result["stop"]),
            attempts=newer["attempted_requests"],
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", required=True)
    parser.parse_args()
    print(json.dumps(run_once(), sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
