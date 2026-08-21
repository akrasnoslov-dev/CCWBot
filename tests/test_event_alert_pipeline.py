import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from telegram import MessageEntity

import bot.alerts as alerts
from bot.alerting.event_analysis import canonicalize_event_key, normalize_event_semantic_family
from bot.db.database import (
    Alert,
    AlertDeliveryOutcome,
    Base,
    EventAiAnalysis,
    MarketEvent,
    User,
    UserPremiumSubscription,
    ensure_default_coin_subscriptions,
    get_user_symbol_alert_state,
    grant_user_premium,
    init_db,
    normalize_stored_severity,
    save_price_snapshot,
    set_user_coin_subscription,
    upsert_user_symbol_alert_state,
)
from bot.handlers import _build_admin_system_status_text
from bot.services.ai_agent_groq import AIInvalidJsonError

FORBIDDEN_EVENT_PLACEHOLDERS = ("n/a", "null", "unknown", "unavailable")


def assert_no_event_placeholders(message: str):
    lowered = message.lower()
    assert all(value not in lowered for value in FORBIDDEN_EVENT_PLACEHOLDERS)


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
    urgency: str | None = None,
    analysed_window_minutes: int | None = None,
    analysed_window_change_percent: float | None = None,
    stable_related_news_ids: list[str] | None = None,
    semantic_family: str | None = None,
    price_action_traits: list[str] | None = None,
    cumulative_change_percent: float | None = None,
    persistence_ratio: float | None = None,
    trigger_reason: str | None = None,
    possible_action: str | None = None,
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
    alert = Alert(
        symbol=symbol.upper(),
        alert_type=alerts.EVENT_ALERT_TYPE,
        message="previous",
        sent_to_chat_id=chat_id,
        user_id=user_id,
        market_event_id=event.id,
        status="sent",
        trigger_reason=trigger_reason,
        created_at=created_at,
        numeric_context=alerts._json_dumps(
            {
                "notification_type": alerts.EVENT_ALERT_TYPE,
                "notification_severity": urgency,
                "analysed_window_minutes": analysed_window_minutes,
                "analysed_window_change_percent": analysed_window_change_percent,
                "stable_related_news_ids": stable_related_news_ids or [],
                "semantic_family": semantic_family,
                "price_action_traits": price_action_traits or [],
                "cumulative_change_percent": cumulative_change_percent,
                "persistence_ratio": persistence_ratio,
                "possible_action": possible_action,
            }
        ),
    )
    session.add(alert)
    await session.flush()
    if semantic_family:
        session.add(
            AlertDeliveryOutcome(
                symbol=symbol.upper(),
                alert_type=alerts.EVENT_ALERT_TYPE,
                market_event_id=event.id,
                alert_id=alert.id,
                user_id=user_id,
                sent_to_chat_id=chat_id,
                status="delivered",
                reason_code="delivered",
                recipient_considered=True,
                recipient_eligible=True,
                trigger_source=alerts.EVENT_ANALYSIS_TYPE,
                semantic_family=semantic_family,
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


@pytest.mark.parametrize(
    ("market", "expected"),
    [
        ({"chg_window": 0.0, "chg_since_msg": 3.0, "chg24h": 8.0}, 0.0),
        ({"chg_window": None, "chg_since_msg": 0.0, "chg24h": -8.0}, 0.0),
        ({"chg_window": "invalid", "chg_since_msg": -1.25, "chg24h": 8.0}, -1.25),
        ({"chg_window": 1.5, "chg_since_msg": -3.0, "chg24h": -8.0}, 1.5),
    ],
)
def test_event_movement_uses_first_numeric_value_without_losing_zero(market, expected):
    assert alerts._event_movement_percent_from_payload({"market": market}) == expected


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


def test_event_instance_key_uses_stable_market_only_family_identity():
    first = alerts._build_event_instance_key(
        symbol="btc",
        event_key="btc_price_downtrend",
        timestamp_value="2026-06-03T21:15:00+00:00",
        related_news_ids=[],
        input_hash="hash-a",
    )
    same_bucket_different_input = alerts._build_event_instance_key(
        symbol="BTC",
        event_key="btc_price_downtrend",
        timestamp_value="2026-06-03T21:45:00+00:00",
        related_news_ids=[],
        input_hash="hash-b",
    )
    next_bucket = alerts._build_event_instance_key(
        symbol="btc",
        event_key="btc_price_downtrend",
        timestamp_value="2026-06-03T22:00:00+00:00",
        related_news_ids=[],
        input_hash="hash-a",
    )
    different_family = alerts._build_event_instance_key(
        symbol="btc",
        event_key="btc_etf_flows",
        timestamp_value="2026-06-03T21:15:00+00:00",
        related_news_ids=[],
        input_hash="hash-a",
    )

    assert first == same_bucket_different_input
    assert next_bucket != first
    assert different_family != first


def test_event_instance_key_uses_stable_news_identity_not_temporary_news_ids():
    first = alerts._build_event_instance_key(
        symbol="btc",
        event_key="btc_price_downtrend",
        timestamp_value="2026-06-03T21:15:00+00:00",
        related_news_ids=["n1"],
        stable_news_ids=["source_title:abc"],
        input_hash="hash-a",
    )
    same_stable_news = alerts._build_event_instance_key(
        symbol="btc",
        event_key="btc_price_downtrend",
        timestamp_value="2026-06-03T21:45:00+00:00",
        related_news_ids=["n2"],
        stable_news_ids=["source_title:abc"],
        input_hash="hash-b",
    )
    different_news = alerts._build_event_instance_key(
        symbol="btc",
        event_key="btc_price_downtrend",
        timestamp_value="2026-06-03T21:15:00+00:00",
        related_news_ids=["n1"],
        stable_news_ids=["source_title:def"],
        input_hash="hash-a",
    )

    assert first == same_stable_news
    assert different_news != first


@pytest.mark.asyncio
async def test_event_alert_market_event_reports_reused_after_race_recovery(monkeypatch):
    class AsyncContextSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    recovered_event = SimpleNamespace(
        id=10,
        event_key="btc_downward_pressure_2026_05_20",
        event_instance_key="instance-race",
        _ccwbot_reused=True,
    )
    monkeypatch.setattr(alerts, "DB_ENABLED", True)
    monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", lambda: AsyncContextSession())
    monkeypatch.setattr(alerts, "get_market_event_by_instance_key", AsyncMock(return_value=None))
    monkeypatch.setattr(
        alerts,
        "get_or_create_market_event",
        AsyncMock(return_value=recovered_event),
    )
    monkeypatch.setattr(
        alerts,
        "_event_instance_key_for_decision",
        lambda *, decision, input_payload: "instance-race",
    )

    market_event_id, event_key, event_instance_key, reused = (
        await alerts._get_or_create_event_alert_market_event(
            decision=event_decision(),
            input_payload={"market": {"price": 103.0, "chg_since_msg": 3.0}},
        )
    )

    assert market_event_id == 10
    assert event_key == "btc_downward_pressure_2026_05_20"
    assert event_instance_key == "instance-race"
    assert reused is True


@pytest.mark.parametrize(
    ("raw_event_key", "expected"),
    [
        ("BTC_price_volatility", "btc_volatility"),
        ("bitcoin_price_volatility", "btc_volatility"),
        ("btc_price_volatility_2026-05-25", "btc_volatility"),
        ("Bitcoin-options-Nadaq", "btc_derivatives_positioning"),
    ],
)
def test_canonical_event_key_normalizes_common_llm_variants(raw_event_key, expected):
    result = canonicalize_event_key("btc", raw_event_key)

    assert result.canonical_event_key == expected


@pytest.mark.parametrize(
    ("symbol", "raw_event_key"),
    [
        ("eth", "eth_price_drop_5pct"),
        ("eth", "eth_price_drop_5_percent"),
        ("eth", "eth_price_drop"),
        ("eth", "market_drop_eth"),
        ("btc", "btc_selloff_prediction"),
        ("btc", "btc_price_test_low"),
        ("btc", "btc_price_test_february_low"),
        ("btc", "btc_price_drop"),
        ("gram", "gram_price_drop"),
        ("gram", "gram_price_decline"),
    ],
)
def test_semantic_event_family_normalizes_equivalent_downtrend_keys(symbol, raw_event_key):
    result = canonicalize_event_key(symbol, raw_event_key)

    assert result.semantic_family == "price_downtrend"
    assert result.canonical_event_key == f"{symbol}_price_downtrend"


def test_semantic_event_family_uses_context_for_ambiguous_movement_key():
    result = canonicalize_event_key(
        "gram",
        "gram_price_movement",
        title="GRAM price weakened again",
        message_body="GRAM moved lower while market pressure remains elevated.",
    )

    assert result.semantic_family == "price_downtrend"
    assert result.canonical_event_key == "gram_price_downtrend"


@pytest.mark.parametrize("raw_event_key", ["news_catalyst", "volatility", "price_movement"])
def test_btc_quantum_security_examples_share_backend_family(raw_event_key):
    result = canonicalize_event_key(
        "btc",
        raw_event_key,
        title="Quantum computing raises Bitcoin security questions",
        message_body=(
            "Analysts discussed whether future quantum attacks could affect Bitcoin "
            "cryptography and protocol security."
        ),
        related_news=[
            {
                "title": "Bitcoin protocol security debate grows around quantum risk",
                "source": "Example Markets",
                "url": "https://example.test/btc-quantum-risk",
            }
        ],
    )

    assert result.semantic_family == "protocol_security_risk"
    assert result.canonical_event_key == "btc_protocol_security_risk"
    assert result.canonical_event_key != "btc_news_catalyst"


@pytest.mark.parametrize(
    ("title", "message_body", "expected_family"),
    [
        (
            "BTC breaks above resistance",
            "Bitcoin moved through a watched resistance level.",
            "price_uptrend",
        ),
        (
            "BTC breakout through key resistance",
            "Bitcoin broke through a key resistance area.",
            "price_uptrend",
        ),
        (
            "BTC rallies above key level",
            "Bitcoin rallied above a watched market level.",
            "price_uptrend",
        ),
        (
            "BTC breaks below support",
            "Bitcoin moved below a watched support level.",
            "price_downtrend",
        ),
        (
            "BTC drops below support",
            "Bitcoin dropped below a watched support level.",
            "price_downtrend",
        ),
    ],
)
def test_btc_directional_level_breaks_win_over_price_level_range(
    title,
    message_body,
    expected_family,
):
    result = canonicalize_event_key(
        "btc",
        "price_movement",
        title=title,
        message_body=message_body,
    )

    assert result.semantic_family == expected_family
    assert result.canonical_event_key == f"btc_{expected_family}"


@pytest.mark.parametrize(
    ("raw_event_key", "title", "message_body"),
    [
        (
            "price_movement",
            "BTC holds near $63k as traders watch support",
            "Bitcoin stayed around a key support level without a material breakout.",
        ),
        (
            "volatility",
            "BTC volatility clusters around resistance",
            "Bitcoin price action remains near resistance and inside a tight range.",
        ),
        (
            "news_catalyst",
            "BTC stays around a key level",
            "Price is hovering near support while the market waits for a new driver.",
        ),
        (
            "price_movement",
            "BTC remains range-bound near support",
            "Bitcoin remains range-bound near support without a decisive move.",
        ),
    ],
)
def test_btc_price_level_examples_share_backend_family(
    raw_event_key,
    title,
    message_body,
):
    result = canonicalize_event_key(
        "btc",
        raw_event_key,
        title=title,
        message_body=message_body,
    )

    assert result.semantic_family == "price_level_range"
    assert result.canonical_event_key == "btc_price_level_range"


def test_semantic_event_family_keeps_distinct_drivers_separate():
    assert normalize_event_semantic_family("btc", "btc_etf_outflows") == "etf_flows"
    assert normalize_event_semantic_family("btc", "btc_liquidation_cascade") == "liquidations"
    assert canonicalize_event_key("btc", "btc_options_expiry").canonical_event_key == (
        "btc_derivatives_positioning"
    )
    assert canonicalize_event_key("btc", "btc_low_volatility").canonical_event_key == (
        "btc_volatility"
    )


def test_cross_family_price_traits_require_explicit_shared_market_theme():
    downtrend_near_support = alerts._price_action_context_traits(
        semantic_family="price_downtrend",
        raw_event_key="btc_price_downtrend",
        title="BTC decline approaches support",
    )
    level_with_decline = alerts._price_action_context_traits(
        semantic_family="price_level_range",
        raw_event_key="btc_price_level_range",
        title="BTC decline approaches support",
    )
    distinct_volatility = alerts._price_action_context_traits(
        semantic_family="volatility",
        raw_event_key="btc_volatility",
        title="BTC turns choppy",
    )

    assert downtrend_near_support == [
        "directional_move",
        "level_interaction",
        "level_test_or_hold",
    ]
    assert level_with_decline == downtrend_near_support
    assert distinct_volatility == ["volatility_regime"]


def test_cross_family_price_traits_distinguish_level_test_from_level_break():
    approaching_support = alerts._price_action_context_traits(
        semantic_family="price_downtrend",
        raw_event_key="btc_price_downtrend",
        title="BTC decline approaches support",
    )
    breaking_support = alerts._price_action_context_traits(
        semantic_family="price_level_range",
        raw_event_key="btc_break_below_support",
        title="BTC decline breaks below support",
    )

    assert "level_test_or_hold" in approaching_support
    assert "level_break" not in approaching_support
    assert "level_break" in breaking_support
    assert approaching_support != breaking_support


def test_cross_family_price_traits_do_not_treat_negated_break_as_break():
    negated_break = alerts._price_action_context_traits(
        semantic_family="price_level_range",
        raw_event_key="btc_price_level_range",
        title="BTC decline shows no sign of a breakdown near support",
    )
    genuine_break = alerts._price_action_context_traits(
        semantic_family="price_downtrend",
        raw_event_key="btc_break_below_support",
        title="BTC drops below support near the range",
    )
    asserted_after_other_clause = alerts._price_action_context_traits(
        semantic_family="price_downtrend",
        raw_event_key="btc_price_downtrend",
        title="No relief as BTC breaks below support",
    )
    modified_break = alerts._price_action_context_traits(
        semantic_family="price_downtrend",
        raw_event_key="btc_price_downtrend",
        title="BTC has broken and holds below support",
    )

    assert "level_break" not in negated_break
    assert "level_break" in genuine_break
    assert "level_side_below" in genuine_break
    assert "level_break" in asserted_after_other_clause
    assert "level_break" in modified_break
    assert negated_break != genuine_break


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


def test_analysed_window_minutes_uses_interval_and_payload_points():
    assert alerts.get_analysed_window_minutes(1800, 6) == 180
    assert alerts.get_analysed_window_minutes(300, 6) == 30


def test_event_alert_payload_uses_analysed_window_change_not_24h():
    payload = alerts._build_event_alert_payload(
        decision=event_decision(),
        input_payload={
            "market": {
                "price": 100000.0,
                "chg_since_msg": 1.2,
                "analysed_window_minutes": 180,
                "chg_window": -2.4,
                "chg24h": -9.9,
            }
        },
        related_news=[],
    )

    message = payload["plain_text"]
    html_message = payload["html_text"] or ""
    assert "Since last alert/message: +1.20%" in message
    assert "3h market move: -2.40%" in message
    assert "Since last BTC alert" not in message
    assert "24h change" not in message
    assert "Price change" not in message
    assert "chg24h" not in message
    assert "Data:" not in message
    assert "Debug:" not in message
    assert "move=" not in message
    assert "Not financial advice." in message
    assert "Since last alert/message: +1.20%" in html_message
    assert "3h market move: -2.40%" in html_message
    assert "Since last BTC alert" not in html_message
    assert "24h change" not in html_message
    assert "Price change" not in html_message
    assert_no_event_placeholders(message)


@pytest.mark.parametrize(
    ("title", "message_body", "possible_action"),
    [
        (
            "Buy BTC now before the next move.",
            "You should consider selling before the next leg lower.",
            "We recommend that you sell immediately.",
        ),
        (
            "BTC market update",
            "It is time to exit your position.",
            "You must immediately sell BTC.",
        ),
        (
            "Go long now.",
            "Open a short position before the next move.",
            "Take profit immediately.",
        ),
        (
            "Hold BTC now.",
            "DCA into BTC today.",
            "Buy-side liquidity is thin.",
        ),
    ],
)
def test_event_alert_payload_never_renders_direct_financial_instructions(
    title, message_body, possible_action
):
    decision = event_decision()
    decision = alerts.EventAnalysisDecision(
        symbol=decision.symbol,
        should_alert=decision.should_alert,
        event_key=decision.event_key,
        title=title,
        message_body=message_body,
        related_news_ids=decision.related_news_ids,
        possible_action=possible_action,
        urgency=decision.urgency,
        confidence=decision.confidence,
        reason_for_no_alert=decision.reason_for_no_alert,
    )

    payload = alerts._build_event_alert_payload(
        decision=decision,
        input_payload={"market": {"price": 100000.0, "chg_window": -2.0}},
        related_news=[],
    )
    rendered = payload["plain_text"].lower()

    assert "buy btc now" not in rendered
    assert "consider selling" not in rendered
    assert "recommend that you sell" not in rendered
    assert "time to exit" not in rendered
    assert "must immediately sell" not in rendered
    assert "go long now" not in rendered
    assert "open a short" not in rendered
    assert "take profit immediately" not in rendered
    assert "hold btc now" not in rendered
    assert "dca into btc" not in rendered
    if possible_action.startswith("Buy-side"):
        assert "buy-side liquidity is thin" in rendered
    else:
        assert "consider" in rendered


@pytest.mark.parametrize(
    "possible_action",
    [
        "Consider buying only if the move confirms.",
        "Consider entering only if it fits your risk plan.",
        "Consider reducing exposure if momentum weakens.",
        "Consider tightening a stop-loss if volatility persists.",
        "Consider taking profit if your target is reached.",
    ],
)
def test_event_alert_payload_preserves_conditional_trading_oriented_suggestions(
    possible_action,
):
    decision = event_decision()
    decision = alerts.EventAnalysisDecision(
        symbol=decision.symbol,
        should_alert=decision.should_alert,
        event_key=decision.event_key,
        title=decision.title,
        message_body=decision.message_body,
        related_news_ids=decision.related_news_ids,
        possible_action=possible_action,
        urgency=decision.urgency,
        confidence=decision.confidence,
        reason_for_no_alert=decision.reason_for_no_alert,
    )

    payload = alerts._build_event_alert_payload(
        decision=decision,
        input_payload={"market": {"price": 100000.0, "chg_window": -2.0}},
        related_news=[],
    )

    assert f"Possible action:\n{possible_action}" in payload["plain_text"]


@pytest.mark.parametrize(
    ("minutes", "expected_label"),
    [
        (30, "30m market move"),
        (45, "45m market move"),
        (60, "1h market move"),
        (180, "3h market move"),
    ],
)
def test_event_alert_payload_uses_actual_analysed_window_label(minutes, expected_label):
    payload = alerts._build_event_alert_payload(
        decision=event_decision(),
        input_payload={
            "market": {
                "price": 100000.0,
                "analysed_window_minutes": minutes,
                "chg_window": 1.5,
            }
        },
        related_news=[],
    )

    message = payload["plain_text"]
    assert f"{expected_label}: +1.50%" in message
    assert "Analysed-window change" not in message
    assert "Price change" not in message
    assert "Since last BTC alert" not in message
    assert_no_event_placeholders(message)


def test_event_alert_payload_hides_missing_market_context_fields():
    payload = alerts._build_event_alert_payload(
        decision=event_decision(),
        input_payload={
            "market": {
                "price": 100000.0,
                "chg_since_msg": None,
                "chg24h": -9.9,
            }
        },
        related_news=[],
    )

    message = payload["plain_text"]
    html_message = payload["html_text"] or ""
    assert "Price: $100,000.00" in message
    assert "Since last alert/message:" not in message
    assert "Since last BTC alert:" not in message
    assert "market move:" not in message
    assert "change:" not in message
    assert "24h change" not in message
    assert_no_event_placeholders(message)
    assert "Since last alert/message:" not in html_message
    assert "Since last BTC alert:" not in html_message
    assert "market move:" not in html_message
    assert_no_event_placeholders(html_message)


def test_event_alert_payload_hides_placeholder_text_from_llm_fields():
    decision = alerts.EventAnalysisDecision(
        symbol="BTC",
        should_alert=True,
        event_key="btc_price_volatility",
        title="BTC context unknown",
        message_body="The current driver is unavailable.",
        related_news_ids=[],
        possible_action="Review null details later.",
        urgency="normal",
        confidence="medium",
        reason_for_no_alert=None,
    )

    payload = alerts._build_event_alert_payload(
        decision=decision,
        input_payload={"market": {"price": 100000.0}},
        related_news=[],
    )

    message = payload["plain_text"]
    assert "BTC market event" in message
    assert "Market conditions changed." in message
    assert "Review the situation calmly and avoid impulsive decisions." in message
    assert_no_event_placeholders(message)


def test_event_alert_small_analysed_window_move_avoids_dramatic_wording():
    decision = alerts.EventAnalysisDecision(
        symbol="BTC",
        should_alert=True,
        event_key="btc_price_volatility",
        title="BTC crash panic as price explosion spreads",
        message_body=(
            "BTC may collapse, start collapsing, or surge despite a small analysed-window move."
        ),
        related_news_ids=[],
        possible_action="Watch calmly if the market meltdown language gets explosive.",
        urgency="normal",
        confidence="medium",
        reason_for_no_alert=None,
    )

    payload = alerts._build_event_alert_payload(
        decision=decision,
        input_payload={
            "market": {
                "price": 100000.0,
                "analysed_window_minutes": 180,
                "chg_window": 0.7,
            }
        },
        related_news=[],
    )

    message = payload["plain_text"].lower()
    for term in (
        "crash",
        "panic",
        "explodes",
        "explosion",
        "explosive",
        "collapse",
        "collapsing",
        "surge",
        "meltdown",
        "bloodbath",
        "moon",
    ):
        assert term not in message
    assert "3h market move: +0.70%" in payload["plain_text"]
    assert "Not financial advice." in payload["plain_text"]


def test_event_alert_material_analysed_window_move_keeps_dramatic_wording():
    decision = alerts.EventAnalysisDecision(
        symbol="BTC",
        should_alert=True,
        event_key="btc_price_volatility",
        title="BTC surge remains notable",
        message_body="BTC may collapse if the move accelerates.",
        related_news_ids=[],
        possible_action="Watch the market calmly.",
        urgency="high",
        confidence="medium",
        reason_for_no_alert=None,
    )

    payload = alerts._build_event_alert_payload(
        decision=decision,
        input_payload={
            "market": {
                "price": 100000.0,
                "analysed_window_minutes": 180,
                "chg_window": 2.5,
            }
        },
        related_news=[],
    )

    message = payload["plain_text"]
    assert "BTC surge remains notable" in message
    assert "BTC may collapse if the move accelerates." not in message
    assert "meaningful market change" in message


def test_event_alert_numeric_guard_replaces_contradictory_llm_percent_claim():
    decision = alerts.EventAnalysisDecision(
        symbol="SOL",
        should_alert=True,
        event_key="sol_price_movement",
        title="SOL jumps +5.58% in 3 hours",
        message_body="SOL rallied +5.58% in 3 hours as momentum improved.",
        related_news_ids=[],
        possible_action="Watch whether the rally keeps extending.",
        urgency="normal",
        confidence="medium",
        reason_for_no_alert=None,
    )

    payload = alerts._build_event_alert_payload(
        decision=decision,
        input_payload={
            "market": {
                "price": 142.35,
                "analysed_window_minutes": 180,
                "chg_window": -0.12,
                "chg_since_msg": -0.2,
                "chg24h": 0.4,
            }
        },
        related_news=[],
    )

    message = payload["plain_text"]
    assert "+5.58%" not in message
    assert "rallied" not in message.lower()
    assert "rally" not in message.lower()
    assert "meaningful market change" in message
    assert "3h market move: -0.12%" in message


def test_event_alert_numeric_guard_rejects_mismatched_window_claim():
    decision = alerts.EventAnalysisDecision(
        symbol="SOL",
        should_alert=True,
        event_key="sol_price_movement",
        title="SOL jumps +5.0% in 3 hours",
        message_body="SOL jumps +5.0% in 3 hours while the trend improves.",
        related_news_ids=[],
        possible_action="Watch whether the 3 hour move keeps extending.",
        urgency="normal",
        confidence="medium",
        reason_for_no_alert=None,
    )

    payload = alerts._build_event_alert_payload(
        decision=decision,
        input_payload={
            "market": {
                "price": 142.35,
                "analysed_window_minutes": 180,
                "chg_window": 0.2,
                "chg_since_msg": 0.1,
                "chg24h": 5.0,
            }
        },
        related_news=[],
    )

    message = payload["plain_text"]
    assert "+5.0% in 3 hours" not in message
    assert "meaningful market change" in message
    assert "3h market move: +0.20%" in message


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
    assert "Related context:" not in payload["plain_text"]
    assert "No major related news selected." not in payload["plain_text"]
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
            event_analysis_interval_seconds=1800,
        )

        assert set(payload["market"]) == {
            "price",
            "snapshots",
            "payload_points",
            "analysed_window_minutes",
            "chg_window",
            "chg24h",
            "chg_since_msg",
        }
        assert "market_data" not in payload
        assert "candidate_news" not in payload
        assert payload["market"]["payload_points"] == 6
        assert payload["market"]["analysed_window_minutes"] == 180
        assert payload["market"]["chg_window"] == 12.0
        snapshots = payload["market"]["snapshots"]
        assert len(snapshots) == 6
        assert snapshots[-1] == {"m": 0, "p": 112.0}
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
async def test_event_analysis_input_ignores_stale_reference_snapshot(monkeypatch):
    engine, session_local = await build_session_factory()
    now = datetime(2026, 6, 5, 11, 40, tzinfo=timezone.utc)
    try:
        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        async with session_local() as session:
            await save_price_snapshot(
                session,
                symbol="gram",
                price=1.93,
                change_24h=-1.0,
                checked_at=datetime(2026, 6, 2, 15, 47, tzinfo=timezone.utc),
            )
            await save_price_snapshot(
                session,
                symbol="gram",
                price=1.55,
                change_24h=-1.0,
                checked_at=now - timedelta(minutes=160),
            )
            await save_price_snapshot(
                session,
                symbol="gram",
                price=1.545,
                change_24h=-1.0,
                checked_at=now - timedelta(minutes=70),
            )
            await save_price_snapshot(
                session,
                symbol="gram",
                price=1.54,
                change_24h=-1.0,
                checked_at=now - timedelta(minutes=5),
            )

        payload = await alerts._build_event_analysis_input(
            analysis_id="event_analysis_gram_stale_reference",
            symbol="gram",
            current_price=1.54,
            change_24h=-1.0,
            now=now,
            state={},
            candidate_news=[],
            event_analysis_interval_seconds=1800,
        )

        market = payload["market"]
        assert market["analysed_window_minutes"] == 180
        assert market["chg_window"] == pytest.approx(-0.6452)
        assert market["chg_window"] != pytest.approx(-20.2073)
        assert all(snapshot["p"] != 1.93 for snapshot in market["snapshots"])
        assert all(snapshot["m"] >= -180 for snapshot in market["snapshots"])
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_event_analysis_input_uses_fresh_boundary_reference(monkeypatch):
    engine, session_local = await build_session_factory()
    now = datetime(2026, 5, 21, 12, 0, tzinfo=timezone.utc)
    try:
        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        async with session_local() as session:
            await save_price_snapshot(
                session,
                symbol="btc",
                price=90.0,
                change_24h=1.0,
                checked_at=now - timedelta(minutes=210),
            )
            await save_price_snapshot(
                session,
                symbol="btc",
                price=95.0,
                change_24h=1.0,
                checked_at=now - timedelta(minutes=150),
            )
            await save_price_snapshot(
                session,
                symbol="btc",
                price=99.0,
                change_24h=1.0,
                checked_at=now - timedelta(minutes=30),
            )

        payload = await alerts._build_event_analysis_input(
            analysis_id="event_analysis_btc_fresh_reference",
            symbol="btc",
            current_price=99.0,
            change_24h=1.0,
            now=now,
            state={},
            candidate_news=[],
            event_analysis_interval_seconds=1800,
        )

        snapshots = payload["market"]["snapshots"]
        assert payload["market"]["chg_window"] == 10.0
        assert snapshots[0] == {"m": -210, "p": 90.0}
        assert snapshots[-1] == {"m": 0, "p": 99.0}
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_event_analysis_input_current_leg_drives_acceleration(monkeypatch):
    engine, session_local = await build_session_factory()
    now = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)
    try:
        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        async with session_local() as session:
            for minutes, price in [(180, 100.0), (120, 100.1), (60, 100.2)]:
                await save_price_snapshot(
                    session,
                    symbol="btc",
                    price=price,
                    change_24h=1.0,
                    checked_at=now - timedelta(minutes=minutes),
                )

        input_payload = await alerts._build_event_analysis_input(
            analysis_id="event_analysis_btc_current_acceleration",
            symbol="btc",
            current_price=100.8,
            change_24h=1.0,
            now=now,
            state={},
            candidate_news=[],
            event_analysis_interval_seconds=1800,
        )
        result = alerts.evaluate_event_significance(input_payload, urgency="normal")

        assert input_payload["market"]["snapshots"][-1] == {"m": 0, "p": 100.8}
        assert result.is_significant is True
        assert result.reason == "material_acceleration"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_event_analysis_input_reports_unknown_change_without_snapshots(monkeypatch):
    engine, session_local = await build_session_factory()
    now = datetime(2026, 5, 21, 12, 0, tzinfo=timezone.utc)
    try:
        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)

        payload = await alerts._build_event_analysis_input(
            analysis_id="event_analysis_btc_no_snapshots",
            symbol="btc",
            current_price=100.0,
            change_24h=1.0,
            now=now,
            state={"last_price": 50.0},
            candidate_news=[],
            event_analysis_interval_seconds=1800,
        )

        assert payload["market"]["chg_window"] is None
        assert payload["market"]["snapshots"] == [{"m": 0, "p": 100.0}]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_event_analysis_input_includes_sanitized_previous_event_alert(monkeypatch):
    engine, session_local = await build_session_factory()
    now = datetime(2026, 5, 21, 12, 0, tzinfo=timezone.utc)
    try:
        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        async with session_local() as session:
            user = await create_user(session)
            await seed_sent_event_alert(
                session,
                user_id=user.id,
                chat_id=user.telegram_chat_id,
                symbol="btc",
                event_key="btc_etf_flows",
                semantic_family="etf_flows",
                analysed_window_change_percent=0.42,
                stable_related_news_ids=["source_title:private-news-id"],
                trigger_reason="BTC ETF flow context repeated",
                possible_action="Wait for price confirmation before reacting.",
                created_at=now - timedelta(hours=2),
            )

        payload = await alerts._build_event_analysis_input(
            analysis_id="event_analysis_btc_previous_context",
            symbol="btc",
            current_price=100.0,
            change_24h=1.0,
            now=now,
            state={},
            candidate_news=[],
            event_analysis_interval_seconds=1800,
        )

        previous = payload["previous_event_alert"]
        assert previous["title"] == "BTC ETF flow context repeated"
        assert previous["canonical_event_key"] == "btc_etf_flows"
        assert previous["semantic_family"] == "etf_flows"
        assert previous["analysed_window_move"] == 0.42
        assert previous["stable_related_news_ids_hash"]
        assert "source_title:private-news-id" not in str(previous)
        assert previous["possible_action"] == "Wait for price confirmation before reacting."
        assert "user_id" not in previous
        assert "telegram" not in str(previous).lower()
        assert "message" not in previous
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_event_analysis_input_excludes_future_snapshots(monkeypatch):
    engine, session_local = await build_session_factory()
    now = datetime(2026, 5, 21, 12, 0, tzinfo=timezone.utc)
    try:
        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        async with session_local() as session:
            await save_price_snapshot(
                session,
                symbol="btc",
                price=100.0,
                change_24h=1.0,
                checked_at=now - timedelta(minutes=60),
            )
            await save_price_snapshot(
                session,
                symbol="btc",
                price=1000.0,
                change_24h=1.0,
                checked_at=now + timedelta(minutes=5),
            )

        payload = await alerts._build_event_analysis_input(
            analysis_id="event_analysis_btc_future_snapshot",
            symbol="btc",
            current_price=100.0,
            change_24h=1.0,
            now=now,
            state={},
            candidate_news=[],
            event_analysis_interval_seconds=1800,
        )

        assert payload["market"]["chg_window"] == 0.0
        assert all(snapshot["m"] <= 0 for snapshot in payload["market"]["snapshots"])
        assert all(snapshot["p"] != 1000.0 for snapshot in payload["market"]["snapshots"])
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_window_market_context_ignores_stale_reference_for_peak(monkeypatch):
    engine, session_local = await build_session_factory()
    now = datetime(2026, 5, 21, 12, 0, tzinfo=timezone.utc)
    try:
        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        async with session_local() as session:
            await save_price_snapshot(
                session,
                symbol="btc",
                price=80.0,
                change_24h=1.0,
                checked_at=now - timedelta(days=3),
            )
            await save_price_snapshot(
                session,
                symbol="btc",
                price=100.0,
                change_24h=1.0,
                checked_at=now - timedelta(minutes=20),
            )

        previous_price, peak = await alerts._resolve_window_market_context(
            symbol="btc",
            current_price=100.0,
            fallback_previous_price=99.0,
            window_seconds=3600,
            now=now,
        )

        assert previous_price == 100.0
        assert peak == 0.0
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
        event_analysis_interval_seconds=1800,
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
        event_analysis_interval_seconds=1800,
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
    monkeypatch.setattr(
        alerts,
        "resolve_alert_recipient_outcomes",
        AsyncMock(return_value=alerts.AlertRecipientResolution(recipients=recipients)),
    )
    monkeypatch.setattr(alerts, "fetch_news_context", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        alerts,
        "_create_event_analysis_decision",
        AsyncMock(return_value=(event_decision(), 123)),
    )
    monkeypatch.setattr(
        alerts,
        "_get_or_create_event_alert_market_event",
        AsyncMock(return_value=(456, "btc_downward_pressure_2026_05_20", "instance-a", False)),
    )
    monkeypatch.setattr(alerts, "_deliver_market_event_alert", deliver_alert)
    monkeypatch.setattr(alerts, "_save_price_state", AsyncMock())

    await alerts.automatic_price_check(SimpleNamespace(application=SimpleNamespace()))

    deliver_alert.assert_awaited_once()
    assert deliver_alert.await_args.kwargs["event_type"] == "event_alert"
    assert "Not financial advice." in deliver_alert.await_args.kwargs["alert_payload"]["plain_text"]


