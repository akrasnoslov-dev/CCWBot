from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import bot.reports as reports
from bot.db.database import Alert, Base, MarketReport, utc_now


class FakeTarget:
    def __init__(self, chat_id=2001):
        self.chat_id = chat_id
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append((text, kwargs))


class AsyncClock:
    def __init__(self, values):
        self.values = list(values)

    def monotonic(self):
        return self.values.pop(0)


async def build_session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_local = async_sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    return engine, session_local


def _daily_message() -> str:
    return (
        "Daily Market Report\n\n"
        "Market overview:\nBTC and ETH are mixed.\n\n"
        "Coins:\n• BTC: $100,000, 24h +1.0%\n\n"
        "News context:\nNo major market-wide news selected.\n\n"
        "Possible action:\nMonitor risk without rushing.\n\n"
        "Not financial advice."
    )


@pytest.fixture(autouse=True)
def clear_report_caches():
    reports._last_report_call.clear()
    reports._memory_report_cache.clear()
    yield
    reports._last_report_call.clear()
    reports._memory_report_cache.clear()


@pytest.mark.asyncio
async def test_daily_report_rate_limit_blocks_repeated_cache_reads(monkeypatch):
    target = FakeTarget()
    get_report = AsyncMock(return_value={"telegram_message": _daily_message()})

    monkeypatch.setattr(reports, "get_or_generate_report", get_report)
    monkeypatch.setattr(reports, "time", AsyncClock([100.0, 120.0]))

    await reports.send_daily_report_message(target)
    await reports.send_daily_report_message(target)

    get_report.assert_awaited_once_with("daily")
    assert target.replies == [
        (_daily_message(), {}),
        ("Please wait a minute before requesting another daily report.", {}),
    ]


