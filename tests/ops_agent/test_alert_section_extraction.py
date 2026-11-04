"""Execute the production aggregate SQL using synthetic final Telegram messages."""

import os
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from ops_agent.db_queries import QUERIES


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["distinct", "repeated", "missing", "generic", "pace"])
async def test_final_section_sql_handles_newlines_fanout_and_missing_sections(kind):
    url = os.getenv("OPS_AGENT_POSTGRES_TEST_DATABASE_URL")
    if not url:
        pytest.skip("requires a throwaway local PostgreSQL database")
    engine = create_async_engine(url)
    since = datetime(2026, 10, 13, tzinfo=timezone.utc)
    query = next(q for q in QUERIES if q.name == "event_alert_possible_action_quality")
    try:
        async with engine.connect() as conn:
            await conn.execute(
                text(
                    "CREATE TEMP TABLE alerts (id int, market_event_id int, "
                    "event_ai_analysis_id int, created_at timestamptz, "
                    "alert_type text, status text, message text) ON COMMIT DROP"
                )
            )
            await conn.execute(
                text(
                    "CREATE TEMP TABLE event_ai_analyses (id int, message_body text, "
                    "possible_action text, should_alert boolean) ON COMMIT DROP"
                )
            )
            for index in range(5):
                situation = (
                    "Shared verified relationship."
                    if kind == "repeated"
                    else f"Distinct verified relationship {index}."
                )
                action = (
                    "Watch whether the next observed interval extends "
                    f"path {min(index, 3)} or turns."
                )
                if kind == "generic" and index < 2:
                    action = "Watch whether the next short-term snapshots continue or reverse."
                if kind == "pace" and index < 2:
                    action = (
                        "Watch whether the next observed steps keep advancing "
                        "at a similar or faster pace."
                    )
                    if index == 1:
                        action = (
                            "Watch whether the next observed steps continue progressing\n"
                            "at roughly the same speed."
                        )
                related = (
                    "Related context:\nSynthetic source-backed headline.\n\n" if index % 2 else ""
                )
                message = (
                    f"ETH Event Alert\n\nSituation:\n{situation}\n\n{related}"
                    f"Possible action:\n{action}\n\nNot financial advice."
                )
                if kind == "missing" and index < 2:
                    message = "Synthetic malformed message without section headings."
                await conn.execute(
                    text("INSERT INTO event_ai_analyses VALUES (:id,:s,:a,true)"),
                    {
                        "id": index,
                        "s": situation,
                        "a": action if index < 3 else "Different provider wording.",
                    },
                )
                # Many recipients do not become many events in quality counts.
                for recipient in range(3):
                    await conn.execute(
                        text(
                            "INSERT INTO alerts VALUES "
                            "(:id,:event,:event,:at,'event_alert','sent',:m)"
                        ),
                        {
                            "id": index * 10 + recipient,
                            "event": index,
                            "at": since + timedelta(hours=1),
                            "m": message,
                        },
                    )
            result = (
                (
                    await conn.execute(
                        text(query.sql),
                        {
                            "since": since,
                            "until": since + timedelta(days=1),
                        },
                    )
                )
                .mappings()
                .one()
            )
            assert result["event_alert_actions"] == 5
            assert result["repeated_situation_count"] == (4 if kind == "repeated" else 0)
            assert result["situation_replaced_count"] == 0
            assert result["action_replaced_count"] == 2
            assert result["repeated_action_count"] == (2 if kind == "generic" else 1)
            assert result["generic_possible_action_count"] == (
                2 if kind in {"generic", "pace"} else 0
            )
            assert result["missing_situation_count"] == (2 if kind == "missing" else 0)
            assert result["missing_action_count"] == (2 if kind == "missing" else 0)
            await conn.rollback()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_delivery_failure_sql_distinguishes_both_error_fields():
    url = os.getenv("OPS_AGENT_POSTGRES_TEST_DATABASE_URL")
    if not url:
        pytest.skip("requires a throwaway local PostgreSQL database")
    engine = create_async_engine(url)
    since = datetime(2026, 10, 13, tzinfo=timezone.utc)
    query = next(q for q in QUERIES if q.name == "telegram_delivery_failure_summary")
    try:
        async with engine.connect() as conn:
            await conn.execute(text(
                "CREATE TEMP TABLE alerts (last_error text, error_message text, status text, "
                "final_failed_at timestamptz, created_at timestamptz) ON COMMIT DROP"
            ))
            for last, error, status in [
                ("timeout", "Forbidden: bot was blocked by the user", "failed"),
                (None, "Bad Request: chat not found", "failed"),
                (None, "Forbidden: permissions changed", "failed"),
                ("timed out", None, "retry_pending"),
            ]:
                await conn.execute(
                    text("INSERT INTO alerts VALUES (:last, :error, :status, NULL, :at)"),
                    {"last": last, "error": error, "status": status, "at": since},
                )
            row = (await conn.execute(text(query.sql), {
                "since": since, "until": since + timedelta(days=1),
            })).mappings().one()
            assert row["failed_or_retry_pending_total"] == 4
            assert row["blocked_user"] == 1
            assert row["recipient_unavailable"] == 1
            assert row["unexplained_telegram_failure"] == 1
            assert row["retry_pending_actionable"] == 1
            await conn.rollback()
    finally:
        await engine.dispose()
