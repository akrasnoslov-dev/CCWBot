"""Scheduled report cache refresh: cadence, grace window, and explicit skip logging.

Regression tests for the production weekly-report staleness (2026-07-14 ops report):
the scheduled job fires at exactly the cache expiry interval, so the cache was always
fresh by a few seconds at fire time, the job skipped silently, and the effective weekly
regeneration cadence doubled to ~48h.
"""

import logging
import time
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest

import bot.reports as reports
from bot.db.database import utc_now


def _cached_report(report_type, *, age_seconds, remaining_seconds):
    now = utc_now()
    return {
        "report_type": report_type,
        "generated_at": now - timedelta(seconds=age_seconds),
        "expires_at": now + timedelta(seconds=remaining_seconds),
        "status": "completed",
        "telegram_message": "Cached report. Not financial advice.",
    }


@pytest.fixture(autouse=True)
def _clear_report_caches():
    reports._memory_report_cache.clear()
    reports._report_provider_backoff_until.clear()
    yield
    reports._memory_report_cache.clear()
    reports._report_provider_backoff_until.clear()


@pytest.mark.asyncio
async def test_expired_weekly_cache_triggers_regeneration(monkeypatch):
    reports._memory_report_cache["weekly"] = _cached_report(
        "weekly", age_seconds=25 * 3600, remaining_seconds=-3600
    )
    generate = AsyncMock(return_value={"status": "completed"})
    monkeypatch.setattr(reports, "generate_report_cache", generate)

    await reports.refresh_report_cache_scheduled("weekly")

    generate.assert_awaited_once_with("weekly")


@pytest.mark.asyncio
async def test_fresh_weekly_cache_skips_with_explicit_log(monkeypatch, caplog):
    reports._memory_report_cache["weekly"] = _cached_report(
        "weekly", age_seconds=3600, remaining_seconds=23 * 3600
    )
    generate = AsyncMock(return_value={"status": "completed"})
    monkeypatch.setattr(reports, "generate_report_cache", generate)

    with caplog.at_level(logging.INFO):
        result = await reports.refresh_report_cache_scheduled("weekly")

    generate.assert_not_awaited()
    assert result is reports._memory_report_cache["weekly"]
    skip_lines = [
        record.getMessage()
        for record in caplog.records
        if "market_report_refresh_skipped" in record.getMessage()
    ]
    assert len(skip_lines) == 1, "a scheduled skip must never be silent"
    assert "report_type=weekly" in skip_lines[0]
    assert "cache_age_seconds=" in skip_lines[0]
    assert "expiry_seconds=86400" in skip_lines[0]


@pytest.mark.asyncio
async def test_weekly_cache_fresh_by_seconds_at_fire_time_regenerates(monkeypatch):
    # The 48h-cadence bug: the job fires ~1 minute before the 24h expiry, the cache is
    # technically still fresh, and the old skip-if-fresh check silently kept it. The
    # scheduled refresh must regenerate a cache that expires within the grace window.
    reports._memory_report_cache["weekly"] = _cached_report(
        "weekly", age_seconds=24 * 3600 - 60, remaining_seconds=60
    )
    generate = AsyncMock(return_value={"status": "completed"})
    monkeypatch.setattr(reports, "generate_report_cache", generate)

    await reports.refresh_report_cache_scheduled("weekly")

    generate.assert_awaited_once_with("weekly")


@pytest.mark.asyncio
async def test_daily_cache_fresh_by_seconds_at_fire_time_regenerates(monkeypatch):
    # The daily job has the same interval == expiry mismatch (4h/4h); apply the same check.
    reports._memory_report_cache["daily"] = _cached_report(
        "daily", age_seconds=4 * 3600 - 60, remaining_seconds=60
    )
    generate = AsyncMock(return_value={"status": "completed"})
    monkeypatch.setattr(reports, "generate_report_cache", generate)

    await reports.refresh_report_cache_scheduled("daily")

    generate.assert_awaited_once_with("daily")


@pytest.mark.asyncio
async def test_scheduled_refresh_respects_provider_backoff(monkeypatch, caplog):
    reports._report_provider_backoff_until["weekly"] = time.monotonic() + 300
    generate = AsyncMock(return_value={"status": "completed"})
    monkeypatch.setattr(reports, "generate_report_cache", generate)

    with caplog.at_level(logging.INFO):
        result = await reports.refresh_report_cache_scheduled("weekly")

    assert result is None
    generate.assert_not_awaited()
    assert any(
        "market_report_skipped" in record.getMessage()
        and "reason=provider_backoff" in record.getMessage()
        for record in caplog.records
    )