@pytest.mark.asyncio
@pytest.mark.parametrize("canonical_html", ["<b>Canonical stored HTML</b>", None])
async def test_reused_market_event_uses_existing_attached_analysis(
    monkeypatch,
    canonical_html,
):
    engine, session_local = await build_session_factory()
    try:
        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        decision = event_decision()
        analysis_input = {
            "analysis_id": "event_analysis_btc_current",
            "symbol": "btc",
            "timestamp_utc": now.isoformat(),
            "market": {
                "price": 103.0,
                "chg_window": -3.0,
                "chg_since_msg": 3.0,
                "chg24h": -1.0,
                "analysed_window_minutes": 180,
            },
            "news": [],
            "raw_event_key": decision.event_key,
            "canonical_event_key": decision.event_key,
            "semantic_family": "price_downtrend",
        }
        canonical_payload = alerts._build_event_alert_payload(
            decision=decision,
            input_payload=analysis_input,
            related_news=[],
        )
        event_instance_key = alerts._event_instance_key_for_decision(
            decision=decision,
            input_payload=analysis_input,
        )
        async with session_local() as session:
            first_user = await create_user(session)
            second_user = await create_user(session, telegram_user_id=1002, chat_id=2002)
            market_event = MarketEvent(
                symbol="BTC",
                event_type=alerts.EVENT_ALERT_TYPE,
                event_key=str(decision.event_key),
                event_instance_key=event_instance_key,
                price=103.0,
                previous_price=100.0,
                price_change_percent=3.0,
                detected_at=now,
            )
            session.add(market_event)
            await session.commit()
            await session.refresh(market_event)
            canonical = EventAiAnalysis(
                market_event_id=market_event.id,
                analysis_id="event_analysis_btc_canonical",
                symbol="BTC",
                analysis_type=alerts.EVENT_ANALYSIS_TYPE,
                provider="groq",
                model="llama-test",
                input_hash="canonical",
                raw_input_json=alerts._json_dumps(analysis_input),
                status="success",
                should_alert=True,
                event_key=decision.event_key,
                title=decision.title,
                message_body=decision.message_body,
                related_news_ids=alerts._json_dumps(decision.related_news_ids),
                possible_action=decision.possible_action,
                urgency=decision.urgency,
                confidence=decision.confidence,
                plain_text=canonical_payload["plain_text"],
                html_text=canonical_html,
            )
            session.add(canonical)
            await session.commit()
            await session.refresh(canonical)
            canonical_id = canonical.id
            market_event_id = market_event.id
            user_ids = {first_user.id, second_user.id}

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        monkeypatch.setattr(alerts, "resolve_symbols_to_check", AsyncMock(return_value=["btc"]))
        monkeypatch.setattr(
            alerts,
            "get_coin_market_data_batch",
            AsyncMock(return_value={"btc": {"price": 103.0, "change_24h": -1.0}}),
        )
        monkeypatch.setattr(
            alerts,
            "get_db_alert_settings",
            AsyncMock(return_value={"automatic_check_interval_seconds": 300}),
        )
        monkeypatch.setattr(
            alerts,
            "_load_news_driven_alert_candidates",
            AsyncMock(return_value={}),
        )
        monkeypatch.setattr(
            alerts,
            "_select_related_news_context",
            AsyncMock(return_value=([], None, False)),
        )
        monkeypatch.setattr(
            alerts,
            "_build_event_analysis_input",
            AsyncMock(return_value=dict(analysis_input)),
        )
        monkeypatch.setattr(
            alerts,
            "resolve_alert_recipient_outcomes",
            AsyncMock(
                return_value=alerts.AlertRecipientResolution(
                    recipients=[
                        alerts.AlertRecipient(chat_id=2001, user_id=first_user.id),
                        alerts.AlertRecipient(chat_id=2002, user_id=second_user.id),
                    ]
                )
            ),
        )
        create_analysis = AsyncMock()
        monkeypatch.setattr(
            alerts,
            "_create_event_analysis_decision",
            create_analysis,
        )
        create_market_event = AsyncMock()
        monkeypatch.setattr(
            alerts,
            "_get_or_create_event_alert_market_event",
            create_market_event,
        )
        monkeypatch.setattr(
            alerts,
            "_filter_event_recipients_for_cooldown",
            AsyncMock(
                return_value=alerts.EventRecipientFilterResult(
                    recipients=[
                        alerts.AlertRecipient(chat_id=2001, user_id=first_user.id),
                        alerts.AlertRecipient(chat_id=2002, user_id=second_user.id),
                    ],
                    suppression_reason_counts={},
                )
            ),
        )
        send_alert = AsyncMock(return_value=(True, None, None))
        monkeypatch.setattr(
            alerts,
            "_send_alert_to_recipient_with_retry",
            send_alert,
        )
        monkeypatch.setattr(alerts, "_save_price_state", AsyncMock())

        await alerts.automatic_price_check(SimpleNamespace(application=SimpleNamespace()))

        async with session_local() as session:
            attached_count = await session.scalar(
                select(func.count())
                .select_from(EventAiAnalysis)
                .where(EventAiAnalysis.market_event_id == market_event_id)
                .where(EventAiAnalysis.analysis_type == alerts.EVENT_ANALYSIS_TYPE)
            )
            deliveries = list(
                (
                    await session.scalars(
                        select(Alert).where(Alert.user_id.in_(user_ids)).order_by(Alert.id)
                    )
                ).all()
            )
            analysis_count = await session.scalar(
                select(func.count()).select_from(EventAiAnalysis)
            )
            delivered_outcomes = list(
                (
                    await session.scalars(
                        select(AlertDeliveryOutcome).where(
                            AlertDeliveryOutcome.status == alerts.OUTCOME_DELIVERED
                        )
                    )
                ).all()
            )

        create_analysis.assert_not_awaited()
        create_market_event.assert_not_awaited()
        assert attached_count == 1
        assert analysis_count == 1
        assert len(deliveries) == 2
        assert {delivery.event_ai_analysis_id for delivery in deliveries} == {canonical_id}
        assert {delivery.message for delivery in deliveries} == {
            canonical_payload["plain_text"]
        }
        assert len(delivered_outcomes) == 2
        assert {outcome.event_ai_analysis_id for outcome in delivered_outcomes} == {
            canonical_id
        }
        assert send_alert.await_count == 2
        assert all(
            call.args[2]["plain_text"] == canonical_payload["plain_text"]
            and call.args[2]["html_text"] == canonical_html
            and call.args[2]["entities"] is None
            for call in send_alert.await_args_list
        )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_reusable_event_analysis_matches_reordered_news_by_stable_identity(monkeypatch):
    engine, session_local = await build_session_factory()
    try:
        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        stored_news = [
            {"news_id": "n1", "source": "Source A", "title": "Article A"},
            {"news_id": "n2", "source": "Source B", "title": "Article B"},
        ]
        current_news = [
            {"news_id": "n1", "source": "Source B", "title": "Article B"},
            {"news_id": "n2", "source": "Source A", "title": "Article A"},
        ]
        decision = event_decision(related_news_ids=["n1"])
        stored_input = {
            "analysis_id": "event_analysis_btc_stored",
            "symbol": "btc",
            "timestamp_utc": now.isoformat(),
            "market": {
                "price": 103.0,
                "chg_window": -3.0,
                "chg_since_msg": 3.0,
                "chg24h": -1.0,
                "analysed_window_minutes": 180,
            },
            "news": stored_news,
            "raw_event_key": decision.event_key,
            "canonical_event_key": decision.event_key,
            "semantic_family": "price_downtrend",
        }
        current_input = {**stored_input, "news": current_news}
        event_instance_key = alerts._event_instance_key_for_decision(
            decision=decision,
            input_payload=stored_input,
        )
        canonical_plain = "Legacy canonical wording. Not financial advice."
        canonical_html = '<a href="https://example.test/a">Article A - Source A</a>'
        async with session_local() as session:
            market_event = MarketEvent(
                symbol="BTC",
                event_type=alerts.EVENT_ALERT_TYPE,
                event_key=str(decision.event_key),
                event_instance_key=event_instance_key,
                price=103.0,
                previous_price=100.0,
                price_change_percent=3.0,
                detected_at=now,
            )
            session.add(market_event)
            await session.flush()
            analysis = EventAiAnalysis(
                market_event_id=market_event.id,
                analysis_id="event_analysis_btc_stored",
                symbol="BTC",
                analysis_type=alerts.EVENT_ANALYSIS_TYPE,
                provider="groq",
                model="llama-test",
                input_hash="canonical-news",
                raw_input_json=alerts._json_dumps(stored_input),
                status="success",
                should_alert=True,
                event_key=decision.event_key,
                title=decision.title,
                message_body=decision.message_body,
                related_news_ids=alerts._json_dumps(decision.related_news_ids),
                possible_action=decision.possible_action,
                urgency=decision.urgency,
                confidence=decision.confidence,
                plain_text=canonical_plain,
                html_text=canonical_html,
            )
            session.add(analysis)
            await session.commit()
            await session.refresh(market_event)
            await session.refresh(analysis)

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        llm_call = AsyncMock()
        monkeypatch.setattr(alerts, "ask_event_analysis_raw", llm_call)
        reusable = await alerts._get_reusable_event_analysis_by_context(current_input)

        llm_call.assert_not_awaited()
        assert reusable is not None
        assert reusable.market_event_id == market_event.id
        assert reusable.event_ai_analysis_id == analysis.id
        assert reusable.decision.related_news_ids == ["n1"]
        assert reusable.current_context_decision.related_news_ids == ["n2"]
        assert alerts._stable_related_news_ids(
            current_input,
            reusable.current_context_decision.related_news_ids,
        ) == [alerts.make_news_key({"source": "Source A", "title": "Article A"})]
        assert reusable.alert_payload == {
            "plain_text": canonical_plain,
            "html_text": canonical_html,
            "entities": None,
        }
        assert "Article A - Source A" in reusable.alert_payload["html_text"]
        assert "https://example.test/a" in reusable.alert_payload["html_text"]
        assert "Article B - Source B" not in reusable.alert_payload["html_text"]
        assert "https://example.test/b" not in reusable.alert_payload["html_text"]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_legacy_reusable_analysis_reconstructs_real_news_link_when_html_missing(
    monkeypatch,
):
    engine, session_local = await build_session_factory()
    try:
        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        compact_news = [
            {"news_id": "n1", "source": "Source A", "title": "Article A"},
        ]
        candidate_news = [
            {
                "news_id": "n1",
                "source": "Source A",
                "title": "Article A",
                "url": "https://example.test/article-a",
            },
        ]
        decision = event_decision(related_news_ids=["n1"])
        input_payload = {
            "analysis_id": "event_analysis_btc_legacy_links",
            "symbol": "btc",
            "timestamp_utc": now.isoformat(),
            "market": {
                "price": 103.0,
                "chg_window": -3.0,
                "chg_since_msg": 3.0,
                "chg24h": -1.0,
                "analysed_window_minutes": 180,
            },
            "news": compact_news,
            "raw_event_key": decision.event_key,
            "canonical_event_key": decision.event_key,
            "semantic_family": "price_downtrend",
        }
        canonical_payload = alerts._build_event_alert_payload(
            decision=decision,
            input_payload=input_payload,
            related_news=candidate_news,
        )
        event_instance_key = alerts._event_instance_key_for_decision(
            decision=decision,
            input_payload=input_payload,
        )
        async with session_local() as session:
            market_event = MarketEvent(
                symbol="BTC",
                event_type=alerts.EVENT_ALERT_TYPE,
                event_key=str(decision.event_key),
                event_instance_key=event_instance_key,
                price=103.0,
                previous_price=100.0,
                price_change_percent=3.0,
                detected_at=now,
            )
            session.add(market_event)
            await session.flush()
            analysis = EventAiAnalysis(
                market_event_id=market_event.id,
                analysis_id="event_analysis_btc_legacy_links",
                symbol="BTC",
                analysis_type=alerts.EVENT_ANALYSIS_TYPE,
                provider="groq",
                model="llama-test",
                input_hash="legacy-links",
                raw_input_json=alerts._json_dumps(input_payload),
                status="success",
                should_alert=True,
                event_key=decision.event_key,
                title=decision.title,
                message_body=decision.message_body,
                related_news_ids=alerts._json_dumps(decision.related_news_ids),
                possible_action=decision.possible_action,
                urgency=decision.urgency,
                confidence=decision.confidence,
                plain_text=canonical_payload["plain_text"],
                html_text=None,
            )
            session.add(analysis)
            await session.commit()

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        reusable = await alerts._get_reusable_event_analysis_by_context(
            dict(input_payload),
            candidate_news=candidate_news,
        )

        assert reusable is not None
        assert reusable.alert_payload["plain_text"] == canonical_payload["plain_text"]
        if reusable.alert_payload["html_text"]:
            assert "https://example.test/article-a" in reusable.alert_payload["html_text"]
        else:
            assert reusable.alert_payload["entities"] is not None
            assert "https://example.test/article-a" in {
                entity.url for entity in reusable.alert_payload["entities"] if entity.url
            }
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_legacy_reusable_analysis_declines_ambiguous_news_links(monkeypatch):
    engine, session_local = await build_session_factory()
    try:
        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        compact_news = [
            {"news_id": "n1", "source": "Source A", "title": "Article A"},
        ]
        decision = event_decision(related_news_ids=["n1"])
        input_payload = {
            "analysis_id": "event_analysis_btc_ambiguous_links",
            "symbol": "btc",
            "timestamp_utc": now.isoformat(),
            "market": {
                "price": 103.0,
                "chg_window": -3.0,
                "chg_since_msg": 3.0,
                "chg24h": -1.0,
                "analysed_window_minutes": 180,
            },
            "news": compact_news,
        }
        canonical_payload = alerts._build_event_alert_payload(
            decision=decision,
            input_payload=input_payload,
            related_news=[
                {
                    **compact_news[0],
                    "url": "https://example.test/original",
                }
            ],
        )
        async with session_local() as session:
            market_event = MarketEvent(
                symbol="BTC",
                event_type=alerts.EVENT_ALERT_TYPE,
                event_key=str(decision.event_key),
                event_instance_key=alerts._event_instance_key_for_decision(
                    decision=decision,
                    input_payload=input_payload,
                ),
                price=103.0,
                previous_price=100.0,
                price_change_percent=3.0,
                detected_at=now,
            )
            session.add(market_event)
            await session.flush()
            session.add(
                EventAiAnalysis(
                    market_event_id=market_event.id,
                    analysis_id="event_analysis_btc_ambiguous_links",
                    symbol="BTC",
                    analysis_type=alerts.EVENT_ANALYSIS_TYPE,
                    provider="groq",
                    model="llama-test",
                    input_hash="ambiguous-links",
                    raw_input_json=alerts._json_dumps(input_payload),
                    status="success",
                    should_alert=True,
                    event_key=decision.event_key,
                    title=decision.title,
                    message_body=decision.message_body,
                    related_news_ids=alerts._json_dumps(decision.related_news_ids),
                    possible_action=decision.possible_action,
                    urgency=decision.urgency,
                    confidence=decision.confidence,
                    plain_text=canonical_payload["plain_text"],
                    html_text=None,
                )
            )
            await session.commit()

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        reusable = await alerts._get_reusable_event_analysis_by_context(
            dict(input_payload),
            candidate_news=[
                {**compact_news[0], "url": "https://example.test/a"},
                {
                    "news_id": "n2",
                    "source": "Source A",
                    "title": "Article A",
                    "url": "https://example.test/b",
                },
            ],
        )

        assert reusable is None
    finally:
        await engine.dispose()


