import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
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


def test_event_alert_presentation_removes_repeated_llm_market_facts():
    decision = EventAnalysisDecision(
        symbol="SOL",
        should_alert=True,
        event_key="sol_momentum",
        title="Solana price jumps ~4% in last 3 hours, up ~8.5% in 24 h",
        message_body=(
            "SOL rose from $105.49 to $109.79 in the last 3 hours (≈4.1% increase) "
            "and is up about 8.5% over the past 24 hours, indicating strong short-term momentum."
        ),
        related_news_ids=[],
        possible_action="Buy now because SOL has strong momentum and sell if the trend changes.",
        urgency="normal",
        confidence="high",
        reason_for_no_alert=None,
    )
    payload = alerts._build_event_alert_payload(
        decision=decision,
        input_payload={
            "timestamp_utc": "2026-09-18T12:00:00+00:00",
            "last_msg": {
                "time": "2026-09-18T08:00:00+00:00",
                "price": Decimal("104.03"),
                "type": "event_alert",
            },
            "market": {
                "price": Decimal("109.79"),
                "analysed_window_minutes": 180,
                "chg_window_percent": Decimal("4.07"),
                "chg24h_percent": Decimal("8.5"),
                "chg_since_msg_percent": Decimal("5.54"),
            },
        },
        related_news=[],
    )["plain_text"]

    assert "SOL up ~4.1% in the last 3 hours" in payload
    assert "24 h" not in payload
    assert "Price: $109.79" in payload
    assert "Since last alert/message (4h ago): +5.54%" in payload
    assert "3h market move: +4.07%" in payload
    assert "broader 24-hour trend" in payload
    assert "$105.49" not in payload
    assert "8.5%" not in payload
    assert "Buy now" not in payload
    assert "Watch the next short-term snapshots" in payload


def test_event_alert_since_last_metric_requires_prior_price_and_time_context():
    decision = EventAnalysisDecision(
        symbol="SOL",
        should_alert=True,
        event_key="sol_momentum",
        title="ignored",
        message_body="Market movement is meaningful.",
        related_news_ids=[],
        possible_action="Watch for confirmation if it fits your risk plan.",
        urgency="normal",
        confidence="high",
        reason_for_no_alert=None,
    )
    common_market = {
        "price": Decimal("109.79"),
        "analysed_window_minutes": 180,
        "chg_window_percent": Decimal("4.07"),
        "chg_since_msg_percent": Decimal("5.54"),
    }
    with_context = alerts._build_event_alert_payload(
        decision=decision,
        input_payload={
            "timestamp_utc": "2026-09-18T12:00:00+00:00",
            "last_msg": {"time": "2026-09-18T08:00:00+00:00", "price": Decimal("104.03")},
            "market": common_market,
        },
        related_news=[],
    )["plain_text"]
    without_context = alerts._build_event_alert_payload(
        decision=decision,
        input_payload={
            "timestamp_utc": "2026-09-18T12:00:00+00:00",
            "last_msg": {"time": None, "price": None},
            "market": common_market,
        },
        related_news=[],
    )["plain_text"]

    assert "Since last alert/message (4h ago): +5.54%" in with_context
    assert "Since last alert/message" not in without_context


@pytest.mark.parametrize(
    ("market", "related_news", "expected_situation", "expected_action"),
    (
        (
            {"chg_window_percent": Decimal("4.07"), "chg24h_percent": Decimal("8.5")},
            [],
            "broader 24-hour trend",
            "broader-trend direction",
        ),
        (
            {"chg_window_percent": Decimal("-1.2"), "chg24h_percent": Decimal("2.0")},
            [],
            "short-term divergence",
            "continue diverging",
        ),
        (
            {
                "snapshots": [
                    {"m": -180, "p": Decimal("100")},
                    {"m": -90, "p": Decimal("102")},
                    {"m": 0, "p": Decimal("103")},
                ]
            },
            [],
            "developed across the supplied snapshots",
            "next few short-term snapshots",
        ),
        (
            {
                "snapshots": [
                    {"m": -180, "p": Decimal("100")},
                    {"m": -90, "p": Decimal("103")},
                    {"m": 0, "p": Decimal("101")},
                ]
            },
            [],
            "reverses part of the earlier path",
            "further reversal",
        ),
        (
            {"chg_window_percent": Decimal("0.042")},
            [],
            "only confirmed signal",
            "continuation or a quick reversal",
        ),
        (
            {"chg_window_percent": Decimal("4.07")},
            [{"news_id": "n1", "title": "Selected context"}],
            "may provide context, but it does not establish causation",
            "selected news develops",
        ),
    ),
)
def test_event_alert_presentation_fallbacks_are_concise_and_evidence_derived(
    market, related_news, expected_situation, expected_action
):
    situation, action = alerts.event_alert_presentation_fallback(market, related_news)

    assert expected_situation in situation
    assert expected_action in action
    assert "%" not in situation
    assert "buy" not in action.lower()
    assert "sell" not in action.lower()


