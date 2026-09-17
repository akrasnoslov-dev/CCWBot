from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

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
            "chg_window": Decimal("0.051851851851851851"),
            "chg24h": Decimal("-0.184"),
            "chg_since_msg": None,
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
        assert 0 < payload["market"]["chg_window"] < 0.1
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


def test_news_only_guard_remains_a_non_numeric_backend_contract():
    source = Path(alerts.__file__).read_text(encoding="utf-8")
    guard_start = source.index("def _is_news_only_event_alert_decision")
    guard = source[guard_start : guard_start + 3000]

    assert "news_only" in guard
    assert "threshold" not in guard.lower()
