import time

import pytest

import health


@pytest.mark.asyncio
async def test_health_response_uses_state_fallback(monkeypatch):
    monkeypatch.setattr(health, "DB_ENABLED", False)
    monkeypatch.setattr(
        health,
        "load_state",
        lambda: {"last_checked_at": "2026-05-08T12:00:00+00:00"},
    )

    response = await health.health_response(time.monotonic() - 7)

    assert response["status"] == "ok"
    assert response["last_btc_check_at"] == "2026-05-08T12:00:00+00:00"
    assert response["uptime_seconds"] >= 7


@pytest.mark.asyncio
async def test_health_response_allows_missing_last_btc_check(monkeypatch):
    monkeypatch.setattr(health, "DB_ENABLED", False)
    monkeypatch.setattr(health, "load_state", lambda: {})

    response = await health.health_response(time.monotonic())

    assert response["status"] == "ok"
    assert response["last_btc_check_at"] is None
    assert "uptime_seconds" in response


@pytest.mark.asyncio
async def test_health_response_hides_read_errors(monkeypatch):
    def fail_load_state():
        raise OSError("state file failed")

    monkeypatch.setattr(health, "DB_ENABLED", False)
    monkeypatch.setattr(health, "load_state", fail_load_state)

    response = await health.health_response(time.monotonic())

    assert response["status"] == "degraded"
    assert response["last_btc_check_at"] is None
    assert response["error"] == "health_check_failed"
    assert "state file failed" not in str(response)
