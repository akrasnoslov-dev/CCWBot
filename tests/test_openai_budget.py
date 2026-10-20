"""Offline tests for the persistent OpenAI spend guard; no provider calls."""

import asyncio
import os
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.db.database import Base, OpenAIBudgetReservation
from bot.services.llm.openai_budget import (
    _POSTGRES_ADVISORY_LOCK_ID,
    OpenAIBudget,
    OpenAIBudgetExhausted,
)


@pytest_asyncio.fixture
async def budget_db(tmp_path, monkeypatch):
    from bot import runtime

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'budget.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(runtime, "DB_ENABLED", True)
    monkeypatch.setattr(runtime, "DB_SESSION_LOCAL", sessions)
    monkeypatch.setenv("OPENAI_MONTHLY_BUDGET_USD", "2.50")
    monkeypatch.setenv("OPENAI_PRICED_MODEL", "gpt-6-luna")
    monkeypatch.setenv("OPENAI_MAX_INPUT_TOKENS", "1000")
    monkeypatch.setenv("OPENAI_INPUT_USD_PER_1M_TOKENS", "1.00")
    monkeypatch.setenv("OPENAI_OUTPUT_USD_PER_1M_TOKENS", "10.00")
    yield sessions
    await engine.dispose()


@pytest.mark.asyncio
async def test_reservation_is_durable_and_reconciles_known_usage(budget_db):
    lease = await OpenAIBudget().reserve(
        model="gpt-6-luna", call_type="daily_report", input_chars=2_000, max_tokens=800
    )
    await OpenAIBudget().settle(
        lease, prompt_tokens=400, completion_tokens=200
    )

    async with budget_db() as session:
        row = await session.get(OpenAIBudgetReservation, lease.reservation_id)
        assert row.status == "settled"
        assert row.actual_usd == Decimal("0.0024000000")
        assert row.reserved_usd > row.actual_usd


@pytest.mark.asyncio
async def test_concurrent_reservations_cannot_exceed_cap(budget_db, monkeypatch):
    monkeypatch.setenv("OPENAI_MONTHLY_BUDGET_USD", "0.015")
    budget = OpenAIBudget()

    async def reserve_once():
        return await budget.reserve(
            model="gpt-6-luna",
            call_type="event_analysis",
            input_chars=2_000,
            max_tokens=1_000,
        )

    results = await asyncio.gather(
        reserve_once(), reserve_once(), return_exceptions=True
    )
    assert sum(not isinstance(result, Exception) for result in results) == 1
    rejected = next(result for result in results if isinstance(result, Exception))
    assert isinstance(rejected, OpenAIBudgetExhausted)
    assert rejected.reason == "exhausted"


@pytest.mark.asyncio
async def test_restart_reads_existing_reservation_and_month_rollover_ignores_old_month(
    budget_db, monkeypatch
):
    monkeypatch.setenv("OPENAI_MONTHLY_BUDGET_USD", "0.015")
    first = await OpenAIBudget().reserve(
        model="gpt-6-luna", call_type="event_analysis", input_chars=2_000, max_tokens=1_000
    )
    with pytest.raises(OpenAIBudgetExhausted, match="exhausted"):
        await OpenAIBudget().reserve(
            model="gpt-6-luna", call_type="event_analysis", input_chars=2_000, max_tokens=1_000
        )

    async with budget_db.begin() as session:
        row = await session.get(OpenAIBudgetReservation, first.reservation_id)
        row.month_start = date(2000, 1, 1)

    replacement = await OpenAIBudget().reserve(
        model="gpt-6-luna", call_type="event_analysis", input_chars=2_000, max_tokens=1_000
    )
    assert replacement.reservation_id != first.reservation_id


@pytest.mark.asyncio
async def test_unknown_usage_remains_conservative(budget_db):
    lease = await OpenAIBudget().reserve(
        model="gpt-6-luna", call_type="market_heartbeat", input_chars=100, max_tokens=100
    )
    await OpenAIBudget().settle(lease, prompt_tokens=None, completion_tokens=None)
    async with budget_db() as session:
        row = await session.get(OpenAIBudgetReservation, lease.reservation_id)
        assert row.status == "conservative"
        assert row.actual_usd is None


@pytest.mark.asyncio
async def test_negative_usage_remains_conservative(budget_db):
    lease = await OpenAIBudget().reserve(
        model="gpt-6-luna", call_type="market_heartbeat", input_chars=100, max_tokens=100
    )
    await OpenAIBudget().settle(lease, prompt_tokens=-1, completion_tokens=10)
    async with budget_db() as session:
        row = await session.get(OpenAIBudgetReservation, lease.reservation_id)
        assert row.status == "conservative"
        assert row.actual_usd is None


