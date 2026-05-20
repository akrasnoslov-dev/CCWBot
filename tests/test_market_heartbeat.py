import json
import logging
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from telegram import MessageEntity

import bot.alerts as alerts
import bot.coin_icons as coin_icons
import bot.handlers as handlers
from bot.alerting.market_heartbeat import MARKET_HEARTBEAT_TYPE
from bot.db.database import (
    Alert,
    Base,
    MarketHeartbeat,
    User,
    ensure_default_coin_subscriptions,
)


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


async def create_user(session, *, chat_id=2001, frequency=3600):
    user = User(
        telegram_user_id=1001,
        telegram_chat_id=chat_id,
        username="user1001",
        first_name="User",
        role="user",
        is_active=True,
        alert_frequency_seconds=frequency,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    await ensure_default_coin_subscriptions(session, user_id=user.id)
    return user


def heartbeat_raw_input(candidate_news=None):
    return json.dumps(
        {
            "symbol": "BTC",
            "candidate_news": candidate_news or [],
            "market_data": {
                "price_now_usd": 100000.0,
                "change_24h_percent": 1.2,
            },
        }
    )


async def create_heartbeat(session, *, generated_at=None):
    heartbeat = MarketHeartbeat(
        symbol="BTC",
        generated_at=generated_at or datetime.now(timezone.utc),
        raw_input_json=heartbeat_raw_input(
            [
                {
                    "news_id": "news_a",
                    "title": "Bitcoin ETF flows remain steady",
                    "source": "CoinDesk",
                    "url": "https://example.com/btc",
                }
            ]
        ),
        raw_output_json="{}",
        title="BTC remains calm with no major market stress",
        message_body="BTC is trading without a clear urgent signal.",
        related_news_ids=json.dumps(["news_a"]),
        possible_action="No urgent action appears necessary. Keep monitoring risk exposure.",
        confidence="medium",
        status="completed",
    )
    session.add(heartbeat)
    await session.commit()
    await session.refresh(heartbeat)
    return heartbeat


def fake_app():
    return SimpleNamespace(bot=SimpleNamespace(send_message=AsyncMock()))


def test_candidate_news_filter_returns_relevant_coin_and_market_items():
    news_items = [
        {"title": "Solana outage hits validators", "source": "A"},
        {"title": "Bitcoin mining company revenue rises", "source": "B"},
        {"title": "SEC crypto market regulation update", "source": "C"},
        {"title": "Sports result unrelated", "source": "D"},
    ]

    filtered = alerts.filter_news_for_symbol("sol", news_items)

    titles = [item["title"] for item in filtered]
    assert "Solana outage hits validators" in titles
    assert "SEC crypto market regulation update" in titles
    assert "Bitcoin mining company revenue rises" not in titles
    assert "Sports result unrelated" not in titles


def test_candidate_news_filter_max_limits_work():
    direct = [{"title": f"Bitcoin headline {index}"} for index in range(8)]
    market = [{"title": f"SEC crypto market update {index}"} for index in range(6)]

    filtered = alerts.filter_news_for_symbol(
        "btc",
        direct + market,
        max_direct=3,
        max_market_wide=2,
    )

    assert len(filtered) == 5
    assert sum("Bitcoin" in item["title"] for item in filtered) == 3
    assert sum("SEC crypto" in item["title"] for item in filtered) == 2


@pytest.mark.asyncio
async def test_heartbeat_generation_stores_record_without_delivery(monkeypatch):
    engine, session_local = await build_session_factory()
    try:
        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        monkeypatch.setattr(alerts, "SUPPORTED_SYMBOLS", ("btc",))
        monkeypatch.setattr(
            alerts,
            "get_coin_market_data_batch",
            AsyncMock(return_value={"btc": {"price": 100000.0, "change_24h": 1.2}}),
        )
        monkeypatch.setattr(alerts, "fetch_news_context", AsyncMock(return_value=[]))
        monkeypatch.setattr(
            alerts,
            "ask_market_heartbeat_raw",
            AsyncMock(
                return_value=(
                    "{}",
                    {
                        "symbol": "BTC",
                        "title": "BTC remains calm with no major market stress",
                        "message_body": "BTC is trading without a clear urgent signal.",
                        "related_news_ids": [],
                        "possible_action": (
                            "No urgent action appears necessary. Keep monitoring risk exposure."
                        ),
                        "confidence": "medium",
                    },
                )
            ),
        )

        await alerts.generate_market_heartbeats(SimpleNamespace())

        async with session_local() as session:
            heartbeats = list((await session.scalars(select(MarketHeartbeat))).all())
            deliveries = list((await session.scalars(select(Alert))).all())
        assert len(heartbeats) == 1
        assert heartbeats[0].status == "completed"
        assert deliveries == []
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_heartbeat_is_sent_when_frequency_due(monkeypatch):
    engine, session_local = await build_session_factory()
    app = fake_app()
    try:
        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        async with session_local() as session:
            user = await create_user(session)
            await create_heartbeat(session)

        sent = await alerts._deliver_market_heartbeat(
            app,
            symbol="btc",
            current_price=101000.0,
            change_24h=1.5,
            now=datetime.now(timezone.utc),
        )

        assert sent is True
        app.bot.send_message.assert_awaited_once()
        text = app.bot.send_message.await_args.kwargs["text"]
        assert "BTC Market Heartbeat" in text
        assert "No major related news selected." not in text
        async with session_local() as session:
            row = await session.scalar(select(Alert).where(Alert.user_id == user.id))
        assert row.alert_type == MARKET_HEARTBEAT_TYPE
        assert row.status == "sent"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_heartbeat_is_not_sent_if_recent_event_alert_exists(monkeypatch):
    engine, session_local = await build_session_factory()
    app = fake_app()
    now = datetime.now(timezone.utc)
    try:
        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        async with session_local() as session:
            user = await create_user(session, frequency=3600)
            await create_heartbeat(session)
            session.add(
                Alert(
                    symbol="BTC",
                    alert_type="event_alert",
                    message="previous",
                    sent_to_chat_id=user.telegram_chat_id,
                    user_id=user.id,
                    status="sent",
                    created_at=now - timedelta(minutes=10),
                )
            )
            await session.commit()

        sent = await alerts._deliver_market_heartbeat(
            app,
            symbol="btc",
            current_price=101000.0,
            change_24h=1.5,
            now=now,
        )

        assert sent is False
        app.bot.send_message.assert_not_awaited()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_heartbeat_missing_or_stale_is_not_sent(monkeypatch):
    engine, session_local = await build_session_factory()
    app = fake_app()
    now = datetime.now(timezone.utc)
    try:
        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        async with session_local() as session:
            await create_user(session)

        assert (
            await alerts._deliver_market_heartbeat(
                app,
                symbol="btc",
                current_price=101000.0,
                change_24h=1.5,
                now=now,
            )
            is False
        )

        async with session_local() as session:
            await create_heartbeat(session, generated_at=now - timedelta(hours=3))

        assert (
            await alerts._deliver_market_heartbeat(
                app,
                symbol="btc",
                current_price=101000.0,
                change_24h=1.5,
                now=now,
            )
            is False
        )
        app.bot.send_message.assert_not_awaited()
    finally:
        await engine.dispose()


def test_event_and_heartbeat_rendering_use_new_labels_and_fallback_emoji():
    decision = alerts.EventAnalysisDecision(
        symbol="BTC",
        should_alert=True,
        event_key="btc_event",
        title="BTC volatility is rising",
        message_body="BTC moved faster than usual.",
        related_news_ids=[],
        possible_action="Review risk exposure calmly.",
        urgency="normal",
        confidence="medium",
        reason_for_no_alert=None,
    )
    input_payload = {
        "market_data": {
            "price_now_usd": 100000.0,
            "change_since_last_user_visible_message_percent": 1.2,
            "change_24h_percent": 2.3,
        }
    }
    event_payload = alerts._build_event_alert_payload(
        decision=decision,
        input_payload=input_payload,
        related_news=[],
    )
    heartbeat = SimpleNamespace(
        symbol="BTC",
        title="BTC remains calm",
        message_body="BTC remains under regular monitoring.",
        possible_action="No urgent action appears necessary.",
    )
    heartbeat_payload = alerts._build_market_heartbeat_payload(
        heartbeat=heartbeat,
        current_price=100000.0,
        change_since_last_message=None,
        change_24h=1.0,
        related_news=[],
    )

    combined = event_payload["plain_text"] + "\n" + heartbeat_payload["plain_text"]
    assert "BTC Event Alert" in combined
    assert "BTC Market Heartbeat" in combined
    assert combined.startswith("🟠")
    assert "Market Update" not in combined
    assert "Important Alert" not in combined
    assert "Critical Alert" not in combined
    assert "Strong Signal" not in combined
    assert event_payload["entities"] is None


def test_custom_emoji_entity_is_used_when_id_exists(monkeypatch):
    monkeypatch.setitem(coin_icons.COIN_CUSTOM_EMOJI_IDS, "BTC", "custom-btc-id")

    decision = alerts.EventAnalysisDecision(
        symbol="BTC",
        should_alert=True,
        event_key="btc_event",
        title="BTC volatility is rising",
        message_body="BTC moved faster than usual.",
        related_news_ids=[],
        possible_action="Review risk exposure calmly.",
        urgency="normal",
        confidence="medium",
        reason_for_no_alert=None,
    )
    payload = alerts._build_event_alert_payload(
        decision=decision,
        input_payload={
            "market_data": {
                "price_now_usd": 100000.0,
                "change_since_last_user_visible_message_percent": None,
                "change_24h_percent": 1.0,
            }
        },
        related_news=[],
    )

    assert payload["entities"][0].custom_emoji_id == "custom-btc-id"


@pytest.mark.asyncio
async def test_custom_emoji_logging_helper_logs_admin_entities(monkeypatch, caplog):
    monkeypatch.setattr(handlers, "is_admin_update", AsyncMock(return_value=True))
    entity = SimpleNamespace(
        type=MessageEntity.CUSTOM_EMOJI,
        offset=0,
        length=2,
        custom_emoji_id="custom-emoji-1",
    )
    message = SimpleNamespace(
        text="🟠 BTC",
        caption=None,
        entities=[entity],
        caption_entities=[],
    )
    update = SimpleNamespace(effective_message=message)

    with caplog.at_level(logging.INFO, logger="bot.handlers"):
        await handlers.log_custom_emoji_ids(update, SimpleNamespace())

    assert "custom_emoji_id=custom-emoji-1" in caplog.text