def test_event_alert_replaces_generic_or_repeated_llm_copy_with_evidence_fallback():
    decision = EventAnalysisDecision(
        symbol="SOL",
        should_alert=True,
        event_key="sol_market_move",
        title="SOL up 4.07% and 8.5% in 24h",
        message_body="SOL is $109.79, up 4.07% in three hours and 8.5% over 24 hours.",
        related_news_ids=[],
        possible_action="Review your risk plan and wait for confirmation.",
        urgency="normal",
        confidence="high",
        reason_for_no_alert=None,
    )
    payload = alerts._build_event_alert_payload(
        decision=decision,
        input_payload={
            "market": {
                "price": Decimal("109.79"),
                "analysed_window_minutes": 180,
                "chg_window_percent": Decimal("4.07"),
                "chg24h_percent": Decimal("8.5"),
            }
        },
        related_news=[],
    )["plain_text"]

    situation = payload.split("Situation:\n", 1)[1].split("\n\nPossible action:", 1)[0]
    action = payload.split("Possible action:\n", 1)[1].split("\n\nNot financial advice.", 1)[0]
    assert "$109.79" not in situation
    assert "4.07%" not in situation
    assert "8.5%" not in situation
    assert "broader 24-hour trend" in situation
    assert "next short-term snapshots" in action
    assert "risk plan" not in action.lower()


def test_event_alert_presentation_replaces_financial_instruction_with_evidence_fallback():
    decision = EventAnalysisDecision(
        symbol="SOL",
        should_alert=True,
        event_key="sol_market_move",
        title="ignored",
        message_body="You should buy now.",
        related_news_ids=[],
        possible_action="Buy now.",
        urgency="normal",
        confidence="high",
        reason_for_no_alert=None,
    )
    payload = alerts._build_event_alert_payload(
        decision=decision,
        input_payload={"market": {"chg_window_percent": Decimal("4.07")}},
        related_news=[],
    )["plain_text"]

    situation = payload.split("Situation:\n", 1)[1].split("\n\nPossible action:", 1)[0]
    action = payload.split("Possible action:\n", 1)[1].split("\n\nNot financial advice.", 1)[0]
    assert "only confirmed signal" in situation
    assert "risk plan" not in situation.lower()
    assert "buy" not in situation.lower()
    assert "next short-term snapshots" in action


def test_event_alert_presentation_ignores_nonfinite_market_values():
    situation, action = alerts.event_alert_presentation_fallback(
        {"chg_window_percent": "NaN", "chg24h_percent": "Infinity"}, []
    )

    assert "only confirmed signal" in situation
    assert "next short-term snapshots" in action


def test_event_alert_presentation_replaces_unsupported_nonnumeric_market_claim():
    situation = alerts.compact_event_alert_situation(
        "Trading volume is rising, which confirms participation.",
        significance_reason=None,
        market_data={"chg_window_percent": Decimal("1")},
        related_news=[],
    )

    assert "only confirmed signal" in situation
    assert "volume" not in situation.lower()


@pytest.mark.parametrize(
    "claim",
    (
        "Institutional demand is strengthening.",
        "Investor confidence is improving.",
    ),
)
def test_event_alert_presentation_replaces_unstructured_llm_claims(claim):
    situation = alerts.compact_event_alert_situation(
        claim,
        significance_reason=None,
        market_data={"chg_window_percent": Decimal("1")},
        related_news=[],
    )

    assert "only confirmed signal" in situation
    assert claim not in situation


def test_event_alert_presentation_keeps_safe_selected_news_context():
    situation = alerts.compact_event_alert_situation(
        "Selected current news coincides with the move and may provide context.",
        significance_reason=None,
        market_data={"chg_window_percent": Decimal("1")},
        related_news=[{"news_id": "n1", "title": "Selected context"}],
    )

    assert situation == "Selected current news coincides with the move and may provide context."


@pytest.mark.parametrize(
    ("change", "expected_direction"),
    ((Decimal("0.042"), "up"), (Decimal("-0.042"), "down")),
)
def test_event_alert_title_preserves_subpercent_percentage_values(change, expected_direction):
    assert (
        alerts._event_alert_presentation_title(
            symbol="SOL",
            analysed_window_minutes=180,
            analysed_window_change=change,
        )
        == f"SOL {expected_direction} ~0.042% in the last 3 hours"
    )


