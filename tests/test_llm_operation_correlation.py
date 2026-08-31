"""Durable logical-operation correlation contracts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.db.database import (
    Base,
    LlmUsageLog,
    save_event_llm_analysis,
    save_llm_usage_log,
    save_market_heartbeat,
    save_market_report,
    update_llm_usage_log_status,
)
from bot.services.llm.operation import new_llm_operation_id
from bot.services.llm.telemetry import rate_limit_header_payload


@pytest.mark.asyncio
async def test_durable_feature_rows_join_only_their_logical_provider_attempts():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_local = async_sessionmaker(engine, expire_on_commit=False)
    event_operation = new_llm_operation_id()
    heartbeat_operation = new_llm_operation_id()
    report_operation = new_llm_operation_id()

    async with session_local() as session:
        await save_llm_usage_log(
            session,
            provider="groq",
            model="primary",
            call_type="event_analysis",
            status="rate_limit",
            llm_operation_id=event_operation,
        )
        await save_llm_usage_log(
            session,
            provider="gemini",
            model="fallback",
            call_type="event_analysis",
            status="success",
            llm_operation_id=event_operation,
        )
        analysis = await save_event_llm_analysis(
            session,
            analysis_id="correlation-event",
            llm_operation_id=event_operation,
            symbol="BTC",
            input_hash="input",
            raw_input_json="{}",
            raw_output_json="{}",
            status="no_alert",
            provider="gemini",
            model="fallback",
            should_alert=False,
        )
        heartbeat = await save_market_heartbeat(
            session,
            symbol="BTC",
            generated_at=datetime.now(timezone.utc),
            llm_operation_id=heartbeat_operation,
            raw_input_json="{}",
            raw_output_json="{}",
        )
        report = await save_market_report(
            session,
            report_type="daily",
            llm_operation_id=report_operation,
            generated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            status="completed",
            raw_input_json="{}",
            raw_output_json="{}",
        )
        attempts = list(
            await session.scalars(
                select(LlmUsageLog).where(LlmUsageLog.llm_operation_id == event_operation)
            )
        )

    assert {attempt.provider for attempt in attempts} == {"groq", "gemini"}
    assert analysis.llm_operation_id == event_operation
    assert heartbeat.llm_operation_id == heartbeat_operation
    assert report.llm_operation_id == report_operation
    assert len({event_operation, heartbeat_operation, report_operation}) == 3
    assert all("user" not in operation for operation in (event_operation, heartbeat_operation))
    await engine.dispose()


@pytest.mark.asyncio
async def test_usage_status_update_fills_missing_operation_id_without_overwriting_it():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_local = async_sessionmaker(engine, expire_on_commit=False)
    first_operation = new_llm_operation_id()
    second_operation = new_llm_operation_id()

    async with session_local() as session:
        usage = await save_llm_usage_log(
            session,
            provider="groq",
            model="primary",
            call_type="market_heartbeat",
            status="success",
        )
        updated = await update_llm_usage_log_status(
            session,
            usage_log_id=usage.id,
            status="schema_error",
            llm_operation_id=first_operation,
        )
        preserved = await update_llm_usage_log_status(
            session,
            usage_log_id=usage.id,
            status="schema_error",
            llm_operation_id=second_operation,
        )

    assert updated is not None
    assert updated.llm_operation_id == first_operation
    assert preserved is not None
    assert preserved.llm_operation_id == first_operation
    await engine.dispose()


@pytest.mark.parametrize(
    ("request_id", "expected"),
    [
        ("request-1", "request-1"),
        ("x" * 128, "x" * 128),
        ("x" * 129, None),
        ("Bearer_secret-value", None),
        ("sk_live_abcdefghijklmnopqrstuvwxyz123456", None),
        ("sk_abcdefghijklmnopqrstuvwxyz123456", None),
        ("AKIA1234567890ABCDEF", None),
        ("unsafe/id", None),
    ],
)
@pytest.mark.asyncio
async def test_provider_request_id_is_bounded_before_usage_persistence(request_id, expected):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_local = async_sessionmaker(engine, expire_on_commit=False)
    payload = rate_limit_header_payload({"x-request-id": request_id})

    async with session_local() as session:
        usage = await save_llm_usage_log(
            session,
            provider="groq",
            model="primary",
            call_type="event_analysis",
            status="success",
            **payload,
        )

    assert usage.provider_request_id == expected
    await engine.dispose()
