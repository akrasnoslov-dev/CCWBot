from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import bot.alerts as alerts
from bot.alerting.event_analysis import EventAnalysisDecision
from bot.db.database import Base, EventAiAnalysis, save_price_snapshot
from bot.domain.supported_coins import SUPPORTED_SYMBOLS


async def _session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


def _event_input() -> dict:
    return {
        "analysis_id": "event_analysis_gram_exact_context",
        "symbol": "GRAM",
        "timestamp_utc": "2026-09-17T12:00:00+00:00",
        "market": {
            "price": Decimal("1.3507"),
            "snapshots": [{"m": 30, "p": Decimal("1.3500")}],
            "payload_points": 6,
            "analysed_window_minutes": 30,
            "chg_window_percent": Decimal("0.051851851851851851"),
            "chg24h_percent": Decimal("-0.184"),
            "chg_since_msg_percent": None,
        },
        "last_msg": {"time": None, "type": None, "price": None},
        "news": [],
        "policy": {"language": "English"},
    }


@pytest.mark.asyncio
async def test_normal_event_analysis_persists_its_exact_context_fingerprint(monkeypatch):
    engine, session_factory = await _session_factory()
    try:
        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_factory)
        payload = _event_input()
        decision = EventAnalysisDecision(
            symbol="GRAM",
            should_alert=False,
            event_key=None,
            title=None,
            message_body=None,
            related_news_ids=[],
            possible_action=None,
            urgency=None,
            confidence=None,
            reason_for_no_alert="No material market event.",
        )

        await alerts._save_event_analysis_attempt(
            input_payload=payload,
            raw_output_json="{}",
            parsed_result={},
            decision=decision,
            status="no_alert",
        )

        async with session_factory() as session:
            stored = await session.scalar(select(EventAiAnalysis))
        assert stored.context_fingerprint == alerts._event_context_fingerprint(payload)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_event_analysis_input_keeps_subcent_decimal_precision(monkeypatch):
    engine, session_factory = await _session_factory()
    now = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)
    try:
        monkeypatch.setattr(alerts, "DB_ENABLED", True)
        monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_factory)
        async with session_factory() as session:
            await save_price_snapshot(
                session,
                symbol="gram",
                price=Decimal("1.3500"),
                change_24h=Decimal("-0.184"),
                checked_at=now - timedelta(minutes=30),
            )

        payload = await alerts._build_event_analysis_input(
            analysis_id="event_analysis_gram_precision",
            symbol="gram",
            current_price=Decimal("1.3507"),
            change_24h=Decimal("-0.184"),
            now=now,
            state={"last_price": Decimal("1.3500")},
            candidate_news=[],
            event_analysis_interval_seconds=300,
        )

        assert payload["market"]["price"] == Decimal("1.3507")
        # SQLite reflects NUMERIC through a floating driver; PostgreSQL NUMERIC is exercised
        # separately by the migration/query-contract verification.
        assert payload["market"]["snapshots"][0]["p"] == pytest.approx(Decimal("1.3500"))
        assert 0 < payload["market"]["chg_window_percent"] < 0.1
        assert payload["market"]["chg24h_percent"] == Decimal("-0.184")
        assert "chg_window" not in payload["market"]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_global_market_detection_covers_every_active_coin():
    assert await alerts.resolve_symbols_to_check() == list(SUPPORTED_SYMBOLS)


def test_event_alert_source_keeps_eligibility_after_analysis_and_strict_cooldown():
    source = (Path(alerts.__file__).read_text(encoding="utf-8"))
    filter_source = source[source.index("async def _filter_event_recipients_for_cooldown") :]

    assert "ask_event_analysis_raw" not in filter_source
    assert "semantic_allowed = elapsed >= semantic_cooldown_seconds" in filter_source
    assert "allowed_stronger_movement" not in source
    assert "allowed_urgency_escalation" not in source
    assert "_record_exact_context_reuse" in source


def test_event_analysis_percentage_contract_does_not_add_a_significance_gate():
    source = Path(alerts.__file__).read_text(encoding="utf-8")
    automatic_check = source[source.index("async def automatic_price_check") :]
    input_builder = source[
        source.index("async def _build_event_analysis_input") : source.index(
            "async def _build_market_heartbeat_input"
        )
    ]

    assert "evaluate_event_significance" not in automatic_check
    assert "threshold_percent" not in automatic_check
    assert "chg_window_percent" in input_builder


def test_news_only_guard_remains_a_non_numeric_backend_contract():
    source = Path(alerts.__file__).read_text(encoding="utf-8")
    guard_start = source.index("def _is_news_only_event_alert_decision")
    guard = source[guard_start : guard_start + 3000]

    assert "news_only" in guard
    assert "threshold" not in guard.lower()