@pytest.mark.parametrize(
    ("stored_plain_text", "stored_html_text"),
    [(None, None), ("", ""), ("   ", "\t")],
)
def test_late_existing_analysis_preserves_fresh_payload_for_missing_canonical_text(
    stored_plain_text,
    stored_html_text,
):
    fresh_entities = [object()]
    fresh_payload = {
        "plain_text": "Fresh rendered text. Not financial advice.",
        "html_text": "<b>Fresh rendered text.</b>",
        "entities": fresh_entities,
    }

    merged = alerts._merge_existing_event_analysis_payload(
        fresh_payload,
        SimpleNamespace(
            plain_text=stored_plain_text,
            html_text=stored_html_text,
        ),
    )

    assert merged == fresh_payload
    assert merged["entities"] is fresh_entities


@pytest.mark.parametrize(
    ("stored_plain_text", "stored_html_text"),
    [
        ("Canonical plain. Not financial advice.", ""),
        ("", "<b>Canonical HTML.</b>"),
    ],
)
def test_late_existing_analysis_does_not_mix_partial_canonical_and_fresh_payloads(
    stored_plain_text,
    stored_html_text,
):
    fresh_entities = [object()]
    fresh_payload = {
        "plain_text": "Fresh rendered text. Not financial advice.",
        "html_text": "<b>Fresh rendered text.</b>",
        "entities": fresh_entities,
    }
    merged = alerts._merge_existing_event_analysis_payload(
        fresh_payload,
        SimpleNamespace(
            plain_text=stored_plain_text,
            html_text=stored_html_text,
        ),
    )

    assert merged == fresh_payload
    assert merged["entities"] is fresh_entities


