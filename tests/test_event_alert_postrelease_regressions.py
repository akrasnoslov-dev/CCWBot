"""Production-pattern regression fixtures; synthetic inputs, never recipient data."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot import alerts
from bot.alerting.event_analysis import canonicalize_event_key
from bot.alerting.event_text import compact_event_alert_possible_action
from bot.db.database import Base
from bot.services.ai_agent_groq import build_event_significance_prompt


@pytest.mark.parametrize(
    "symbol,move,raw,expected",
    [
        ("BTC", "-0.29", "btc_price_uptrend", "price_downtrend"),
        ("ETH", "-0.42", "eth_price_uptrend", "price_downtrend"),
        ("SOL", "-0.53", "sol_price_rebound", "price_downtrend"),
        ("GRAM", "0.38", "gram_price_downtrend", "price_uptrend"),
    ],
)
def test_current_market_move_anchors_directional_identity(symbol, move, raw, expected):
    result = canonicalize_event_key(
        symbol,
        raw,
        title="Broader 24h uptrend remains",
        message_body="Market pullback",
        analysed_window_change=move,
    )
    assert result.semantic_family == expected
    assert result.canonical_event_key == f"{symbol.lower()}_{expected}"


def test_absent_current_move_does_not_invent_price_direction():
    result = canonicalize_event_key("BTC", "btc_price_uptrend", analysed_window_change=None)
    assert result.canonical_event_key == "btc_price_uptrend"


def test_identical_generic_possible_action_is_replaced_by_grounded_fallback():
    fallback = "Watch the next observed snapshot to see whether the decline continues or reverses."
    assert (
        compact_event_alert_possible_action(
            "If the market moves, keep watching.", fallback=fallback
        )
        == fallback
    )


def test_significance_prompt_calibrates_materiality_before_novelty_without_a_threshold():
    prompt = build_event_significance_prompt(
        {
            "symbol": "BTC",
            "market": {
                "analysed_window_minutes": 180,
                "chg_window_percent": -0.29,
                "relative_window_percentile_30d": 55,
                "snapshots": [{"m": -180, "p": 100}, {"m": 0, "p": 99.71}],
            },
            "recent_event_counts": {"h6": 2, "h24": 4},
        }
    ).lower()
    assert "ordinary for the asset" in prompt
    assert "trajectory" in prompt
    assert "novel" in prompt
    assert "no fixed numeric cutoff" in prompt


@pytest.mark.asyncio
async def test_mislabeled_legacy_direction_does_not_bypass_four_hour_cooldown(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime(2026, 10, 12, 14, tzinfo=timezone.utc)
    previous = SimpleNamespace(
        id=55,
        user_id=7,
        created_at=now - timedelta(hours=3, minutes=59),
        numeric_context='{"semantic_family":"price_uptrend","analysed_window_change_percent":-0.29}',
    )
    monkeypatch.setattr(alerts, "DB_ENABLED", True)
    monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_factory)
    monkeypatch.setattr(
        alerts,
        "get_recent_sent_event_alert_contexts",
        AsyncMock(return_value=[(previous, "btc_price_uptrend", "price_uptrend")]),
    )
    params = dict(
        symbol="BTC",
        urgency="normal",
        cooldown_seconds=60,
        canonical_event_key="btc_price_downtrend",
        semantic_family="price_downtrend",
        now=now,
        return_summary=True,
    )
    recipient = alerts.AlertRecipient(chat_id=10, user_id=7)
    blocked = await alerts._filter_event_recipients_for_cooldown([recipient], **params)
    assert not blocked.recipients
    assert blocked.suppression_reason_counts == {alerts.SUPPRESSION_SEMANTIC_COOLDOWN: 1}
    # Older deliveries may only have a canonical key, not a stored family.
    previous.numeric_context = '{"analysed_window_change_percent":-0.29}'
    alerts.get_recent_sent_event_alert_contexts.return_value = [
        (previous, "btc_price_uptrend", None)
    ]
    assert not (
        await alerts._filter_event_recipients_for_cooldown([recipient], **params)
    ).recipients
    previous.created_at = now - timedelta(hours=4)
    allowed = await alerts._filter_event_recipients_for_cooldown([recipient], **params)
    assert allowed.recipients == [recipient]
    await engine.dispose()


@pytest.mark.parametrize(
    "symbol,move,percentile",
    [
        ("BTC", -0.29, 55),
        ("GRAM", -0.28, 21),
    ],
)
def test_documented_weak_move_cases_are_context_not_automatic_triggers(symbol, move, percentile):
    prompt = build_event_significance_prompt(
        {
            "symbol": symbol,
            "market": {
                "analysed_window_minutes": 180,
                "chg_window_percent": move,
                "relative_window_percentile_30d": percentile,
                "snapshots": [{"m": -180, "p": 100}, {"m": 0, "p": 100 * (1 + move / 100)}],
            },
            "recent_event_counts": {"h6": 2, "h24": 3},
        }
    )
    assert '"pw":' + str(percentile) in prompt
    assert "Default=>no alert" in prompt
    assert "No fixed numeric cutoff" in prompt


def test_btc_followup_copy_uses_verified_comparable_prior_window():
    from bot.alerting.event_analysis import EventAnalysisDecision

    def render(move, prior=None):
        return alerts._build_event_alert_payload(
            decision=EventAnalysisDecision(
                symbol="BTC",
                should_alert=True,
                event_key="btc_price_downtrend",
                title="Market event",
                message_body="Market movement needs attention.",
                related_news_ids=[],
                possible_action="If the market moves, keep watching.",
                urgency="normal",
                confidence="medium",
                reason_for_no_alert=None,
            ),
            input_payload={
                "market": {
                    "price": 100 * (1 + move / 100),
                    "analysed_window_minutes": 180,
                    "chg_window_percent": move,
                    "chg24h_percent": -1.5,
                    "snapshots": [{"m": 0, "p": 100 * (1 + move / 100)}],
                },
                "previous_event_alert": prior,
            },
            related_news=[],
        )["plain_text"]

    first = render(-0.29)
    second = render(
        -0.68,
        {
            "analysed_window_minutes": 180,
            "analysed_window_move": -0.29,
            "age_minutes": 240,
        },
    )
    assert "3h market move: -0.29%" in first
    assert "3h market move: -0.68%" in second
    # The accepted Stage-2 text is preserved, including when previous
    # market metrics differ. The model, not a Python template, owns comparison.
    assert "Situation:\nMarket movement needs attention." in first
    assert "Situation:\nMarket movement needs attention." in second
    assert "Possible action:\nIf the market moves, keep watching." in second
    assert second.endswith("Not financial advice.")


def test_unrelated_or_stale_previous_window_cannot_claim_comparability():
    from bot.alerting.event_text import event_alert_presentation_fallback

    market = {"analysed_window_minutes": 180, "chg_window_percent": -0.68, "chg24h_percent": -2}
    for prior in (
        {"analysed_window_minutes": 60, "analysed_window_move": -0.29, "age_minutes": 240},
        {"analysed_window_minutes": 180, "analysed_window_move": -0.29, "age_minutes": 1500},
    ):
        situation, _ = event_alert_presentation_fallback(market, [], previous_event_alert=prior)
        assert "previous alert" not in situation.lower()


def test_valid_but_repeated_model_situation_uses_comparable_prior_market_evidence():
    from bot.alerting.event_text import compact_event_alert_situation

    market = {
        "analysed_window_minutes": 180,
        "chg_window_percent": -0.68,
        "chg24h_percent": -1.5,
    }
    model_text = "The short-term move aligns with the broader 24-hour trend."
    without_previous = compact_event_alert_situation(
        model_text, significance_reason=None, market_data=market
    )
    with_previous = compact_event_alert_situation(
        model_text,
        significance_reason=None,
        market_data=market,
        previous_event_alert={
            "analysed_window_minutes": 180,
            "analysed_window_move": -0.29,
            "age_minutes": 240,
        },
    )
    assert without_previous == model_text
    assert with_previous != model_text
    assert "larger than the prior recorded alert's comparable window" in with_previous
    assert "24-hour trend" not in with_previous


@pytest.mark.parametrize(
    ("raw_key", "move", "family"),
    [
        ("btc_down_0_0240032_in_the_last_3_hours", -0.024, "price_downtrend"),
        ("btc_down_0_0526873_in_the_last_3_hours", -0.053, "price_downtrend"),
        ("gram_down_0_0909821_in_the_last_3_hours", -0.091, "price_downtrend"),
        ("btc_up_0_649_in_the_last_3_hours", 0.649, "price_uptrend"),
    ],
)
def test_production_style_numeric_directional_keys_collapse_to_semantic_family(
    raw_key, move, family
):
    canonical = canonicalize_event_key(
        raw_key.split("_")[0], raw_key, analysed_window_change=move
    )
    assert canonical.semantic_family == family
    assert canonical.canonical_event_key == f"{raw_key.split('_')[0]}_{family}"


@pytest.mark.asyncio
async def test_legacy_numeric_price_key_cannot_bypass_four_hour_semantic_cooldown(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime(2026, 10, 12, 20, tzinfo=timezone.utc)
    prior = SimpleNamespace(
        id=10, user_id=7, created_at=now - timedelta(minutes=30),
        numeric_context='{"analysed_window_change_percent":-0.024}',
    )
    monkeypatch.setattr(alerts, "DB_ENABLED", True)
    monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_factory)
    monkeypatch.setattr(alerts, "get_recent_sent_event_alert_contexts", AsyncMock(
        return_value=[(
            prior, "btc_down_0_0240032_in_the_last_3_hours", None
        )]
    ))
    recipient = alerts.AlertRecipient(chat_id=10, user_id=7)
    result = await alerts._filter_event_recipients_for_cooldown(
        [recipient], symbol="BTC", urgency="normal", cooldown_seconds=60,
        canonical_event_key="btc_price_downtrend", semantic_family="price_downtrend",
        now=now, return_summary=True,
    )
    assert result.recipients == []
    assert result.suppression_reason_counts == {alerts.SUPPRESSION_SEMANTIC_COOLDOWN: 1}
    await engine.dispose()


@pytest.mark.parametrize(
    ("symbol", "prior_key", "current_key", "previous_move"),
    [
        ("ETH", "eth_down_1_0_in_the_last_3_hours", "eth_down_2_3_in_the_last_3_hours", -1.015),
        ("GRAM", "gram_down_1_4_in_the_last_3_hours", "gram_down_2_4_in_the_last_3_hours", -1.412),
        ("SOL", "sol_down_0_6_in_the_last_3_hours", "sol_down_2_4_in_the_last_3_hours", -0.589),
    ],
)
@pytest.mark.asyncio
async def test_missing_current_and_prior_price_family_cannot_bypass_cooldown(
    monkeypatch, symbol, prior_key, current_key, previous_move
):
    """The production 2026-10-12/13 numeric-key path omitted both stored families."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime(2026, 10, 13, 0, 10, tzinfo=timezone.utc)
    prior = SimpleNamespace(
        id=37,
        user_id=7,
        created_at=now - timedelta(minutes=90),
        numeric_context='{"analysed_window_change_percent":' + str(previous_move) + "}",
    )
    monkeypatch.setattr(alerts, "DB_ENABLED", True)
    monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_factory)
    monkeypatch.setattr(
        alerts,
        "get_recent_sent_event_alert_contexts",
        AsyncMock(return_value=[(prior, prior_key, None)]),
    )
    recipient = alerts.AlertRecipient(chat_id=10, user_id=7)
    kwargs = dict(
        symbol=symbol, urgency="normal", cooldown_seconds=60,
        canonical_event_key=current_key, semantic_family=None,
        now=now, return_summary=True,
    )
    blocked = await alerts._filter_event_recipients_for_cooldown([recipient], **kwargs)
    assert blocked.recipients == []
    assert blocked.suppression_reason_counts == {alerts.SUPPRESSION_SEMANTIC_COOLDOWN: 1}
    prior.created_at = now - timedelta(hours=4)
    allowed = await alerts._filter_event_recipients_for_cooldown([recipient], **kwargs)
    assert allowed.recipients == [recipient]
    await engine.dispose()
