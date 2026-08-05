"""In-process health signal for Event Analysis.

Event Alerts were fully dead for 18 days without a single monitoring surface reporting
anything but healthy. ``/health`` only proves price polling runs, and the one trace was an
identical WARNING repeated 3396 times at unchanged severity — nothing that distinguishes
"failed once" from "has failed continuously for two and a half weeks".

This module holds the small amount of state that makes duration visible:

- a consecutive-failure counter, so severity can rise with duration instead of staying flat;
- the last time an analysis actually succeeded in this process.

It is deliberately observability-only. Nothing here creates market events, influences an
alert decision, or gates a delivery — it only records what already happened. State is
per process and resets on restart, which is the safe direction: a restart reports "unknown"
rather than falsely reporting health. ``/health`` reads the authoritative last-success time
from the database and uses this only for the counter.
"""

import threading
from datetime import datetime, timezone

# Read through the shared parser so a mistyped threshold warns instead of silently reverting
# to the default — the same guarantee the LLM configuration got, applied to the settings that
# decide when an outage becomes visible.
from bot.services.llm.env import get_int_env

# Consecutive failures before the repeating per-symbol log line escalates to ERROR and
# /health reports the degraded state. The first occurrences stay at WARNING: a single failed
# analysis is normal, a streak is not.
_DEFAULT_FAILURE_ESCALATION_THRESHOLD = 5

# How stale the last successful analysis may get before /health calls it degraded. Six missed
# cycles at the default 30-minute cadence.
_DEFAULT_MAX_SUCCESS_AGE_SECONDS = 3 * 60 * 60

_lock = threading.Lock()

_consecutive_failures = 0
_last_failure_reason: str | None = None
_last_success_at: datetime | None = None
_last_failure_at: datetime | None = None


def record_success(*, now: datetime | None = None) -> None:
    """A successful event analysis clears the failure streak."""
    global _consecutive_failures, _last_success_at, _last_failure_reason
    with _lock:
        _consecutive_failures = 0
        _last_failure_reason = None
        _last_success_at = now or datetime.now(timezone.utc)


def record_failure(*, reason: str | None = None, now: datetime | None = None) -> int:
    """Count one failed event analysis and return the new consecutive-failure count."""
    global _consecutive_failures, _last_failure_reason, _last_failure_at
    with _lock:
        _consecutive_failures += 1
        _last_failure_reason = reason
        _last_failure_at = now or datetime.now(timezone.utc)
        return _consecutive_failures


def consecutive_failures() -> int:
    with _lock:
        return _consecutive_failures


def snapshot() -> dict:
    """Sanitized view for diagnostics: counters and timestamps only, never payload data."""
    with _lock:
        return {
            "consecutive_failures": _consecutive_failures,
            "last_failure_reason": _last_failure_reason,
            "last_success_at": _last_success_at,
            "last_failure_at": _last_failure_at,
        }


def failure_escalation_threshold() -> int:
    return get_int_env(
        "EVENT_ANALYSIS_FAILURE_ESCALATION_THRESHOLD",
        _DEFAULT_FAILURE_ESCALATION_THRESHOLD,
        minimum=1,
    )


def max_success_age_seconds() -> int:
    return get_int_env(
        "EVENT_ANALYSIS_HEALTH_MAX_AGE_SECONDS",
        _DEFAULT_MAX_SUCCESS_AGE_SECONDS,
        minimum=1,
    )


def evaluate_state(
    *,
    last_success_at: datetime | None,
    consecutive_failures: int,
    now: datetime | None = None,
) -> tuple[str, int | None]:
    """Return ``(state, last_success_age_seconds)`` for the Event Analysis health block.

    ``unknown`` when there is nothing to judge on — no recorded success and no failure streak.
    Per the project rule, an unknown result is incomplete evidence, not a healthy one, so it is
    reported as its own state rather than folded into ``ok``.
    """
    now = now or datetime.now(timezone.utc)
    age_seconds: int | None = None
    if last_success_at is not None:
        reference = last_success_at
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=timezone.utc)
        age_seconds = max(0, int((now - reference.astimezone(timezone.utc)).total_seconds()))

    if consecutive_failures >= failure_escalation_threshold():
        return "degraded", age_seconds
    if age_seconds is None:
        return ("degraded" if consecutive_failures else "unknown"), None
    if age_seconds > max_success_age_seconds():
        return "degraded", age_seconds
    return "ok", age_seconds


def reset() -> None:
    """Clear all state (tests and controlled restarts)."""
    global _consecutive_failures, _last_failure_reason, _last_success_at, _last_failure_at
    with _lock:
        _consecutive_failures = 0
        _last_failure_reason = None
        _last_success_at = None
        _last_failure_at = None
