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
async def test_failed_scheduled_refresh_backs_off_before_next_poll(monkeypatch):
    generate = AsyncMock(return_value={"status": "failed"})
    monkeypatch.setattr(reports, "generate_report_cache", generate)

    first = await reports.refresh_report_cache_scheduled("weekly")
    second = await reports.refresh_report_cache_scheduled("weekly")

    assert first == {"status": "failed"}
    assert second is None
    generate.assert_awaited_once_with("weekly")
    remaining = reports._report_provider_backoff_until["weekly"] - time.monotonic()
    assert remaining > 15 * 60


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

@pytest.mark.asyncio
async def test_failed_memory_refresh_preserves_still_valid_report(monkeypatch):
    previous = _cached_report("daily", age_seconds=3 * 3600, remaining_seconds=600)
    reports._memory_report_cache["daily"] = previous
    now = utc_now()
    failed = await reports._save_or_remember_report(
        report_type="daily", generated_at=now,
        expires_at=now + timedelta(hours=4), status="failed",
        raw_input_json=None, raw_output_json=None, telegram_message=None,
        error_message="rate_limit_backoff_active",
    )
    assert failed["status"] == "failed"
    assert reports._memory_report_cache["daily"] is previous
    generate = AsyncMock(side_effect=AssertionError("must reuse successful cache"))
    monkeypatch.setattr(reports, "generate_report_cache", generate)
    assert await reports.get_or_generate_report("daily") is previous
    generate.assert_not_awaited()


@pytest.mark.asyncio
async def test_failed_scheduled_job_schedules_one_retry_and_no_retry_storm(monkeypatch):
    from types import SimpleNamespace

    queue = SimpleNamespace(get_jobs_by_name=lambda name: [], run_once=lambda *a, **kw: None)
    calls = []
    queue.run_once = lambda callback, **kwargs: calls.append((callback, kwargs))
    context = SimpleNamespace(
        application=SimpleNamespace(job_queue=queue),
        job=SimpleNamespace(name="daily_market_report_cache"),
    )
    monkeypatch.setattr(
        reports, "refresh_report_cache_scheduled", AsyncMock(return_value={"status": "failed"})
    )
    await reports.generate_daily_report_cache_job(context)
    assert len(calls) == 1
    callback, kwargs = calls[0]
    assert kwargs["when"] >= reports.REPORT_SCHEDULED_FAILURE_BACKOFF_SECONDS
    assert kwargs["when"] < reports.REPORT_SCHEDULED_FAILURE_BACKOFF_SECONDS + 120
    retry_context = SimpleNamespace(
        application=context.application, job=SimpleNamespace(name=kwargs["name"])
    )
    await callback(retry_context)
    assert len(calls) == 1