def test_late_existing_analysis_uses_complete_canonical_payload_atomically():
    merged = alerts._merge_existing_event_analysis_payload(
        {
            "plain_text": "Fresh rendered text. Not financial advice.",
            "html_text": "<b>Fresh rendered text.</b>",
            "entities": [object()],
        },
        SimpleNamespace(
            plain_text="Canonical plain. Not financial advice.",
            html_text="<b>Canonical HTML.</b>",
        ),
    )

    assert merged == {
        "plain_text": "Canonical plain. Not financial advice.",
        "html_text": "<b>Canonical HTML.</b>",
        "entities": None,
    }


@pytest.mark.asyncio
async def test_deliver_market_event_alert_does_not_create_ai_analysis(monkeypatch):
    engine, session_local = await build_session_factory()
    try:
        async with session_local() as session:
            user = await create_user(session)
            market_event = MarketEvent(
                symbol="BTC",
                event_type=alerts.EVENT_ALERT_TYPE,
                event_key="btc_downward_pressure_2026_05_20",
                event_instance_key="instance-delivery-only",
                price=103.0,
                previous_price=100.0,
                price_change_percent=3.0,
                detected_at=datetime(2026, 5, 20, 12, 0, tzinfo=timezone.utc),
            )
            session.add(market_event)
            await session.commit()
            await session.refresh(market_event)
            analysis = EventAiAnalysis(
                market_event_id=market_event.id,
                analysis_id="event_analysis_btc_delivery_only",
                symbol="BTC",
                analysis_type=alerts.EVENT_ANALYSIS_TYPE,
                provider="groq",
                model="llama-test",
                input_hash="delivery-only",
                status="success",
                should_alert=True,
                plain_text="Delivery text. Not financial advice.",
            )
            session.add(analysis)
            await session.commit()
            await session.refresh(analysis)
            user_id = user.id
            market_event_id = market_event.id
            analysis_id = analysis.id

        groq_call = AsyncMock(side_effect=AssertionError("delivery must not call Groq"))
        save_analysis = AsyncMock(side_effect=AssertionError("delivery must not create analysis"))
        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        monkeypatch.setattr(alerts, "ask_event_analysis_raw", groq_call)
        monkeypatch.setattr(alerts, "save_event_llm_analysis", save_analysis)
        monkeypatch.setattr(
            alerts,
            "_send_alert_to_recipient_with_retry",
            AsyncMock(return_value=(True, None, None)),
        )

        delivered = await alerts._deliver_market_event_alert(
            SimpleNamespace(),
            symbol="btc",
            alert_payload={"plain_text": "Delivery text. Not financial advice."},
            market_event_id=market_event_id,
            event_ai_analysis_id=analysis_id,
            recipients=[alerts.AlertRecipient(chat_id=2001, user_id=user_id)],
            event_type=alerts.EVENT_ALERT_TYPE,
            trigger_source=alerts.EVENT_ANALYSIS_TYPE,
        )

        async with session_local() as session:
            analysis_count = await session.scalar(select(func.count()).select_from(EventAiAnalysis))
            delivery_count = await session.scalar(select(func.count()).select_from(Alert))

        assert delivered is True
        assert analysis_count == 1
        assert delivery_count == 1
        groq_call.assert_not_awaited()
        save_analysis.assert_not_awaited()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("symbol", "premium_required"),
    [("btc", False), ("sol", True)],
)
async def test_should_alert_event_with_eligible_recipient_creates_delivery_rows(
    monkeypatch, symbol, premium_required
):
    engine, session_local = await build_session_factory()
    try:
        async with session_local() as session:
            user = await create_user(session)
            if premium_required:
                await grant_user_premium(
                    session,
                    telegram_user_id=user.telegram_user_id,
                    days=30,
                    now=datetime(2026, 5, 20, 12, 0, tzinfo=timezone.utc),
                )
                await set_user_coin_subscription(
                    session,
                    user_id=user.id,
                    symbol=symbol,
                    is_enabled=True,
                )
            market_event = MarketEvent(
                symbol=symbol.upper(),
                event_type=alerts.EVENT_ALERT_TYPE,
                event_key=f"{symbol}_delivery_gap_regression",
                event_instance_key=f"{symbol}:delivery-gap-regression",
                price=100.0,
                previous_price=98.0,
                price_change_percent=2.0,
                detected_at=datetime(2026, 5, 20, 12, 0, tzinfo=timezone.utc),
            )
            session.add(market_event)
            await session.commit()
            await session.refresh(market_event)
            analysis = EventAiAnalysis(
                market_event_id=market_event.id,
                analysis_id=f"event_analysis_{symbol}_delivery_gap_regression",
                symbol=symbol.upper(),
                analysis_type=alerts.EVENT_ANALYSIS_TYPE,
                provider="groq",
                model="llama-test",
                input_hash=f"{symbol}-delivery-gap",
                status="success",
                should_alert=True,
                plain_text=f"{symbol.upper()} alert. Not financial advice.",
            )
            session.add(analysis)
            await session.commit()
            await session.refresh(analysis)
            market_event_id = market_event.id
            analysis_id = analysis.id
            user_id = user.id

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        monkeypatch.setattr(
            alerts,
            "_send_alert_to_recipient_with_retry",
            AsyncMock(return_value=(True, None, None)),
        )

        delivered = await alerts._deliver_market_event_alert(
            SimpleNamespace(),
            symbol=symbol,
            alert_payload={
                "plain_text": f"{symbol.upper()} alert.\n\nNot financial advice."
            },
            market_event_id=market_event_id,
            event_ai_analysis_id=analysis_id,
            recipients=[alerts.AlertRecipient(chat_id=2001, user_id=user_id)],
            event_type=alerts.EVENT_ALERT_TYPE,
            trigger_source=alerts.EVENT_ANALYSIS_TYPE,
        )

        async with session_local() as session:
            delivery_count = await session.scalar(select(func.count()).select_from(Alert))
            outcome = await session.scalar(select(AlertDeliveryOutcome))

        assert delivered is True
        assert delivery_count == 1
        assert outcome.status == "delivered"
        assert outcome.market_event_id == market_event_id
        assert outcome.event_ai_analysis_id == analysis_id
    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("symbol", "premium_required"),
    [("btc", False), ("sol", True)],
)
async def test_automatic_should_alert_creates_delivery_rows_through_recipient_resolution(
    monkeypatch, symbol, premium_required
):
    engine, session_local = await build_session_factory()
    try:
        async with session_local() as session:
            users = [
                await create_user(session),
                await create_user(session, telegram_user_id=1002, chat_id=2002),
            ]
            if premium_required:
                for user in users:
                    await set_user_coin_subscription(
                        session, user_id=user.id, symbol="btc", is_enabled=False
                    )
                    await grant_user_premium(
                        session,
                        telegram_user_id=user.telegram_user_id,
                        days=3650,
                        now=datetime(2026, 5, 20, 12, 0, tzinfo=timezone.utc),
                    )
                    await set_user_coin_subscription(
                        session, user_id=user.id, symbol=symbol, is_enabled=True
                    )
            await save_price_snapshot(
                session,
                symbol=symbol,
                price=100.0,
                change_24h=-2.4,
                checked_at=datetime.now(timezone.utc) - timedelta(minutes=30),
            )
            user_ids = {user.id for user in users}

        parsed = {
            "symbol": symbol.upper(),
            "should_alert": True,
            "event_key": f"{symbol}_delivery_gap_regression",
            "title": f"{symbol.upper()} market pressure is increasing",
            "message_body": (
                f"{symbol.upper()} has moved enough in the analysed window to warrant "
                "a cautious Event Alert."
            ),
            "related_news_ids": [],
            "possible_action": "Review your exposure calmly and avoid reacting impulsively.",
            "urgency": "high",
            "confidence": "medium",
            "reason_for_no_alert": None,
        }
        groq_call = AsyncMock(return_value=("raw should-alert output", parsed))
        send_alert = AsyncMock(return_value=(True, None, None))

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        monkeypatch.setattr(
            alerts,
            "get_coin_market_data_batch",
            AsyncMock(
                return_value={
                    symbol: {
                        "price": 103.0,
                        "change_24h": -2.4,
                        "change_7d": -4.8,
                    }
                }
            ),
        )
        monkeypatch.setattr(
            alerts,
            "get_db_alert_settings",
            AsyncMock(return_value={"automatic_check_interval_seconds": 300}),
        )
        monkeypatch.setattr(
            alerts,
            "_load_news_driven_alert_candidates",
            AsyncMock(return_value={}),
        )
        monkeypatch.setattr(
            alerts,
            "_select_related_news_context",
            AsyncMock(return_value=([], None, False)),
        )
        monkeypatch.setattr(alerts, "ask_event_analysis_raw", groq_call)
        monkeypatch.setattr(alerts, "_send_alert_to_recipient_with_retry", send_alert)
        monkeypatch.setattr(alerts, "_deliver_market_heartbeat", AsyncMock())

        await alerts.automatic_price_check(SimpleNamespace(application=SimpleNamespace()))

        async with session_local() as session:
            deliveries = list((await session.scalars(select(Alert))).all())
            analyses = list((await session.scalars(select(EventAiAnalysis))).all())
            market_events = list((await session.scalars(select(MarketEvent))).all())
            outcomes = list(
                (await session.scalars(select(AlertDeliveryOutcome))).all()
            )

        assert len(analyses) == 1
        assert len(market_events) == 1
        assert len(deliveries) == 2
        analysis = analyses[0]
        market_event = market_events[0]
        assert analysis.market_event_id == market_event.id
        assert {delivery.market_event_id for delivery in deliveries} == {market_event.id}
        assert {delivery.event_ai_analysis_id for delivery in deliveries} == {analysis.id}
        assert {delivery.user_id for delivery in deliveries} == user_ids
        assert {delivery.status for delivery in deliveries} == {"sent"}
        outcome_statuses = {outcome.status for outcome in outcomes}
        assert alerts.OUTCOME_ALLOWED in outcome_statuses
        assert alerts.OUTCOME_DELIVERED in outcome_statuses
        delivered_outcomes = [
            outcome for outcome in outcomes if outcome.status == alerts.OUTCOME_DELIVERED
        ]
        assert len(delivered_outcomes) == 2
        assert {outcome.market_event_id for outcome in delivered_outcomes} == {market_event.id}
        assert {outcome.event_ai_analysis_id for outcome in delivered_outcomes} == {analysis.id}
        assert {outcome.user_id for outcome in delivered_outcomes} == user_ids
        assert all(outcome.recipient_eligible is True for outcome in delivered_outcomes)
        allowed_outcome = next(
            outcome for outcome in outcomes if outcome.status == alerts.OUTCOME_ALLOWED
        )
        assert allowed_outcome.event_ai_analysis_id == analysis.id
        assert groq_call.await_count == 1
        assert send_alert.await_count == 2
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_weak_llm_positive_is_rejected_before_market_event_creation(monkeypatch):
    engine, session_local = await build_session_factory()
    try:
        async with session_local() as session:
            await create_user(session)
            await save_price_snapshot(
                session,
                symbol="btc",
                price=99.99,
                change_24h=0.2,
                checked_at=datetime.now(timezone.utc) - timedelta(minutes=30),
            )

        parsed = {
            "symbol": "BTC",
            "should_alert": True,
            "event_key": "btc_tiny_move",
            "title": "BTC tiny move",
            "message_body": "BTC moved by 0.01%.",
            "related_news_ids": [],
            "possible_action": "Buy now.",
            "urgency": "high",
            "confidence": "medium",
            "reason_for_no_alert": None,
        }
        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        monkeypatch.setattr(
            alerts,
            "get_coin_market_data_batch",
            AsyncMock(return_value={"btc": {"price": 100.0, "change_24h": 0.2}}),
        )
        monkeypatch.setattr(
            alerts,
            "get_db_alert_settings",
            AsyncMock(return_value={"automatic_check_interval_seconds": 300}),
        )
        monkeypatch.setattr(
            alerts, "_load_news_driven_alert_candidates", AsyncMock(return_value={})
        )
        monkeypatch.setattr(
            alerts,
            "_select_related_news_context",
            AsyncMock(return_value=([], None, False)),
        )
        monkeypatch.setattr(
            alerts, "ask_event_analysis_raw", AsyncMock(return_value=("raw", parsed))
        )
        send = AsyncMock(side_effect=AssertionError("weak event must not be delivered"))
        monkeypatch.setattr(alerts, "_send_alert_to_recipient_with_retry", send)
        monkeypatch.setattr(alerts, "_deliver_market_heartbeat", AsyncMock())

        await alerts.automatic_price_check(SimpleNamespace(application=SimpleNamespace()))

        async with session_local() as session:
            analysis = await session.scalar(select(EventAiAnalysis))
            events = await session.scalar(select(func.count()).select_from(MarketEvent))
            deliveries = await session.scalar(select(func.count()).select_from(Alert))
            outcomes = list((await session.scalars(select(AlertDeliveryOutcome))).all())

        assert analysis.should_alert is True
        assert analysis.market_event_id is None
        assert events == 0
        assert deliveries == 0
        assert any(
            outcome.decision_stage == "significance"
            and outcome.decision_reason == "significance_rejected"
            and outcome.detail == "unsupported_urgency"
            for outcome in outcomes
        )
        send.assert_not_awaited()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_gram_eligible_no_alert_is_healthy_and_keeps_heartbeat_path(monkeypatch):
    engine, session_local = await build_session_factory()
    try:
        async with session_local() as session:
            user = await create_user(session)
            await set_user_coin_subscription(
                session, user_id=user.id, symbol="btc", is_enabled=False
            )
            await grant_user_premium(
                session,
                telegram_user_id=user.telegram_user_id,
                days=3650,
                now=datetime.now(timezone.utc),
            )
            await set_user_coin_subscription(
                session, user_id=user.id, symbol="gram", is_enabled=True
            )

        parsed = {
            "symbol": "GRAM",
            "should_alert": False,
            "event_key": None,
            "title": None,
            "message_body": None,
            "related_news_ids": [],
            "possible_action": None,
            "urgency": None,
            "confidence": "medium",
            "reason_for_no_alert": "The analysed-window move is 0.04% with no material context.",
        }
        provider = AsyncMock(return_value=("raw", parsed))
        heartbeat = AsyncMock()
        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        monkeypatch.setattr(
            alerts,
            "get_coin_market_data_batch",
            AsyncMock(return_value={"gram": {"price": 3.2, "change_24h": 0.3}}),
        )
        monkeypatch.setattr(
            alerts,
            "get_db_alert_settings",
            AsyncMock(return_value={"automatic_check_interval_seconds": 1800}),
        )
        monkeypatch.setattr(
            alerts, "_load_news_driven_alert_candidates", AsyncMock(return_value={})
        )
        monkeypatch.setattr(
            alerts,
            "_select_related_news_context",
            AsyncMock(return_value=([], None, False)),
        )
        monkeypatch.setattr(alerts, "ask_event_analysis_raw", provider)
        monkeypatch.setattr(alerts, "_deliver_market_heartbeat", heartbeat)

        await alerts.automatic_price_check(SimpleNamespace(application=SimpleNamespace()))

        async with session_local() as session:
            analysis = await session.scalar(select(EventAiAnalysis))
            event_count = await session.scalar(select(func.count()).select_from(MarketEvent))
        assert analysis.symbol == "GRAM"
        assert analysis.status == "no_alert"
        assert analysis.should_alert is False
        assert event_count == 0
        provider.assert_awaited_once()
        heartbeat.assert_awaited_once()
    finally:
        await engine.dispose()


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
        "resolve_alert_recipient_outcomes",
        AsyncMock(
            return_value=alerts.AlertRecipientResolution(
                recipients=[alerts.AlertRecipient(chat_id=2001, user_id=1)]
            )
        ),
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
            outcome = await session.scalar(select(AlertDeliveryOutcome))
            assert row.status == "no_alert"
            assert row.should_alert is False
            assert row.related_news_ids == "[]"
            assert row.urgency is None
            assert row.confidence is None
            assert row.error_reason is None
            assert row.error_message is None
            assert outcome.event_ai_analysis_id == row.id
            assert outcome.status == "not_scheduled"
            assert outcome.reason_code == "llm_no_alert"
            assert outcome.decision_stage == "llm"
            assert outcome.decision_reason == "llm_no_alert"
            assert outcome.context_fingerprint
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_news_only_no_alert_persists_news_only_rejected(monkeypatch):
    engine, session_local = await build_session_factory()
    try:
        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        parsed = {
            "symbol": "BTC",
            "should_alert": False,
            "event_key": None,
            "title": None,
            "message_body": None,
            "related_news_ids": [],
            "possible_action": None,
            "urgency": None,
            "confidence": "medium",
            "reason_for_no_alert": (
                "News alone is repeated ETF context, while the analysed-window market "
                "move does not justify a new alert."
            ),
        }
        monkeypatch.setattr(
            alerts,
            "ask_event_analysis_raw",
            AsyncMock(return_value=("raw no-alert output", parsed)),
        )
        payload = {
            "analysis_id": "event_analysis_btc_news_only_no_alert",
            "symbol": "BTC",
            "news": [{"news_id": "n1", "title": "ETF outflows continue"}],
            "market": {"chg_window": 0.1},
        }

        decision, analysis_id = await alerts._create_event_analysis_decision(payload)

        assert decision is not None
        assert analysis_id is not None
        async with session_local() as session:
            outcome = await session.scalar(select(AlertDeliveryOutcome))
        assert outcome.status == "not_scheduled"
        assert outcome.reason_code == "news_only_rejected"
        assert outcome.decision_stage == "llm"
        assert outcome.decision_reason == "news_only_rejected"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_pre_llm_similar_context_reuse_skips_event_analysis_and_delivery(monkeypatch):
    engine, session_local = await build_session_factory()
    payload = {
        "analysis_id": "event_analysis_btc_repeated_context",
        "symbol": "BTC",
        "display_symbol": "BTC",
        "news": [
            {"news_id": "n1", "title": "BTC ETF outflows continue", "source": "Example"}
        ],
        "market": {
            "price": 64000.0,
            "snapshots": [{"m": -180, "p": 64100.0}, {"m": 0, "p": 64000.0}],
            "payload_points": 6,
            "analysed_window_minutes": 180,
            "chg_window": -0.16,
            "chg_since_msg": -0.16,
            "chg24h": -0.4,
        },
    }
    try:
        async with session_local() as session:
            user = await create_user(session)
            user_id = user.id
            session.add(
                AlertDeliveryOutcome(
                    symbol="BTC",
                    alert_type=alerts.EVENT_ALERT_TYPE,
                    status="not_scheduled",
                    reason_code="llm_no_alert",
                    trigger_source=alerts.EVENT_ANALYSIS_TYPE,
                    decision_stage="llm",
                    decision_reason="llm_no_alert",
                    context_fingerprint=alerts._event_context_fingerprint(payload),
                )
            )
            await session.commit()

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        monkeypatch.setattr(alerts, "resolve_symbols_to_check", AsyncMock(return_value=["btc"]))
        monkeypatch.setattr(
            alerts,
            "get_coin_market_data_batch",
            AsyncMock(return_value={"btc": {"price": 64000.0, "change_24h": -0.4}}),
        )
        monkeypatch.setattr(
            alerts,
            "get_db_alert_settings",
            AsyncMock(return_value={"automatic_check_interval_seconds": 1800}),
        )
        monkeypatch.setattr(
            alerts,
            "resolve_alert_recipient_outcomes",
            AsyncMock(
                return_value=alerts.AlertRecipientResolution(
                    recipients=[alerts.AlertRecipient(chat_id=2001, user_id=user_id)]
                )
            ),
        )
        monkeypatch.setattr(
            alerts,
            "_load_news_driven_alert_candidates",
            AsyncMock(return_value={}),
        )
        monkeypatch.setattr(
            alerts,
            "_select_related_news_context",
            AsyncMock(return_value=(payload["news"], None, False)),
        )
        monkeypatch.setattr(alerts, "_build_event_analysis_input", AsyncMock(return_value=payload))
        monkeypatch.setattr(
            alerts,
            "ask_event_analysis_raw",
            AsyncMock(side_effect=AssertionError("similar context should skip LLM")),
        )
        monkeypatch.setattr(
            alerts,
            "_get_or_create_event_alert_market_event",
            AsyncMock(side_effect=AssertionError("similar context must not create event")),
        )
        monkeypatch.setattr(
            alerts,
            "_deliver_market_event_alert",
            AsyncMock(side_effect=AssertionError("similar context must not deliver")),
        )
        monkeypatch.setattr(alerts, "_deliver_market_heartbeat", AsyncMock())
        monkeypatch.setattr(alerts, "_save_price_state", AsyncMock())

        await alerts.automatic_price_check(SimpleNamespace(application=SimpleNamespace()))

        async with session_local() as session:
            analysis_count = await session.scalar(select(func.count()).select_from(EventAiAnalysis))
            market_event_count = await session.scalar(select(func.count()).select_from(MarketEvent))
            delivery_count = await session.scalar(select(func.count()).select_from(Alert))
            outcomes = list(
                (
                    await session.scalars(
                        select(AlertDeliveryOutcome).order_by(AlertDeliveryOutcome.id)
                    )
                ).all()
            )

        assert analysis_count == 0
        assert market_event_count == 0
        assert delivery_count == 0
        assert outcomes[-1].decision_stage == "pre_llm"
        assert outcomes[-1].decision_reason == "similar_context_reused"
        assert outcomes[-1].context_fingerprint == alerts._event_context_fingerprint(payload)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_pre_llm_similarity_reuse_is_conservative_when_market_context_changes(monkeypatch):
    engine, session_local = await build_session_factory()
    base_payload = {
        "analysis_id": "event_analysis_btc_base",
        "symbol": "BTC",
        "news": [{"news_id": "n1", "title": "Analysts say BTC bottomed", "source": "Example"}],
        "market": {"analysed_window_minutes": 180, "chg_window": -1.0, "chg24h": -2.0},
    }
    changed_payload = {
        **base_payload,
        "analysis_id": "event_analysis_btc_changed",
        "market": {"analysed_window_minutes": 180, "chg_window": -6.0, "chg24h": -7.0},
    }
    try:
        async with session_local() as session:
            session.add(
                AlertDeliveryOutcome(
                    symbol="BTC",
                    alert_type=alerts.EVENT_ALERT_TYPE,
                    status="not_scheduled",
                    reason_code="news_only_rejected",
                    trigger_source=alerts.EVENT_ANALYSIS_TYPE,
                    decision_stage="llm",
                    decision_reason="news_only_rejected",
                    context_fingerprint=alerts._event_context_fingerprint(base_payload),
                )
            )
            await session.commit()

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)

        assert (
            await alerts._get_recent_event_analysis_decision_by_similarity(
                changed_payload,
                now=datetime.now(timezone.utc),
            )
            is None
        )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_news_only_should_alert_true_is_rejected_before_delivery(monkeypatch):
    engine, session_local = await build_session_factory()
    try:
        async with session_local() as session:
            user = await create_user(session)
            user_id = user.id

        parsed = {
            "symbol": "BTC",
            "should_alert": True,
            "event_key": "btc_etf_headline",
            "title": "ETF headline raises BTC attention",
            "message_body": "A new ETF report is the only notable input for this alert.",
            "related_news_ids": ["n1"],
            "possible_action": "Review the ETF headline calmly.",
            "urgency": "normal",
            "confidence": "medium",
            "reason_for_no_alert": None,
        }
        payload = {
            "analysis_id": "event_analysis_btc_news_only_true",
            "symbol": "BTC",
            "display_symbol": "BTC",
            "news": [{"news_id": "n1", "title": "ETF flows update", "source": "Example"}],
            "market": {
                "price": 100000.0,
                "snapshots": [{"m": 0, "p": 100000.0}],
                "payload_points": 6,
                "analysed_window_minutes": 180,
                "chg_window": None,
                "chg_since_msg": None,
                "chg24h": 0.2,
            },
        }

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        monkeypatch.setattr(alerts, "resolve_symbols_to_check", AsyncMock(return_value=["btc"]))
        monkeypatch.setattr(
            alerts,
            "get_coin_market_data_batch",
            AsyncMock(return_value={"btc": {"price": 100000.0, "change_24h": 0.2}}),
        )
        monkeypatch.setattr(
            alerts,
            "get_db_alert_settings",
            AsyncMock(return_value={"automatic_check_interval_seconds": 300}),
        )
        monkeypatch.setattr(
            alerts,
            "resolve_alert_recipient_outcomes",
            AsyncMock(
                return_value=alerts.AlertRecipientResolution(
                    recipients=[alerts.AlertRecipient(chat_id=2001, user_id=user_id)]
                )
            ),
        )
        monkeypatch.setattr(
            alerts,
            "_load_news_driven_alert_candidates",
            AsyncMock(return_value={}),
        )
        monkeypatch.setattr(
            alerts,
            "_select_related_news_context",
            AsyncMock(return_value=([{"news_id": "n1", "title": "ETF flows update"}], None, False)),
        )
        monkeypatch.setattr(alerts, "_build_event_analysis_input", AsyncMock(return_value=payload))
        monkeypatch.setattr(
            alerts,
            "ask_event_analysis_raw",
            AsyncMock(return_value=("raw news-only alert output", parsed)),
        )
        monkeypatch.setattr(
            alerts,
            "_get_or_create_event_alert_market_event",
            AsyncMock(side_effect=AssertionError("news-only alert must not create a market event")),
        )
        monkeypatch.setattr(
            alerts,
            "_deliver_market_event_alert",
            AsyncMock(side_effect=AssertionError("news-only alert must not be delivered")),
        )
        monkeypatch.setattr(alerts, "_deliver_market_heartbeat", AsyncMock())
        monkeypatch.setattr(alerts, "_save_price_state", AsyncMock())

        await alerts.automatic_price_check(SimpleNamespace(application=SimpleNamespace()))

        async with session_local() as session:
            analysis = await session.scalar(select(EventAiAnalysis))
            outcome = await session.scalar(select(AlertDeliveryOutcome))
            market_event_count = await session.scalar(select(func.count()).select_from(MarketEvent))
            delivery_count = await session.scalar(select(func.count()).select_from(Alert))

        assert analysis.status == "no_alert"
        assert analysis.should_alert is False
        assert analysis.market_event_id is None
        stored_parsed = alerts.json.loads(analysis.parsed_result_json)
        assert stored_parsed["possible_action"] == "Review the ETF headline calmly."
        assert stored_parsed["should_alert"] is True
        assert outcome.status == "not_scheduled"
        assert outcome.reason_code == "news_only_rejected"
        assert outcome.decision_stage == "llm"
        assert outcome.decision_reason == "news_only_rejected"
        assert outcome.context_fingerprint
        assert market_event_count == 0
        assert delivery_count == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_news_supported_market_event_with_tiny_move_is_allowed(monkeypatch):
    engine, session_local = await build_session_factory()
    try:
        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        parsed = {
            "symbol": "BTC",
            "should_alert": True,
            "event_key": "btc_etf_price_reaction",
            "title": "BTC price starts reacting while ETF news develops",
            "message_body": "BTC price moved during the analysed window as ETF context developed.",
            "related_news_ids": ["n1"],
            "possible_action": "Review the situation calmly.",
            "urgency": "normal",
            "confidence": "medium",
            "reason_for_no_alert": None,
        }
        monkeypatch.setattr(
            alerts,
            "ask_event_analysis_raw",
            AsyncMock(return_value=("raw tiny-move alert output", parsed)),
        )
        payload = {
            "analysis_id": "event_analysis_btc_tiny_market_move",
            "symbol": "BTC",
            "news": [{"news_id": "n1", "title": "ETF flows update", "source": "Example"}],
            "market": {
                "price": 100000.0,
                "snapshots": [{"m": -180, "p": 99990.0}, {"m": 0, "p": 100000.0}],
                "payload_points": 6,
                "analysed_window_minutes": 180,
                "chg_window": 0.01,
                "chg_since_msg": 0.01,
                "chg24h": 0.2,
            },
        }

        decision, analysis_id = await alerts._create_event_analysis_decision(payload)

        assert decision is not None
        assert decision.should_alert is True
        assert decision.possible_action == "Review the situation calmly."
        assert analysis_id is not None
        async with session_local() as session:
            row = await session.scalar(select(EventAiAnalysis))
            outcome = await session.scalar(select(AlertDeliveryOutcome))
        assert row.status == "success"
        assert row.should_alert is True
        assert row.possible_action == "Review the situation calmly."
        assert outcome.status == "allowed"
        assert outcome.reason_code == "llm_should_alert"
        assert outcome.decision_reason == "llm_should_alert"
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
async def test_alert_empty_llm_event_key_is_canonicalized_to_backend_family(monkeypatch):
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
        assert decision.event_key == "btc_volatility"
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
        assert "⚠️ AI — latest invalid_json" in status_text
        assert "Reason: bad json" in status_text
        assert "Latest failure: invalid_json" not in status_text
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
        assert "❌ AI — latest failed: other_error" in status_text
        assert "Reason: provider unavailable" in status_text
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
async def test_filtered_recipient_outcome_records_watchlist_reason(monkeypatch):
    engine, session_local = await build_session_factory()
    now = datetime(2026, 5, 20, 12, 0, tzinfo=timezone.utc)
    try:
        async with session_local() as session:
            user = await create_user(session)

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)

        resolution = await alerts.resolve_alert_recipient_outcomes(
            symbol="eth",
            event_type=alerts.EVENT_ALERT_TYPE,
            now=now,
            bypass_frequency=True,
        )
        assert resolution.recipients == []
        assert resolution.filtered

        await alerts._record_recipient_outcomes(
            resolution.filtered,
            symbol="eth",
            alert_type=alerts.EVENT_ALERT_TYPE,
            market_event_id=None,
            event_ai_analysis_id=None,
            trigger_source=alerts.EVENT_ANALYSIS_TYPE,
        )

        async with session_local() as session:
            outcome = await session.scalar(select(AlertDeliveryOutcome))
            assert outcome.user_id == user.id
            assert outcome.status == "filtered"
            assert outcome.reason_code == "watchlist_disabled"
            assert outcome.recipient_considered is True
            assert outcome.recipient_eligible is False
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_normal_urgency_respects_cooldown_and_high_urgency_shortens_it(
    monkeypatch,
    caplog,
):
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

        with caplog.at_level("DEBUG", logger="bot.alerts"):
            normal_filtered = await alerts._filter_event_recipients_for_cooldown(
                recipients,
                symbol="btc",
                urgency="normal",
                cooldown_seconds=3600,
                now=now,
            )
        assert normal_filtered == []
        assert "event_alert_suppressed" in caplog.text
        assert "suppression_reason=exact_cooldown" in caplog.text
        assert "cooldown_remaining_seconds=900" in caplog.text
        caplog.clear()

        assert await alerts._filter_event_recipients_for_cooldown(
            recipients,
            symbol="btc",
            urgency="high",
            cooldown_seconds=3600,
            now=now,
        ) == recipients
        assert "event_alert_suppressed" not in caplog.text
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_semantic_event_alert_cooldown_suppresses_same_user_symbol_and_key(
    monkeypatch,
    caplog,
):
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

        with caplog.at_level("DEBUG", logger="bot.alerts"):
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
        assert "event_alert_semantic_cooldown_check" in caplog.text
        assert "allowed=False" in caplog.text
        assert "event_alert_suppressed" in caplog.text
        assert "suppression_reason=semantic_cooldown" in caplog.text
        assert "cooldown_remaining_seconds=10800" in caplog.text
        assert "user_id=" not in caplog.text
        assert "chat_id=" not in caplog.text
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_semantic_event_alert_cooldown_suppresses_different_keys_in_same_family(
    monkeypatch,
    caplog,
):
    engine, session_local = await build_session_factory()
    now = datetime(2026, 6, 3, 21, 30, tzinfo=timezone.utc)
    try:
        async with session_local() as session:
            user = await create_user(session)
            previous = canonicalize_event_key("btc", "btc_price_drop")
            current = canonicalize_event_key("btc", "btc_selloff_prediction")
            await seed_sent_event_alert(
                session,
                user_id=user.id,
                chat_id=user.telegram_chat_id,
                symbol="btc",
                event_key=previous.canonical_event_key,
                created_at=now - timedelta(hours=1),
            )

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)

        with caplog.at_level("DEBUG", logger="bot.alerts"):
            filtered = await alerts._filter_event_recipients_for_cooldown(
                [alerts.AlertRecipient(chat_id=2001, user_id=user.id)],
                symbol="btc",
                urgency="normal",
                cooldown_seconds=0,
                canonical_event_key=current.canonical_event_key,
                semantic_family=current.semantic_family,
                semantic_cooldown_seconds=4 * 3600,
                now=now,
            )

        assert previous.canonical_event_key == current.canonical_event_key
        assert current.semantic_family == "price_downtrend"
        assert filtered == []
        assert "semantic_family=price_downtrend" in caplog.text
        assert "suppression_reason=semantic_cooldown" in caplog.text
        assert "user_id=" not in caplog.text
        assert "chat_id=" not in caplog.text
    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("symbol", ["btc", "eth"])
