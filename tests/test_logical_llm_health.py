"""Rolling logical outcomes stay distinct from provider attempts."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.db.database import (
    Base,
    EventAiAnalysis,
    LlmOperationOutcome,
    LlmUsageLog,
    MarketHeartbeat,
    MarketReport,
)
from bot.observability.logical_llm_health import read_logical_llm_health
from bot.observability.system_status import (
    build_admin_llm_diagnostics_text,
    build_admin_system_status_text,
)

NOW = datetime(2026, 10, 10, 12, tzinfo=timezone.utc)


async def _db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


def _event(index, *, success=True, symbol="BTC", op_id=None, at=None):
    return EventAiAnalysis(
        analysis_id=f"op-{index}",
        llm_operation_id=op_id,
        analysis_type="event_analysis",
        symbol=symbol,
        status="no_alert" if success else "llm_error",
        provider="groq",
        model="not-displayed",
        input_hash=f"input-{index}",
        created_at=at or NOW - timedelta(minutes=20),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("successes", "failures", "expected"),
    [
        (20, 0, "ok"),
        (16, 4, "unknown"),  # Below alert-count gate; not falsely healthy.
        (19, 6, "degraded"),
        (12, 15, "failed"),
        (1, 0, "unknown"),
        (0, 0, "unknown"),
        (0, 10, "degraded"),
    ],
)
async def test_rolling_states_and_low_volume(successes, failures, expected):
    engine, factory = await _db()
    try:
        async with factory() as session:
            session.add_all([_event(i) for i in range(successes)])
            session.add_all([
                _event(1000 + i, success=False) for i in range(failures)
            ])
            await session.commit()
            result = (await read_logical_llm_health(session, now=NOW))["event_analysis"]
        assert result.state == expected
        assert result.successes == successes
        assert result.terminal_failures == failures
        assert result.operations == successes + failures
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_recovered_provider_failure_is_not_a_terminal_failure():
    engine, factory = await _db()
    try:
        async with factory() as session:
            session.add(_event(1, op_id="logical-recovered"))
            for status in ("rate_limit", "success"):
                session.add(LlmUsageLog(
                    llm_operation_id="logical-recovered",
                    call_type="event_analysis",
                    symbol="BTC",
                    provider="groq",
                    model="opaque-model",
                    status=status,
                    created_at=NOW - timedelta(minutes=20),
                ))
            await session.commit()
            result = (await read_logical_llm_health(session, now=NOW))["event_analysis"]
        assert result.successes == 1
        assert result.terminal_failures == 0
        assert result.missing_outcomes == 0
        assert result.recovered_operations == 1
        assert result.state == "unknown"  # Insufficient sample, not degraded.
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_missing_correlated_outcome_is_unknown_not_healthy():
    engine, factory = await _db()
    try:
        async with factory() as session:
            session.add_all([_event(i, op_id=f"known-{i}") for i in range(25)])
            session.add(LlmUsageLog(
                llm_operation_id="unrecorded-operation",
                call_type="event_analysis",
                provider="groq", model="secret-model", status="success",
                created_at=NOW - timedelta(minutes=20),
            ))
            await session.commit()
            result = (await read_logical_llm_health(session, now=NOW))["event_analysis"]
        assert result.success_rate_percent == 100.0
        assert result.state == "unknown"
        assert result.missing_outcomes == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_stale_and_inflight_attempts_do_not_create_false_gaps():
    engine, factory = await _db()
    try:
        async with factory() as session:
            session.add_all([_event(i) for i in range(20)])
            for i, age in enumerate((2, 1435)):
                session.add(LlmUsageLog(
                    llm_operation_id=f"boundary-{i}", call_type="event_analysis",
                    provider="groq", model="opaque", status="timeout",
                    created_at=NOW - timedelta(minutes=age),
                ))
            await session.commit()
            result = (await read_logical_llm_health(session, now=NOW))["event_analysis"]
        assert result.state == "ok"
        assert result.missing_outcomes == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_other_call_types_and_symbol_scoped_problem_only():
    engine, factory = await _db()
    try:
        async with factory() as session:
            session.add_all([_event(i, symbol="BTC", success=i < 10) for i in range(20)])
            session.add_all([_event(i + 100, symbol="ETH") for i in range(20)])
            session.add(LlmOperationOutcome(
                llm_operation_id="render-1", call_type="event_alert_render",
                symbol="BTC", status="success", created_at=NOW - timedelta(minutes=20),
            ))
            session.add(LlmOperationOutcome(
                llm_operation_id="news-1", call_type="news_intelligence",
                status="failed", created_at=NOW - timedelta(minutes=20),
            ))
            session.add(MarketHeartbeat(
                symbol="BTC", generated_at=NOW, created_at=NOW,
                status="completed",
            ))
            for typ in ("daily", "weekly"):
                session.add(MarketReport(
                    report_type=typ, status="completed",
                    generated_at=NOW, expires_at=NOW + timedelta(days=1),
                    created_at=NOW,
                ))
            await session.commit()
            all_health = await read_logical_llm_health(session, now=NOW)
        assert all_health["event_analysis"].problem_symbols == ("BTC",)
        assert all_health["event_alert_render"].successes == 1
        assert all_health["news_intelligence"].terminal_failures == 1
        assert all_health["market_heartbeat"].successes == 1
        assert all_health["daily_report"].successes == 1
        assert all_health["weekly_report"].successes == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_admin_surfaces_terminal_failures_without_double_counting_attempts():
    engine, factory = await _db()
    try:
        async with factory() as session:
            session.add_all([_event(i) for i in range(127)])
            session.add_all([_event(i + 500, success=False) for i in range(65)])
            session.add(LlmUsageLog(
                call_type="event_analysis", provider="groq",
                model="sensitive-model", status="rate_limit",
                created_at=NOW - timedelta(minutes=20),
            ))
            await session.commit()
        system = await build_admin_system_status_text(
            db_enabled=True, session_factory=factory, now=NOW
        )
        diagnostics = await build_admin_llm_diagnostics_text(
            db_enabled=True, session_factory=factory, now=NOW
        )
        assert "❌ AI — 24h logical success 66.1%" in system
        assert "Terminal failures: 65 in 24h" in system
        assert "Event Analysis — failed: 127 success, 65 terminal failed" in diagnostics
        assert "Provider attempts — Summary" in diagnostics
        assert "Total: 1 attempt" in diagnostics
        assert "sensitive-model" not in system + diagnostics
    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rolling_state", "completed", "successes", "failures", "expected"),
    [
        ("ok", 20, 20, 0, "ok"),
        ("degraded", 25, 19, 6, "degraded"),
        ("failed", 27, 12, 15, "failed"),
        ("unknown", 0, 0, 0, "unknown"),
    ],
)
async def test_health_nested_logical_state_keeps_top_level_ok(
    monkeypatch, rolling_state, completed, successes, failures, expected
):
    import time

    from bot import health
    from bot.observability import event_analysis_health
    from bot.observability.logical_llm_health import LogicalHealth

    event_analysis_health.reset()
    monkeypatch.setattr(health, "DB_ENABLED", False)
    monkeypatch.setattr(health, "load_state", lambda: {})

    async def _recent_success():
        return datetime.now(timezone.utc) - timedelta(minutes=5)

    async def _logical():
        return LogicalHealth(
            "event_analysis", rolling_state, completed, successes, failures, 0, 0,
            round(100 * successes / completed, 1) if completed else None,
        )

    monkeypatch.setattr(health, "_read_last_event_analysis_success_at", _recent_success)
    monkeypatch.setattr(health, "_read_event_analysis_logical_health", _logical)
    result = await health.health_response(time.monotonic())
    assert result["status"] == "ok"
    assert result["event_analysis"]["state"] == expected
    assert result["event_analysis"]["logical_24h"]["terminal_failures"] == failures


@pytest.mark.asyncio
async def test_health_reports_unknown_when_rollup_query_fails(monkeypatch):
    import time

    from bot import health
    from bot.observability import event_analysis_health

    event_analysis_health.reset()
    monkeypatch.setattr(health, "DB_ENABLED", False)
    monkeypatch.setattr(health, "load_state", lambda: {})

    async def _success():
        return datetime.now(timezone.utc) - timedelta(minutes=3)

    async def _telemetry_error():
        raise RuntimeError("never leak database query text")

    monkeypatch.setattr(health, "_read_last_event_analysis_success_at", _success)
    monkeypatch.setattr(health, "_read_event_analysis_logical_health", _telemetry_error)

    result = await health.health_response(time.monotonic())
    assert result["status"] == "ok"
    assert result["event_analysis"]["state"] == "unknown"
    assert "never leak" not in str(result)
