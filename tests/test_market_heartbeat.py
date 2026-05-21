import json
import logging
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from telegram import MessageEntity
from telegram.constants import ParseMode

import bot.alerts as alerts
import bot.coin_icons as coin_icons
import bot.handlers as handlers
from bot.alerting.market_heartbeat import (
    MARKET_HEARTBEAT_TYPE,
    SAFE_NEUTRAL_HEARTBEAT_ACTION,
    sanitize_heartbeat_message_body,
    sanitize_heartbeat_possible_action,
    validate_market_heartbeat_output,
)
from bot.db.database import (
    Alert,
    Base,
    MarketHeartbeat,
    User,
    ensure_default_coin_subscriptions,
)
from bot.services import ai_agent_groq


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
        possible_action=SAFE_NEUTRAL_HEARTBEAT_ACTION,
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
                        "possible_action": SAFE_NEUTRAL_HEARTBEAT_ACTION,
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
        send_kwargs = app.bot.send_message.await_args.kwargs
        text = send_kwargs["text"]
        assert "BTC Market Heartbeat" in text
        assert send_kwargs["parse_mode"] == ParseMode.HTML
        assert (
            '<a href="https://example.com/btc">Bitcoin ETF flows remain steady</a> - CoinDesk'
            in text
        )
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


def test_event_and_heartbeat_rendering_use_new_labels_and_fallback_emoji(monkeypatch):
    monkeypatch.setitem(coin_icons.COIN_CUSTOM_EMOJI_IDS, "BTC", "")
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


def heartbeat_result(**overrides):
    result = {
        "symbol": "BTC",
        "title": "BTC remains calm with no major market stress",
        "message_body": "BTC is trading without a clear urgent signal.",
        "related_news_ids": [],
        "possible_action": SAFE_NEUTRAL_HEARTBEAT_ACTION,
        "confidence": "medium",
    }
    result.update(overrides)
    return result


def test_market_heartbeat_safe_neutral_wording_is_accepted():
    decision = validate_market_heartbeat_output(
        heartbeat_result(
            message_body=(
                "BTC has traded without a clear urgent signal. "
                "Watch whether the current trend continues before the next update."
            ),
            possible_action=(
                "No immediate action is suggested by this heartbeat. "
                "Continue monitoring if this coin is on your watchlist."
            ),
        ),
        expected_symbol="btc",
        candidate_news_ids=set(),
    )

    assert decision.possible_action == SAFE_NEUTRAL_HEARTBEAT_ACTION


@pytest.mark.parametrize(
    "possible_action",
    [
        "Consider reviewing your investment portfolio.",
        "Assess whether any adjustments are needed.",
        "Review your investment strategy and financial goals.",
        "Adjusting your portfolio as needed may help with risk tolerance.",
        "Consider selling if this no longer fits your plan.",
        "Consider buying only if it fits your plan.",
    ],
)
def test_market_heartbeat_possible_action_advice_like_wording_is_allowed(possible_action):
    decision = validate_market_heartbeat_output(
        heartbeat_result(possible_action=possible_action),
        expected_symbol="btc",
        candidate_news_ids=set(),
    )

    assert decision.possible_action == possible_action
    assert sanitize_heartbeat_possible_action(possible_action) == possible_action


def test_market_heartbeat_message_body_advice_like_wording_is_allowed():
    message_body = (
        "BTC has traded in a narrow range. "
        "It may be a good time to review your investment portfolio."
    )

    decision = validate_market_heartbeat_output(
        heartbeat_result(
            message_body=message_body,
            possible_action="Consider selling if this no longer fits your plan.",
        ),
        expected_symbol="btc",
        candidate_news_ids=set(),
    )

    assert decision.message_body == message_body
    assert decision.possible_action == "Consider selling if this no longer fits your plan."
    assert sanitize_heartbeat_message_body(
        message_body,
        "BTC remains under regular monitoring.",
    ) == message_body


@pytest.mark.asyncio
async def test_market_heartbeat_generation_accepts_advice_like_wording(monkeypatch):
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
                        "message_body": "BTC is calm. It may be worth reviewing your portfolio.",
                        "related_news_ids": [],
                        "possible_action": "Consider buying or selling only if it fits your plan.",
                        "confidence": "medium",
                    },
                )
            ),
        )

        await alerts.generate_market_heartbeats(SimpleNamespace())

        async with session_local() as session:
            heartbeat = await session.scalar(select(MarketHeartbeat))
        assert heartbeat.status == "completed"
        assert "reviewing your portfolio" in heartbeat.message_body
        assert "buying or selling" in heartbeat.possible_action
    finally:
        await engine.dispose()