async def test_semantic_cooldown_suppresses_equivalent_cross_family_price_context(
    monkeypatch,
    symbol,
):
    engine, session_local = await build_session_factory()
    now = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)
    try:
        async with session_local() as session:
            user = await create_user(session)
            await seed_sent_event_alert(
                session,
                user_id=user.id,
                chat_id=user.telegram_chat_id,
                symbol=symbol,
                event_key=f"{symbol}_price_downtrend",
                urgency="normal",
                analysed_window_minutes=180,
                analysed_window_change_percent=-3.0,
                stable_related_news_ids=[],
                semantic_family="price_downtrend",
                price_action_traits=[
                    "directional_move", "level_interaction", "level_test_or_hold"
                ],
                created_at=now - timedelta(hours=1),
            )

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)

        result = await alerts._filter_event_recipients_for_cooldown(
            [alerts.AlertRecipient(chat_id=2001, user_id=user.id)],
            symbol=symbol,
            urgency="normal",
            cooldown_seconds=0,
            canonical_event_key=f"{symbol}_price_level_range",
            semantic_family="price_level_range",
            current_movement_percent=-3.2,
            current_analysed_window_minutes=180,
            current_price_action_traits=[
                "directional_move", "level_interaction", "level_test_or_hold"
            ],
            current_stable_news_ids=[],
            semantic_cooldown_seconds=4 * 3600,
            now=now,
            return_summary=True,
        )

        assert result.recipients == []
        assert result.suppression_reason_counts == {"semantic_cooldown": 1}
        assert result.suppressed[0].previous_alert_id is not None
    finally:
        await engine.dispose()