@pytest.mark.asyncio
async def test_fresh_daily_report_cache_is_reused(monkeypatch):
    engine, session_local = await build_session_factory()
    now = utc_now()
    try:
        async with session_local() as session:
            session.add(
                MarketReport(
                    report_type="daily",
                    generated_at=now,
                    expires_at=now + timedelta(hours=1),
                    status="completed",
                    raw_input_json="{}",
                    raw_output_json="{}",
                    telegram_message=_daily_message(),
                    provider="groq",
                    model="report-model",
                )
            )
            await session.commit()

        monkeypatch.setattr(reports, "DB_ENABLED", True)
        monkeypatch.setattr(reports, "DB_SESSION_LOCAL", session_local)
        ask_report = AsyncMock(side_effect=AssertionError("LLM should not be called"))
        monkeypatch.setattr(reports, "ask_market_report_raw", ask_report)

        report = await reports.get_or_generate_report("daily")

        assert report.telegram_message == _daily_message()
        ask_report.assert_not_awaited()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_weekly_report_cache_is_reused(monkeypatch):
    engine, session_local = await build_session_factory()
    now = utc_now()
    weekly_message = _daily_message().replace("Daily", "Weekly")
    try:
        async with session_local() as session:
            session.add(
                MarketReport(
                    report_type="weekly",
                    generated_at=now,
                    expires_at=now + timedelta(hours=3),
                    status="completed",
                    raw_input_json="{}",
                    raw_output_json="{}",
                    telegram_message=weekly_message,
                    provider="groq",
                    model="report-model",
                )
            )
            await session.commit()

        monkeypatch.setattr(reports, "DB_ENABLED", True)
        monkeypatch.setattr(reports, "DB_SESSION_LOCAL", session_local)
        ask_report = AsyncMock(side_effect=AssertionError("LLM should not be called"))
        monkeypatch.setattr(reports, "ask_market_report_raw", ask_report)

        report = await reports.get_or_generate_report("weekly")

        assert report.telegram_message == weekly_message
        ask_report.assert_not_awaited()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_daily_and_weekly_commands_use_cached_reports_without_alert_rows(monkeypatch):
    engine, session_local = await build_session_factory()
    now = utc_now()
    target = FakeTarget()
    try:
        async with session_local() as session:
            for report_type in ("daily", "weekly"):
                session.add(
                    MarketReport(
                        report_type=report_type,
                        generated_at=now,
                        expires_at=now + timedelta(hours=1),
                        status="completed",
                        raw_input_json="{}",
                        raw_output_json="{}",
                        telegram_message=f"{report_type.title()} cached\n\nNot financial advice.",
                        provider="groq",
                        model="report-model",
                    )
                )
            await session.commit()

        monkeypatch.setattr(reports, "DB_ENABLED", True)
        monkeypatch.setattr(reports, "DB_SESSION_LOCAL", session_local)
        monkeypatch.setattr(reports, "time", AsyncClock([100.0, 161.0]))

        await reports.send_daily_report_message(target)
        await reports.send_weekly_report_message(target)

        assert [reply[0] for reply in target.replies] == [
            "Daily cached\n\nNot financial advice.",
            "Weekly cached\n\nNot financial advice.",
        ]
        async with session_local() as session:
            assert await session.scalar(select(func.count()).select_from(Alert)) == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_missing_daily_report_generates_one_global_cache_row(monkeypatch):
    engine, session_local = await build_session_factory()
    try:
        monkeypatch.setattr(reports, "DB_ENABLED", True)
        monkeypatch.setattr(reports, "DB_SESSION_LOCAL", session_local)
        monkeypatch.setattr(
            reports,
            "get_coin_market_data_batch",
            AsyncMock(
                return_value={
                    "btc": {"price": 100000.0, "change_24h": 1.0, "change_7d": None},
                    "eth": {"price": 4000.0, "change_24h": 2.0, "change_7d": None},
                    "ton": {"price": 5.0, "change_24h": -1.0, "change_7d": None},
                    "sol": {"price": 200.0, "change_24h": 0.5, "change_7d": None},
                }
            ),
        )
        monkeypatch.setattr(reports, "fetch_news_context", AsyncMock(return_value=[]))
        monkeypatch.setattr(reports, "remember_news_context", AsyncMock())
        ask_report = AsyncMock(
            return_value=(
                '{"report_type":"daily"}',
                {
                    "report_type": "daily",
                    "title": "Daily Market Report",
                    "market_overview": "Mixed market.",
                    "coin_summaries": [{"symbol": "BTC", "summary": "BTC is steady."}],
                    "news_context": "No major market-wide news selected.",
                    "possible_action": "Monitor risk without rushing.",
                    "telegram_message": _daily_message(),
                },
            )
        )
        monkeypatch.setattr(reports, "ask_market_report_raw", ask_report)

        await reports.get_or_generate_report("daily")
        await reports.get_or_generate_report("daily")

        ask_report.assert_awaited_once()
        async with session_local() as session:
            assert await session.scalar(select(func.count()).select_from(MarketReport)) == 1
            assert await session.scalar(select(func.count()).select_from(Alert)) == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_daily_command_sends_report_when_llm_omits_disclaimer(monkeypatch):
    engine, session_local = await build_session_factory()
    target = FakeTarget()
    try:
        monkeypatch.setattr(reports, "DB_ENABLED", True)
        monkeypatch.setattr(reports, "DB_SESSION_LOCAL", session_local)
        monkeypatch.setattr(
            reports,
            "get_coin_market_data_batch",
            AsyncMock(
                return_value={
                    "btc": {"price": 100000.0, "change_24h": 1.0, "change_7d": None},
                    "eth": {"price": 4000.0, "change_24h": 2.0, "change_7d": None},
                    "ton": {"price": 5.0, "change_24h": -1.0, "change_7d": None},
                    "sol": {"price": 200.0, "change_24h": 0.5, "change_7d": None},
                }
            ),
        )
        monkeypatch.setattr(reports, "fetch_news_context", AsyncMock(return_value=[]))
        monkeypatch.setattr(reports, "remember_news_context", AsyncMock())
        ask_report = AsyncMock(
            return_value=(
                '{"report_type":"daily"}',
                {
                    "report_type": "daily",
                    "title": "Daily Market Report",
                    "market_overview": "Mixed market.",
                    "coin_summaries": [{"symbol": "BTC", "summary": "BTC is steady."}],
                    "news_context": "No major market-wide news selected.",
                    "possible_action": "Monitor risk without rushing.",
                    "telegram_message": "Daily Market Report\n\nCoins:\nBTC ETH TON SOL",
                },
            )
        )
        monkeypatch.setattr(reports, "ask_market_report_raw", ask_report)

        await reports.send_daily_report_message(target)

        assert target.replies[0][0].endswith("Not financial advice.")
        assert "temporarily unavailable" not in target.replies[0][0]
        async with session_local() as session:
            saved_report = await session.scalar(select(MarketReport))
            assert saved_report.status == "completed"
            assert saved_report.telegram_message.endswith("Not financial advice.")
            assert await session.scalar(select(func.count()).select_from(Alert)) == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_failed_report_generation_does_not_create_fake_fallback(monkeypatch):
    engine, session_local = await build_session_factory()
    target = FakeTarget()
    try:
        monkeypatch.setattr(reports, "DB_ENABLED", True)
        monkeypatch.setattr(reports, "DB_SESSION_LOCAL", session_local)
        ask_report = AsyncMock(side_effect=RuntimeError("LLM should not be called"))
        monkeypatch.setattr(reports, "get_coin_market_data_batch", AsyncMock(return_value={}))
        monkeypatch.setattr(reports, "fetch_news_context", AsyncMock(return_value=[]))
        monkeypatch.setattr(reports, "ask_market_report_raw", ask_report)

        await reports.send_daily_report_message(target)

        ask_report.assert_not_awaited()
        assert target.replies == [
            ("Daily report is temporarily unavailable. Please try again later.", {})
        ]
        async with session_local() as session:
            failed = await session.scalar(select(MarketReport))
            assert failed.status == "failed"
            assert failed.telegram_message is None
            assert await session.scalar(select(func.count()).select_from(Alert)) == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_scheduled_report_cache_generation_does_not_send_telegram(monkeypatch):
    get_or_generate = AsyncMock(return_value={"telegram_message": _daily_message()})
    monkeypatch.setattr(reports, "get_or_generate_report", get_or_generate)
    context = SimpleNamespace(application=SimpleNamespace(bot=AsyncMock()))

    await reports.generate_daily_report_cache_job(context)

    get_or_generate.assert_awaited_once_with("daily")
    context.application.bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_report_input_includes_active_symbols(monkeypatch):
    captured_symbols = []

    async def fake_market_data(symbols):
        captured_symbols.extend(symbols)
        return {symbol: {"price": 1.0, "change_24h": 0.1, "change_7d": None} for symbol in symbols}

    monkeypatch.setattr(reports, "get_coin_market_data_batch", fake_market_data)
    monkeypatch.setattr(reports, "fetch_news_context", AsyncMock(return_value=[]))

    payload, _ = await reports._build_market_report_input("daily", utc_now())

    assert captured_symbols == ["btc", "eth", "ton", "sol"]
    assert [coin["symbol"] for coin in payload["coins"]] == ["BTC", "ETH", "TON", "SOL"]
