from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import bot.reports as reports
from bot.alerting.market_report import validate_market_report_output
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
        "News context:\nNo clearly relevant fresh news found for tracked coins\n\n"
        "Possible action:\nMonitor risk without rushing.\n\n"
        "Not financial advice."
    )


def _market_data():
    return {
        "btc": {
            "price": 77361.0,
            "change_1h": 0.1,
            "change_24h": -0.4,
            "change_7d": -3.2,
            "volume_24h": 25000000000.0,
            "market_cap": 1500000000000.0,
            "rank": 1,
            "sparkline_7d": [76000.0, 78000.0, 77361.0],
            "weekly_start": 76000.0,
            "weekly_end": 77361.0,
            "weekly_high": 78000.0,
            "weekly_low": 76000.0,
            "range_position": 0.68,
        },
        "eth": {
            "price": 2127.86,
            "change_24h": -0.2,
            "change_7d": None,
            "sparkline_7d": [],
        },
        "ton": {
            "price": 3.12,
            "change_24h": None,
            "change_7d": 1.4,
            "sparkline_7d": [3.0, 3.2, 3.12],
            "weekly_start": 3.0,
            "weekly_end": 3.12,
        },
        "sol": {
            "price": 142.35,
            "change_24h": 0.7,
            "change_7d": -4.6,
            "sparkline_7d": [149.0, 145.0, 142.35],
            "weekly_start": 149.0,
            "weekly_end": 142.35,
        },
    }


def _empty_report_news_context():
    return (
        {
            "market_news": [],
            "coin_news": {"BTC": [], "ETH": [], "GRAM": [], "SOL": []},
            "fallback": "No clearly relevant fresh news found for tracked coins",
        },
        [],
    )


def _llm_report_payload(report_type="daily", **overrides):
    payload = {
        "report_type": report_type,
        "title": "Daily Market Report" if report_type == "daily" else "Weekly Market Report",
        "market_pulse": "Mixed market.",
        "dashboard": ["BTC is steady.", "ETH is mixed."],
        "coin_cards": [
            {"symbol": "BTC", "summary": "BTC is steady.", "watch": "Watch the range."},
            {"symbol": "ETH", "summary": "ETH is mixed.", "watch": "Watch ETF flow news."},
            {"symbol": "GRAM", "summary": "GRAM is steady.", "watch": "Watch liquidity."},
            {"symbol": "SOL", "summary": "SOL is steady.", "watch": "Watch network news."},
        ],
        "market_catalysts": ["No clearly relevant fresh news found for tracked coins"],
        "why_it_matters": "Mixed conditions make confirmation more useful than speed.",
        "watch_next": "Monitor risk without rushing.",
        "week_timeline": [] if report_type == "daily" else ["Midweek: BTC tested its range."],
        "themes": [] if report_type == "daily" else ["BTC led while alt participation was mixed."],
        "next_week_focus": (
            ""
            if report_type == "daily"
            else "Review whether BTC leadership broadens to ETH and SOL."
        ),
    }
    payload.update(overrides)
    return payload