@pytest.mark.parametrize("symbol", ["btc", "eth"])
def test_news_or_etf_family_wording_cannot_bypass_equivalent_price_context(symbol):
    assert alerts._event_cross_family_context_matches(
        symbol=symbol,
        previous_event_key=f"{symbol}_etf_flows",
        previous_semantic_family="etf_flows",
        previous_numeric_context={
            "analysed_window_change_percent": 2.0,
            "analysed_window_minutes": 180,
            "price_action_traits": ["directional_move"],
        },
        current_semantic_family="price_uptrend",
        current_movement_percent=2.1,
        current_analysed_window_minutes=180,
        current_price_action_traits=["directional_move"],
    )

    assert not alerts._event_cross_family_context_matches(
        symbol=symbol,
        previous_event_key=f"{symbol}_protocol_security_risk",
        previous_semantic_family="protocol_security_risk",
        previous_numeric_context={
            "analysed_window_change_percent": -2.0,
            "analysed_window_minutes": 180,
            "price_action_traits": ["directional_move"],
        },
        current_semantic_family="price_downtrend",
        current_movement_percent=-2.1,
        current_analysed_window_minutes=180,
        current_price_action_traits=["directional_move"],
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("urgency", "movement"),
    [("high", -3.6), ("normal", -5.5)],
)
async def test_semantic_cooldown_allows_cross_family_market_escalation(
    monkeypatch,
    urgency,
    movement,
):
    engine, session_local = await build_session_factory()
    now = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)
    try:
        async with session_local() as session:
            user = await create_user(session)
            await seed_sent_event_alert(
                session,
                user_id=user.id,
                chat_id=user.telegram_chat_id,
                symbol="btc",
                event_key="btc_price_downtrend",
                urgency="normal",
                analysed_window_minutes=180,
                analysed_window_change_percent=-3.0,
                stable_related_news_ids=["article:old"],
                semantic_family="price_downtrend",
                price_action_traits=[
                    "directional_move", "level_interaction", "level_test_or_hold"
                ],
                created_at=now - timedelta(hours=1),
            )

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)

        result = await alerts._filter_event_recipients_for_cooldown(
            [alerts.AlertRecipient(chat_id=2001, user_id=user.id)],
            symbol="btc",
            urgency=urgency,
            cooldown_seconds=0,
            canonical_event_key="btc_price_level_range",
            semantic_family="price_level_range",
            current_movement_percent=movement,
            current_analysed_window_minutes=180,
            current_price_action_traits=[
                "directional_move", "level_interaction", "level_test_or_hold"
            ],
            current_stable_news_ids=["article:shared"],
            semantic_cooldown_seconds=4 * 3600,
            now=now,
            return_summary=True,
        )

        assert result.recipients == [alerts.AlertRecipient(chat_id=2001, user_id=user.id)]
        assert result.delivery_decision_reasons_by_recipient[(user.id, 2001)] == (
            "allowed_urgency_escalation"
            if urgency == "high"
            else "allowed_stronger_movement"
        )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_semantic_cooldown_persists_cumulative_strengthening_allow_reason(
    monkeypatch,
):
    engine, session_local = await build_session_factory()
    now = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)
    try:
        async with session_local() as session:
            user = await create_user(session)
            await seed_sent_event_alert(
                session,
                user_id=user.id,
                chat_id=user.telegram_chat_id,
                symbol="eth",
                event_key="eth_price_uptrend",
                urgency="normal",
                analysed_window_minutes=180,
                analysed_window_change_percent=1.0,
                cumulative_change_percent=1.1,
                persistence_ratio=0.7,
                semantic_family="price_uptrend",
                price_action_traits=["directional_move"],
                created_at=now - timedelta(hours=1),
            )

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        result = await alerts._filter_event_recipients_for_cooldown(
            [alerts.AlertRecipient(chat_id=2001, user_id=user.id)],
            symbol="eth",
            urgency="normal",
            cooldown_seconds=0,
            canonical_event_key="eth_price_uptrend",
            semantic_family="price_uptrend",
            current_movement_percent=1.1,
            current_analysed_window_minutes=180,
            current_price_action_traits=["directional_move"],
            current_cumulative_change_percent=2.2,
            current_persistence_ratio=0.8,
            semantic_cooldown_seconds=4 * 3600,
            now=now,
            return_summary=True,
        )

        assert result.recipients == [alerts.AlertRecipient(chat_id=2001, user_id=user.id)]
        assert result.delivery_decision_reasons_by_recipient[(user.id, 2001)] == (
            "allowed_cumulative_strengthening"
        )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_semantic_cooldown_cross_family_new_news_only_does_not_bypass(
    monkeypatch,
):
    engine, session_local = await build_session_factory()
    now = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)
    try:
        async with session_local() as session:
            user = await create_user(session)
            await seed_sent_event_alert(
                session,
                user_id=user.id,
                chat_id=user.telegram_chat_id,
                symbol="btc",
                event_key="btc_price_downtrend",
                urgency="normal",
                analysed_window_minutes=180,
                analysed_window_change_percent=-3.0,
                stable_related_news_ids=["article:shared"],
                semantic_family="price_downtrend",
                price_action_traits=["directional_move", "volatility_regime"],
                created_at=now - timedelta(hours=1),
            )

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)

        result = await alerts._filter_event_recipients_for_cooldown(
            [alerts.AlertRecipient(chat_id=2001, user_id=user.id)],
            symbol="btc",
            urgency="normal",
            cooldown_seconds=0,
            canonical_event_key="btc_volatility",
            semantic_family="volatility",
            current_movement_percent=-3.6,
            current_analysed_window_minutes=180,
            current_price_action_traits=["directional_move", "volatility_regime"],
            current_stable_news_ids=["article:new"],
            semantic_cooldown_seconds=4 * 3600,
            now=now,
        )

        assert result == []
    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("current_family", "movement", "window"),
    [
        ("regulatory", -3.1, 180),
        ("price_uptrend", 3.1, 180),
        ("price_level_range", -3.1, 60),
    ],
)
async def test_semantic_cooldown_keeps_distinct_cross_family_events_deliverable(
    monkeypatch,
    current_family,
    movement,
    window,
):
    engine, session_local = await build_session_factory()
    now = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)
    try:
        async with session_local() as session:
            user = await create_user(session)
            await seed_sent_event_alert(
                session,
                user_id=user.id,
                chat_id=user.telegram_chat_id,
                symbol="btc",
                event_key="btc_price_downtrend",
                urgency="normal",
                analysed_window_minutes=180,
                analysed_window_change_percent=-3.0,
                stable_related_news_ids=["article:shared"],
                semantic_family="price_downtrend",
                created_at=now - timedelta(hours=1),
            )

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)

        result = await alerts._filter_event_recipients_for_cooldown(
            [alerts.AlertRecipient(chat_id=2001, user_id=user.id)],
            symbol="btc",
            urgency="normal",
            cooldown_seconds=0,
            canonical_event_key=f"btc_{current_family}",
            semantic_family=current_family,
            current_movement_percent=movement,
            current_analysed_window_minutes=window,
            current_stable_news_ids=["article:shared"],
            semantic_cooldown_seconds=4 * 3600,
            now=now,
        )

        assert result == [alerts.AlertRecipient(chat_id=2001, user_id=user.id)]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("current_family", "current_traits"),
    [
        ("price_level_range", ["level_interaction"]),
        ("volatility", ["volatility_regime"]),
    ],
)
async def test_cross_family_same_direction_and_window_keeps_distinct_price_traits_deliverable(
    monkeypatch,
    current_family,
    current_traits,
):
    engine, session_local = await build_session_factory()
    now = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)
    try:
        async with session_local() as session:
            user = await create_user(session)
            await seed_sent_event_alert(
                session,
                user_id=user.id,
                chat_id=user.telegram_chat_id,
                symbol="btc",
                event_key="btc_price_downtrend",
                urgency="normal",
                analysed_window_minutes=180,
                analysed_window_change_percent=-3.0,
                semantic_family="price_downtrend",
                price_action_traits=["directional_move"],
                created_at=now - timedelta(hours=1),
            )

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)

        result = await alerts._filter_event_recipients_for_cooldown(
            [alerts.AlertRecipient(chat_id=2001, user_id=user.id)],
            symbol="btc",
            urgency="normal",
            cooldown_seconds=0,
            canonical_event_key=f"btc_{current_family}",
            semantic_family=current_family,
            current_movement_percent=-3.1,
            current_analysed_window_minutes=180,
            current_price_action_traits=current_traits,
            semantic_cooldown_seconds=4 * 3600,
            now=now,
        )

        assert result == [alerts.AlertRecipient(chat_id=2001, user_id=user.id)]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_negated_level_break_does_not_suppress_later_genuine_break(monkeypatch):
    engine, session_local = await build_session_factory()
    now = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)
    previous_traits = alerts._price_action_context_traits(
        semantic_family="price_level_range",
        raw_event_key="btc_price_level_range",
        title="BTC decline shows no sign of a breakdown near support",
    )
    current_traits = alerts._price_action_context_traits(
        semantic_family="price_downtrend",
        raw_event_key="btc_break_below_support",
        title="BTC drops below support near the range",
    )
    try:
        async with session_local() as session:
            user = await create_user(session)
            await seed_sent_event_alert(
                session,
                user_id=user.id,
                chat_id=user.telegram_chat_id,
                symbol="btc",
                event_key="btc_price_level_range",
                urgency="normal",
                analysed_window_minutes=180,
                analysed_window_change_percent=-3.0,
                semantic_family="price_level_range",
                price_action_traits=previous_traits,
                created_at=now - timedelta(hours=1),
            )

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)

        result = await alerts._filter_event_recipients_for_cooldown(
            [alerts.AlertRecipient(chat_id=2001, user_id=user.id)],
            symbol="btc",
            urgency="normal",
            cooldown_seconds=0,
            canonical_event_key="btc_price_downtrend",
            semantic_family="price_downtrend",
            current_movement_percent=-3.1,
            current_analysed_window_minutes=180,
            current_price_action_traits=current_traits,
            semantic_cooldown_seconds=4 * 3600,
            now=now,
        )

        assert result == [alerts.AlertRecipient(chat_id=2001, user_id=user.id)]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_semantic_cooldown_keeps_unknown_events_distinct_despite_shared_news(monkeypatch):
    engine, session_local = await build_session_factory()
    now = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)
    try:
        async with session_local() as session:
            user = await create_user(session)
            await seed_sent_event_alert(
                session,
                user_id=user.id,
                chat_id=user.telegram_chat_id,
                symbol="btc",
                event_key="btc_custom_alpha",
                urgency="normal",
                analysed_window_minutes=180,
                analysed_window_change_percent=-3.0,
                stable_related_news_ids=["article:shared"],
                semantic_family=None,
                created_at=now - timedelta(hours=1),
            )

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)

        result = await alerts._filter_event_recipients_for_cooldown(
            [alerts.AlertRecipient(chat_id=2001, user_id=user.id)],
            symbol="btc",
            urgency="normal",
            cooldown_seconds=0,
            canonical_event_key="btc_custom_beta",
            semantic_family=None,
            current_movement_percent=-3.1,
            current_analysed_window_minutes=180,
            current_stable_news_ids=["article:shared"],
            semantic_cooldown_seconds=4 * 3600,
            now=now,
        )

        assert result == [alerts.AlertRecipient(chat_id=2001, user_id=user.id)]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_cross_family_price_namespace_does_not_change_non_btc_delivery(monkeypatch):
    engine, session_local = await build_session_factory()
    now = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)
    try:
        async with session_local() as session:
            user = await create_user(session)
            await seed_sent_event_alert(
                session,
                user_id=user.id,
                chat_id=user.telegram_chat_id,
                symbol="eth",
                event_key="eth_price_downtrend",
                urgency="normal",
                analysed_window_minutes=180,
                analysed_window_change_percent=-3.0,
                semantic_family="price_downtrend",
                created_at=now - timedelta(hours=1),
            )

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)

        result = await alerts._filter_event_recipients_for_cooldown(
            [alerts.AlertRecipient(chat_id=2001, user_id=user.id)],
            symbol="eth",
            urgency="normal",
            cooldown_seconds=0,
            canonical_event_key="eth_volatility",
            semantic_family="volatility",
            current_movement_percent=-3.1,
            current_analysed_window_minutes=180,
            semantic_cooldown_seconds=4 * 3600,
            now=now,
        )

        assert result == [alerts.AlertRecipient(chat_id=2001, user_id=user.id)]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_semantic_event_alert_cooldown_suppresses_previous_key_by_family(
    monkeypatch,
    caplog,
):
    engine, session_local = await build_session_factory()
    now = datetime(2026, 6, 3, 21, 30, tzinfo=timezone.utc)
    try:
        async with session_local() as session:
            user = await create_user(session)
            current = canonicalize_event_key(
                "btc",
                "news_catalyst",
                title="BTC holds near $63k as traders watch support",
                message_body="Bitcoin stayed around a key support level.",
            )
            await seed_sent_event_alert(
                session,
                user_id=user.id,
                chat_id=user.telegram_chat_id,
                symbol="btc",
                event_key="btc_volatility",
                urgency="normal",
                analysed_window_change_percent=1.0,
                semantic_family=current.semantic_family,
                created_at=now - timedelta(hours=1),
            )

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)

        with caplog.at_level("DEBUG", logger="bot.alerts"):
            filtered = await alerts._filter_event_recipients_for_cooldown(
                [alerts.AlertRecipient(chat_id=2001, user_id=user.id)],
                symbol="btc",
                urgency="normal",
                cooldown_seconds=0,
                canonical_event_key=current.canonical_event_key,
                semantic_family=current.semantic_family,
                current_movement_percent=1.2,
                semantic_cooldown_seconds=4 * 3600,
                now=now,
            )

        assert current.semantic_family == "price_level_range"
        assert current.canonical_event_key == "btc_price_level_range"
        assert filtered == []
        assert "semantic_family=price_level_range" in caplog.text
        assert "material_movement_increased=False" in caplog.text
        assert "new_news_driver=False" in caplog.text
        assert "suppression_reason=semantic_cooldown" in caplog.text
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_semantic_event_alert_cooldown_allows_same_family_urgency_increase(monkeypatch):
    engine, session_local = await build_session_factory()
    now = datetime(2026, 6, 3, 21, 30, tzinfo=timezone.utc)
    try:
        async with session_local() as session:
            user = await create_user(session)
            event_key = canonicalize_event_key("btc", "btc_price_drop").canonical_event_key
            await seed_sent_event_alert(
                session,
                user_id=user.id,
                chat_id=user.telegram_chat_id,
                symbol="btc",
                event_key=event_key,
                urgency="normal",
                analysed_window_change_percent=-3.0,
                created_at=now - timedelta(minutes=10),
            )

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)

        filtered = await alerts._filter_event_recipients_for_cooldown(
            [alerts.AlertRecipient(chat_id=2001, user_id=user.id)],
            symbol="btc",
            urgency="high",
            cooldown_seconds=1800,
            canonical_event_key=event_key,
            semantic_family="price_downtrend",
            current_movement_percent=-3.6,
            semantic_cooldown_seconds=4 * 3600,
            now=now,
        )

        assert filtered == [alerts.AlertRecipient(chat_id=2001, user_id=user.id)]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_semantic_event_alert_cooldown_allows_material_movement_increase(monkeypatch):
    engine, session_local = await build_session_factory()
    now = datetime(2026, 6, 3, 21, 30, tzinfo=timezone.utc)
    try:
        async with session_local() as session:
            user = await create_user(session)
            event_key = canonicalize_event_key("btc", "btc_price_drop").canonical_event_key
            await seed_sent_event_alert(
                session,
                user_id=user.id,
                chat_id=user.telegram_chat_id,
                symbol="btc",
                event_key=event_key,
                urgency="normal",
                analysed_window_change_percent=-3.0,
                created_at=now - timedelta(minutes=10),
            )

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)

        filtered = await alerts._filter_event_recipients_for_cooldown(
            [alerts.AlertRecipient(chat_id=2001, user_id=user.id)],
            symbol="btc",
            urgency="normal",
            cooldown_seconds=1800,
            canonical_event_key=event_key,
            semantic_family="price_downtrend",
            current_movement_percent=-5.5,
            semantic_cooldown_seconds=4 * 3600,
            now=now,
        )

        assert filtered == [alerts.AlertRecipient(chat_id=2001, user_id=user.id)]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_delivery_reason_market_context_changed_is_per_recipient(monkeypatch):
    engine, session_local = await build_session_factory()
    now = datetime(2026, 6, 3, 21, 30, tzinfo=timezone.utc)
    try:
        async with session_local() as session:
            normal_user = await create_user(session, telegram_user_id=1001, chat_id=2001)
            escalated_user = await create_user(session, telegram_user_id=1002, chat_id=2002)
            suppressed_user = await create_user(session, telegram_user_id=1003, chat_id=2003)
            event_key = canonicalize_event_key("btc", "btc_price_drop").canonical_event_key
            await seed_sent_event_alert(
                session,
                user_id=escalated_user.id,
                chat_id=escalated_user.telegram_chat_id,
                symbol="btc",
                event_key=event_key,
                urgency="normal",
                analysed_window_change_percent=-3.0,
                semantic_family="price_downtrend",
                created_at=now - timedelta(minutes=10),
            )
            await seed_sent_event_alert(
                session,
                user_id=suppressed_user.id,
                chat_id=suppressed_user.telegram_chat_id,
                symbol="btc",
                event_key=event_key,
                urgency="normal",
                analysed_window_change_percent=-4.0,
                semantic_family="price_downtrend",
                created_at=now - timedelta(minutes=10),
            )
            current_event = MarketEvent(
                symbol="BTC",
                event_type=alerts.EVENT_ALERT_TYPE,
                event_key=event_key,
                event_instance_key="mixed-recipient-delivery-reason",
                price=100.0,
                previous_price=95.0,
                price_change_percent=-5.5,
                detected_at=now,
            )
            session.add(current_event)
            await session.flush()
            analysis = EventAiAnalysis(
                market_event_id=current_event.id,
                analysis_id="event_analysis_btc_mixed_recipients",
                symbol="BTC",
                analysis_type=alerts.EVENT_ANALYSIS_TYPE,
                provider="groq",
                model="llama-test",
                input_hash="mixed-recipients",
                status="success",
                should_alert=True,
                plain_text="BTC moved materially. Not financial advice.",
            )
            session.add(analysis)
            await session.commit()
            await session.refresh(current_event)
            await session.refresh(analysis)

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)
        groq_call = AsyncMock(side_effect=AssertionError("delivery must not call Groq"))
        monkeypatch.setattr(alerts, "ask_event_analysis_raw", groq_call)
        monkeypatch.setattr(
            alerts,
            "_send_alert_to_recipient_with_retry",
            AsyncMock(return_value=(True, None, None)),
        )
        recipients = [
            alerts.AlertRecipient(chat_id=normal_user.telegram_chat_id, user_id=normal_user.id),
            alerts.AlertRecipient(
                chat_id=escalated_user.telegram_chat_id,
                user_id=escalated_user.id,
            ),
            alerts.AlertRecipient(
                chat_id=suppressed_user.telegram_chat_id,
                user_id=suppressed_user.id,
            ),
        ]

        result = await alerts._filter_event_recipients_for_cooldown(
            recipients,
            symbol="btc",
            urgency="normal",
            cooldown_seconds=0,
            canonical_event_key=event_key,
            semantic_family="price_downtrend",
            current_movement_percent=-5.5,
            semantic_cooldown_seconds=4 * 3600,
            now=now,
            return_summary=True,
        )
        await alerts._record_recipient_outcomes(
            result.suppressed,
            symbol="btc",
            alert_type=alerts.EVENT_ALERT_TYPE,
            market_event_id=current_event.id,
            event_ai_analysis_id=analysis.id,
            trigger_source=alerts.EVENT_ANALYSIS_TYPE,
            semantic_family="price_downtrend",
        )
        delivered = await alerts._deliver_market_event_alert(
            SimpleNamespace(),
            symbol="btc",
            alert_payload={"plain_text": "BTC moved materially. Not financial advice."},
            market_event_id=current_event.id,
            event_ai_analysis_id=analysis.id,
            recipients=result.recipients,
            event_type=alerts.EVENT_ALERT_TYPE,
            trigger_source=alerts.EVENT_ANALYSIS_TYPE,
            semantic_family="price_downtrend",
            delivery_decision_reasons_by_recipient=(
                result.delivery_decision_reasons_by_recipient
            ),
        )

        async with session_local() as session:
            outcomes = list(
                (
                    await session.scalars(
                        select(AlertDeliveryOutcome).where(
                            AlertDeliveryOutcome.market_event_id == current_event.id
                        )
                    )
                ).all()
            )

        reasons_by_user = {outcome.user_id: outcome.decision_reason for outcome in outcomes}
        assert delivered is True
        assert result.recipients == [recipients[0], recipients[1]]
        assert len(result.suppressed) == 1
        assert reasons_by_user[normal_user.id] == "delivered"
        assert reasons_by_user[escalated_user.id] == "allowed_stronger_movement"
        assert reasons_by_user[suppressed_user.id] == "semantic_cooldown_suppressed"
        groq_call.assert_not_awaited()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_semantic_event_alert_cooldown_suppresses_new_news_driver_without_market_change(
    monkeypatch,
):
    engine, session_local = await build_session_factory()
    now = datetime(2026, 6, 3, 21, 30, tzinfo=timezone.utc)
    try:
        async with session_local() as session:
            user = await create_user(session)
            event_key = canonicalize_event_key("btc", "btc_price_drop").canonical_event_key
            await seed_sent_event_alert(
                session,
                user_id=user.id,
                chat_id=user.telegram_chat_id,
                symbol="btc",
                event_key=event_key,
                urgency="normal",
                analysed_window_change_percent=-3.0,
                stable_related_news_ids=["source_title:old"],
                created_at=now - timedelta(minutes=10),
            )

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)

        filtered = await alerts._filter_event_recipients_for_cooldown(
            [alerts.AlertRecipient(chat_id=2001, user_id=user.id)],
            symbol="btc",
            urgency="normal",
            cooldown_seconds=1800,
            canonical_event_key=event_key,
            semantic_family="price_downtrend",
            current_movement_percent=-3.1,
            current_stable_news_ids=["source_title:old", "source_title:new"],
            semantic_cooldown_seconds=4 * 3600,
            now=now,
        )

        assert filtered == []
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_semantic_event_alert_cooldown_suppresses_same_family_without_escalation(
    monkeypatch,
):
    engine, session_local = await build_session_factory()
    now = datetime(2026, 6, 3, 21, 30, tzinfo=timezone.utc)
    try:
        async with session_local() as session:
            user = await create_user(session)
            event_key = canonicalize_event_key("btc", "btc_price_drop").canonical_event_key
            await seed_sent_event_alert(
                session,
                user_id=user.id,
                chat_id=user.telegram_chat_id,
                symbol="btc",
                event_key=event_key,
                urgency="normal",
                analysed_window_change_percent=-3.0,
                stable_related_news_ids=["source_title:old"],
                created_at=now - timedelta(minutes=10),
            )

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)

        result = await alerts._filter_event_recipients_for_cooldown(
            [alerts.AlertRecipient(chat_id=2001, user_id=user.id)],
            symbol="btc",
            urgency="normal",
            cooldown_seconds=1800,
            canonical_event_key=event_key,
            semantic_family="price_downtrend",
            current_movement_percent=-4.0,
            current_stable_news_ids=["source_title:old"],
            semantic_cooldown_seconds=4 * 3600,
            now=now,
            return_summary=True,
        )

        assert result.recipients == []
        assert result.suppression_reason_counts == {"semantic_cooldown": 1}
        await alerts._record_recipient_outcomes(
            result.suppressed,
            symbol="btc",
            alert_type=alerts.EVENT_ALERT_TYPE,
            market_event_id=None,
            event_ai_analysis_id=None,
            trigger_source=alerts.EVENT_ANALYSIS_TYPE,
            semantic_family="price_downtrend",
        )
        async with session_local() as session:
            outcome = await session.scalar(select(AlertDeliveryOutcome))
            assert outcome.status == "suppressed"
            assert outcome.reason_code == "similar_event_suppressed"
            assert outcome.semantic_family == "price_downtrend"
            assert outcome.decision_stage == "semantic_cooldown"
            assert outcome.decision_reason == "semantic_cooldown_suppressed"
            assert outcome.previous_alert_id is not None
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_event_recipient_cooldown_filter_can_return_suppression_summary(monkeypatch):
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
                    created_at=now - timedelta(minutes=10),
                )
            )
            await session.commit()

        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)

        result = await alerts._filter_event_recipients_for_cooldown(
            [alerts.AlertRecipient(chat_id=2001, user_id=user.id)],
            symbol="btc",
            urgency="normal",
            cooldown_seconds=1800,
            now=now,
            return_summary=True,
        )

        assert result.recipients == []
        assert result.suppression_reason_counts == {"exact_cooldown": 1}
        await alerts._record_recipient_outcomes(
            result.suppressed,
            symbol="btc",
            alert_type=alerts.EVENT_ALERT_TYPE,
            market_event_id=None,
            event_ai_analysis_id=None,
            trigger_source=alerts.EVENT_ANALYSIS_TYPE,
        )
        async with session_local() as session:
            outcome = await session.scalar(select(AlertDeliveryOutcome))
            assert outcome.status == "cooldown"
            assert outcome.reason_code == "cooldown_active"
            assert outcome.recipient_considered is True
            assert outcome.recipient_eligible is False
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