def test_event_alert_situation_replaces_unsupported_causal_context_without_market_repetition():
    decision = EventAnalysisDecision(
        symbol="SOL",
        should_alert=True,
        event_key="sol_protocol_context",
        title="ignored",
        message_body=(
            "SOL gained 4.1 percent after a protocol upgrade increased network capacity."
        ),
        related_news_ids=[],
        possible_action="Watch for confirmation if it fits your risk plan.",
        urgency="normal",
        confidence="high",
        reason_for_no_alert=None,
    )
    payload = alerts._build_event_alert_payload(
        decision=decision,
        input_payload={
            "market": {
                "price": Decimal("109.79"),
                "analysed_window_minutes": 180,
                "chg_window_percent": Decimal("4.07"),
                "chg24h_percent": Decimal("8.5"),
            }
        },
        related_news=[],
    )["plain_text"]

    assert "broader 24-hour trend" in payload
    assert "protocol upgrade" not in payload
    assert "4.1 percent" not in payload


def test_event_alert_situation_rejects_usd_and_percent_market_restatement():
    decision = EventAnalysisDecision(
        symbol="SOL",
        should_alert=True,
        event_key="sol_momentum",
        title="ignored",
        message_body=(
            "SOL rose from 105.49 USD to 109.79 USD after market news, a 4.1 percent "
            "move with 8.5 percent over 24 hours."
        ),
        related_news_ids=[],
        possible_action="Watch for confirmation if it fits your risk plan.",
        urgency="normal",
        confidence="high",
        reason_for_no_alert=None,
    )
    payload = alerts._build_event_alert_payload(
        decision=decision,
        input_payload={
            "market": {
                "price": Decimal("109.79"),
                "snapshots": [{"p": Decimal("105.49")}],
                "analysed_window_minutes": 180,
                "chg_window_percent": Decimal("4.07"),
                "chg24h_percent": Decimal("8.5"),
            }
        },
        related_news=[],
    )["plain_text"]

    assert "broader 24-hour trend" in payload
    assert "105.49 USD" not in payload
    assert "4.1 percent" not in payload


def test_event_alert_situation_rejects_percentage_point_market_restatement():
    decision = EventAnalysisDecision(
        symbol="SOL",
        should_alert=True,
        event_key="sol_momentum",
        title="ignored",
        message_body=(
            "SOL rose 4.07 percentage points in 3 hours and is up 8.5 percentage points "
            "over 24 hours."
        ),
        related_news_ids=[],
        possible_action="Watch for confirmation if it fits your risk plan.",
        urgency="normal",
        confidence="high",
        reason_for_no_alert=None,
    )
    payload = alerts._build_event_alert_payload(
        decision=decision,
        input_payload={
            "market": {
                "price": Decimal("109.79"),
                "analysed_window_minutes": 180,
                "chg_window_percent": Decimal("4.07"),
                "chg24h_percent": Decimal("8.5"),
            }
        },
        related_news=[],
    )["plain_text"]

    assert "broader 24-hour trend" in payload
    assert "4.07 percentage points" not in payload


def test_event_alert_situation_replaces_unsupported_causal_context_for_subpercent_move():
    decision = EventAnalysisDecision(
        symbol="SOL",
        should_alert=True,
        event_key="sol_momentum",
        title="ignored",
        message_body="SOL rose 0.1% after ETF news.",
        related_news_ids=[],
        possible_action="Watch for confirmation if it fits your risk plan.",
        urgency="normal",
        confidence="high",
        reason_for_no_alert=None,
    )
    payload = alerts._build_event_alert_payload(
        decision=decision,
        input_payload={
            "market": {
                "price": Decimal("109.79"),
                "analysed_window_minutes": 180,
                "chg_window_percent": Decimal("0.042"),
            }
        },
        related_news=[],
    )["plain_text"]

    assert "only confirmed signal" in payload
    assert "ETF news" not in payload
    assert "0.1%" not in payload


def test_event_alert_situation_replaces_unsupported_market_metric_context():
    decision = EventAnalysisDecision(
        symbol="SOL",
        should_alert=True,
        event_key="sol_momentum",
        title="ignored",
        message_body="ETF news and a 12% funding-rate change explain the market reaction.",
        related_news_ids=[],
        possible_action="Watch for confirmation if it fits your risk plan.",
        urgency="normal",
        confidence="high",
        reason_for_no_alert=None,
    )
    payload = alerts._build_event_alert_payload(
        decision=decision,
        input_payload={
            "market": {
                "price": Decimal("109.79"),
                "analysed_window_minutes": 180,
                "chg_window_percent": Decimal("4.07"),
                "chg24h_percent": Decimal("8.5"),
            }
        },
        related_news=[],
    )["plain_text"]

    assert "broader 24-hour trend" in payload
    assert "funding-rate" not in payload


