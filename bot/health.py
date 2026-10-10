from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

from aiohttp import web

from bot.alerting.event_analysis import EVENT_ANALYSIS_SUCCESS_STATUSES
from bot.db.database import get_latest_event_analysis_success_at, get_price_state
from bot.observability import event_analysis_health
from bot.observability.logical_llm_health import read_logical_llm_health
from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL
from bot.storage import load_state


def _isoformat_timestamp(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value or None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


async def _read_last_btc_check_at() -> str | None:
    if DB_ENABLED and DB_SESSION_LOCAL:
        async with DB_SESSION_LOCAL() as session:
            row = await get_price_state(session, "BTC")
            return _isoformat_timestamp(row.last_checked_at if row else None)

    state = load_state()
    return _isoformat_timestamp(state.get("last_checked_at"))


async def _read_last_event_analysis_success_at() -> datetime | None:
    """Authoritative last successful Event Analysis time, or None when unavailable.

    Read from the database rather than process memory so a restart does not look like a fresh
    outage. Returns None when storage is off or the lookup fails; the caller reports that as
    ``unknown`` rather than as healthy.
    """
    if not (DB_ENABLED and DB_SESSION_LOCAL):
        return None
    async with DB_SESSION_LOCAL() as session:
        # Both statuses count. `no_alert` means the LLM answered and decided against alerting,
        # which is the overwhelmingly common outcome — treating only `success` as healthy would
        # report degraded any time no alert had fired recently, i.e. most of the time.
        return await get_latest_event_analysis_success_at(
            session, set(EVENT_ANALYSIS_SUCCESS_STATUSES)
        )


async def _read_event_analysis_logical_health():
    if not (DB_ENABLED and DB_SESSION_LOCAL):
        return None
    async with DB_SESSION_LOCAL() as session:
        results = await read_logical_llm_health(
            session, call_types=("event_analysis",)
        )
        return results["event_analysis"]


async def _event_analysis_block() -> dict[str, Any]:
    """Event Analysis health, as a nested block that never changes the top-level status.

    The Compose healthcheck fails the container whenever ``status`` is not ``"ok"``. Nothing
    here restarts it — ``restart: always`` reacts to process exit, not to health — so flipping
    ``status`` would buy no remediation and would instead mark the container ``unhealthy`` in
    ``docker compose ps`` and to any external monitor, permanently, on a bot that is still
    serving prices, heartbeats and reports. Degradation is reported *inside* the payload and
    ``status`` is left alone.
    """
    counters = event_analysis_health.snapshot()
    last_success_at = None
    logical = None
    # A shared 2s deadline below Docker's 5s healthcheck timeout.
    # Sequential reads avoid leaving a sibling DB task running after an early error.
    try:
        async with asyncio.timeout(2):
            try:
                last_success_at = await _read_last_event_analysis_success_at()
            except Exception:
                pass
            try:
                logical = await _read_event_analysis_logical_health()
            except Exception:
                pass
    except TimeoutError:
        pass
    state, age_seconds = event_analysis_health.evaluate_state(
        last_success_at=last_success_at,
        consecutive_failures=counters["consecutive_failures"],
    )
    if logical is not None:
        if logical.state == "failed":
            state = "failed"
        elif logical.state == "degraded":
            state = "degraded"
        elif logical.state == "unknown" and state == "ok":
            state = "unknown"
        elif (logical.state == "ok" and state == "degraded"
              and counters["consecutive_failures"] == 0):
            # Stale success alone is no outage when no recent work was expected.
            state = "unknown"
    elif state == "ok":
        state = "unknown"  # Missing DB telemetry cannot prove logical success.
    if logical is None or logical.operations == 0:
        if state == "degraded" and counters["consecutive_failures"] == 0:
            # No sampled workload: an old last-success timestamp is not proof of failure.
            state = "unknown"
    return {
        "state": state,
        "last_success_at": _isoformat_timestamp(last_success_at),
        "last_success_age_seconds": age_seconds,
        "consecutive_failures": counters["consecutive_failures"],
        "logical_24h": {
            "state": logical.state if logical else "unknown",
            "operations": logical.operations if logical else 0,
            "successes": logical.successes if logical else 0,
            "terminal_failures": logical.terminal_failures if logical else 0,
            "missing_outcomes": logical.missing_outcomes if logical else 0,
            "recovered_operations": logical.recovered_operations if logical else 0,
            "success_rate_percent": logical.success_rate_percent if logical else None,
        },
    }


async def health_response(started_at: float) -> dict[str, Any]:
    uptime_seconds = max(0, int(time.monotonic() - started_at))
    try:
        return {
            "status": "ok",
            "last_btc_check_at": await _read_last_btc_check_at(),
            "uptime_seconds": uptime_seconds,
            "event_analysis": await _event_analysis_block(),
        }
    except Exception:
        return {
            "status": "degraded",
            "last_btc_check_at": None,
            "uptime_seconds": uptime_seconds,
            "error": "health_check_failed",
        }


async def start_health_server(port: int, *, started_at: float | None = None) -> web.AppRunner:
    start_time = started_at if started_at is not None else time.monotonic()

    async def handle_health(_request: web.Request) -> web.Response:
        return web.json_response(await health_response(start_time))

    app = web.Application()
    app.router.add_get("/health", handle_health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    return runner


async def stop_health_server(runner: web.AppRunner | None) -> None:
    if runner is not None:
        await runner.cleanup()
