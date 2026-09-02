from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import bot.alerts as alerts
import bot.settings as settings
from bot.db.database import (
    Alert,
    AlertDeliveryOutcome,
    Base,
    User,
    UserCoinSubscription,
    UserPremiumTrial,
    activate_premium_from_telegram_stars_payment,
    ensure_default_coin_subscriptions,
    get_or_create_market_event,
    grant_user_premium,
    reserve_alert_delivery,
    revoke_user_premium,
    save_alert,
    set_user_coin_subscription,
    update_alert_delivery_status,
)


async def build_session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    return engine, SessionLocal


async def create_user(session, telegram_user_id, chat_id, *, is_active=True):
    user = User(
        telegram_user_id=telegram_user_id,
        telegram_chat_id=chat_id,
        username=f"user{telegram_user_id}",
        first_name="User",
        role="user",
        is_active=is_active,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    await ensure_default_coin_subscriptions(session, user_id=user.id)
    return user


@pytest.mark.asyncio
async def test_resolve_symbols_to_check_uses_enabled_active_eligible_users(monkeypatch):
    engine, SessionLocal = await build_session_factory()
    now = datetime.now(timezone.utc)
    try:
        async with SessionLocal() as session:
            free_user = await create_user(session, 1001, 2001)
            premium_user = await create_user(session, 1002, 2002)
            expired_user = await create_user(session, 1003, 2003)
            inactive_user = await create_user(session, 1004, 2004, is_active=False)

            await set_user_coin_subscription(
                session, user_id=free_user.id, symbol="btc", is_enabled=False
            )
            await set_user_coin_subscription(
                session, user_id=free_user.id, symbol="eth", is_enabled=True
            )
            await grant_user_premium(
                session,
                telegram_user_id=premium_user.telegram_user_id,
                days=10,
                now=now,
            )
            await set_user_coin_subscription(
                session, user_id=premium_user.id, symbol="btc", is_enabled=False
            )
            await set_user_coin_subscription(
                session, user_id=premium_user.id, symbol="sol", is_enabled=True
            )
            await grant_user_premium(
                session,
                telegram_user_id=expired_user.telegram_user_id,
                days=1,
                now=now - timedelta(days=2),
            )
            await set_user_coin_subscription(
                session, user_id=expired_user.id, symbol="btc", is_enabled=False
            )
            session.add(
                UserCoinSubscription(user_id=expired_user.id, symbol="xrp", is_enabled=True)
            )
            await session.commit()
            await set_user_coin_subscription(
                session, user_id=inactive_user.id, symbol="btc", is_enabled=True
            )

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", SessionLocal)

        assert await alerts.resolve_symbols_to_check(now) == ["sol"]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_resolve_symbols_includes_btc_when_active_user_enabled(monkeypatch):
    engine, SessionLocal = await build_session_factory()
    now = datetime(2026, 5, 11, tzinfo=timezone.utc)
    try:
        async with SessionLocal() as session:
            await create_user(session, 1001, 2001)

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", SessionLocal)

        assert await alerts.resolve_symbols_to_check(now) == ["btc"]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_resolve_symbols_scope_is_free_btc_and_premium_watchlist(monkeypatch):
    engine, SessionLocal = await build_session_factory()
    now = datetime(2026, 5, 11, tzinfo=timezone.utc)
    try:
        async with SessionLocal() as session:
            free_user = await create_user(session, 1001, 2001)
            premium_user = await create_user(session, 1002, 2002)
            await set_user_coin_subscription(
                session, user_id=free_user.id, symbol="eth", is_enabled=True
            )
            await grant_user_premium(
                session,
                telegram_user_id=premium_user.telegram_user_id,
                days=10,
                now=now,
            )
            await set_user_coin_subscription(
                session, user_id=premium_user.id, symbol="sol", is_enabled=True
            )

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", SessionLocal)

        assert await alerts.resolve_symbols_to_check(now) == ["btc", "sol"]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_resolve_symbols_to_check_does_not_create_default_subscriptions(monkeypatch):
    engine, SessionLocal = await build_session_factory()
    now = datetime(2026, 5, 11, tzinfo=timezone.utc)
    try:
        async with SessionLocal() as session:
            user = User(
                telegram_user_id=1001,
                telegram_chat_id=2001,
                username="user1001",
                first_name="User",
                role="user",
                is_active=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            session.add(
                UserCoinSubscription(user_id=user.id, symbol="btc", is_enabled=True)
            )
            await session.commit()

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", SessionLocal)

        assert await alerts.resolve_symbols_to_check(now) == ["btc"]
        async with SessionLocal() as session:
            assert (
                await session.scalar(select(func.count()).select_from(UserCoinSubscription))
            ) == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_get_alert_recipients_applies_premium_and_frequency(monkeypatch):
    engine, SessionLocal = await build_session_factory()
    now = datetime(2026, 5, 11, tzinfo=timezone.utc)
    try:
        async with SessionLocal() as session:
            free_user = await create_user(session, 1001, 2001)
            premium_user = await create_user(session, 1002, 2002)
            expired_user = await create_user(session, 1003, 2003)

            await set_user_coin_subscription(
                session, user_id=free_user.id, symbol="eth", is_enabled=True
            )
            await grant_user_premium(
                session,
                telegram_user_id=premium_user.telegram_user_id,
                days=10,
                now=now,
            )
            await set_user_coin_subscription(
                session, user_id=premium_user.id, symbol="eth", is_enabled=True
            )
            await grant_user_premium(
                session,
                telegram_user_id=expired_user.telegram_user_id,
                days=1,
                now=now - timedelta(days=2),
            )
            await set_user_coin_subscription(
                session, user_id=expired_user.id, symbol="eth", is_enabled=True
            )
            await save_alert(
                session,
                symbol="ETH",
                alert_type="price_movement",
                message="previous sent",
                sent_to_chat_id=2002,
                user_id=premium_user.id,
                status="failed",
            )

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", SessionLocal)

        recipients = await alerts.get_alert_recipients("eth", "price_movement", now=now)

        assert recipients == [alerts.AlertRecipient(chat_id=2002, user_id=premium_user.id)]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_get_alert_recipients_sent_status_blocks_frequency(monkeypatch):
    engine, SessionLocal = await build_session_factory()
    now = datetime(2026, 5, 11, tzinfo=timezone.utc)
    try:
        async with SessionLocal() as session:
            premium_user = await create_user(session, 1002, 2002)
            await grant_user_premium(
                session,
                telegram_user_id=premium_user.telegram_user_id,
                days=10,
                now=now,
            )
            await set_user_coin_subscription(
                session, user_id=premium_user.id, symbol="eth", is_enabled=True
            )
            await save_alert(
                session,
                symbol="ETH",
                alert_type="price_movement",
                message="previous sent",
                sent_to_chat_id=2002,
                user_id=premium_user.id,
                status="sent",
            )

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", SessionLocal)

        assert await alerts.get_alert_recipients("eth", "price_movement", now=now) == []
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_trial_unlocks_premium_delivery_then_expiry_preserves_intent(monkeypatch):
    engine, SessionLocal = await build_session_factory()
    now = datetime(2026, 5, 11, tzinfo=timezone.utc)
    try:
        async with SessionLocal() as session:
            user = await create_user(session, 1002, 2002)
            await set_user_coin_subscription(
                session,
                user_id=user.id,
                symbol="eth",
                is_enabled=True,
            )
            session.add(
                UserPremiumTrial(
                    user_id=user.id,
                    started_at=now,
                    active_until=now + timedelta(days=7),
                )
            )
            await session.commit()

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", SessionLocal)

        assert await alerts.get_alert_recipients("eth", "price_movement", now=now) == [
            alerts.AlertRecipient(chat_id=2002, user_id=user.id)
        ]
        assert await alerts.get_alert_recipients(
            "eth", "price_movement", now=now + timedelta(days=7)
        ) == []
        async with SessionLocal() as session:
            await activate_premium_from_telegram_stars_payment(
                session,
                telegram_user_id=user.telegram_user_id,
                provider_payment_id="trial-to-paid",
                telegram_payment_charge_id="trial-to-paid",
                provider_payment_charge_id="trial-to-paid-provider",
                amount=199,
                currency="XTR",
                payload="trial-to-paid",
                now=now + timedelta(days=7),
            )
        assert await alerts.get_alert_recipients(
            "eth", "price_movement", now=now + timedelta(days=7)
        ) == [alerts.AlertRecipient(chat_id=2002, user_id=user.id)]
        async with SessionLocal() as session:
            intent = await session.scalar(
                select(UserCoinSubscription).where(
                    UserCoinSubscription.user_id == user.id,
                    UserCoinSubscription.symbol == "eth",
                )
            )
        assert intent.is_enabled is True
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_revoke_ends_trial_and_paid_premium_delivery_immediately(monkeypatch):
    engine, SessionLocal = await build_session_factory()
    now = datetime(2026, 5, 11, tzinfo=timezone.utc)
    try:
        async with SessionLocal() as session:
            user = await create_user(session, 1003, 2003)
            await set_user_coin_subscription(
                session, user_id=user.id, symbol="eth", is_enabled=True
            )
            session.add(
                UserPremiumTrial(
                    user_id=user.id,
                    started_at=now,
                    active_until=now + timedelta(days=7),
                )
            )
            await grant_user_premium(
                session,
                telegram_user_id=user.telegram_user_id,
                days=10,
                now=now + timedelta(days=1),
            )
            await revoke_user_premium(
                session,
                telegram_user_id=user.telegram_user_id,
                now=now + timedelta(days=2),
            )

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", SessionLocal)

        assert await alerts.get_alert_recipients(
            "eth", "price_movement", now=now + timedelta(days=2, seconds=1)
        ) == []
    finally:
        await engine.dispose()


def test_filter_news_for_symbol_excludes_btc_only_news_for_eth():
    news = [
        {"title": "Bitcoin miners see BTC fees rise", "source": "A", "link": "https://a.test"},
        {"title": "Ethereum staking demand rises", "source": "B", "link": "https://b.test"},
        {"title": "Fed rate decision moves crypto market", "source": "C", "link": "https://c.test"},
        {"title": "Unrelated equity earnings", "source": "D", "link": "https://d.test"},
    ]

    filtered = alerts.filter_news_for_symbol("eth", news)

    assert [item["title"] for item in filtered] == [
        "Ethereum staking demand rises",
        "Fed rate decision moves crypto market",
    ]
    assert all(item["link"].startswith("https://") for item in filtered)


@pytest.mark.asyncio
async def test_delivery_reservation_is_idempotent_and_retryable():
    engine, SessionLocal = await build_session_factory()
    try:
        async with SessionLocal() as session:
            user = await create_user(session, 1001, 2001)
            market_event = await get_or_create_market_event(
                session,
                symbol="eth",
                event_type="price_movement",
                event_key="eth:price_movement:test",
                price=3000,
                previous_price=2900,
                price_change_percent=3.4,
            )
            first, should_send_first = await reserve_alert_delivery(
                session,
                user_id=user.id,
                symbol="eth",
                alert_type="price_movement",
                sent_to_chat_id=2001,
                market_event_id=market_event.id,
                event_ai_analysis_id=None,
                message="ETH alert",
            )
            second, should_send_second = await reserve_alert_delivery(
                session,
                user_id=user.id,
                symbol="ETH",
                alert_type="price_movement",
                sent_to_chat_id=2001,
                market_event_id=market_event.id,
                event_ai_analysis_id=None,
                message="ETH alert",
            )
            await update_alert_delivery_status(session, alert_id=first.id, status="failed")
            third, should_send_third = await reserve_alert_delivery(
                session,
                user_id=user.id,
                symbol="eth",
                alert_type="price_movement",
                sent_to_chat_id=2001,
                market_event_id=market_event.id,
                event_ai_analysis_id=None,
                message="ETH alert retry",
            )

            assert first.id == second.id == third.id
            assert should_send_first is True
            assert should_send_second is False
            assert should_send_third is True
            assert await session.scalar(select(func.count()).select_from(Alert)) == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_one_analysis_payload_is_delivered_to_multiple_recipients(monkeypatch):
    sent_messages = []

    class FakeBot:
        async def send_message(self, chat_id, text, parse_mode=None):
            sent_messages.append((chat_id, text, parse_mode))

    engine, SessionLocal = await build_session_factory()
    now = datetime.now(timezone.utc)
    try:
        async with SessionLocal() as session:
            first = await create_user(session, 1001, 2001)
            second = await create_user(session, 1002, 2002)
            await grant_user_premium(session, telegram_user_id=1001, days=30, now=now)
            await grant_user_premium(session, telegram_user_id=1002, days=30, now=now)
            await set_user_coin_subscription(
                session, user_id=first.id, symbol="eth", is_enabled=True
            )
            await set_user_coin_subscription(
                session, user_id=second.id, symbol="eth", is_enabled=True
            )
            market_event = await get_or_create_market_event(
                session,
                symbol="eth",
                event_type="price_movement",
                event_key="eth:price_movement:delivery",
                price=3000,
                previous_price=2900,
                price_change_percent=3.4,
            )

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", SessionLocal)

        delivered = await alerts._deliver_market_event_alert(
            SimpleNamespace(bot=FakeBot()),
            symbol="eth",
            alert_payload={"plain_text": "ETH movement alert\n\nNot financial advice."},
            market_event_id=market_event.id,
            event_ai_analysis_id=123,
        )

        assert delivered is True
        assert sent_messages == [
            (2001, "ETH movement alert\n\nNot financial advice.", None),
            (2002, "ETH movement alert\n\nNot financial advice.", None),
        ]
        async with SessionLocal() as session:
            assert await session.scalar(select(func.count()).select_from(Alert)) == 2
            assert (
                await session.scalar(select(func.count()).select_from(AlertDeliveryOutcome))
                == 2
            )
            assert {
                row.status
                for row in (await session.scalars(select(AlertDeliveryOutcome))).all()
            } == {"delivered"}
            assert {
                row.reason_code
                for row in (await session.scalars(select(AlertDeliveryOutcome))).all()
            } == {"delivered"}
            assert {
                row.decision_stage
                for row in (await session.scalars(select(AlertDeliveryOutcome))).all()
            } == {"delivery"}
            assert {
                row.decision_reason
                for row in (await session.scalars(select(AlertDeliveryOutcome))).all()
            } == {"delivered"}
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_deliver_market_event_alert_respects_empty_recipient_list(monkeypatch):
    engine, SessionLocal = await build_session_factory()
    get_recipients = AsyncMock(side_effect=AssertionError("recipients should not be queried"))
    monkeypatch.setattr(alerts, "get_alert_recipients", get_recipients)
    monkeypatch.setattr(alerts, "DB_ENABLED", True)
    monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", SessionLocal)

    try:
        delivered = await alerts._deliver_market_event_alert(
            SimpleNamespace(bot=SimpleNamespace()),
            symbol="btc",
            alert_payload={"plain_text": "BTC movement alert\n\nNot financial advice."},
            market_event_id=None,
            event_ai_analysis_id=None,
            recipients=[],
        )

        assert delivered is False
        get_recipients.assert_not_awaited()
        async with SessionLocal() as session:
            outcome = await session.scalar(select(AlertDeliveryOutcome))
            assert outcome.status == "no_eligible_recipients"
            assert outcome.reason_code == "no_recipients"
            assert outcome.recipient_considered is False
    finally:
        await engine.dispose()


def test_schedule_automatic_price_check_coalesces_overlapping_runs():
    captured_kwargs = []
    removed_names = []

    class FakeJobQueue:
        def get_jobs_by_name(self, name):
            removed_names.append(name)
            return []

        def run_repeating(self, callback, **kwargs):
            captured_kwargs.append(kwargs)

    alerts.schedule_automatic_market_check(SimpleNamespace(job_queue=FakeJobQueue()), 60)

    assert removed_names == [
        alerts.AUTOMATIC_MARKET_CHECK_JOB_NAME,
        "automatic_market_check:btc",
        "automatic_market_check:eth",
        "automatic_market_check:gram",
        "automatic_market_check:sol",
    ]
    assert [kwargs["name"] for kwargs in captured_kwargs] == [
        "automatic_market_check:btc",
        "automatic_market_check:eth",
        "automatic_market_check:gram",
        "automatic_market_check:sol",
    ]
    assert all(kwargs["interval"] == 1800 for kwargs in captured_kwargs)
    assert all(
        kwargs["job_kwargs"] == {
            "max_instances": 1,
            "coalesce": True,
            "misfire_grace_time": 15,
        }
        for kwargs in captured_kwargs
    )
    assert [kwargs["data"] for kwargs in captured_kwargs] == [
        {"symbol": "btc"},
        {"symbol": "eth"},
        {"symbol": "gram"},
        {"symbol": "sol"},
    ]


def test_legacy_automatic_btc_scheduler_alias_uses_market_job_name():
    captured_kwargs = []
    removed_names = []

    class FakeJobQueue:
        def get_jobs_by_name(self, name):
            removed_names.append(name)
            return []

        def run_repeating(self, callback, **kwargs):
            captured_kwargs.append(kwargs)

    alerts.schedule_automatic_btc_check(SimpleNamespace(job_queue=FakeJobQueue()), 60)

    assert removed_names[0] == alerts.AUTOMATIC_MARKET_CHECK_JOB_NAME
    assert [kwargs["name"] for kwargs in captured_kwargs] == [
        "automatic_market_check:btc",
        "automatic_market_check:eth",
        "automatic_market_check:gram",
        "automatic_market_check:sol",
    ]


def test_symbol_stagger_offsets_match_default_thirty_minute_cycle():
    now = datetime(2026, 6, 5, 12, 0, tzinfo=timezone.utc)

    assert alerts._symbol_stagger_offsets_seconds(
        symbols=("btc", "eth", "gram", "sol"),
        interval_seconds=1800,
    ) == {
        "btc": 0,
        "eth": 300,
        "gram": 600,
        "sol": 900,
    }
    assert alerts._seconds_until_next_symbol_check(
        symbol="btc",
        interval_seconds=1800,
        now=now,
    ) == 0
    assert alerts._seconds_until_next_symbol_check(
        symbol="eth",
        interval_seconds=1800,
        now=now,
    ) == 300
    assert alerts._seconds_until_next_symbol_check(
        symbol="gram",
        interval_seconds=1800,
        now=now,
    ) == 600
    assert alerts._seconds_until_next_symbol_check(
        symbol="sol",
        interval_seconds=1800,
        now=now,
    ) == 900


def test_symbol_first_delays_are_deterministic_after_mid_cycle_restart():
    now = datetime(2026, 6, 5, 12, 0, 43, tzinfo=timezone.utc)

    first_delays = {
        symbol: alerts._seconds_until_next_symbol_check(
            symbol=symbol,
            interval_seconds=1800,
            now=now,
        )
        for symbol in ("btc", "eth", "gram", "sol")
    }

    assert first_delays == {
        "btc": 1757,
        "eth": 257,
        "gram": 557,
        "sol": 857,
    }
    assert len(set(first_delays.values())) == len(first_delays)
    assert first_delays == {
        symbol: alerts._seconds_until_next_symbol_check(
            symbol=symbol,
            interval_seconds=1800,
            now=now,
        )
        for symbol in ("btc", "eth", "gram", "sol")
    }


def test_symbol_stagger_offsets_do_not_pair_symbols_on_shorter_interval():
    offsets = alerts._symbol_stagger_offsets_seconds(
        symbols=("btc", "eth", "gram", "sol"),
        interval_seconds=600,
    )

    assert offsets == {
        "btc": 0,
        "eth": 100,
        "gram": 200,
        "sol": 300,
    }
    assert len(set(offsets.values())) == len(offsets)


def test_state_event_analysis_interval_is_normalized_to_supported_cadence():
    assert (
        settings.get_state_alert_settings(
            {"automatic_check_interval_seconds": 600}
        )["automatic_check_interval_seconds"]
        == 1800
    )
    assert (
        settings.get_state_alert_settings(
            {"automatic_check_interval_seconds": 3600}
        )["automatic_check_interval_seconds"]
        == 1800
    )


def test_automatic_check_startup_log_shows_separated_symbol_first_delays(monkeypatch):
    captured_kwargs = []
    captured_logs = []

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 6, 5, 12, 0, tzinfo=tz)

    class FakeJobQueue:
        def get_jobs_by_name(self, name):
            return []

        def run_repeating(self, callback, **kwargs):
            captured_kwargs.append(kwargs)

    monkeypatch.setattr(alerts, "datetime", FixedDateTime)
    monkeypatch.setattr(alerts, "log", captured_logs.append)

    alerts.schedule_automatic_market_check(SimpleNamespace(job_queue=FakeJobQueue()), 1800)

    assert [kwargs["first"] for kwargs in captured_kwargs] == [0, 300, 600, 900]
    assert captured_logs == [
        "ops_event=automatic_check_scheduled "
        "interval_seconds=1800 symbol_first_delays=BTC:0s,ETH:300s,GRAM:600s,SOL:900s"
    ]


def test_report_cache_scheduler_replaces_weekly_direct_send_and_strong_signal():
    captured = []

    class FakeJobQueue:
        def get_jobs_by_name(self, name):
            return []

        def run_repeating(self, callback, **kwargs):
            captured.append((callback, kwargs))

    alerts.schedule_report_cache_generation(SimpleNamespace(job_queue=FakeJobQueue()))

    assert [kwargs["name"] for _, kwargs in captured] == [
        alerts.DAILY_REPORT_CACHE_JOB_NAME,
        alerts.WEEKLY_REPORT_CACHE_JOB_NAME,
    ]
    assert [kwargs["interval"] for _, kwargs in captured] == [4 * 3600, 24 * 3600]
    assert not hasattr(alerts, "strong_signal_check")
    assert not hasattr(alerts, "schedule_strong_signal_job")


def test_generic_sentiment_news_is_weak_not_material():
    news = [
        {
            "title": "Bitcoin analyst says euphoria may create a bear trap",
            "source": "Example",
            "link": "https://example.test/analysis",
        }
    ]

    assert alerts._classify_news_context("btc", news) == "weak"


def test_material_news_is_relevant():
    news = [
        {
            "title": "SEC approves major Bitcoin ETF flow disclosure rule",
            "source": "Example",
            "link": "https://example.test/etf",
        }
    ]

    assert alerts._classify_news_context("btc", news) == "strong"


def test_btc_soluna_revenue_article_is_weak():
    news = [
        {
            "title": (
                "Soluna revenue jumps 58% as hosting business offsets weaker Bitcoin mining"
            ),
            "source": "Example",
            "link": "https://example.test/soluna",
        }
    ]

    assert alerts._classify_news_context("btc", news) == "weak"
    assert alerts._build_news_candidates("btc", news)[0]["relevance"] == "weak"


def test_swan_lawsuit_article_is_weak_background_for_btc():
    news = [
        {
            "title": (
                "Swan Bitcoin sued for nearly $1B over pre-bankruptcy transfers "
                "from Prime Trust"
            ),
            "source": "Cointelegraph.com News",
            "link": "https://example.test/swan-bitcoin-lawsuit",
        }
    ]

    candidates = alerts._build_news_candidates("btc", news)

    assert alerts._classify_news_context("btc", news) == "weak"
    assert candidates[0]["relevance"] == "weak"
    assert "clear market catalyst" in candidates[0]["reason"]


def test_btc_is_weak_when_bitcoin_is_secondary_fund_flow_context():
    news = [
        {
            "title": (
                "XRP and Solana funds attract inflows as bitcoin outflows hit nearly $1 billion"
            ),
            "source": "Example",
            "link": "https://example.test/funds",
        }
    ]

    assert alerts._classify_news_context("btc", news) == "weak"
    assert alerts._classify_news_context("sol", news) == "medium"


def test_direct_btc_support_article_is_user_visible():
    news = [
        {
            "title": "Bitcoin price tests key support as ETF outflows pressure BTC",
            "source": "Example",
            "link": "https://example.test/btc-support",
        }
    ]

    assert alerts._classify_news_context("btc", news) in {"medium", "strong"}


@pytest.mark.asyncio
async def test_automatic_price_check_skips_ai_when_no_recipients(monkeypatch):
    save_price_state = AsyncMock()
    resolve_recipients = AsyncMock(return_value=alerts.AlertRecipientResolution(recipients=[]))
    fetch_news = AsyncMock(side_effect=AssertionError("news should not be fetched"))
    create_market_event = AsyncMock(
        side_effect=AssertionError("market event should not be created")
    )
    deliver_alert = AsyncMock(side_effect=AssertionError("delivery should not be attempted"))

    monkeypatch.setattr(alerts, "DB_ENABLED", False)
    monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", None)
    monkeypatch.setattr(alerts, "resolve_symbols_to_check", AsyncMock(return_value=["btc"]))
    monkeypatch.setattr(
        alerts,
        "get_coin_market_data_batch",
        AsyncMock(return_value={"btc": {"price": 103.0, "change_24h": 1.0, "change_7d": None}}),
    )
    monkeypatch.setattr(alerts, "load_state", lambda: {"last_price": 100.0})
    monkeypatch.setattr(alerts, "save_state", lambda state: None)
    monkeypatch.setattr(
        alerts,
        "get_state_alert_settings",
        lambda state: {"price_move_alert_percent": 2.0},
    )
    monkeypatch.setattr(alerts, "resolve_alert_recipient_outcomes", resolve_recipients)
    monkeypatch.setattr(alerts, "fetch_news_context", fetch_news)
    monkeypatch.setattr(alerts, "_get_or_create_price_movement_market_event", create_market_event)
    monkeypatch.setattr(alerts, "_deliver_market_event_alert", deliver_alert)
    monkeypatch.setattr(alerts, "_save_price_state", save_price_state)

    await alerts.automatic_price_check(SimpleNamespace(application=SimpleNamespace()))

    resolve_recipients.assert_awaited_once()
    fetch_news.assert_not_awaited()
    create_market_event.assert_not_awaited()
    deliver_alert.assert_not_awaited()
    save_price_state.assert_awaited_once()
    assert save_price_state.await_args.kwargs["last_alert_at"] is None


@pytest.mark.asyncio
async def test_automatic_price_check_persists_filtered_outcomes_before_ai(monkeypatch):
    fetch_news = AsyncMock(side_effect=AssertionError("news should not be fetched"))
    create_decision = AsyncMock(side_effect=AssertionError("LLM should not be called"))
    create_market_event = AsyncMock(
        side_effect=AssertionError("market event should not be created")
    )
    deliver_alert = AsyncMock(side_effect=AssertionError("delivery should not be attempted"))

    engine, SessionLocal = await build_session_factory()
    try:
        async with SessionLocal() as session:
            user = await create_user(session, 1001, 2001)

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", SessionLocal)
        monkeypatch.setattr(alerts, "resolve_symbols_to_check", AsyncMock(return_value=["eth"]))
        monkeypatch.setattr(
            alerts,
            "get_coin_market_data_batch",
            AsyncMock(
                return_value={"eth": {"price": 3000.0, "change_24h": 1.0, "change_7d": None}}
            ),
        )
        monkeypatch.setattr(
            alerts,
            "get_db_alert_settings",
            AsyncMock(return_value={"automatic_check_interval_seconds": 300}),
        )
        monkeypatch.setattr(alerts, "fetch_news_context", fetch_news)
        monkeypatch.setattr(alerts, "_create_event_analysis_decision", create_decision)
        monkeypatch.setattr(alerts, "_get_or_create_event_alert_market_event", create_market_event)
        monkeypatch.setattr(alerts, "_deliver_market_event_alert", deliver_alert)

        await alerts.automatic_price_check(SimpleNamespace(application=SimpleNamespace()))

        fetch_news.assert_not_awaited()
        create_decision.assert_not_awaited()
        create_market_event.assert_not_awaited()
        deliver_alert.assert_not_awaited()
        async with SessionLocal() as session:
            outcomes = (await session.scalars(select(AlertDeliveryOutcome))).all()

        assert [(row.status, row.reason_code, row.user_id) for row in outcomes] == [
            ("filtered", "watchlist_disabled", user.id),
            ("no_eligible_recipients", "no_recipients", None),
        ]
        assert outcomes[0].recipient_considered is True
        assert outcomes[0].recipient_eligible is False
        assert outcomes[1].recipient_considered is False
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_automatic_price_check_reuses_one_ai_payload_for_eligible_recipients(monkeypatch):
    recipients = [
        alerts.AlertRecipient(chat_id=2001, user_id=1),
        alerts.AlertRecipient(chat_id=2002, user_id=2),
    ]
    decision = alerts.EventAnalysisDecision(
        symbol="BTC",
        should_alert=True,
        event_key="btc_downward_pressure_2026_05_20",
        title="BTC is showing renewed downside pressure",
        message_body="BTC has weakened while the 24h trend remains negative.",
        related_news_ids=[],
        possible_action="Review your exposure and avoid reacting impulsively.",
        urgency="normal",
        confidence="medium",
        reason_for_no_alert=None,
    )
    create_decision = AsyncMock(return_value=(decision, 456))
    deliver_alert = AsyncMock(return_value=True)

    monkeypatch.setattr(alerts, "DB_ENABLED", False)
    monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", None)
    monkeypatch.setattr(alerts, "resolve_symbols_to_check", AsyncMock(return_value=["btc"]))
    monkeypatch.setattr(
        alerts,
        "get_coin_market_data_batch",
        AsyncMock(return_value={"btc": {"price": 103.0, "change_24h": 1.0, "change_7d": None}}),
    )
    monkeypatch.setattr(alerts, "load_state", lambda: {"last_price": 100.0})
    monkeypatch.setattr(alerts, "save_state", lambda state: None)
    monkeypatch.setattr(
        alerts,
        "get_state_alert_settings",
        lambda state: {"automatic_check_interval_seconds": 300},
    )
    monkeypatch.setattr(
        alerts,
        "resolve_alert_recipient_outcomes",
        AsyncMock(return_value=alerts.AlertRecipientResolution(recipients=recipients)),
    )
    monkeypatch.setattr(alerts, "fetch_news_context", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        alerts,
        "_get_or_create_event_alert_market_event",
        AsyncMock(return_value=(123, "btc:event", "instance-a", False)),
    )
    monkeypatch.setattr(alerts, "_create_event_analysis_decision", create_decision)
    monkeypatch.setattr(alerts, "_deliver_market_event_alert", deliver_alert)
    monkeypatch.setattr(alerts, "_save_price_state", AsyncMock())
    monkeypatch.setattr(alerts, "remember_news_context", AsyncMock())

    await alerts.automatic_price_check(SimpleNamespace(application=SimpleNamespace()))

    create_decision.assert_awaited_once()
    deliver_alert.assert_awaited_once()
    assert deliver_alert.await_args.kwargs["event_type"] == "event_alert"
    assert deliver_alert.await_args.kwargs["recipients"] == recipients
    assert "BTC Event Alert" in deliver_alert.await_args.kwargs["alert_payload"]["plain_text"]


@pytest.mark.asyncio
async def test_automatic_price_check_uses_product_analysis_for_each_event_group(monkeypatch):
    recipient = alerts.AlertRecipient(chat_id=2001, user_id=1)
    decision = alerts.EventAnalysisDecision(
        symbol="BTC",
        should_alert=True,
        event_key="btc_downward_pressure_2026_05_20",
        title="BTC is showing renewed downside pressure",
        message_body="BTC has weakened while the 24h trend remains negative.",
        related_news_ids=[],
        possible_action="Review your exposure and avoid reacting impulsively.",
        urgency="normal",
        confidence="medium",
        reason_for_no_alert=None,
    )
    create_decision = AsyncMock(side_effect=[(decision, 1), (decision, 2)])

    monkeypatch.setattr(alerts, "DB_ENABLED", False)
    monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", None)
    monkeypatch.setattr(alerts, "resolve_symbols_to_check", AsyncMock(return_value=["btc", "btc"]))
    monkeypatch.setattr(
        alerts,
        "get_coin_market_data_batch",
        AsyncMock(return_value={"btc": {"price": 103.0, "change_24h": 1.0, "change_7d": None}}),
    )
    monkeypatch.setattr(alerts, "load_state", lambda: {"last_price": 100.0})
    monkeypatch.setattr(alerts, "save_state", lambda state: None)
    monkeypatch.setattr(
        alerts,
        "get_state_alert_settings",
        lambda state: {
            "price_move_alert_percent": 2.0,
            "automatic_check_interval_seconds": 300,
        },
    )
    monkeypatch.setattr(
        alerts,
        "resolve_alert_recipient_outcomes",
        AsyncMock(return_value=alerts.AlertRecipientResolution(recipients=[recipient])),
    )
    monkeypatch.setattr(alerts, "fetch_news_context", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        alerts,
        "_get_or_create_event_alert_market_event",
        AsyncMock(
            side_effect=[
                (123, "btc:event:1", "instance-a", False),
                (124, "btc:event:2", "instance-b", False),
            ]
        ),
    )
    monkeypatch.setattr(alerts, "_create_event_analysis_decision", create_decision)
    monkeypatch.setattr(alerts, "_deliver_market_event_alert", AsyncMock(return_value=True))
    monkeypatch.setattr(alerts, "_save_price_state", AsyncMock())
    monkeypatch.setattr(alerts, "remember_news_context", AsyncMock())

    await alerts.automatic_price_check(SimpleNamespace(application=SimpleNamespace()))

    assert create_decision.await_count == 2