def test_event_alert_situation_rejects_invented_market_movement_percentage():
    decision = EventAnalysisDecision(
        symbol="SOL",
        should_alert=True,
        event_key="sol_momentum",
        title="ignored",
        message_body="SOL rose 100% after ETF news.",
        related_news_ids=[],
        possible_action="Watch for confirmation if it fits your risk plan.",
        urgency="normal",
        confidence="high",
        reason_for_no_alert=None,
    )
    payload = alerts._build_event_alert_payload(
        decision=decision,
        input_payload={
            "market": {
                "price": Decimal("109.79"),
                "analysed_window_minutes": 180,
                "chg_window_percent": Decimal("4.07"),
                "chg24h_percent": Decimal("8.5"),
            }
        },
        related_news=[],
    )["plain_text"]

    assert "100%" not in payload
    assert "broader 24-hour trend" in payload


@pytest.mark.parametrize(
    "message_body",
    (
        "SOL rose 100% after ETF news and a 12% funding-rate change added context.",
        "SOL rose 100%. Funding rate was 12%.",
    ),
)
def test_event_alert_situation_rejects_invented_move_mixed_with_causal_metric(message_body):
    decision = EventAnalysisDecision(
        symbol="SOL",
        should_alert=True,
        event_key="sol_momentum",
        title="ignored",
        message_body=message_body,
        related_news_ids=[],
        possible_action="Watch for confirmation if it fits your risk plan.",
        urgency="normal",
        confidence="high",
        reason_for_no_alert=None,
    )
    payload = alerts._build_event_alert_payload(
        decision=decision,
        input_payload={
            "market": {
                "price": Decimal("109.79"),
                "analysed_window_minutes": 180,
                "chg_window_percent": Decimal("4.07"),
                "chg24h_percent": Decimal("8.5"),
            }
        },
        related_news=[],
    )["plain_text"]

    assert "100%" not in payload


def test_existing_market_event_keeps_current_compact_alert_rendering():
    current_payload = {
        "plain_text": "SOL up ~4.1% in the last 3 hours",
        "html_text": None,
        "entities": None,
    }
    existing_analysis = SimpleNamespace(
        plain_text="legacy verbose Event Alert payload",
        html_text="<b>legacy verbose Event Alert payload</b>",
    )

    assert (
        alerts._merge_existing_event_analysis_payload(current_payload, existing_analysis)
        == current_payload
    )


@pytest.mark.asyncio
async def test_exact_context_reuse_rerenders_legacy_verbose_alert_payload(monkeypatch):
    input_payload = {
        "symbol": "SOL",
        "timestamp_utc": "2026-09-18T12:00:00+00:00",
        "market": {
            "price": 109.79,
            "analysed_window_minutes": 180,
            "chg_window_percent": 4.07,
            "chg24h_percent": 8.5,
        },
        "news": [],
    }
    analysis = SimpleNamespace(
        id=11,
        symbol="SOL",
        title="SOL price jumps ~4% in last 3 hours, up ~8.5% in 24 h",
        message_body=(
            "SOL rose from $105.49 to $109.79 in the last 3 hours (≈4.1% increase) "
            "and is up about 8.5% over the past 24 hours."
        ),
        possible_action="Buy now because momentum is strong.",
        urgency="normal",
        confidence="high",
        related_news_ids="[]",
        raw_input_json=json.dumps(input_payload),
        plain_text="legacy verbose Event Alert payload",
        event_key="sol_momentum",
    )
    market_event = SimpleNamespace(
        id=7,
        event_instance_key="sol:instance",
        event_key="sol_momentum",
    )

    @asynccontextmanager
    async def fake_session():
        yield object()

    async def fake_candidates(*_args, **_kwargs):
        return [(market_event, analysis)]

    monkeypatch.setattr(alerts, "DB_ENABLED", True)
    monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", lambda: fake_session())
    monkeypatch.setattr(alerts, "get_reusable_event_analysis_candidates", fake_candidates)

    reusable = await alerts._get_reusable_event_analysis_by_context(input_payload)

    assert reusable is not None
    rendered = reusable.alert_payload["plain_text"]
    assert "SOL up ~4.1% in the last 3 hours" in rendered
    assert "legacy verbose Event Alert payload" not in rendered
    assert "$105.49" not in rendered