@pytest.mark.asyncio
async def test_missing_pricing_and_state_fail_closed(monkeypatch):
    from bot import runtime

    monkeypatch.delenv("OPENAI_INPUT_USD_PER_1M_TOKENS", raising=False)
    monkeypatch.delenv("OPENAI_OUTPUT_USD_PER_1M_TOKENS", raising=False)
    with pytest.raises(OpenAIBudgetExhausted) as unknown:
        await OpenAIBudget().reserve(
            model="gpt-6-luna", call_type="daily_report", input_chars=1, max_tokens=1
        )
    assert unknown.value.reason == "unknown_pricing"

    monkeypatch.setenv("OPENAI_INPUT_USD_PER_1M_TOKENS", "1")
    monkeypatch.setenv("OPENAI_OUTPUT_USD_PER_1M_TOKENS", "1")
    monkeypatch.setenv("OPENAI_PRICED_MODEL", "gpt-6-luna")
    monkeypatch.setenv("OPENAI_MAX_INPUT_TOKENS", "1000")
    monkeypatch.setattr(runtime, "DB_ENABLED", False)
    with pytest.raises(OpenAIBudgetExhausted) as missing:
        await OpenAIBudget().reserve(
            model="gpt-6-luna", call_type="daily_report", input_chars=1, max_tokens=1
        )
    assert missing.value.reason == "state_unavailable"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "value",
    [
        "NaN",
        "sNaN",
        "Infinity",
        "-Infinity",
        "1e999999",
        "1e-999999",
        "2.5000000001",
        "100",
    ],
)
async def test_non_finite_budget_values_fail_closed(monkeypatch, value):
    monkeypatch.setenv("OPENAI_MONTHLY_BUDGET_USD", value)
    monkeypatch.setenv("OPENAI_INPUT_USD_PER_1M_TOKENS", "1")
    monkeypatch.setenv("OPENAI_OUTPUT_USD_PER_1M_TOKENS", "1")
    monkeypatch.setenv("OPENAI_PRICED_MODEL", "gpt-6-luna")
    monkeypatch.setenv("OPENAI_MAX_INPUT_TOKENS", "1000")
    with pytest.raises(OpenAIBudgetExhausted) as blocked:
        await OpenAIBudget().reserve(
            model="gpt-6-luna", call_type="daily_report", input_chars=1, max_tokens=1
        )
    assert blocked.value.reason == "invalid_cap"


@pytest.mark.asyncio
async def test_model_and_input_limit_must_match_verified_pricing(budget_db, monkeypatch):
    monkeypatch.setenv("OPENAI_PRICED_MODEL", "different-model")
    with pytest.raises(OpenAIBudgetExhausted) as mismatch:
        await OpenAIBudget().reserve(
            model="gpt-6-luna", call_type="daily_report", input_chars=1, max_tokens=1
        )
    assert mismatch.value.reason == "unverified_model_limits"

    monkeypatch.setenv("OPENAI_PRICED_MODEL", "gpt-6-luna")
    monkeypatch.setenv("OPENAI_MAX_INPUT_TOKENS", "not-an-int")
    with pytest.raises(OpenAIBudgetExhausted) as unknown_limit:
        await OpenAIBudget().reserve(
            model="gpt-6-luna", call_type="daily_report", input_chars=1, max_tokens=1
        )
    assert unknown_limit.value.reason == "unverified_model_limits"

    monkeypatch.setenv("OPENAI_MAX_INPUT_TOKENS", "9" * 1000)
    with pytest.raises(OpenAIBudgetExhausted) as extreme_limit:
        await OpenAIBudget().reserve(
            model="gpt-6-luna", call_type="daily_report", input_chars=1, max_tokens=1
        )
    assert extreme_limit.value.reason == "unverified_model_limits"