@pytest.fixture(autouse=True)
def clear_report_caches():
    reports._last_report_call.clear()
    reports._memory_report_cache.clear()
    reports._report_provider_backoff_until.clear()
    yield
    reports._last_report_call.clear()
    reports._memory_report_cache.clear()
    reports._report_provider_backoff_until.clear()


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
            "get_report_market_data_batch",
            AsyncMock(return_value=_market_data()),
        )
        monkeypatch.setattr(
            reports,
            "fetch_report_news_context",
            AsyncMock(return_value=_empty_report_news_context()),
        )
        monkeypatch.setattr(reports, "remember_news_context", AsyncMock())
        ask_report = AsyncMock(
            return_value=(
                '{"report_type":"daily"}',
                _llm_report_payload("daily"),
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
            "get_report_market_data_batch",
            AsyncMock(return_value=_market_data()),
        )
        monkeypatch.setattr(
            reports,
            "fetch_report_news_context",
            AsyncMock(return_value=_empty_report_news_context()),
        )
        monkeypatch.setattr(reports, "remember_news_context", AsyncMock())
        ask_report = AsyncMock(
            return_value=(
                '{"report_type":"daily"}',
                _llm_report_payload("daily"),
            )
        )
        monkeypatch.setattr(reports, "ask_market_report_raw", ask_report)

        await reports.send_daily_report_message(target)

        assert target.replies[0][0].endswith("Not financial advice.")
        assert "adjust your strategy" not in target.replies[0][0]
        assert "temporarily unavailable" not in target.replies[0][0]
        async with session_local() as session:
            saved_report = await session.scalar(select(MarketReport))
            assert saved_report.status == "completed"
            assert saved_report.telegram_message.endswith("Not financial advice.")
            assert await session.scalar(select(func.count()).select_from(Alert)) == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_daily_report_accepts_strategy_wording(monkeypatch):
    engine, session_local = await build_session_factory()
    try:
        monkeypatch.setattr(reports, "DB_ENABLED", True)
        monkeypatch.setattr(reports, "DB_SESSION_LOCAL", session_local)
        monkeypatch.setattr(
            reports,
            "get_report_market_data_batch",
            AsyncMock(return_value=_market_data()),
        )
        monkeypatch.setattr(
            reports,
            "fetch_report_news_context",
            AsyncMock(return_value=_empty_report_news_context()),
        )
        monkeypatch.setattr(reports, "remember_news_context", AsyncMock())
        monkeypatch.setattr(
            reports,
            "ask_market_report_raw",
            AsyncMock(
                return_value=(
                    "{}",
                    _llm_report_payload(
                        "daily",
                        market_pulse="Adjust your strategy as needed while BTC is mixed.",
                        watch_next="Adjust your strategy as needed.",
                    ),
                )
            ),
        )

        report = await reports.get_or_generate_report("daily")

        assert report.status == "completed"
        assert "Adjust your strategy as needed." in report.telegram_message
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_weekly_report_backend_coin_rows_include_7d_and_24h(monkeypatch):
    engine, session_local = await build_session_factory()
    try:
        monkeypatch.setattr(reports, "DB_ENABLED", True)
        monkeypatch.setattr(reports, "DB_SESSION_LOCAL", session_local)
        monkeypatch.setattr(
            reports,
            "get_report_market_data_batch",
            AsyncMock(return_value=_market_data()),
        )
        monkeypatch.setattr(
            reports,
            "fetch_report_news_context",
            AsyncMock(return_value=_empty_report_news_context()),
        )
        monkeypatch.setattr(reports, "remember_news_context", AsyncMock())
        monkeypatch.setattr(
            reports,
            "ask_market_report_raw",
            AsyncMock(
                return_value=(
                    "{}",
                    _llm_report_payload(
                        "weekly",
                        market_pulse="Review your portfolio and adjust your strategy.",
                        next_week_focus="Review your portfolio if needed.",
                    ),
                )
            ),
        )

        report = await reports.get_or_generate_report("weekly")

        assert report.status == "completed"
        assert "• BTC: $77,361, 7d -3.2%, 24h -0.4%" in report.telegram_message
        assert "mid weekly range" in report.telegram_message
        assert "• ETH: $2,127.86, 7d unavailable from provider, 24h -0.2%" in (
            report.telegram_message
        )
        assert "• GRAM: $3.12, 7d +1.4%, 24h not enough data yet" in report.telegram_message
        assert "• SOL: $142.35, 7d -4.6%, 24h +0.7%" in report.telegram_message
        assert "Market breadth:" in report.telegram_message
        assert "1/3 tracked assets are positive over 7d" in report.telegram_message
        assert "Week timeline:" in report.telegram_message
        assert "BTC: week opened near $76,000" in report.telegram_message
        assert "ETH: 7d path unavailable from provider" in report.telegram_message
        assert report.telegram_message.endswith("Not financial advice.")
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
        monkeypatch.setattr(reports, "get_report_market_data_batch", AsyncMock(return_value={}))
        monkeypatch.setattr(
            reports,
            "fetch_report_news_context",
            AsyncMock(return_value=_empty_report_news_context()),
        )
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
            assert failed.error_message == "market data unavailable"
            assert await session.scalar(select(func.count()).select_from(Alert)) == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_report_rate_limit_failure_starts_provider_backoff(monkeypatch):
    engine, session_local = await build_session_factory()
    try:
        monkeypatch.setattr(reports, "DB_ENABLED", True)
        monkeypatch.setattr(reports, "DB_SESSION_LOCAL", session_local)
        market_data = AsyncMock(side_effect=reports.CoinGeckoRateLimitError("rate limited"))
        monkeypatch.setattr(reports, "get_report_market_data_batch", market_data)
        monkeypatch.setattr(
            reports,
            "fetch_report_news_context",
            AsyncMock(return_value=_empty_report_news_context()),
        )
        monkeypatch.setattr(
            reports,
            "ask_market_report_raw",
            AsyncMock(side_effect=AssertionError("LLM should not be called")),
        )

        first_report = await reports.get_or_generate_report("daily")
        second_report = await reports.get_or_generate_report("daily")

        assert first_report.status == "failed"
        assert first_report.error_message == "coingecko rate limit"
        assert second_report is None
        market_data.assert_awaited_once_with(["btc", "eth", "ton", "sol"])
        async with session_local() as session:
            assert await session.scalar(select(func.count()).select_from(MarketReport)) == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_failed_report_stores_exact_schema_failure(monkeypatch):
    engine, session_local = await build_session_factory()
    try:
        monkeypatch.setattr(reports, "DB_ENABLED", True)
        monkeypatch.setattr(reports, "DB_SESSION_LOCAL", session_local)
        monkeypatch.setattr(
            reports,
            "get_report_market_data_batch",
            AsyncMock(return_value=_market_data()),
        )
        monkeypatch.setattr(
            reports,
            "fetch_report_news_context",
            AsyncMock(return_value=_empty_report_news_context()),
        )
        monkeypatch.setattr(
            reports,
            "ask_market_report_raw",
            AsyncMock(
                return_value=(
                    "{}",
                    _llm_report_payload(
                        "daily",
                        coin_cards=[
                            {
                                "symbol": "XRP",
                                "summary": "XRP is steady.",
                                "watch": "Watch the range.",
                            }
                        ],
                    ),
                )
            ),
        )

        report = await reports.get_or_generate_report("daily")

        assert report.status == "failed"
        assert report.error_message == "coin card symbol is not active"
        assert report.error_message != "unknown error"
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

    monkeypatch.setattr(reports, "get_report_market_data_batch", fake_market_data)
    monkeypatch.setattr(
        reports, "fetch_report_news_context", AsyncMock(return_value=_empty_report_news_context())
    )

    payload, _ = await reports._build_market_report_input("daily", utc_now())

    assert captured_symbols == ["btc", "eth", "ton", "sol"]
    assert [coin["symbol"] for coin in payload["coins"]] == ["BTC", "ETH", "GRAM", "SOL"]
    assert payload["coins"][0] == {
        "symbol": "BTC",
        "name": "Bitcoin",
        "price": 1.0,
        "change_1h": None,
        "change_24h": 0.1,
        "change_7d": None,
        "volume_24h": None,
        "market_cap": None,
        "rank": None,
        "sparkline_7d": None,
        "weekly_start": None,
        "weekly_end": None,
        "weekly_high": None,
        "weekly_low": None,
        "range_position": None,
    }
    assert payload["market_news"] == []
    assert payload["coin_news"] == {"BTC": [], "ETH": [], "GRAM": [], "SOL": []}
    assert payload["news_fallback"] == "No clearly relevant fresh news found for tracked coins"
    assert payload["weekly_context"] == {}


@pytest.mark.asyncio
async def test_weekly_report_input_includes_breadth_and_timeline(monkeypatch):
    monkeypatch.setattr(
        reports,
        "get_report_market_data_batch",
        AsyncMock(return_value=_market_data()),
    )
    monkeypatch.setattr(
        reports,
        "fetch_report_news_context",
        AsyncMock(
            return_value=(
                {
                    "market_news": [
                        {
                            "title": "Crypto market liquidity improves",
                            "source": "CoinDesk",
                            "link": "https://example.com/market",
                            "published_at": "2026-06-25T08:00:00+00:00",
                        }
                    ],
                    "coin_news": {"BTC": [], "ETH": [], "GRAM": [], "SOL": []},
                    "fallback": "",
                },
                [],
            )
        ),
    )

    payload, _ = await reports._build_market_report_input("weekly", utc_now())

    weekly_context = payload["weekly_context"]
    assert weekly_context["breadth"]["summary"].startswith("1/3 tracked assets are positive")
    assert weekly_context["scoreboard"][0]["symbol"] == "BTC"
    assert weekly_context["scoreboard"][0]["weekly_start"] == 76000.0
    assert weekly_context["scoreboard"][0]["vs_btc_7d"] is None
    assert weekly_context["scoreboard"][2]["vs_btc_7d"] == 4.6
    assert not any("Crypto market liquidity improves" in row for row in weekly_context["timeline"])


def test_report_message_renders_market_catalysts_and_selected_news_links():
    decision = validate_market_report_output(
        _llm_report_payload(
            "daily",
            market_catalysts=["BTC 24h volume stayed elevated versus the weekly average."],
        ),
        expected_report_type="daily",
    )
    message = reports._build_report_telegram_message(
        report_type="daily",
        input_payload={
            "active_symbols": ["BTC", "ETH"],
            "coins": [],
            "market_news": [
                {
                    "title": "Crypto market liquidity improves",
                    "source": "CoinDesk",
                    "link": "https://example.com/market",
                }
            ],
            "coin_news": {
                "BTC": [],
                "ETH": [
                    {
                        "title": "Ethereum ETF inflows accelerate",
                        "source": "Cointelegraph",
                        "link": "https://example.com/eth",
                    }
                ],
            },
            "news_fallback": "",
        },
        decision=decision,
    )

    assert "BTC 24h volume stayed elevated versus the weekly average." in message
    assert "Market pulse:" in message
    assert "Coin-specific news:" in message
    assert "Crypto market liquidity improves (CoinDesk) https://example.com/market" in message
    assert "ETH: Ethereum ETF inflows accelerate (Cointelegraph) https://example.com/eth" in message


def test_report_message_renders_news_fallback_when_no_selected_news():
    decision = validate_market_report_output(
        _llm_report_payload("daily"),
        expected_report_type="daily",
    )
    message = reports._build_report_telegram_message(
        report_type="daily",
        input_payload={
            "active_symbols": ["BTC"],
            "coins": [],
            "market_news": [],
            "coin_news": {"BTC": []},
            "news_fallback": "No clearly relevant fresh news found for tracked coins",
        },
        decision=decision,
    )

    assert "No clearly relevant fresh news found for tracked coins" in message
    assert "No major market-wide news selected" not in message


def test_daily_report_message_exact_render_includes_catalysts_and_news_links():
    decision = validate_market_report_output(
        _llm_report_payload(
            "daily",
            market_pulse="Tracked assets are mixed.",
            dashboard=["BTC is steady.", "ETH is mixed."],
            market_catalysts=["BTC 24h volume stayed elevated."],
            why_it_matters="Confirmation matters more than speed.",
            watch_next="Watch whether BTC holds its current range.",
        ),
        expected_report_type="daily",
    )

    message = reports._build_report_telegram_message(
        report_type="daily",
        input_payload={
            "active_symbols": ["BTC", "ETH"],
            "coins": [
                {"symbol": "BTC", "price": 77361.0, "change_24h": -0.4},
                {"symbol": "ETH", "price": 2127.86, "change_24h": None},
            ],
            "market_news": [
                {
                    "title": "Crypto market liquidity improves",
                    "source": "CoinDesk",
                    "link": "https://example.com/market",
                }
            ],
            "coin_news": {
                "BTC": [],
                "ETH": [
                    {
                        "title": "Ethereum ETF inflows accelerate",
                        "source": "Cointelegraph",
                        "link": "https://example.com/eth",
                    }
                ],
            },
            "news_fallback": "",
        },
        decision=decision,
    )

    assert message == (
        "📊 Daily Market Report\n\n"
        "Market pulse:\n"
        "Tracked assets are mixed.\n\n"
        "Dashboard:\n"
        "• BTC is steady.\n"
        "• ETH is mixed.\n\n"
        "Tracked assets:\n"
        "• BTC: $77,361, 24h -0.4%\n"
        "• ETH: $2,127.86, 24h not enough data yet\n\n"
        "What moved today:\n"
        "• BTC is steady.\n"
        "• ETH is mixed.\n"
        "• BTC 24h volume stayed elevated.\n"
        "• Confirmation matters more than speed.\n\n"
        "Coin-specific news:\n"
        "• Crypto market liquidity improves (CoinDesk) https://example.com/market\n"
        "• ETH: Ethereum ETF inflows accelerate (Cointelegraph) https://example.com/eth\n\n"
        "What to watch next:\n"
        "Watch whether BTC holds its current range.\n\n"
        "Not financial advice."
    )


def test_daily_report_message_exact_render_uses_no_news_fallback():
    decision = validate_market_report_output(
        _llm_report_payload(
            "daily",
            market_pulse="Tracked assets are quiet.",
            dashboard=["BTC is steady."],
            market_catalysts=[],
            why_it_matters="Quiet conditions can still change quickly.",
            watch_next="Watch whether volume expands.",
        ),
        expected_report_type="daily",
    )

    message = reports._build_report_telegram_message(
        report_type="daily",
        input_payload={
            "active_symbols": ["BTC"],
            "coins": [{"symbol": "BTC", "price": 77361.0, "change_24h": -0.4}],
            "market_news": [],
            "coin_news": {"BTC": []},
            "news_fallback": "No clearly relevant fresh news found for tracked coins",
        },
        decision=decision,
    )

    assert message == (
        "📊 Daily Market Report\n\n"
        "Market pulse:\n"
        "Tracked assets are quiet.\n\n"
        "Dashboard:\n"
        "• BTC is steady.\n\n"
        "Tracked assets:\n"
        "• BTC: $77,361, 24h -0.4%\n\n"
        "What moved today:\n"
        "• BTC is steady.\n"
        "• Quiet conditions can still change quickly.\n\n"
        "Coin-specific news:\n"
        "No clearly relevant fresh news found for tracked coins\n\n"
        "What to watch next:\n"
        "Watch whether volume expands.\n\n"
        "Not financial advice."
    )


def test_weekly_report_message_exact_render_uses_breadth_timeline_and_linked_news():
    chart = "\U0001F4CA"
    bullet = "\u2022"
    sparkline = "\u2581\u2588\u2586"
    decision = validate_market_report_output(
        _llm_report_payload(
            "weekly",
            market_pulse="BTC led a mixed tracked basket.",
            dashboard=["BTC held its range.", "ETH lacked follow-through."],
            market_catalysts=["BTC range position stayed mid-weekly range."],
            why_it_matters="Participation was narrow across tracked assets.",
            themes=["BTC leadership stayed visible."],
            next_week_focus="Watch whether BTC leadership broadens to ETH and SOL.",
        ),
        expected_report_type="weekly",
    )

    message = reports._build_report_telegram_message(
        report_type="weekly",
        input_payload={
            "active_symbols": ["BTC", "ETH", "GRAM", "SOL"],
            "coins": [
                {
                    "symbol": "BTC",
                    "price": 77361.0,
                    "change_24h": -0.4,
                    "change_7d": -3.2,
                    "sparkline_7d": sparkline,
                    "range_position": 0.68,
                },
                {"symbol": "ETH", "price": 2127.86, "change_24h": -0.2, "change_7d": None},
            ],
            "market_news": [
                {
                    "title": "Crypto market liquidity improves",
                    "source": "CoinDesk",
                    "link": "https://example.com/market",
                }
            ],
            "coin_news": {
                "BTC": [],
                "ETH": [
                    {
                        "title": "Ethereum ETF inflows accelerate",
                        "source": "Cointelegraph",
                        "link": "https://example.com/eth",
                    }
                ],
                "GRAM": [],
                "SOL": [],
            },
            "news_fallback": "",
            "weekly_context": {
                "breadth": {
                    "summary": (
                        "1/3 tracked assets are positive over 7d; "
                        "leaders: GRAM, BTC; laggards: BTC, SOL"
                    )
                },
                "timeline": [
                    "BTC: week opened near $76,000, midweek near $78,000, now near $77,361",
                    "ETH: 7d path unavailable from provider",
                ],
            },
        },
        decision=decision,
    )

    assert message == (
        f"{chart} Weekly Market Report\n\n"
        "Week in one line:\n"
        "BTC led a mixed tracked basket.\n\n"
        "Weekly scoreboard:\n"
        f"{bullet} BTC: $77,361, 7d -3.2%, 24h -0.4%, {sparkline} mid weekly range\n"
        f"{bullet} ETH: $2,127.86, 7d unavailable from provider, 24h -0.2%\n\n"
        "Market breadth:\n"
        f"{bullet} 1/3 tracked assets are positive over 7d; "
        "leaders: GRAM, BTC; laggards: BTC, SOL\n\n"
        "Themes of the week:\n"
        f"{bullet} BTC leadership stayed visible.\n"
        f"{bullet} BTC held its range.\n"
        f"{bullet} ETH lacked follow-through.\n"
        f"{bullet} BTC range position stayed mid-weekly range.\n"
        f"{bullet} Participation was narrow across tracked assets.\n\n"
        "Week timeline:\n"
        f"{bullet} BTC: week opened near $76,000, midweek near $78,000, now near $77,361\n"
        f"{bullet} ETH: 7d path unavailable from provider\n\n"
        "Coin-specific recap:\n"
        f"{bullet} BTC: BTC is steady. Watch: Watch the range.\n"
        f"{bullet} ETH: ETH is mixed. Watch: Watch ETF flow news.\n"
        f"{bullet} GRAM: GRAM is steady. Watch: Watch liquidity.\n"
        f"{bullet} SOL: SOL is steady. Watch: Watch network news.\n\n"
        "Top catalysts of the week:\n"
        f"{bullet} Crypto market liquidity improves (CoinDesk) https://example.com/market\n"
        f"{bullet} ETH: Ethereum ETF inflows accelerate (Cointelegraph) https://example.com/eth\n\n"
        "Next week in focus:\n"
        "Watch whether BTC leadership broadens to ETH and SOL.\n\n"
        "Not financial advice."
    )
