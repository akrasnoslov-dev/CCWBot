"""Regression coverage for the disabled standalone-news Event Alert path."""

from datetime import datetime, timezone

import pytest

import bot.alerts as alerts


@pytest.mark.asyncio
async def test_news_driven_flag_cannot_bypass_product_policy(monkeypatch):
    monkeypatch.setattr(alerts, "ENABLE_NEWS_DRIVEN_ALERTS", True)

    candidates = await alerts._load_news_driven_alert_candidates(
        ["btc"], now=datetime.now(timezone.utc)
    )

    assert candidates == {}


@pytest.mark.asyncio
async def test_news_driven_alerts_warning_logs_once_not_per_cycle(monkeypatch, caplog):
    monkeypatch.setattr(alerts, "ENABLE_NEWS_DRIVEN_ALERTS", True)
    monkeypatch.setattr(alerts, "_news_driven_alerts_warning_logged", False)

    with caplog.at_level("WARNING", logger=alerts.logger.name):
        for _ in range(3):
            await alerts._load_news_driven_alert_candidates(
                ["btc"], now=datetime.now(timezone.utc)
            )

    warning_count = sum(
        "ENABLE_NEWS_DRIVEN_ALERTS is set" in record.message for record in caplog.records
    )
    assert warning_count == 1
