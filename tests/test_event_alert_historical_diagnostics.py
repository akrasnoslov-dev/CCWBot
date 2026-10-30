"""Historical alert defect contracts: never call an external provider or Telegram.

Examples are reconstructed synthetic shapes inspired by documented incidents,
NOT historical raw production observations or independent usefulness labels.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot import alerts
from bot.alerting.event_analysis import (
    EventAnalysisDecision,
    canonicalize_event_key,
    validate_event_significance_output,
)
from bot.alerting.event_identity import _build_exact_event_context_fingerprint
from bot.db.database import Base
from bot.services.ai_agent_groq import build_event_significance_prompt


def _market(move, day=1):
    return {
        "price": Decimal("100"),
        "chg_window_percent": Decimal(str(move)),
        "chg24h_percent": Decimal(str(day)),
        "analysed_window_minutes": 180,
        "snapshots": [
            {"m": -180, "p": Decimal("98")},
            {"m": -90, "p": Decimal("99")},
            {"m": 0, "p": Decimal("100")},
        ],
    }


@pytest.mark.parametrize("symbol,move", [("BTC", "0.1602"), ("ETH", "0.028")])
def test_historical_weak_move_requires_model_judgment_not_news_or_daily_delta(
    symbol, move,
):
    context = {
        "symbol": symbol,
        "market": {
            **_market(move, day=7.8),
            "relative_window_percentile_30d": Decimal("32.9"),
        },
        "news": [{"news_id": "n1", "title": "Related asset headline",
                  "relevance_label": "asset_specific", "material": True}],
        "recent_event_counts": {"h6": 3, "h24": 6},
    }
    prompt = build_event_significance_prompt(context)
    assert move in prompt
    assert "Q1 materiality" in prompt
    assert "Q2 novelty" in prompt
    assert "default=>no alert" in prompt.lower()
    assert "recent counts never increase materiality" in prompt
    # This only tests evidence passed to the model, never assigns a human verdict.


def test_historical_sol_four_percent_movement_remains_eligible_for_llm_significance():
    payload = {"symbol": "SOL", "market": _market("4.03", day="3.5"),
               "recent_event_counts": {"h6": 0, "h24": 0}}
    assert "4.03" in build_event_significance_prompt(payload)
    accepted = validate_event_significance_output(
        {
            "symbol": "SOL", "materiality": "material", "novelty": "new",
            "should_alert": True, "reason_code": "unusual_move", "confidence": "high",
        },
        expected_symbol="SOL",
    )
    assert accepted.should_alert
    # Historical model false negative is not reproducible without its exact input/model.


@pytest.mark.parametrize(
    "symbol,primary,raw,expected",
    [
        ("BTC", "-0.053", "btc_down_0_0526873_in_the_last_3_hours", "price_downtrend"),
        ("ETH", "-2.3", "eth_down_2_3_in_the_last_3_hours", "price_downtrend"),
        ("GRAM", "1.6", "gram_up_1_6_in_the_last_3_hours", "price_uptrend"),
        ("SOL", "-0.4", "sol_price_uptrend", "price_downtrend"),
    ],
)
def test_historical_numeric_keys_cannot_fragment_directional_identity(
    symbol, primary, raw, expected,
):
    key = canonicalize_event_key(
        symbol, raw, analysed_window_change=Decimal(primary),
    )
    assert key.semantic_family == expected
    assert key.canonical_event_key == f"{symbol.lower()}_{expected}"


@pytest.mark.asyncio
@pytest.mark.parametrize("symbol", ["BTC", "ETH", "GRAM", "SOL"])
async def test_numeric_family_drift_never_bypasses_four_hour_cooldown(
    monkeypatch, symbol,
):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        now = datetime(2026, 10, 16, 12, tzinfo=timezone.utc)
        old = SimpleNamespace(
            id=1, user_id=12, created_at=now - timedelta(hours=3, minutes=59),
            numeric_context='{"analysed_window_change_percent":-0.8}',
        )
        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", factory)
        mocked = AsyncMock(return_value=[
            (old, f"{symbol.lower()}_down_0_8_in_the_last_3_hours", None),
        ])
        monkeypatch.setattr(alerts, "get_recent_sent_event_alert_contexts", mocked)
        recipient = alerts.AlertRecipient(chat_id=112, user_id=12)
        opts = dict(
            symbol=symbol, urgency="high", cooldown_seconds=60,
            canonical_event_key=f"{symbol.lower()}_down_1_4_in_the_last_3_hours",
            semantic_family=None, now=now, return_summary=True,
        )
        blocked = await alerts._filter_event_recipients_for_cooldown(
            [recipient], **opts,
        )
        assert blocked.recipients == []
        assert blocked.suppression_reason_counts == {
            alerts.SUPPRESSION_SEMANTIC_COOLDOWN: 1,
        }
        old.created_at = now - timedelta(hours=4)
        permitted = await alerts._filter_event_recipients_for_cooldown(
            [recipient], **opts,
        )
        assert permitted.recipients == [recipient]
    finally:
        await engine.dispose()


def test_exact_reuse_excludes_changed_micro_moves_and_news():
    base = {
        "symbol": "BTC",
        "market": _market("0.160200000"),
        "news": [{"news_id": "n1", "title": "Example story", "source": "Wire",
                  "time": "2026-10-16T05:00:00+00:00"}],
        "timestamp_utc": "2026-10-16T05:30:00+00:00",
        "previous_event_alert": {"semantic_family": "price_uptrend",
                                 "analysed_window_move": Decimal("1.0")},
    }
    minor_change = deepcopy(base)
    minor_change["market"]["chg_window_percent"] = Decimal("0.160200001")
    changed_news = deepcopy(base)
    changed_news["news"][0]["title"] = "Updated story"
    old_context = deepcopy(base)
    old_context["previous_event_alert"]["analysed_window_move"] = Decimal("1.2")
    fingerprint = _build_exact_event_context_fingerprint(base)
    assert fingerprint != _build_exact_event_context_fingerprint(minor_change)
    assert fingerprint != _build_exact_event_context_fingerprint(changed_news)
    assert fingerprint != _build_exact_event_context_fingerprint(old_context)


def test_grounded_render_survives_final_message_without_generic_substitution():
    situation = "The short-term rise contrasts with the broader 24-hour decline."
    action = "Watch whether the next observed interval extends the divergence or turns."
    decision = EventAnalysisDecision(
        symbol="ETH", should_alert=True, event_key="eth_price_uptrend",
        title="Untrusted title", message_body=situation, related_news_ids=[],
        urgency="normal", confidence="medium", possible_action=action,
        reason_for_no_alert=None,
    )
    result = alerts._build_event_alert_payload(
        decision=decision, input_payload={"market": _market("2", day="-1")},
        related_news=[],
    )
    final = result["plain_text"]
    assert f"Situation:\n{situation}\n\n" in final
    assert f"Possible action:\n{action}\n\n" in final
    assert final.count("Not financial advice.") == 1


def test_contradictory_period_alignment_is_never_delivered_as_factual_claim():
    situation = "The short-term move is aligned with the broader decline."
    market = _market("2", day="-1")
    normalized = alerts._event_alert_render_result_for_validation(
        {"message_body": situation, "related_news_ids": [],
         "possible_action": "Watch whether the next observed interval turns."},
        input_payload={"market": market}, expected_symbol="ETH",
        confidence="medium", candidate_news_ids=set(),
    )
    with pytest.raises(alerts.EventAnalysisValidationError):
        alerts._validate_event_alert_render_causality(
            {"message_body": situation}, market_data=market
        )
        alerts.validate_event_analysis_output(
            normalized, expected_symbol="ETH", candidate_news_ids=set(),
            market_data=market,
        )