def test_market_heartbeat_prompt_discourages_exact_numeric_repetition():
    prompt = ai_agent_groq.build_market_heartbeat_prompt(
        {
            "symbol": "BTC",
            "market_data": {
                "price_now_usd": 77566.0,
                "change_since_last_user_visible_message_percent": 0.06,
                "change_24h_percent": 0.78,
            },
            "candidate_news": [],
        }
    )

    assert "Do not repeat exact price values" in prompt
    assert "exact percentage values" in prompt
    assert "current price" in prompt
    assert "since-last-message change" in prompt
    assert "24h change" in prompt


def test_market_heartbeat_numeric_details_are_sanitized_from_message_body():
    decision = validate_market_heartbeat_output(
        heartbeat_result(
            message_body=(
                "Bitcoin is currently at $77,566 and is up 0.78% over the past 24 hours. "
                "Recent news flow is mixed, with ETF and mining stories in broader context."
            )
        ),
        expected_symbol="btc",
        candidate_news_ids=set(),
    )

    assert "$77,566" not in decision.message_body
    assert "0.78%" not in decision.message_body
    assert decision.message_body == (
        "Recent news flow is mixed, with ETF and mining stories in broader context."
    )


def test_heartbeat_rendering_preserves_cached_advice_like_text():
    heartbeat = SimpleNamespace(
        symbol="BTC",
        title="BTC remains calm",
        message_body=(
            "BTC remains under regular monitoring. "
            "Consider reviewing your investment portfolio."
        ),
        possible_action="Adjust your portfolio according to your risk tolerance.",
    )

    payload = alerts._build_market_heartbeat_payload(
        heartbeat=heartbeat,
        current_price=100000.0,
        change_since_last_message=None,
        change_24h=1.0,
        related_news=[],
    )

    text = payload["plain_text"]
    assert "BTC remains under regular monitoring." in text
    assert "investment portfolio" in text
    assert "Adjust your portfolio according to your risk tolerance." in text


def test_heartbeat_related_context_uses_direct_article_links_and_escaping():
    heartbeat = SimpleNamespace(
        symbol="BTC",
        title="BTC remains calm & steady",
        message_body="BTC is showing mild movement.",
        possible_action="Review your portfolio if it fits your own plan.",
    )
    related_news = [
        {
            "news_id": "news_a",
            "title": "SEC seeks public comment as it weighs ETFs & funds",
            "source": "Cointelegraph.com News",
            "url": "https://cointelegraph.com/news/sec?x=1&y=2",
        }
    ]

    payload = alerts._build_market_heartbeat_payload(
        heartbeat=heartbeat,
        current_price=100000.0,
        change_since_last_message=0.6,
        change_24h=1.0,
        related_news=related_news,
    )

    assert payload["html_text"] is not None
    assert (
        '<a href="https://cointelegraph.com/news/sec?x=1&amp;y=2">'
        "SEC seeks public comment as it weighs ETFs &amp; funds</a> - Cointelegraph.com News"
        in payload["html_text"]
    )
    assert "BTC remains calm &amp; steady" in payload["html_text"]


def test_heartbeat_related_context_missing_url_stays_plain_text():
    heartbeat = SimpleNamespace(
        symbol="BTC",
        title="BTC remains calm",
        message_body="BTC is showing mild movement.",
        possible_action="No urgent action appears necessary.",
    )
    related_news = [
        {
            "news_id": "news_a",
            "title": "Bitcoin ETF flows remain steady",
            "source": "CoinDesk",
            "url": "",
        }
    ]

    payload = alerts._build_market_heartbeat_payload(
        heartbeat=heartbeat,
        current_price=100000.0,
        change_since_last_message=0.6,
        change_24h=1.0,
        related_news=related_news,
    )

    assert payload["html_text"] is None
    assert "• Bitcoin ETF flows remain steady - CoinDesk" in payload["plain_text"]


def test_heartbeat_related_context_empty_selection_is_preserved():
    heartbeat = SimpleNamespace(
        symbol="BTC",
        title="BTC remains calm",
        message_body="BTC is showing mild movement.",
        possible_action="No urgent action appears necessary.",
    )

    payload = alerts._build_market_heartbeat_payload(
        heartbeat=heartbeat,
        current_price=100000.0,
        change_since_last_message=0.6,
        change_24h=1.0,
        related_news=[],
    )

    assert payload["html_text"] is None
    assert "No major related news selected." in payload["plain_text"]


def test_event_alert_validation_still_allows_existing_cautious_event_wording():
    decision = alerts.validate_event_analysis_output(
        {
            "symbol": "BTC",
            "should_alert": True,
            "event_key": "btc_market_event_2026_05_21",
            "title": "BTC volatility is rising",
            "message_body": "BTC moved faster than usual.",
            "related_news_ids": [],
            "possible_action": "Review exposure and avoid reacting impulsively.",
            "urgency": "normal",
            "confidence": "medium",
            "reason_for_no_alert": None,
        },
        expected_symbol="btc",
        candidate_news_ids=set(),
    )

    assert decision.should_alert is True


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
