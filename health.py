from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from aiohttp import web

from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL
from database import get_price_state
from storage import load_state


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


async def health_response(started_at: float) -> dict[str, Any]:
    uptime_seconds = max(0, int(time.monotonic() - started_at))
    try:
        return {
            "status": "ok",
            "last_btc_check_at": await _read_last_btc_check_at(),
            "uptime_seconds": uptime_seconds,
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
