from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import bot.reports as reports


class FakeTarget:
    def __init__(self, chat_id=2001):
        self.chat_id = chat_id
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append((text, kwargs))


@pytest.fixture(autouse=True)
def clear_report_cooldowns():
    reports._last_report_call.clear()
    yield
    reports._last_report_call.clear()


@pytest.mark.asyncio
async def test_daily_report_rate_limit_blocks_repeated_external_calls(monkeypatch):
    get_market_data = AsyncMock(return_value=(100000.0, 1.2, 3.4))
    fetch_news = AsyncMock(return_value=[])
    create_report = AsyncMock(
        return_value={"telegram_message": "BTC daily\n\nNot financial advice."}
    )
    target = FakeTarget()

    monkeypatch.setattr(reports, "get_btc_market_data", get_market_data)
    monkeypatch.setattr(reports, "fetch_news_context", fetch_news)
    monkeypatch.setattr(reports, "create_daily_report", create_report)
    monkeypatch.setattr(reports, "remember_news_context", AsyncMock())
    monkeypatch.setattr(reports, "DB_ENABLED", False)
    monkeypatch.setattr(reports, "time", SimpleNamespace(monotonic=AsyncClock([100.0, 120.0])))

    await reports.send_daily_report_message(target)
    await reports.send_daily_report_message(target)

    assert get_market_data.await_count == 1
    assert fetch_news.await_count == 1
    assert create_report.await_count == 1
    assert target.replies == [
        ("BTC daily\n\nNot financial advice.", {}),
        ("Please wait a minute before requesting another daily report.", {}),
    ]


@pytest.mark.asyncio
async def test_weekly_report_rate_limit_allows_after_cooldown(monkeypatch):
    get_market_data = AsyncMock(return_value=(100000.0, 1.2, 3.4))
    fetch_news = AsyncMock(return_value=[])
    create_report = AsyncMock(
        return_value={"telegram_message": "BTC weekly\n\nNot financial advice."}
    )
    target = FakeTarget()

    monkeypatch.setattr(reports, "get_btc_market_data", get_market_data)
    monkeypatch.setattr(reports, "fetch_news_context", fetch_news)
    monkeypatch.setattr(reports, "create_weekly_report", create_report)
    monkeypatch.setattr(reports, "remember_news_context", AsyncMock())
    monkeypatch.setattr(reports, "DB_ENABLED", False)
    monkeypatch.setattr(reports, "time", SimpleNamespace(monotonic=AsyncClock([100.0, 161.0])))

    await reports.send_weekly_report_message(target)
    await reports.send_weekly_report_message(target)

    assert get_market_data.await_count == 2
    assert fetch_news.await_count == 2
    assert create_report.await_count == 2
    assert target.replies == [
        ("BTC weekly\n\nNot financial advice.", {}),
        ("BTC weekly\n\nNot financial advice.", {}),
    ]


class AsyncClock:
    def __init__(self, values):
        self.values = list(values)

    def __call__(self):
        return self.values.pop(0)
