"""Regression contracts for content-rich cached reports and concise admin diagnostics."""
import json
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import bot.reports as reports
from bot.alerting.market_report import MarketReportDecision
from bot.alerting.market_report_rich import (
    format_html_market_report,
    format_rich_market_report,
)
from bot.db.database import Base, LlmUsageLog, MarketReport, utc_now
from bot.handlers.admin import _llm_diagnostics_menu
from bot.observability.system_status import build_admin_llm_summary_html


def _decision(kind):
    return MarketReportDecision(
        report_type=kind,
        title="Daily Market Report" if kind == "daily" else "Weekly Market Report",
        market_pulse="The market is mixed; near-term direction remains uncertain.",
        dashboard=["BTC +1.2% 24h", "BTC +1.2% 24h"],
        coin_cards=[
            {"symbol": "BTC", "summary": "BTC +1.2% 24h", "watch": "Watch BTC support."},
            {"symbol": "ETH", "summary": "ETH is steady", "watch": "Watch Ethereum volumes."},
            {"symbol": "GRAM", "summary": "GRAM +0.4% 24h", "watch": "Watch liquidity."},
            {"symbol": "SOL", "summary": "SOL -0.7% 24h", "watch": "Watch network activity."},
        ],
        market_catalysts=["Unverified regulators move markets"],
        why_it_matters="A generic repeated statement.",
        watch_next="Monitor the next observed market interval.",
        week_timeline=["BTC opened near $80,000", "BTC closed near $82,000"],
        themes=["BTC +1.2%"],
        next_week_focus="Watch whether market breadth recovers.",
    )


@pytest.mark.parametrize("kind", ["daily", "weekly"])
def test_watchpoints_restore_distinct_coin_information_without_repeating_movements(kind):
    payload = {
        "report_type": kind,
        "active_symbols": ["BTC", "ETH", "GRAM", "SOL"],
        "coins": [
            {"symbol": s, "price": 100 + i, "change_24h_percent": 1.2,
             "change_7d_percent": -2.2}
            for i, s in enumerate(["BTC", "ETH", "GRAM", "SOL"])
        ],
        "market_news": [
            {"title": "Bitcoin ETF update", "source": "Publisher",
             "link": "https://example.org/story"}
        ],
        "coin_news": {},
    }
    message = reports._build_report_telegram_message(
        report_type=kind, input_payload=payload, decision=_decision(kind),
    )
    section = "What to monitor:" if kind == "daily" else "Coin watchpoints:"
    assert section in message
    assert "Watch BTC support." in message
    assert "Watch Ethereum volumes." in message
    assert "Bitcoin ETF update (Publisher) https://example.org/story" in message
    assert "Unverified regulators move markets" not in message
    assert "A generic repeated statement" not in message
    assert "Dashboard:" not in message
    assert "Themes of the week:" not in message
    assert "Week timeline:" not in message
    assert message.count("BTC: $100") == 1
    assert "Not financial advice." in message

    rich = format_rich_market_report(
        message, report_type=kind, chart_available=False,
    )
    assert "<h3>🔎 " in rich
    assert '<tg-emoji emoji-id="5220072735815802195">🖕</tg-emoji>' in rich
    assert '<tg-emoji emoji-id="5219946347813182032">👨‍⚕️</tg-emoji>' in rich
    # Telegram HTML fallback should show neutral emoji, never unrelated alt.
    fallback = format_html_market_report(message, report_type=kind)
    assert "<tg-emoji" not in fallback
    assert "🟠" in fallback


@pytest.mark.asyncio
async def test_outdated_cached_report_refreshes_once_globally_and_reuses_result(monkeypatch):
    reports._report_upgrade_retry_until.clear()
    reports._memory_report_cache.clear()
    monkeypatch.setattr(reports, "DB_ENABLED", False)
    now = utc_now()
    old = {
        "status": "completed",
        "report_type": "weekly",
        "telegram_message": "📊 Weekly Market Report\n\nNot financial advice.",
        "generated_at": now - timedelta(hours=1),
        "expires_at": now + timedelta(hours=10),
        "raw_input_json": json.dumps({"report_type": "weekly", "coins": []}),
    }
    new = {
        **old, "telegram_message": "Fresh weekly, with news. Not financial advice.",
        "raw_input_json": json.dumps({
            "report_type": "weekly",
            "report_content_version": reports.REPORT_CONTENT_VERSION,
            "coins": [],
        }),
    }
    reports._memory_report_cache["weekly"] = old

    async def generation(report_type):
        reports._memory_report_cache[report_type] = new
        return new

    monkeypatch.setattr(reports, "generate_report_cache", AsyncMock(side_effect=generation))
    assert await reports.get_or_generate_report("weekly") == new
    assert await reports.get_or_generate_report("weekly") == new
    assert reports.generate_report_cache.await_count == 1
    reports._memory_report_cache.clear()


