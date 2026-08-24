"""Circuit breaker for (call_type, provider, model) triples that keep failing deterministically.

A decommissioned model does not recover on its own. Before this existed, the event-analysis
call kept hitting the same dead Groq model at full cadence for 18 days — roughly 720 doomed
requests a day, all of them consuming the shared per-account rate-limit headroom that the
still-working call types depend on.

The breaker stops that without slowing recovery down:

- Only *deterministic* failures count. Rate limits have their own backoff registry in
  :mod:`bot.services.llm.telemetry`, and timeouts/5xx are transient by nature; neither should
  latch a breaker open.
- After ``LLM_BREAKER_FAILURE_THRESHOLD`` consecutive deterministic failures the triple opens
  and is skipped. Each subsequent failure widens the interval along
  ``LLM_BREAKER_BACKOFF_SECONDS``.
- When the interval elapses the triple goes half-open: the next cycle attempts it exactly once.
  A success closes it immediately and clears all state, so a fixed provider is used again on
  the very next cycle rather than after the remaining backoff.
- Skipping is *not* failing. The router treats an open triple as "move to the next provider
  now", so a broken primary means the fallback answers this cycle, not that the cycle is lost.

State is per process and in memory, matching the existing rate-limit backoff registry. A
restart clears it, which is the safe direction: the worst case is one extra probe per triple.
"""

import logging
import os
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from bot.services.llm.env import get_int_env, warn_rejected_value

logger = logging.getLogger(__name__)

_DEFAULT_FAILURE_THRESHOLD = 5
_DEFAULT_BACKOFF_SECONDS = (60, 300, 900, 3600)

# Failure reasons that open a breaker. Two conditions must both hold, and each excludes a
# tempting-but-wrong category:
#
# 1. The failure must be *fallback-eligible*. A reason the router treats as terminal
#    (``provider_bad_request``, residual ``provider_4xx``) is a defect in our own request, so
#    it fails identically everywhere. Opening a breaker on it would skip the primary next
#    cycle and hand the same broken request to the fallback, which opens its breaker too —
#    a purely client-side bug would walk down the chain and take out every provider.
# 2. The failure must not be self-resolving. Rate limits have their own backoff registry;
#    timeouts and 5xx are transient. Neither should latch a breaker open.
#
# ``provider_json_validate_failed`` is deliberately absent even though it is fallback-eligible:
# it means the model sampled unusable output for *this* prompt, and the prompt carries fresh
# market data every cycle. The client-side equivalent (``AIInvalidJsonError``) does not open a
# breaker either, and these two must agree.
DETERMINISTIC_BREAKER_REASONS = frozenset(
    {
        "provider_model_error",
        "provider_quota_exhausted",
        "auth_error",
        "config_missing",
    }
)

# Upper bound per backoff step. Without it a zero-count typo (999999999999) makes
# ``now + timedelta(seconds=...)`` raise OverflowError — and because the breaker is updated
# from inside the router's exception handler, that would replace the real provider error and
# abort the whole chain, disabling the exact resilience this module exists to add.
_MAX_BACKOFF_SECONDS = 86_400

# How long a half-open probe may be outstanding before another probe is allowed. A probe that
# never reports back (an exception path that does not reach the breaker) must not leave the
# triple skipped forever.
_HALF_OPEN_PROBE_TIMEOUT_SECONDS = 300


@dataclass
class _BreakerState:
    consecutive_failures: int = 0
    open_until: datetime | None = None
    backoff_index: int = 0
    half_open: bool = False
    # When a half-open probe was handed out. Used to let another probe through if the first
    # one never reports back, so a triple can never be skipped indefinitely.
    probe_started_at: datetime | None = None
    last_reason: str | None = None


_states: dict[tuple[str, str, str], _BreakerState] = {}
_lock = threading.Lock()


def _failure_threshold() -> int:
    return get_int_env("LLM_BREAKER_FAILURE_THRESHOLD", _DEFAULT_FAILURE_THRESHOLD, minimum=1)


def _backoff_schedule() -> tuple[int, ...]:
    raw = os.getenv("LLM_BREAKER_BACKOFF_SECONDS")
    if raw is None or not raw.strip():
        return _DEFAULT_BACKOFF_SECONDS
    parsed: list[int] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            value = int(token)
        except ValueError:
            parsed = []
            break
        if value < 1 or value > _MAX_BACKOFF_SECONDS:
            parsed = []
            break
        parsed.append(value)
    if not parsed:
        warn_rejected_value(
            "LLM_BREAKER_BACKOFF_SECONDS",
            raw,
            f"not_a_second_list_within_1_to_{_MAX_BACKOFF_SECONDS}",
            ",".join(str(value) for value in _DEFAULT_BACKOFF_SECONDS),
        )
        return _DEFAULT_BACKOFF_SECONDS
    return tuple(parsed)