def _no_alert_result(reason_for_no_alert: str) -> dict:
    return {
        "symbol": "BTC",
        "should_alert": False,
        "event_key": None,
        "title": None,
        "message_body": None,
        "related_news_ids": [],
        "possible_action": None,
        "urgency": None,
        "confidence": None,
        "reason_for_no_alert": reason_for_no_alert,
    }


def _runtime_no_alert_payload(*, chg_window_percent: float) -> dict:
    payload = _event_input()
    payload.update(
        {
            "analysis_id": "event_analysis_btc_no_alert_observability",
            "symbol": "BTC",
            "news": [
                {
                    "news_id": "unrelated-news",
                    "title": "Unrelated market headline",
                    "source": "Example News",
                }
            ],
            "market": {
                "price": 100.0,
                "snapshots": [
                    {"m": 180, "p": 100.0},
                    {"m": 0, "p": 100.0 + chg_window_percent},
                ],
                "payload_points": 6,
                "analysed_window_minutes": 180,
                "chg_window_percent": chg_window_percent,
                "chg24h_percent": 5.45,
                "chg_since_msg_percent": None,
            },
        }
    )
    return payload


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "reason_for_no_alert",
    (
        (
            "Market price change in the recent 180-minute window is minimal and news items "
            "are unrelated."
        ),
        (
            "Market snapshot shows a 5.45% 24h increase but no short-term change window; "
            "news items are unrelated."
        ),
        "No significant market movement is evident and no material news is present.",
    ),
)
async def test_runtime_market_no_alert_explanations_record_llm_no_alert(
    monkeypatch, reason_for_no_alert
):
    recorded_outcome = AsyncMock()
    monkeypatch.setattr(
        alerts,
        "ask_event_analysis_raw",
        AsyncMock(return_value=("{}", _no_alert_result(reason_for_no_alert))),
    )
    monkeypatch.setattr(alerts, "_save_event_analysis_attempt", AsyncMock(return_value=321))
    monkeypatch.setattr(alerts, "_record_alert_delivery_outcome", recorded_outcome)
    monkeypatch.setattr(alerts, "_get_previous_event_alert_id", AsyncMock(return_value=None))

    decision, analysis_id = await alerts._create_event_analysis_decision(
        _runtime_no_alert_payload(chg_window_percent=0.05)
    )

    assert decision is not None
    assert analysis_id == 321
    assert (
        recorded_outcome.await_args.kwargs["decision_reason"]
        == alerts.DECISION_REASON_LLM_NO_ALERT
    )
    assert recorded_outcome.await_args.kwargs["reason_code"] == alerts.REASON_LLM_NO_ALERT


@pytest.mark.parametrize(
    ("reason_for_no_alert", "chg_window_percent", "expected_reason"),
    (
        (
            "News alone is the only notable input; the analysed market window is flat.",
            0.0,
            alerts.DECISION_REASON_NEWS_ONLY_REJECTED,
        ),
        (
            "News alone is the only notable input, but the analysed market window moved.",
            0.05,
            alerts.DECISION_REASON_LLM_NO_ALERT,
        ),
        (
            "Repeated news is unrelated while market movement is minimal.",
            0.0,
            alerts.DECISION_REASON_LLM_NO_ALERT,
        ),
    ),
)
def test_news_only_no_alert_requires_explicit_sole_news_language_and_flat_market_context(
    reason_for_no_alert, chg_window_percent, expected_reason
):
    decision = EventAnalysisDecision(
        symbol="BTC",
        should_alert=False,
        event_key=None,
        title=None,
        message_body=None,
        related_news_ids=[],
        possible_action=None,
        urgency=None,
        confidence=None,
        reason_for_no_alert=reason_for_no_alert,
    )

    assert (
        alerts._llm_no_alert_decision_reason(
            decision, _runtime_no_alert_payload(chg_window_percent=chg_window_percent)
        )
        == expected_reason
    )


def test_news_only_no_alert_does_not_treat_decimal_market_context_as_flat():
    payload = _runtime_no_alert_payload(chg_window_percent=0.0)
    payload["market"].update(
        {
            "chg_window_percent": None,
            "chg_since_msg_percent": Decimal("0.05"),
            "snapshots": [
                {"m": 180, "p": Decimal("100.00")},
                {"m": 0, "p": Decimal("100.05")},
            ],
        }
    )
    decision = EventAnalysisDecision(
        symbol="BTC",
        should_alert=False,
        event_key=None,
        title=None,
        message_body=None,
        related_news_ids=[],
        possible_action=None,
        urgency=None,
        confidence=None,
        reason_for_no_alert="News alone is the only notable input.",
    )

    assert alerts._has_non_flat_analysed_market_context(payload)
    assert (
        alerts._llm_no_alert_decision_reason(decision, payload)
        == alerts.DECISION_REASON_LLM_NO_ALERT
    )