def test_llm_severity_is_normalized_to_allowed_values():
    assert normalize_stored_severity("info") == "low"
    assert normalize_stored_severity("watch") == "medium"
    assert normalize_stored_severity("moderate") == "medium"
    assert normalize_stored_severity("critical") == "extreme"


def test_new_user_facing_alert_types_are_limited_to_product_model():
    assert alerts.PRODUCT_ALERT_TYPES == {"market_update", "important_alert", "critical_alert"}


@pytest.mark.asyncio
async def test_last_market_update_time_persists_after_restart(tmp_path):
    db_path = tmp_path / "market_update.sqlite"
    engine, session_local = await init_db(
        f"sqlite+aiosqlite:///{db_path.as_posix()}",
        run_migrations=True,
    )
    update_time = datetime.now(timezone.utc)
    async with session_local() as session:
        await upsert_user_symbol_alert_state(
            session,
            user_id=1,
            symbol="btc",
            last_market_update_time=update_time,
        )

    async with session_local() as restarted_session:
        row = await get_user_symbol_alert_state(
            restarted_session,
            user_id=1,
            symbol="btc",
        )

    assert row is not None
    assert row.last_market_update_time is not None
    await engine.dispose()


@pytest.mark.asyncio
async def test_important_alert_updates_effective_baseline(tmp_path, monkeypatch):
    db_path = tmp_path / "important_baseline.sqlite"
    engine, session_local = await init_db(
        f"sqlite+aiosqlite:///{db_path.as_posix()}",
        run_migrations=True,
    )
    monkeypatch.setattr(alerts, "DB_ENABLED", True)
    monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)

    await alerts._persist_successful_product_alert_state(
        recipient=alerts.AlertRecipient(chat_id=123, user_id=1, alert_frequency_seconds=3600),
        symbol="eth",
        event_type=alerts.NotificationType.IMPORTANT_ALERT.value,
        severity="medium",
        numeric_context=json.dumps(
            {
                "notification_direction": "up",
                "change_since_last_market_update_percent": 1.4,
                "current_price": 2500.0,
            }
        ),
    )

    async with session_local() as session:
        row = await get_user_symbol_alert_state(session, user_id=1, symbol="eth")

    assert row is not None
    assert row.last_important_alert_time is not None
    assert row.last_market_update_time is not None
    assert row.last_cumulative_movement_percent == 1.4
    await engine.dispose()
