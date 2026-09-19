import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import bot.alerts as alerts
from bot.alerting.event_analysis import canonicalize_event_key
from bot.db.database import Base


@pytest.mark.parametrize(
    ("raw_event_key", "title", "news_title", "material", "expected_family"),
    (
        (
            "btc_price_down_180min",
            "Bitcoin dips over 3-hour window",
            "US stock perpetual futures",
            False,
            "price_downtrend",
        ),
        (
            "btc_price_down_180min",
            "Bitcoin dips over 3-hour window",
            "Options positioning changes",
            True,
            "price_downtrend",
        ),
        (
            "btc_price_up_180min",
            "Bitcoin rises over 3-hour window",
            "ETF inflows update",
            True,
            "price_uptrend",
        ),
        (
            "btc_price_down_180min",
            "Bitcoin dips over 3-hour window",
            "Regulatory hearing update",
            False,
            "price_downtrend",
        ),
    ),
)
def test_core_price_identity_cannot_be_hijacked_by_related_news(
    raw_event_key, title, news_title, material, expected_family
):
    canonical = canonicalize_event_key(
        "btc",
        raw_event_key,
        title=title,
        message_body="Short-term market move.",
        related_news=[{"title": news_title, "material": material}],
    )

    assert canonical.semantic_family == expected_family
    assert canonical.canonical_event_key == f"btc_{expected_family}"


@pytest.mark.parametrize(
    "message_body",
    (
        "The short-term pullback coincides with futures positioning news.",
        "The short-term pullback coincides with an ETF update.",
        "The short-term pullback coincides with regulatory news.",
    ),
)
def test_core_price_identity_is_not_hijacked_by_supporting_context_in_message_body(message_body):
    canonical = canonicalize_event_key(
        "btc",
        "btc_price_down_180min",
        title="Bitcoin dips over 3-hour window",
        message_body=message_body,
        related_news=[{"title": "Material context", "material": True}],
    )

    assert canonical.semantic_family == "price_downtrend"
    assert canonical.canonical_event_key == "btc_price_downtrend"


def test_ambiguous_core_uses_selected_material_news_as_identity_fallback():
    canonical = canonicalize_event_key(
        "btc",
        "btc_market_event",
        title="Bitcoin market update",
        message_body="Current context requires attention.",
        related_news=[{"title": "ETF inflows rise", "material": True}],
    )

    assert canonical.semantic_family == "etf_flows"
    assert canonical.canonical_event_key == "btc_etf_flows"


def test_nonmaterial_related_news_cannot_supply_ambiguous_event_identity():
    canonical = canonicalize_event_key(
        "btc",
        "btc_market_event",
        title="Bitcoin market update",
        message_body="Current context requires attention.",
        related_news=[{"title": "ETF inflows rise", "material": False}],
    )

    assert canonical.semantic_family is None
    assert canonical.canonical_event_key == "btc_market_event"


@pytest.mark.asyncio
async def test_semantic_cooldown_suppresses_the_corrected_price_family(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime(2026, 9, 19, 12, tzinfo=timezone.utc)
    canonical = canonicalize_event_key(
        "btc",
        "btc_price_down_180min",
        title="Bitcoin dips over 3-hour window",
        message_body="Short-term pullback.",
        related_news=[{"title": "US stock perpetual futures", "material": False}],
    )
    previous_alert = SimpleNamespace(
        id=99,
        user_id=7,
        created_at=now - timedelta(minutes=30),
        numeric_context='{"semantic_family":"price_downtrend"}',
    )
    monkeypatch.setattr(alerts, "DB_ENABLED", True)
    monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_factory)
    monkeypatch.setattr(
        alerts,
        "get_recent_sent_event_alert_contexts",
        AsyncMock(return_value=[(previous_alert, "btc_price_downtrend", "price_downtrend")]),
    )

    result = await alerts._filter_event_recipients_for_cooldown(
        [alerts.AlertRecipient(chat_id=1, user_id=7)],
        symbol="btc",
        urgency="normal",
        cooldown_seconds=300,
        canonical_event_key=canonical.canonical_event_key,
        semantic_family=canonical.semantic_family,
        now=now,
        return_summary=True,
    )

    assert canonical.semantic_family == "price_downtrend"
    assert result.recipients == []
    assert result.suppression_reason_counts == {alerts.SUPPRESSION_SEMANTIC_COOLDOWN: 1}
    await engine.dispose()


@pytest.mark.asyncio
async def test_exact_context_reuse_recanonicalizes_and_rerenders_market_context(monkeypatch):
    news = {
        "news_id": "n1",
        "title": "US stock perpetual futures",
        "source": "Example News",
        "material": False,
    }
    input_payload = {
        "symbol": "BTC",
        "market": {
            "chg_window_percent": -0.53,
            "chg24h_percent": 0.19,
            "snapshots": [
                {"m": -180, "p": 100},
                {"m": -90, "p": 99},
                {"m": 0, "p": 98},
            ],
        },
        "news": [news],
    }
    analysis = SimpleNamespace(
        id=11,
        symbol="BTC",
        title="Bitcoin dips over 3-hour window",
        message_body="Market movement is meaningful.",
        possible_action="Review your risk plan.",
        urgency="normal",
        confidence="medium",
        related_news_ids='["n1"]',
        raw_input_json=json.dumps({**input_payload, "raw_event_key": "btc_price_down_180min"}),
        event_key="btc_derivatives_positioning",
    )
    market_event = SimpleNamespace(
        id=7,
        event_instance_key="btc:instance",
        event_key="btc_derivatives_positioning",
    )

    async def fake_candidates(*_args, **_kwargs):
        return [(market_event, analysis)]

    class FakeSession:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *_args):
            return None

    monkeypatch.setattr(alerts, "DB_ENABLED", True)
    monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", FakeSession)
    monkeypatch.setattr(alerts, "get_reusable_event_analysis_candidates", fake_candidates)

    reusable = await alerts._get_reusable_event_analysis_by_context(
        input_payload, candidate_news=[news]
    )

    assert reusable is not None
    assert reusable.current_context_decision.event_key == "btc_price_downtrend"
    assert reusable.semantic_family == "price_downtrend"
    assert "persisted across the supplied short-term snapshots" in reusable.alert_payload[
        "plain_text"
    ]