@pytest.mark.asyncio
async def test_full_input_ceiling_covers_token_dense_prompt_near_cap(budget_db, monkeypatch):
    monkeypatch.setenv("OPENAI_MONTHLY_BUDGET_USD", "0.0021")
    lease = await OpenAIBudget().reserve(
        model="gpt-6-luna",
        call_type="event_analysis",
        input_chars=1,
        max_tokens=100,
    )
    await OpenAIBudget().settle(lease, prompt_tokens=1000, completion_tokens=100)
    async with budget_db() as session:
        row = await session.get(OpenAIBudgetReservation, lease.reservation_id)
        assert row.status == "settled"
        assert row.actual_usd <= row.reserved_usd

    with pytest.raises(OpenAIBudgetExhausted, match="exhausted"):
        await OpenAIBudget().reserve(
            model="gpt-6-luna",
            call_type="event_analysis",
            input_chars=1,
            max_tokens=100,
        )


@pytest.mark.asyncio
async def test_usage_overrun_persistently_blocks_current_month(budget_db):
    lease = await OpenAIBudget().reserve(
        model="gpt-6-luna",
        call_type="event_analysis",
        input_chars=1,
        max_tokens=100,
    )
    await OpenAIBudget().settle(lease, prompt_tokens=2000, completion_tokens=100)
    async with budget_db() as session:
        row = await session.get(OpenAIBudgetReservation, lease.reservation_id)
        assert row.status == "cap_breach"
        assert row.actual_usd > row.reserved_usd
        breach_charge = row.actual_usd

    # Settlement is idempotent and cap_breach is absorbing: a duplicate provider
    # result cannot clear the current-month safety latch or lower accounting.
    await OpenAIBudget().settle(lease, prompt_tokens=1, completion_tokens=1)
    await OpenAIBudget().settle(lease, prompt_tokens=None, completion_tokens=None)
    async with budget_db() as session:
        row = await session.get(OpenAIBudgetReservation, lease.reservation_id)
        assert row.status == "cap_breach"
        assert row.actual_usd == breach_charge

    with pytest.raises(OpenAIBudgetExhausted) as blocked:
        await OpenAIBudget().reserve(
            model="gpt-6-luna",
            call_type="event_analysis",
            input_chars=1,
            max_tokens=100,
        )
    assert blocked.value.reason == "invariant_breach"


@pytest.mark.asyncio
async def test_ledger_never_counts_less_than_reserved_without_known_usage(budget_db):
    lease = await OpenAIBudget().reserve(
        model="gpt-6-luna", call_type="weekly_report", input_chars=100, max_tokens=100
    )
    async with budget_db() as session:
        total = await session.scalar(
            select(
                func.sum(
                    func.coalesce(
                        OpenAIBudgetReservation.actual_usd,
                        OpenAIBudgetReservation.reserved_usd,
                    )
                )
            ).where(
                OpenAIBudgetReservation.month_start
                == datetime.now(timezone.utc).date().replace(day=1)
            )
        )
    assert Decimal(total) == lease.reserved_usd