def is_enabled() -> bool:
    return os.getenv("LLM_BREAKER_ENABLED", "true").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def reset_breakers() -> None:
    """Clear all breaker state (tests and controlled restarts)."""
    with _lock:
        _states.clear()


def breaker_snapshot() -> dict[tuple[str, str, str], dict]:
    """Read-only view of current breaker state, for diagnostics."""
    with _lock:
        return {
            key: {
                "consecutive_failures": state.consecutive_failures,
                "open_until": state.open_until,
                "half_open": state.half_open,
                "last_reason": state.last_reason,
            }
            for key, state in _states.items()
        }


def should_skip(
    *,
    call_type: str,
    provider: str,
    model: str,
    now: datetime | None = None,
) -> bool:
    """True when this triple is open and must be skipped in favour of the next provider.

    Transitions an elapsed breaker to half-open and returns False for exactly one caller, so
    a single trial attempt goes through per interval even if several callers race here.
    """
    if not is_enabled():
        return False
    now = now or datetime.now(timezone.utc)
    key = (call_type, provider, model)
    with _lock:
        state = _states.get(key)
        if state is None:
            return False
        if state.half_open:
            # A probe is already outstanding: skip, unless it has been outstanding so long
            # that it plainly will not report back.
            started = state.probe_started_at
            if started is not None and (now - started).total_seconds() < (
                _HALF_OPEN_PROBE_TIMEOUT_SECONDS
            ):
                return True
        elif state.open_until is None:
            return False
        elif state.open_until > now:
            return True
        # Interval elapsed (or a stale probe timed out): hand out exactly one probe.
        state.open_until = None
        state.half_open = True
        state.probe_started_at = now
        consecutive_failures = state.consecutive_failures
    logger.info(
        "ops_event=llm_breaker_half_open provider=%s model=%s call_type=%s "
        "consecutive_failures=%s",
        provider,
        model,
        call_type,
        consecutive_failures,
    )
    return False


def record_success(*, call_type: str, provider: str, model: str) -> None:
    """Close the breaker for this triple. The first success clears all accumulated state."""
    key = (call_type, provider, model)
    with _lock:
        state = _states.pop(key, None)
    if state is None:
        return
    if state.open_until is not None or state.half_open or state.consecutive_failures:
        logger.info(
            "ops_event=llm_breaker_closed provider=%s model=%s call_type=%s",
            provider,
            model,
            call_type,
        )


def record_not_attempted(
    *,
    call_type: str,
    provider: str,
    model: str,
    now: datetime | None = None,
) -> None:
    """Return an unspent half-open probe when no request actually left the process.

    A probe can be intercepted one layer down — the provider's own rate-limit backoff refuses
    before any HTTP call — which proves nothing about whether the model is back. Without this
    the probe is consumed and ``open_until`` stays cleared, so the configured backoff schedule
    silently degrades to the half-open staleness timeout and never widens.
    """
    if not is_enabled():
        return
    now = now or datetime.now(timezone.utc)
    schedule = _backoff_schedule()
    key = (call_type, provider, model)
    with _lock:
        state = _states.get(key)
        if state is None or not state.half_open:
            return
        state.half_open = False
        state.probe_started_at = None
        # Re-arm the same interval rather than widening: nothing was learned.
        state.open_until = now + timedelta(seconds=schedule[state.backoff_index])


def record_failure(
    *,
    call_type: str,
    provider: str,
    model: str,
    reason: str,
    now: datetime | None = None,
) -> None:
    """Count a failure and open (or re-open, with a wider interval) when the threshold is hit.

    Non-deterministic reasons reset nothing and count nothing: a rate limit or timeout between
    two deterministic failures must not disguise a model that is still dead.
    """
    if not is_enabled() or reason not in DETERMINISTIC_BREAKER_REASONS:
        return
    now = now or datetime.now(timezone.utc)
    threshold = _failure_threshold()
    schedule = _backoff_schedule()
    key = (call_type, provider, model)

    with _lock:
        state = _states.setdefault(key, _BreakerState())
        state.consecutive_failures += 1
        state.last_reason = reason
        was_half_open = state.half_open
        state.half_open = False
        if state.consecutive_failures < threshold and not was_half_open:
            return
        # A failed half-open probe widens the interval; the first open uses the first step.
        if was_half_open:
            state.backoff_index = min(state.backoff_index + 1, len(schedule) - 1)
        backoff_seconds = schedule[state.backoff_index]
        state.open_until = now + timedelta(seconds=backoff_seconds)
        consecutive_failures = state.consecutive_failures

    logger.warning(
        "ops_event=llm_breaker_opened provider=%s model=%s call_type=%s reason=%s "
        "consecutive_failures=%s backoff_seconds=%s",
        provider,
        model,
        call_type,
        reason,
        consecutive_failures,
        backoff_seconds,
    )
