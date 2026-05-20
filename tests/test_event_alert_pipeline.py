from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import bot.alerts as alerts
from bot.db.database import (
    Alert,
    Base,
    EventAiAnalysis,
    User,
    ensure_default_coin_subscriptions,
)
from bot.handlers import _build_admin_system_status_text
from bot.services.ai_agent_groq import AIInvalidJsonError


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


async def create_user(session, telegram_user_id=1001, chat_id=2001):
    user = User(
        telegram_user_id=telegram_user_id,
        telegram_chat_id=chat_id,
        username=f"user{telegram_user_id}",
        first_name="User",
        role="user",
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    await ensure_default_coin_subscriptions(session, user_id=user.id)
    return user


def event_decision(*, should_alert=True, urgency="normal"):
    return alerts.EventAnalysisDecision(
        symbol="BTC",
        should_alert=should_alert,
        event_key="btc_downward_pressure_2026_05_20" if should_alert else None,
        title="BTC is showing renewed downside pressure" if should_alert else None,
        message_body="BTC has weakened while the 24h trend remains negative."
        if should_alert
        else None,
        related_news_ids=[],
        possible_action="Review your exposure and avoid reacting impulsively."
        if should_alert
        else None,
        urgency=urgency,
        confidence="medium",
        reason_for_no_alert=None if should_alert else "No meaningful market event detected.",
    )


@pytest.mark.asyncio
async def test_llm_should_alert_true_creates_event_alert_candidate(monkeypatch):
    recipients = [alerts.AlertRecipient(chat_id=2001, user_id=1)]
    deliver_alert = AsyncMock(return_value=True)

    monkeypatch.setattr(alerts, "DB_ENABLED", False)
    monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", None)
    monkeypatch.setattr(alerts, "resolve_symbols_to_check", AsyncMock(return_value=["btc"]))
    monkeypatch.setattr(
        alerts,
        "get_coin_market_data_batch",
        AsyncMock(return_value={"btc": {"price": 103.0, "change_24h": -1.0}}),
    )
    monkeypatch.setattr(alerts, "load_state", lambda: {"last_price": 100.0})
    monkeypatch.setattr(alerts, "save_state", lambda state: None)
    monkeypatch.setattr(
        alerts,
        "get_state_alert_settings",
        lambda state: {"automatic_check_interval_seconds": 300},
    )
    monkeypatch.setattr(alerts, "get_alert_recipients", AsyncMock(return_value=recipients))
    monkeypatch.setattr(alerts, "fetch_news_context", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        alerts,
        "_create_event_analysis_decision",
        AsyncMock(return_value=(event_decision(), 123)),
    )
    monkeypatch.setattr(
        alerts,
        "_get_or_create_event_alert_market_event",
        AsyncMock(return_value=(456, "btc_downward_pressure_2026_05_20")),
    )
    monkeypatch.setattr(alerts, "_deliver_market_event_alert", deliver_alert)
    monkeypatch.setattr(alerts, "_save_price_state", AsyncMock())

    await alerts.automatic_price_check(SimpleNamespace(application=SimpleNamespace()))

    deliver_alert.assert_awaited_once()
    assert deliver_alert.await_args.kwargs["event_type"] == "event_alert"
    assert "Not financial advice." in deliver_alert.await_args.kwargs["alert_payload"]["plain_text"]


@pytest.mark.asyncio
async def test_llm_should_alert_false_creates_no_delivery(monkeypatch):
    deliver_alert = AsyncMock(side_effect=AssertionError("delivery should not happen"))

    monkeypatch.setattr(alerts, "DB_ENABLED", False)
    monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", None)
    monkeypatch.setattr(alerts, "resolve_symbols_to_check", AsyncMock(return_value=["btc"]))
    monkeypatch.setattr(
        alerts,
        "get_coin_market_data_batch",
        AsyncMock(return_value={"btc": {"price": 150.0, "change_24h": 15.0}}),
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
        "get_alert_recipients",
        AsyncMock(return_value=[alerts.AlertRecipient(chat_id=2001, user_id=1)]),
    )
    monkeypatch.setattr(alerts, "fetch_news_context", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        alerts,
        "_create_event_analysis_decision",
        AsyncMock(return_value=(event_decision(should_alert=False), 123)),
    )
    monkeypatch.setattr(alerts, "_deliver_market_event_alert", deliver_alert)
    monkeypatch.setattr(alerts, "_save_price_state", AsyncMock())

    await alerts.automatic_price_check(SimpleNamespace(application=SimpleNamespace()))

    deliver_alert.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalid_json_creates_no_delivery_and_marks_ai_not_ok(monkeypatch):
    engine, session_local = await build_session_factory()
    try:
        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        monkeypatch.setattr("bot.handlers.DB_ENABLED", True)
        monkeypatch.setattr("bot.handlers.DB_SESSION_LOCAL", session_local)
        monkeypatch.setattr(
            alerts,
            "ask_event_analysis_raw",
            AsyncMock(side_effect=AIInvalidJsonError("bad json", raw_content="not json")),
        )
        payload = {
            "analysis_id": "event_analysis_btc_invalid",
            "symbol": "BTC",
            "candidate_news": [],
            "market_data": {},
        }

        decision, analysis_id = await alerts._create_event_analysis_decision(payload)

        assert decision is None
        assert analysis_id is None
        async with session_local() as session:
            row = await session.scalar(select(EventAiAnalysis))
            assert row.status == "invalid_json"
            assert row.raw_output_json == "not json"
        status_text = await _build_admin_system_status_text()
        assert "Groq AI status: NOT OK" in status_text
        assert "Last AI error reason: invalid JSON" in status_text
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_llm_unavailable_creates_no_delivery_and_marks_ai_not_ok(monkeypatch):
    engine, session_local = await build_session_factory()
    try:
        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        monkeypatch.setattr("bot.handlers.DB_ENABLED", True)
        monkeypatch.setattr("bot.handlers.DB_SESSION_LOCAL", session_local)
        monkeypatch.setattr(
            alerts,
            "ask_event_analysis_raw",
            AsyncMock(side_effect=RuntimeError("provider unavailable")),
        )
        payload = {
            "analysis_id": "event_analysis_btc_error",
            "symbol": "BTC",
            "candidate_news": [],
            "market_data": {},
        }

        decision, analysis_id = await alerts._create_event_analysis_decision(payload)

        assert decision is None
        assert analysis_id is None
        async with session_local() as session:
            row = await session.scalar(select(EventAiAnalysis))
            assert row.status == "llm_error"
        status_text = await _build_admin_system_status_text()
        assert "Groq AI status: NOT OK" in status_text
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_normal_urgency_respects_cooldown_and_high_urgency_shortens_it(monkeypatch):
    engine, session_local = await build_session_factory()
    now = datetime(2026, 5, 20, 12, 0, tzinfo=timezone.utc)
    try:
        async with session_local() as session:
            user = await create_user(session)
            session.add(
                Alert(
                    symbol="BTC",
                    alert_type="event_alert",
                    message="previous",
                    sent_to_chat_id=user.telegram_chat_id,
                    user_id=user.id,
                    status="sent",
                    created_at=now - timedelta(minutes=45),
                )
            )
            await session.commit()

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        recipients = [alerts.AlertRecipient(chat_id=2001, user_id=user.id)]

        assert (
            await alerts._filter_event_recipients_for_cooldown(
                recipients,
                symbol="btc",
                urgency="normal",
                cooldown_seconds=3600,
                now=now,
            )
            == []
        )
        assert await alerts._filter_event_recipients_for_cooldown(
            recipients,
            symbol="btc",
            urgency="high",
            cooldown_seconds=3600,
            now=now,
        ) == recipients
    finally:
        await engine.dispose()