@pytest.mark.asyncio
async def test_postgres_advisory_lock_serializes_distinct_workers(monkeypatch):
    """Exercise the production cross-worker lock when CI provides throwaway PostgreSQL."""
    from bot import runtime

    url = os.getenv("ALEMBIC_POSTGRES_TEST_DATABASE_URL") or os.getenv(
        "OPS_AGENT_POSTGRES_TEST_DATABASE_URL"
    )
    if not url:
        pytest.skip("set ALEMBIC_POSTGRES_TEST_DATABASE_URL to a migrated throwaway PostgreSQL DB")
    engine = create_async_engine(url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    month_start = datetime.now(timezone.utc).date().replace(day=1)
    monkeypatch.setattr(runtime, "DB_ENABLED", True)
    monkeypatch.setattr(runtime, "DB_SESSION_LOCAL", sessions)
    monkeypatch.setenv("OPENAI_MONTHLY_BUDGET_USD", "0.015")
    monkeypatch.setenv("OPENAI_PRICED_MODEL", "gpt-6-luna")
    monkeypatch.setenv("OPENAI_MAX_INPUT_TOKENS", "1000")
    monkeypatch.setenv("OPENAI_INPUT_USD_PER_1M_TOKENS", "1")
    monkeypatch.setenv("OPENAI_OUTPUT_USD_PER_1M_TOKENS", "10")
    try:
        async with sessions.begin() as session:
            await session.execute(
                delete(OpenAIBudgetReservation).where(
                    OpenAIBudgetReservation.month_start == month_start
                )
            )
        first_worker = OpenAIBudget()
        second_worker = OpenAIBudget()
        results = await asyncio.gather(
            first_worker.reserve(
                model="gpt-6-luna",
                call_type="event_analysis",
                input_chars=1,
                max_tokens=1000,
            ),
            second_worker.reserve(
                model="gpt-6-luna",
                call_type="event_analysis",
                input_chars=1,
                max_tokens=1000,
            ),
            return_exceptions=True,
        )
        assert sum(not isinstance(result, Exception) for result in results) == 1
        rejected = next(result for result in results if isinstance(result, Exception))
        assert isinstance(rejected, OpenAIBudgetExhausted)
        assert rejected.reason == "exhausted"
    finally:
        async with sessions.begin() as session:
            await session.execute(
                delete(OpenAIBudgetReservation).where(
                    OpenAIBudgetReservation.month_start == month_start
                )
            )
        await engine.dispose()


@pytest.mark.asyncio
async def test_postgres_settlement_breach_is_ordered_before_new_admission(monkeypatch):
    """A queued breach settlement must commit before a later queued reservation."""
    from bot import runtime

    url = os.getenv("ALEMBIC_POSTGRES_TEST_DATABASE_URL") or os.getenv(
        "OPS_AGENT_POSTGRES_TEST_DATABASE_URL"
    )
    if not url:
        pytest.skip("set ALEMBIC_POSTGRES_TEST_DATABASE_URL to a migrated throwaway PostgreSQL DB")
    engine = create_async_engine(url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    month_start = datetime.now(timezone.utc).date().replace(day=1)
    monkeypatch.setattr(runtime, "DB_ENABLED", True)
    monkeypatch.setattr(runtime, "DB_SESSION_LOCAL", sessions)
    monkeypatch.setenv("OPENAI_MONTHLY_BUDGET_USD", "2.50")
    monkeypatch.setenv("OPENAI_PRICED_MODEL", "gpt-6-luna")
    monkeypatch.setenv("OPENAI_MAX_INPUT_TOKENS", "1000")
    monkeypatch.setenv("OPENAI_INPUT_USD_PER_1M_TOKENS", "1")
    monkeypatch.setenv("OPENAI_OUTPUT_USD_PER_1M_TOKENS", "10")
    lock_high = _POSTGRES_ADVISORY_LOCK_ID >> 32
    lock_low = _POSTGRES_ADVISORY_LOCK_ID & 0xFFFFFFFF

    async def wait_for_lock_waiters(expected: int) -> None:
        for _attempt in range(200):
            async with engine.connect() as connection:
                waiting = await connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_locks "
                        "WHERE locktype = 'advisory' AND classid = :high "
                        "AND objid = :low AND NOT granted"
                    ),
                    {"high": lock_high, "low": lock_low},
                )
            if int(waiting or 0) >= expected:
                return
            await asyncio.sleep(0.01)
        raise AssertionError(f"expected {expected} advisory-lock waiters")

    blocker = await engine.connect()
    try:
        async with sessions.begin() as session:
            await session.execute(
                delete(OpenAIBudgetReservation).where(
                    OpenAIBudgetReservation.month_start == month_start
                )
            )
        settling_worker = OpenAIBudget()
        admitting_worker = OpenAIBudget()
        lease = await settling_worker.reserve(
            model="gpt-6-luna",
            call_type="event_analysis",
            input_chars=1,
            max_tokens=100,
        )
        await blocker.execute(
            text("SELECT pg_advisory_lock(:lock_id)"),
            {"lock_id": _POSTGRES_ADVISORY_LOCK_ID},
        )
        settlement = asyncio.create_task(
            settling_worker.settle(lease, prompt_tokens=2000, completion_tokens=100)
        )
        await wait_for_lock_waiters(1)
        admission = asyncio.create_task(
            admitting_worker.reserve(
                model="gpt-6-luna",
                call_type="event_analysis",
                input_chars=1,
                max_tokens=100,
            )
        )
        await wait_for_lock_waiters(2)
        await blocker.execute(
            text("SELECT pg_advisory_unlock(:lock_id)"),
            {"lock_id": _POSTGRES_ADVISORY_LOCK_ID},
        )
        await settlement
        with pytest.raises(OpenAIBudgetExhausted) as blocked:
            await admission
        assert blocked.value.reason == "invariant_breach"
    finally:
        if blocker.in_transaction():
            await blocker.execute(
                text("SELECT pg_advisory_unlock(:lock_id)"),
                {"lock_id": _POSTGRES_ADVISORY_LOCK_ID},
            )
        await blocker.close()
        async with sessions.begin() as session:
            await session.execute(
                delete(OpenAIBudgetReservation).where(
                    OpenAIBudgetReservation.month_start == month_start
                )
            )
        await engine.dispose()