@pytest.mark.asyncio
async def test_failed_format_refresh_keeps_current_cache_and_throttles_retries(monkeypatch):
    reports._report_upgrade_retry_until.clear()
    reports._memory_report_cache.clear()
    monkeypatch.setattr(reports, "DB_ENABLED", False)
    now = utc_now()
    old = {
        "status": "completed", "report_type": "daily",
        "telegram_message": "📊 Daily Market Report\n\nNot financial advice.",
        "generated_at": now, "expires_at": now + timedelta(hours=2),
        "raw_input_json": json.dumps({"report_type": "daily", "coins": []}),
    }
    reports._memory_report_cache["daily"] = old
    monkeypatch.setattr(
        reports, "generate_report_cache",
        AsyncMock(return_value={"status": "failed"}),
    )
    assert await reports.get_or_generate_report("daily") is old
    assert await reports.get_or_generate_report("daily") is old
    assert reports.generate_report_cache.await_count == 1
    assert reports._report_upgrade_retry_until["daily"] > time.monotonic()
    reports._report_upgrade_retry_until.clear()
    reports._memory_report_cache.clear()


@pytest.mark.asyncio
async def test_admin_llm_summary_is_compact_and_provider_details_are_separate():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as db:
        await db.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    now = utc_now()
    try:
        async with factory() as session:
            session.add_all([
                MarketReport(
                    report_type="weekly", status="completed",
                    generated_at=now - timedelta(minutes=8),
                    created_at=now - timedelta(minutes=8),
                    expires_at=now + timedelta(hours=4),
                    telegram_message="Test",
                ),
                MarketReport(
                    report_type="weekly", status="failed",
                    generated_at=now - timedelta(minutes=4),
                    created_at=now - timedelta(minutes=4),
                    expires_at=now + timedelta(hours=4),
                ),
                LlmUsageLog(
                    provider="groq", model="secret-alpha-model",
                    call_type="weekly_report", status="invalid_json",
                    created_at=now - timedelta(minutes=4),
                    error_message="Bearer SECRET https://secret.example",
                ),
            ])
            await session.commit()
        text = await build_admin_llm_summary_html(
            db_enabled=True, session_factory=factory, now=now,
        )
        assert "<pre>" in text
        assert "Window ending:" in text
        assert "Latest provider log:" in text
        assert "$" not in text
        assert "Weekly" in text
        assert "1" in text
        assert "Provider requests:" in text
        assert "skipped without request" in text.lower()
        assert "secret-alpha-model" not in text
        assert "SECRET" not in text
        assert len(text) < 1200
        menu = _llm_diagnostics_menu(detailed=False)
        assert menu.inline_keyboard[0][0].callback_data == "admin:llm_diagnostics_detail"
        back = _llm_diagnostics_menu(detailed=True)
        assert back.inline_keyboard[0][0].callback_data == "admin:llm_diagnostics"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_llm_summary_uses_fresh_bounded_24h_query_not_cumulative_snapshot():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as db:
        await db.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime(2026, 10, 29, 18, tzinfo=timezone.utc)
    try:
        async with factory.begin() as session:
            session.add_all([
                LlmUsageLog(
                    provider="groq", model="gpt-oss", call_type="event_analysis",
                    status="success", created_at=now - timedelta(hours=23),
                ),
                LlmUsageLog(
                    provider="groq", model="gpt-oss", call_type="event_analysis",
                    status="success", created_at=now - timedelta(hours=25),
                ),
                LlmUsageLog(
                    provider="groq", model="gpt-oss", call_type="event_analysis",
                    status="success", created_at=now + timedelta(hours=2),
                ),
            ])
        at_now = await build_admin_llm_summary_html(
            db_enabled=True, session_factory=factory, now=now,
        )
        assert "Provider requests: <b>1 succeeded · 0 failed</b>" in at_now
        assert "Window ending: 2026-10-29 18:00 UTC" in at_now
        assert "Latest provider log: 2026-10-28 19:00 UTC" in at_now

        just_after_expiry = await build_admin_llm_summary_html(
            db_enabled=True, session_factory=factory,
            now=now + timedelta(hours=1, minutes=1),
        )
        assert "Provider requests: <b>0 succeeded · 0 failed</b>" in just_after_expiry
        assert "Latest provider log: none in window" in just_after_expiry

        after_future_record = await build_admin_llm_summary_html(
            db_enabled=True, session_factory=factory,
            now=now + timedelta(hours=2, minutes=1),
        )
        assert "Provider requests: <b>1 succeeded · 0 failed</b>" in after_future_record
        assert "Latest provider log: 2026-10-29 20:00 UTC" in after_future_record
    finally:
        await engine.dispose()
