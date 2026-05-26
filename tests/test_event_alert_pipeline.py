from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from telegram import MessageEntity

import bot.alerts as alerts
from bot.alerting.event_analysis import canonicalize_event_key
from bot.db.database import (
    Alert,
    Base,
    EventAiAnalysis,
    MarketEvent,
    User,
    UserPremiumSubscription,
    ensure_default_coin_subscriptions,
    save_price_snapshot,
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


async def seed_sent_event_alert(
    session,
    *,
    user_id: int,
    chat_id: int,
    symbol: str,
    event_key: str,
    created_at: datetime,
):
    event = MarketEvent(
        symbol=symbol.upper(),
        event_type=alerts.EVENT_ALERT_TYPE,
        event_key=event_key,
        event_instance_key=f"{symbol}:{event_key}:{user_id}:{created_at.isoformat()}",
        price=100.0,
        previous_price=99.0,
        price_change_percent=1.0,
        detected_at=created_at,
    )
    session.add(event)
    await session.flush()
    session.add(
        Alert(
            symbol=symbol.upper(),
            alert_type=alerts.EVENT_ALERT_TYPE,
            message="previous",
            sent_to_chat_id=chat_id,
            user_id=user_id,
            market_event_id=event.id,
            status="sent",
            created_at=created_at,
        )
    )
    await session.commit()
    await session.refresh(event)
    return event


def _utf16_slice(value: str, offset: int, length: int) -> str:
    encoded = value.encode("utf-16-le")
    start = offset * 2
    end = start + length * 2
    return encoded[start:end].decode("utf-16-le")


def event_decision(*, should_alert=True, urgency="normal", related_news_ids=None):
    return alerts.EventAnalysisDecision(
        symbol="BTC",
        should_alert=should_alert,
        event_key="btc_downward_pressure_2026_05_20" if should_alert else None,
        title="BTC is showing renewed downside pressure" if should_alert else None,
        message_body="BTC has weakened while the 24h trend remains negative."
        if should_alert
        else None,
        related_news_ids=list(related_news_ids or []),
        possible_action="Review your exposure and avoid reacting impulsively."
        if should_alert
        else None,
        urgency=urgency if should_alert else None,
        confidence="medium" if should_alert else None,
        reason_for_no_alert=None if should_alert else "No meaningful market event detected.",
    )


def test_event_instance_key_reuses_same_bucket_and_splits_distinct_occurrences():
    first = alerts._build_event_instance_key(
        symbol="btc",
        event_key="btc_price_volatility",
        timestamp_value="2026-05-22T12:15:00+00:00",
        related_news_ids=["n2", "n1"],
        input_hash="hash-a",
    )
    same_bucket = alerts._build_event_instance_key(
        symbol="BTC",
        event_key="btc_price_volatility",
        timestamp_value="2026-05-22T12:45:00+00:00",
        related_news_ids=["n1", "n2"],
        input_hash="hash-b",
    )
    next_bucket = alerts._build_event_instance_key(
        symbol="btc",
        event_key="btc_price_volatility",
        timestamp_value="2026-05-22T13:00:00+00:00",
        related_news_ids=["n1", "n2"],
        input_hash="hash-a",
    )
    no_news_different_input = alerts._build_event_instance_key(
        symbol="btc",
        event_key="btc_price_volatility",
        timestamp_value="2026-05-22T12:15:00+00:00",
        related_news_ids=[],
        input_hash="hash-c",
    )

    assert first == same_bucket
    assert next_bucket != first
    assert no_news_different_input != first


@pytest.mark.parametrize(
    ("raw_event_key", "expected"),
    [
        ("BTC_price_volatility", "btc_price_volatility"),
        ("bitcoin_price_volatility", "btc_price_volatility"),
        ("btc_price_volatility_2026-05-25", "btc_price_volatility"),
        ("Bitcoin-options-Nadaq", "btc_options_nasdaq"),
    ],
)
def test_canonical_event_key_normalizes_common_llm_variants(raw_event_key, expected):
    result = canonicalize_event_key("btc", raw_event_key)

    assert result.canonical_event_key == expected


def test_canonical_event_key_replaces_random_analysis_key_with_stable_fallback():
    result = canonicalize_event_key(
        "btc",
        "event_analysis_btc_03ff98fbf7d54bbab079af2500ec0dd7",
        title="BTC volatility returns around options expiry",
        message_body="Bitcoin price action became choppy as options positioning shifted.",
    )

    assert result.canonical_event_key != "event_analysis_btc_03ff98fbf7d54bbab079af2500ec0dd7"
    assert result.canonical_event_key.startswith("btc_")
    assert result.reason == "fallback_random"


def test_empty_event_key_derives_stable_fallback():
    first = canonicalize_event_key(
        "btc",
        "",
        title="BTC volatility returns",
        message_body="Bitcoin price action became choppy.",
    )
    second = canonicalize_event_key(
        "BTC",
        None,
        title="BTC volatility returns",
        message_body="Bitcoin price action became choppy.",
    )

    assert first.canonical_event_key == second.canonical_event_key
    assert first.canonical_event_key.startswith("btc_")
    assert first.reason == "fallback_empty"


def test_event_alert_related_context_uses_clickable_article_entities():
    decision = event_decision(related_news_ids=["n1"])
    related_news = [
        {
            "news_id": "n1",
            "title": (
                "Bitcoin ETF flows & custody <update> - "
                "CoinDesk: Bitcoin, Ethereum, Crypto News and Price Data"
            ),
            "source": 'CoinDesk "Markets"',
            "url": "https://example.test/btc?x=1&y=2",
        }
    ]

    payload = alerts._build_event_alert_payload(
        decision=decision,
        input_payload={"market": {"price": 100000.0, "chg_since_msg": 1.2, "chg24h": -0.4}},
        related_news=related_news,
    )

    message = payload["plain_text"]
    link_entities = [
        entity for entity in payload["entities"] if entity.type == MessageEntity.TEXT_LINK
    ]
    assert "\u2022 Bitcoin ETF flows & custody <update>" in message
    assert 'Bitcoin ETF flows & custody <update> - CoinDesk "Markets"' not in message
    assert link_entities[0].url == "https://example.test/btc?x=1&y=2"
    assert (
        _utf16_slice(message, link_entities[0].offset, link_entities[0].length)
        == "Bitcoin ETF flows & custody <update>"
    )
    assert payload["entities"][0].offset == 0
    assert payload["html_text"] is not None
    assert "<tg-emoji emoji-id=" in payload["html_text"]
    assert "&lt;tg-emoji" not in payload["html_text"]
    assert (
        '<a href="https://example.test/btc?x=1&amp;y=2">'
        "Bitcoin ETF flows &amp; custody &lt;update&gt;</a>"
        in payload["html_text"]
    )


def test_event_alert_related_context_renders_multiple_links_in_selected_order():
    decision = event_decision(related_news_ids=["n1", "n2"])
    related_news = [
        {
            "news_id": "n1",
            "title": "First selected article",
            "source": "Cointelegraph",
            "url": "https://example.test/first",
        },
        {
            "news_id": "n2",
            "title": "Second selected article",
            "source": "CoinDesk",
            "url": "https://example.test/second",
        },
    ]

    payload = alerts._build_event_alert_payload(
        decision=decision,
        input_payload={"market": {"price": 100000.0, "chg_since_msg": 1.2, "chg24h": -0.4}},
        related_news=related_news,
    )

    message = payload["plain_text"]
    assert message.index("First selected article") < message.index("Second selected article")
    link_entities = [
        entity for entity in payload["entities"] if entity.type == MessageEntity.TEXT_LINK
    ]
    assert [entity.url for entity in link_entities] == [
        "https://example.test/first",
        "https://example.test/second",
    ]


def test_missing_event_related_news_id_logs_and_uses_safe_fallback(caplog):
    caplog.set_level("WARNING")

    related_news = alerts._related_news_by_id(
        [{"news_id": "n1", "title": "Mapped", "url": "https://example.test/mapped"}],
        ["n999"],
        symbol="BTC",
        context="event analysis",
    )
    payload = alerts._build_event_alert_payload(
        decision=event_decision(related_news_ids=["n999"]),
        input_payload={"market": {"price": 100000.0, "chg_since_msg": 1.2, "chg24h": -0.4}},
        related_news=related_news,
    )

    assert related_news == []
    assert "No major related news selected." in payload["plain_text"]
    assert "n999" in caplog.text


@pytest.mark.asyncio
async def test_event_analysis_input_compacts_snapshots_and_news(monkeypatch):
    engine, session_local = await build_session_factory()
    now = datetime(2026, 5, 21, 12, 0, tzinfo=timezone.utc)
    try:
        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        async with session_local() as session:
            for index in range(12):
                await save_price_snapshot(
                    session,
                    symbol="btc",
                    price=100.0 + index,
                    change_24h=1.0,
                    checked_at=now - timedelta(minutes=55 - index * 5),
                )

        payload = await alerts._build_event_analysis_input(
            analysis_id="event_analysis_btc_test",
            symbol="btc",
            current_price=112.0,
            change_24h=1.0,
            now=now,
            state={},
            candidate_news=alerts._format_candidate_news(
                [
                    {
                        "title": f"BTC article {index}",
                        "source": "Example News",
                        "url": f"https://example.test/{index}",
                        "link": f"https://example.test/link/{index}",
                        "summary": "x" * 400,
                    }
                    for index in range(5)
                ]
            ),
        )

        assert set(payload["market"]) == {"price", "snapshots", "chg24h", "chg_since_msg"}
        assert "market_data" not in payload
        assert "candidate_news" not in payload
        snapshots = payload["market"]["snapshots"]
        assert len(snapshots) == 6
        assert snapshots[-1]["p"] == 111.0
        assert all(set(snapshot) == {"m", "p"} for snapshot in snapshots)
        assert all(isinstance(snapshot["m"], int) for snapshot in snapshots)
        assert all(snapshot["m"] <= 0 for snapshot in snapshots)
        assert "timestamp_utc" not in snapshots[-1]
        assert "price_usd" not in snapshots[-1]
        assert len(payload["news"]) == 3
        assert [item["news_id"] for item in payload["news"]] == ["n1", "n2", "n3"]
        assert all(len(item["summary"]) <= 300 for item in payload["news"])
        assert all("url" not in item and "link" not in item for item in payload["news"])
        assert payload["policy"] == {
            "language": "English",
            "audience": "General retail crypto holder.",
            "noise": "Prefer fewer useful alerts; avoid repetitive low-value alerts.",
        }
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_ton_event_analysis_payload_excludes_btc_only_news_without_direct_ton(monkeypatch):
    now = datetime(2026, 5, 21, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(alerts, "DB_ENABLED", False)
    monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", None)
    raw_news = [
        {"title": "Bitcoin ETFs crushed by billions in outflows", "source": "A"},
        {"title": "Crypto market sells off after Fed decision", "source": "B"},
    ]
    candidate_news = alerts._format_candidate_news(
        alerts.filter_news_for_symbol("ton", raw_news),
        preserve_order=True,
        symbol="ton",
    )

    payload = await alerts._build_event_analysis_input(
        analysis_id="event_analysis_ton_test",
        symbol="ton",
        current_price=6.2,
        change_24h=5.8,
        now=now,
        state={"last_price": 6.0},
        candidate_news=candidate_news,
    )

    titles = [item["title"] for item in payload["news"]]
    assert "Crypto market sells off after Fed decision" in titles
    assert "Bitcoin ETFs crushed by billions in outflows" not in titles
    assert payload["market"]["chg24h"] == 5.8
    assert [item["relevance_label"] for item in payload["news"]] == ["market_wide"]


@pytest.mark.asyncio
async def test_sol_event_analysis_payload_excludes_bitcoin_etf_only_news(monkeypatch):
    now = datetime(2026, 5, 21, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(alerts, "DB_ENABLED", False)
    monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", None)
    raw_news = [
        {"title": "Bitcoin ETF-only article dominates fund flows", "source": "A"},
        {"title": "Solana network outage hits validators", "source": "B"},
    ]
    candidate_news = alerts._format_candidate_news(
        alerts.filter_news_for_symbol("sol", raw_news),
        preserve_order=True,
        symbol="sol",
    )

    payload = await alerts._build_event_analysis_input(
        analysis_id="event_analysis_sol_test",
        symbol="sol",
        current_price=180.0,
        change_24h=2.4,
        now=now,
        state={"last_price": 178.0},
        candidate_news=candidate_news,
    )

    titles = [item["title"] for item in payload["news"]]
    assert titles == ["Solana network outage hits validators"]
    assert payload["news"][0]["relevance_label"] == "direct_symbol"


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
async def test_no_alert_schema_decision_persists_as_no_alert(monkeypatch):
    engine, session_local = await build_session_factory()
    try:
        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        parsed = {
            "symbol": "SOL",
            "should_alert": False,
            "event_key": None,
            "title": None,
            "message_body": None,
            "related_news_ids": None,
            "possible_action": None,
            "urgency": None,
            "confidence": None,
            "reason_for_no_alert": (
                "No significant market event or news that requires user attention "
                "has been detected."
            ),
        }
        monkeypatch.setattr(
            alerts,
            "ask_event_analysis_raw",
            AsyncMock(return_value=("raw no-alert output", parsed)),
        )
        payload = {
            "analysis_id": "event_analysis_sol_no_alert",
            "symbol": "SOL",
            "candidate_news": [],
            "market_data": {},
        }

        decision, analysis_id = await alerts._create_event_analysis_decision(payload)

        assert decision is not None
        assert decision.should_alert is False
        assert decision.related_news_ids == []
        assert decision.urgency is None
        assert decision.confidence is None
        assert analysis_id is not None
        async with session_local() as session:
            row = await session.scalar(select(EventAiAnalysis))
            assert row.status == "no_alert"
            assert row.should_alert is False
            assert row.related_news_ids == "[]"
            assert row.urgency is None
            assert row.confidence is None
            assert row.error_reason is None
            assert row.error_message is None
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_no_alert_low_urgency_is_normalized_before_validation(monkeypatch):
    engine, session_local = await build_session_factory()
    try:
        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        parsed = {
            "symbol": "BTC",
            "should_alert": False,
            "event_key": "",
            "title": "",
            "message_body": "",
            "related_news_ids": [],
            "possible_action": "",
            "urgency": "low",
            "confidence": "low",
            "reason_for_no_alert": "No significant event detected.",
        }
        monkeypatch.setattr(
            alerts,
            "ask_event_analysis_raw",
            AsyncMock(return_value=("raw scout no-alert output", parsed)),
        )
        payload = {
            "analysis_id": "event_analysis_btc_scout_no_alert",
            "symbol": "BTC",
            "news": [],
            "market": {},
        }

        decision, analysis_id = await alerts._create_event_analysis_decision(payload)

        assert decision is not None
        assert decision.should_alert is False
        assert decision.urgency is None
        assert decision.confidence == "low"
        assert analysis_id is not None
        async with session_local() as session:
            row = await session.scalar(select(EventAiAnalysis))
            assert row.status == "no_alert"
            assert row.urgency is None
            assert row.confidence == "low"
            assert row.error_reason is None
            assert row.error_message is None
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_event_analysis_accepts_advice_like_possible_action(monkeypatch):
    engine, session_local = await build_session_factory()
    try:
        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        parsed = {
            "symbol": "BTC",
            "should_alert": True,
            "event_key": "btc_event_2026_05_21",
            "title": "BTC market conditions changed",
            "message_body": "BTC moved while related context remains active.",
            "related_news_ids": ["n1"],
            "possible_action": "Consider selling only if it fits your own plan.",
            "urgency": "normal",
            "confidence": "medium",
            "reason_for_no_alert": None,
        }
        monkeypatch.setattr(
            alerts,
            "ask_event_analysis_raw",
            AsyncMock(return_value=("raw alert output", parsed)),
        )
        payload = {
            "analysis_id": "event_analysis_btc_advice_like",
            "symbol": "BTC",
            "news": [{"news_id": "n1", "title": "Related", "source": "Example"}],
            "market": {},
        }

        decision, analysis_id = await alerts._create_event_analysis_decision(payload)

        assert decision is not None
        assert decision.possible_action == "Consider selling only if it fits your own plan."
        assert analysis_id is not None
        async with session_local() as session:
            row = await session.scalar(select(EventAiAnalysis))
            assert row.status == "success"
            assert row.error_message is None
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_alert_empty_llm_event_key_is_canonicalized_to_fallback(monkeypatch):
    engine, session_local = await build_session_factory()
    try:
        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        parsed = {
            "symbol": "BTC",
            "should_alert": True,
            "event_key": "",
            "title": "BTC volatility returns",
            "message_body": "Bitcoin price action became choppy.",
            "related_news_ids": [],
            "possible_action": "Review the situation calmly.",
            "urgency": "normal",
            "confidence": "medium",
            "reason_for_no_alert": None,
        }
        monkeypatch.setattr(
            alerts,
            "ask_event_analysis_raw",
            AsyncMock(return_value=("raw alert output", parsed)),
        )
        payload = {
            "analysis_id": "event_analysis_btc_empty_key",
            "symbol": "BTC",
            "news": [],
            "market": {},
        }

        decision, analysis_id = await alerts._create_event_analysis_decision(payload)

        assert decision is not None
        assert decision.event_key == "btc_volatility_returns_bitcoin_price_action_became_choppy"
        assert analysis_id is not None
        async with session_local() as session:
            row = await session.scalar(select(EventAiAnalysis))
            assert row.event_key == decision.event_key
            assert row.raw_output_json == "raw alert output"
    finally:
        await engine.dispose()


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
async def test_event_alert_recipient_selection_bypasses_user_frequency(monkeypatch):
    engine, session_local = await build_session_factory()
    now = datetime(2026, 5, 20, 12, 0, tzinfo=timezone.utc)
    try:
        async with session_local() as session:
            user = await create_user(session)
            user.alert_frequency_seconds = 86400
            session.add(
                UserPremiumSubscription(
                    user_id=user.id,
                    status="active",
                    active_until=now + timedelta(days=1),
                )
            )
            session.add(
                Alert(
                    symbol="BTC",
                    alert_type="market_heartbeat",
                    message="recent heartbeat",
                    sent_to_chat_id=user.telegram_chat_id,
                    user_id=user.id,
                    status="sent",
                    created_at=now - timedelta(minutes=5),
                )
            )
            await session.commit()

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)

        recipients = await alerts.get_alert_recipients(
            symbol="btc",
            event_type="event_alert",
            now=now,
            bypass_frequency=True,
        )

        assert recipients == [
            alerts.AlertRecipient(
                chat_id=2001,
                user_id=user.id,
                alert_frequency_seconds=86400,
            )
        ]
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


@pytest.mark.asyncio
async def test_semantic_event_alert_cooldown_suppresses_same_user_symbol_and_key(monkeypatch):
    engine, session_local = await build_session_factory()
    now = datetime(2026, 5, 20, 12, 0, tzinfo=timezone.utc)
    try:
        async with session_local() as session:
            user = await create_user(session)
            await seed_sent_event_alert(
                session,
                user_id=user.id,
                chat_id=user.telegram_chat_id,
                symbol="btc",
                event_key="btc_price_volatility",
                created_at=now - timedelta(hours=1),
            )

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        recipients = [alerts.AlertRecipient(chat_id=2001, user_id=user.id)]

        filtered = await alerts._filter_event_recipients_for_cooldown(
            recipients,
            symbol="btc",
            urgency="normal",
            cooldown_seconds=0,
            canonical_event_key="btc_price_volatility",
            semantic_cooldown_seconds=4 * 3600,
            now=now,
        )

        assert filtered == []
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_semantic_event_alert_cooldown_allows_different_identity_dimensions(monkeypatch):
    engine, session_local = await build_session_factory()
    now = datetime(2026, 5, 20, 12, 0, tzinfo=timezone.utc)
    try:
        async with session_local() as session:
            user = await create_user(session, telegram_user_id=1001, chat_id=2001)
            other_user = await create_user(session, telegram_user_id=1002, chat_id=2002)
            await seed_sent_event_alert(
                session,
                user_id=user.id,
                chat_id=user.telegram_chat_id,
                symbol="btc",
                event_key="btc_price_volatility",
                created_at=now - timedelta(hours=1),
            )

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)

        same_user_different_key = await alerts._filter_event_recipients_for_cooldown(
            [alerts.AlertRecipient(chat_id=2001, user_id=user.id)],
            symbol="btc",
            urgency="normal",
            cooldown_seconds=0,
            canonical_event_key="btc_options_nasdaq",
            semantic_cooldown_seconds=4 * 3600,
            now=now,
        )
        different_user_same_key = await alerts._filter_event_recipients_for_cooldown(
            [alerts.AlertRecipient(chat_id=2002, user_id=other_user.id)],
            symbol="btc",
            urgency="normal",
            cooldown_seconds=0,
            canonical_event_key="btc_price_volatility",
            semantic_cooldown_seconds=4 * 3600,
            now=now,
        )
        same_user_different_symbol = await alerts._filter_event_recipients_for_cooldown(
            [alerts.AlertRecipient(chat_id=2001, user_id=user.id)],
            symbol="eth",
            urgency="normal",
            cooldown_seconds=0,
            canonical_event_key="btc_price_volatility",
            semantic_cooldown_seconds=4 * 3600,
            now=now,
        )

        assert same_user_different_key == [alerts.AlertRecipient(chat_id=2001, user_id=user.id)]
        assert different_user_same_key == [
            alerts.AlertRecipient(chat_id=2002, user_id=other_user.id)
        ]
        assert same_user_different_symbol == [
            alerts.AlertRecipient(chat_id=2001, user_id=user.id)
        ]
    finally:
        await engine.dispose()
