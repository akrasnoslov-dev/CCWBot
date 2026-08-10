from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.db.database import (
    Alert,
    Base,
    EventAiAnalysis,
    LlmUsageLog,
    NewsItem,
    PriceState,
    User,
)
from bot.domain.supported_coins import SUPPORTED_SYMBOLS
from bot.observability import system_status
from bot.observability.system_status import build_admin_system_status_text
from bot.services.ai_agent_groq import reset_llm_rate_limit_backoffs


async def build_session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_local = async_sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    return engine, session_local


def _now() -> datetime:
    return datetime(2026, 6, 15, 16, 55, tzinfo=timezone.utc)


async def _seed_fresh_prices(session, now: datetime, *, skip: set[str] | None = None):
    skip = skip or set()
    for index, symbol in enumerate(SUPPORTED_SYMBOLS):
        if symbol in skip:
            continue
        session.add(
            PriceState(
                symbol=symbol.upper(),
                last_price=1000.0 + index,
                last_24h_change=1.0,
                last_checked_at=now - timedelta(minutes=10),
            )
        )


async def _seed_healthy_status_dependencies(session, now: datetime):
    await _seed_fresh_prices(session, now)
    session.add(
        _event_analysis(
            status="success",
            created_at=now - timedelta(minutes=5),
            analysis_id="healthy_status_success",
        )
    )
    session.add(
        LlmUsageLog(
            provider="groq",
            model="event-model",
            call_type="event_analysis",
            status="success",
            created_at=now - timedelta(minutes=5),
        )
    )
    session.add(
        NewsItem(
            news_key="healthy-news",
            title="BTC news",
            url="https://example.com/news",
            fetched_at=now - timedelta(minutes=20),
            llm_status="success",
            updated_at=now - timedelta(minutes=19),
        )
    )


def _event_analysis(
    *,
    status: str,
    created_at: datetime,
    analysis_id: str,
    error_reason: str | None = None,
    error_message: str | None = None,
) -> EventAiAnalysis:
    return EventAiAnalysis(
        analysis_id=analysis_id,
        symbol="BTC",
        analysis_type="event_analysis",
        provider="groq",
        model="event-model",
        input_hash=analysis_id,
        raw_input_json="{}",
        status=status,
        error_reason=error_reason,
        error_message=error_message,
        created_at=created_at,
    )


def _final_failed_alert(
    *,
    sent_to_chat_id: int,
    created_at: datetime,
    last_error: str | None = None,
    error_message: str | None = None,
) -> Alert:
    return Alert(
        symbol="BTC",
        alert_type="event_alert",
        message="safe",
        sent_to_chat_id=sent_to_chat_id,
        status="failed",
        created_at=created_at,
        error_message=error_message,
        last_error=last_error,
        final_failed_at=created_at,
    )


@pytest.mark.asyncio
async def test_system_status_uses_real_fresh_telemetry():
    now = _now()
    engine, session_local = await build_session_factory()
    try:
        async with session_local() as session:
            await _seed_fresh_prices(session, now)
            session.add(
                _event_analysis(
                    status="success",
                    created_at=now - timedelta(minutes=5),
                    analysis_id="latest_success",
                )
            )
            session.add(
                LlmUsageLog(
                    provider="groq",
                    model="event-model",
                    call_type="event_analysis",
                    status="success",
                    created_at=now - timedelta(minutes=5),
                )
            )
            session.add(
                NewsItem(
                    news_key="news-1",
                    title="BTC news",
                    url="https://example.com/news",
                    fetched_at=now - timedelta(minutes=20),
                    llm_status="success",
                    updated_at=now - timedelta(minutes=19),
                )
            )
            session.add(
                Alert(
                    symbol="BTC",
                    alert_type="event_alert",
                    message="safe",
                    sent_to_chat_id=100,
                    status="sent",
                    created_at=now - timedelta(minutes=3),
                )
            )
            await session.commit()

        text = await build_admin_system_status_text(
            db_enabled=True,
            session_factory=session_local,
            now=now,
        )

        assert "Overall: ✅ OK" in text
        assert "✅ Bot — running" in text
        assert "✅ Database — connected" in text
        assert "✅ Market data — BTC, ETH, GRAM, SOL fresh" in text
        assert "✅ AI analysis — latest success 5m ago" in text
        assert "✅ LLM rate limit — no active limit" in text
        assert "✅ News — 1 usable items in 24h" in text
        assert "✅ Telegram delivery — sent 1 in 24h" in text
        assert (
            "Event Analysis / groq: 1 attempt (1 success, 0 rate-limit, 0 backoff, "
            "0 circuit, 0 schema-invalid, 0 provider failure) in 24h"
        ) in text
        assert len(text.splitlines()) <= 12
        assert "CoinGecko id" not in text
        assert "price_state" not in text
        assert "$" not in text
        assert "Latest news cache" not in text
        assert "Recent usable news items" not in text
        assert "News intelligence" not in text
        assert "Latest failure" not in text
        assert "Rate limit status: no active rate limit recorded" not in text
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_system_status_db_disabled_is_not_fake_ok():
    text = await build_admin_system_status_text(
        db_enabled=False,
        session_factory=None,
        state_loader=lambda: {"last_checked_at": "2026-06-15T14:29:00+00:00"},
        now=_now(),
    )

    assert "Overall: ⚠️ Needs attention" in text
    assert "✅ Bot — running" in text
    assert "⚠️ Database — local JSON fallback" in text
    assert "⚠️ Market data — no price telemetry" in text
    assert "⚠️ AI analysis — no analysis telemetry" in text
    assert "PostgreSQL" not in text


@pytest.mark.asyncio
async def test_system_status_shows_missing_symbols_compactly():
    now = _now()
    engine, session_local = await build_session_factory()
    try:
        async with session_local() as session:
            await _seed_fresh_prices(session, now, skip={"eth", "gram", "sol"})
            await session.commit()

        text = await build_admin_system_status_text(
            db_enabled=True,
            session_factory=session_local,
            now=now,
        )

        assert "⚠️ Market data — stale/missing symbols" in text
        assert "Missing: ETH, GRAM, SOL" in text
        assert "CoinGecko id" not in text
        assert "price_state" not in text
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_system_status_shows_stale_btc_without_price_details():
    now = _now()
    engine, session_local = await build_session_factory()
    try:
        async with session_local() as session:
            await _seed_fresh_prices(session, now, skip={"btc"})
            session.add(
                PriceState(
                    symbol="BTC",
                    last_price=65000.0,
                    last_24h_change=-1.0,
                    last_checked_at=now - timedelta(hours=32),
                )
            )
            await session.commit()

        text = await build_admin_system_status_text(
            db_enabled=True,
            session_factory=session_local,
            now=now,
        )

        assert "⚠️ Market data — stale/missing symbols" in text
        assert "BTC stale: last check 32h ago" in text
        assert "$65,000.00" not in text
        assert "CoinGecko id" not in text
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_system_status_marks_old_ai_failure_resolved_by_newer_success():
    now = _now()
    engine, session_local = await build_session_factory()
    try:
        async with session_local() as session:
            session.add(
                _event_analysis(
                    status="llm_error",
                    created_at=now - timedelta(days=1),
                    analysis_id="old_failure",
                    error_reason="other_error",
                    error_message="APIConnectionError - connection failed",
                )
            )
            session.add(
                _event_analysis(
                    status="no_alert",
                    created_at=now - timedelta(minutes=10),
                    analysis_id="new_success",
                )
            )
            await session.commit()

        text = await build_admin_system_status_text(
            db_enabled=True,
            session_factory=session_local,
            now=now,
        )

        assert "✅ AI analysis — latest success 10m ago" in text
        assert "Latest failure" not in text
        assert "Failure detail" not in text
        assert "APIConnectionError" not in text
    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error_message", "expected_detail", "rejected_text"),
    [
        (
            "APIConnectionError - connection failed",
            "Reason: APIConnectionError - connection failed",
            None,
        ),
        (
            "{'error': {'message': 'raw provider body', 'type': 'invalid_request'}}",
            "Reason: provider response redacted",
            "raw provider body",
        ),
        (
            "Authorization: Bearer secret-token",
            "Reason: internal error detail redacted",
            "secret-token",
        ),
        (
            "DATABASE_URL=postgresql://ccwbot:secret@example/db",
            "Reason: internal error detail redacted",
            "postgresql://",
        ),
        (
            "Traceback (most recent call last):\n  File \"bot.py\", line 1\nRuntimeError: bad",
            "Reason: internal error detail redacted",
            "bot.py",
        ),
    ],
)
async def test_system_status_sanitizes_ai_failure_detail(
    error_message,
    expected_detail,
    rejected_text,
):
    now = _now()
    engine, session_local = await build_session_factory()
    try:
        async with session_local() as session:
            session.add(
                _event_analysis(
                    status="llm_error",
                    created_at=now - timedelta(minutes=1),
                    analysis_id="failure_with_detail",
                    error_reason="other_error",
                    error_message=error_message,
                )
            )
            await session.commit()

        text = await build_admin_system_status_text(
            db_enabled=True,
            session_factory=session_local,
            now=now,
        )

        assert expected_detail in text
        if rejected_text:
            assert rejected_text not in text
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_system_status_marks_latest_ai_failure_active():
    now = _now()
    engine, session_local = await build_session_factory()
    try:
        async with session_local() as session:
            session.add(
                _event_analysis(
                    status="invalid_json",
                    created_at=now - timedelta(minutes=1),
                    analysis_id="latest_failure",
                    error_reason="invalid_json",
                )
            )
            await session.commit()

        text = await build_admin_system_status_text(
            db_enabled=True,
            session_factory=session_local,
            now=now,
        )

        assert "⚠️ AI analysis — latest invalid_json" in text
        assert "Reason: invalid_json" in text
        assert "resolved by newer success" not in text
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_system_status_rate_limit_active_backoff(monkeypatch):
    now = _now()
    engine, session_local = await build_session_factory()
    limited_until = now + timedelta(minutes=5)
    try:
        monkeypatch.setattr(
            system_status,
            "get_active_llm_rate_limit_backoffs",
            lambda **kwargs: (
                {
                    "provider": "groq",
                    "model": "event-model",
                    "limited_until": limited_until,
                    "call_types": ("event_analysis",),
                },
            ),
        )

        text = await build_admin_system_status_text(
            db_enabled=True,
            session_factory=session_local,
            now=now,
        )

        assert "⚠️ LLM rate limit — Event Analysis backoff active until 17:00 UTC" in text
        assert "Event Analysis: groq backoff active until 2026-06-15 17:00 UTC" in text
    finally:
        reset_llm_rate_limit_backoffs()
        await engine.dispose()


@pytest.mark.asyncio
async def test_system_status_attributes_shared_model_backoff_to_triggering_call_type(monkeypatch):
    now = _now()
    engine, session_local = await build_session_factory()
    limited_until = now + timedelta(minutes=5)
    try:
        monkeypatch.setattr(
            system_status,
            "get_active_llm_rate_limit_backoffs",
            lambda **kwargs: (
                {
                    "provider": "mistral",
                    "model": "shared-model",
                    "limited_until": limited_until,
                    "call_types": ("daily_report",),
                },
            ),
        )

        text = await build_admin_system_status_text(
            db_enabled=True,
            session_factory=session_local,
            now=now,
        )

        assert "Daily report backoff active until 17:00 UTC" in text
        assert "Daily report: mistral backoff active" in text
        assert "Market Heartbeat backoff" not in text
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_system_status_rate_limit_recent_telemetry_without_backoff():
    now = _now()
    engine, session_local = await build_session_factory()
    try:
        async with session_local() as session:
            session.add(
                LlmUsageLog(
                    provider="groq",
                    model="event-model",
                    call_type="event_analysis",
                    status="rate_limit",
                    retry_after="10",
                    error_reason="rate_limit",
                    created_at=now - timedelta(minutes=30),
                )
            )
            await session.commit()

        text = await build_admin_system_status_text(
            db_enabled=True,
            session_factory=session_local,
            now=now,
        )

        assert (
            "⚠️ LLM rate limit — Event Analysis recent limit, retry_after 10"
        ) in text
        assert (
            "Event Analysis: recent groq rate-limit at 2026-06-15 16:25 UTC, retry_after 10"
        ) in text
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_system_status_news_cache_stale_and_missing():
    now = _now()
    engine, session_local = await build_session_factory()
    try:
        text = await build_admin_system_status_text(
            db_enabled=True,
            session_factory=session_local,
            now=now,
        )
        assert "⚠️ News — no cache telemetry" in text

        async with session_local() as session:
            session.add(
                NewsItem(
                    news_key="news-old",
                    title="Old news",
                    url="https://example.com/old",
                    fetched_at=now - timedelta(days=2),
                    llm_status="failed",
                    updated_at=now - timedelta(days=2),
                )
            )
            await session.commit()

        text = await build_admin_system_status_text(
            db_enabled=True,
            session_factory=session_local,
            now=now,
        )
        assert "⚠️ News — stale or empty" in text
        assert "Usable items in 24h: 0" in text
        assert "News intelligence" not in text
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_system_status_news_fresh_without_enrichment_stays_ok():
    now = _now()
    engine, session_local = await build_session_factory()
    try:
        async with session_local() as session:
            session.add(
                NewsItem(
                    news_key="news-fresh",
                    title="Fresh news",
                    url="https://example.com/fresh",
                    fetched_at=now - timedelta(minutes=20),
                    llm_status=None,
                    updated_at=now - timedelta(minutes=20),
                )
            )
            await session.commit()

        text = await build_admin_system_status_text(
            db_enabled=True,
            session_factory=session_local,
            now=now,
        )

        assert "✅ News — 1 usable items in 24h" in text
        assert "News — stale or empty" not in text
        assert "Latest news cache" not in text
        assert "Recent usable news items" not in text
        assert "News intelligence" not in text
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_system_status_delivery_counts():
    now = _now()
    engine, session_local = await build_session_factory()
    try:
        async with session_local() as session:
            await _seed_healthy_status_dependencies(session, now)
            session.add_all(
                [
                    User(
                        telegram_user_id=200,
                        telegram_chat_id=200,
                        bot_blocked=True,
                        blocked_at=now - timedelta(hours=2),
                    ),
                    User(
                        telegram_user_id=201,
                        telegram_chat_id=201,
                        bot_blocked=True,
                        blocked_at=now - timedelta(hours=1),
                    ),
                    Alert(
                        symbol="BTC",
                        alert_type="event_alert",
                        message="safe",
                        sent_to_chat_id=100,
                        status="sent",
                        created_at=now - timedelta(hours=1),
                    ),
                    Alert(
                        symbol="BTC",
                        alert_type="event_alert",
                        message="safe",
                        sent_to_chat_id=101,
                        status="retry_pending",
                        created_at=now - timedelta(hours=1),
                    ),
                ]
            )
            await session.commit()

        text = await build_admin_system_status_text(
            db_enabled=True,
            session_factory=session_local,
            now=now,
        )

        assert "⚠️ Telegram delivery — retry/pending deliveries" in text
        assert "Blocked users: 2" in text
        assert "retry_pending 1" not in text
        assert "blocked_users" not in text
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_system_status_delivery_blocked_only_final_failures_are_not_system_failure():
    now = _now()
    engine, session_local = await build_session_factory()
    try:
        async with session_local() as session:
            await _seed_healthy_status_dependencies(session, now)
            session.add_all(
                [
                    User(
                        telegram_user_id=200,
                        telegram_chat_id=200,
                        bot_blocked=True,
                        blocked_at=now - timedelta(hours=2),
                    ),
                    User(
                        telegram_user_id=201,
                        telegram_chat_id=201,
                        bot_blocked=True,
                        blocked_at=now - timedelta(hours=1),
                    ),
                    _final_failed_alert(
                        sent_to_chat_id=200,
                        created_at=now - timedelta(hours=1),
                        error_message="Forbidden: bot was blocked by the user 200",
                    ),
                    _final_failed_alert(
                        sent_to_chat_id=201,
                        created_at=now - timedelta(minutes=30),
                        last_error="Bad Request: chat is unavailable for chat 201",
                    ),
                ]
            )
            await session.commit()

        text = await build_admin_system_status_text(
            db_enabled=True,
            session_factory=session_local,
            now=now,
        )

        assert "Overall: ❌ Problems detected" not in text
        assert "❌ Telegram delivery" not in text
        assert "✅ Telegram delivery — no system delivery issue" in text
        assert "Blocked-user failures: 2 in 24h" in text
        assert "Blocked users: 2" in text
        assert "bot was blocked by the user" not in text
        assert "chat is unavailable" not in text
        assert "200" not in text
        assert "201" not in text
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_system_status_delivery_real_final_failures_fail_without_raw_details():
    now = _now()
    engine, session_local = await build_session_factory()
    try:
        async with session_local() as session:
            session.add_all(
                [
                    _final_failed_alert(
                        sent_to_chat_id=301,
                        created_at=now - timedelta(hours=1),
                        error_message="Timed out while sending Telegram message to chat 301",
                    ),
                    _final_failed_alert(
                        sent_to_chat_id=302,
                        created_at=now - timedelta(minutes=30),
                        last_error="Bad Request: can't parse entities in message for 302",
                    ),
                ]
            )
            await session.commit()

        text = await build_admin_system_status_text(
            db_enabled=True,
            session_factory=session_local,
            now=now,
        )

        assert "Overall: ❌ Problems detected" in text
        assert "❌ Telegram delivery — final_failed 2 in 24h" in text
        assert "Network/timeouts: 1" in text
        assert "Bad request/message format: 1" in text
        assert "Timed out while sending Telegram message" not in text
        assert "can't parse entities" not in text
        assert "301" not in text
        assert "302" not in text
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_system_status_delivery_mixed_final_failures_show_real_and_blocked_counts():
    now = _now()
    engine, session_local = await build_session_factory()
    try:
        async with session_local() as session:
            session.add_all(
                [
                    _final_failed_alert(
                        sent_to_chat_id=401,
                        created_at=now - timedelta(hours=2),
                        error_message="Forbidden: user is deactivated 401",
                    ),
                    _final_failed_alert(
                        sent_to_chat_id=402,
                        created_at=now - timedelta(hours=1),
                        error_message="Telegram gateway returned unknown error for 402",
                    ),
                    _final_failed_alert(
                        sent_to_chat_id=403,
                        created_at=now - timedelta(minutes=30),
                        last_error="Timed out while sending Telegram message to 403",
                    ),
                ]
            )
            await session.commit()

        text = await build_admin_system_status_text(
            db_enabled=True,
            session_factory=session_local,
            now=now,
        )

        assert "❌ Telegram delivery — final_failed 3 in 24h" in text
        assert "Real delivery failures: 2" in text
        assert "Blocked-user failures: 1" in text
        assert "Network/timeouts: 1" in text
        assert "Other delivery failures: 1" in text
        assert "user is deactivated" not in text
        assert "unknown error" not in text
        assert "Timed out while sending Telegram message" not in text
        assert "401" not in text
        assert "402" not in text
        assert "403" not in text
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_system_status_delivery_ok_shows_blocked_users_info():
    now = _now()
    engine, session_local = await build_session_factory()
    try:
        async with session_local() as session:
            session.add_all(
                [
                    User(
                        telegram_user_id=200,
                        telegram_chat_id=200,
                        bot_blocked=True,
                        blocked_at=now - timedelta(hours=2),
                    ),
                    User(
                        telegram_user_id=201,
                        telegram_chat_id=201,
                        bot_blocked=True,
                        blocked_at=now - timedelta(hours=1),
                    ),
                    Alert(
                        symbol="BTC",
                        alert_type="event_alert",
                        message="safe",
                        sent_to_chat_id=100,
                        status="sent",
                        created_at=now - timedelta(hours=1),
                    ),
                    Alert(
                        symbol="BTC",
                        alert_type="event_alert",
                        message="safe",
                        sent_to_chat_id=101,
                        status="sent",
                        created_at=now - timedelta(hours=1),
                    ),
                ]
            )
            await session.commit()

        text = await build_admin_system_status_text(
            db_enabled=True,
            session_factory=session_local,
            now=now,
        )

        assert "✅ Telegram delivery — sent 2 in 24h" in text
        assert "Blocked users: 2" in text
        assert "blocked_users" not in text
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_system_status_delivery_success_with_blocked_final_failures_stays_non_fail():
    now = _now()
    engine, session_local = await build_session_factory()
    try:
        async with session_local() as session:
            session.add_all(
                [
                    User(
                        telegram_user_id=501,
                        telegram_chat_id=501,
                        bot_blocked=True,
                        blocked_at=now - timedelta(hours=1),
                    ),
                    Alert(
                        symbol="BTC",
                        alert_type="event_alert",
                        message="safe",
                        sent_to_chat_id=100,
                        status="sent",
                        created_at=now - timedelta(minutes=20),
                    ),
                    _final_failed_alert(
                        sent_to_chat_id=501,
                        created_at=now - timedelta(minutes=10),
                        error_message="Forbidden: bot was blocked by the user",
                    ),
                ]
            )
            await session.commit()

        text = await build_admin_system_status_text(
            db_enabled=True,
            session_factory=session_local,
            now=now,
        )

        assert "❌ Telegram delivery" not in text
        assert "✅ Telegram delivery — no system delivery issue" in text
        assert "Blocked-user failures: 1 in 24h" in text
        assert "Blocked users: 1" in text
        assert "bot was blocked by the user" not in text
        assert "501" not in text
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_system_status_delivery_no_rows_is_compact_warning():
    now = _now()
    engine, session_local = await build_session_factory()
    try:
        text = await build_admin_system_status_text(
            db_enabled=True,
            session_factory=session_local,
            now=now,
        )

        assert "⚠️ Telegram delivery — no delivery rows in 24h" in text
        assert "Blocked users:" not in text
        assert "blocked_users" not in text
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_system_status_shows_per_call_type_provider_llm_breakdown():
    now = _now()
    engine, session_local = await build_session_factory()
    try:
        async with session_local() as session:
            for status in (
                "success",
                "success",
                "rate_limit",
                "skipped_due_to_rate_limit",
                "skipped_due_to_circuit_breaker",
                "invalid_json",
                "timeout",
            ):
                session.add(
                    LlmUsageLog(
                        provider="groq",
                        model="event-model",
                        call_type="event_analysis",
                        status=status,
                        created_at=now - timedelta(minutes=10),
                    )
                )
            session.add(
                LlmUsageLog(
                    provider="cerebras",
                    model="cerebras-model",
                    call_type="market_heartbeat",
                    status="success",
                    created_at=now - timedelta(minutes=8),
                )
            )
            # Stale row (older than 24h) must be excluded from the breakdown.
            session.add(
                LlmUsageLog(
                    provider="mistral",
                    model="mistral-model",
                    call_type="event_analysis",
                    status="timeout",
                    created_at=now - timedelta(hours=30),
                )
            )
            await session.commit()

        text = await build_admin_system_status_text(
            db_enabled=True,
            session_factory=session_local,
            now=now,
        )

        assert (
            "Event Analysis / groq: 7 attempts (2 success, 1 rate-limit, 1 backoff, "
            "1 circuit, 1 schema-invalid, 1 provider failure) in 24h"
        ) in text
        assert (
            "Market Heartbeat / cerebras: 1 attempt (1 success, 0 rate-limit, "
            "0 backoff, 0 circuit, 0 schema-invalid, 0 provider failure) in 24h"
        ) in text
        # Provider with only stale (>24h) usage is not surfaced.
        assert "/ mistral:" not in text
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_system_status_bounds_provider_breakdown_for_telegram_card():
    now = _now()
    engine, session_local = await build_session_factory()
    try:
        async with session_local() as session:
            await _seed_healthy_status_dependencies(session, now)
            for index in range(28):
                session.add(
                    LlmUsageLog(
                        provider=f"provider-{index}",
                        model=f"model-{index}",
                        call_type=f"call-type-{index}",
                        status="timeout",
                        created_at=now - timedelta(minutes=1),
                    )
                )
            await session.commit()

        text = await build_admin_system_status_text(
            db_enabled=True,
            session_factory=session_local,
            now=now,
        )

        assert "additional call-type/provider rows omitted" in text
        assert len(text) < 4096
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_healthy_event_analysis_stays_healthy_when_heartbeat_is_rate_limited():
    now = _now()
    engine, session_local = await build_session_factory()
    try:
        async with session_local() as session:
            await _seed_healthy_status_dependencies(session, now)
            session.add(
                LlmUsageLog(
                    provider="groq",
                    model="heartbeat-model",
                    call_type="market_heartbeat",
                    status="rate_limit",
                    error_reason="rate_limit",
                    created_at=now - timedelta(minutes=2),
                )
            )
            await session.commit()

        text = await build_admin_system_status_text(
            db_enabled=True,
            session_factory=session_local,
            now=now,
        )

        assert "✅ AI analysis — latest success 5m ago" in text
        assert "⚠️ AI analysis" not in text
        assert "⚠️ LLM rate limit — Market Heartbeat recent limit" in text
        assert "Market Heartbeat / groq:" in text
        assert "Event Analysis / groq:" in text
    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("age_seconds", "expected_market_status"),
    [
        (3599, "✅ Market data — BTC, ETH, GRAM, SOL fresh"),
        (3600, "✅ Market data — BTC, ETH, GRAM, SOL fresh"),
        (3601, "⚠️ Market data — stale/missing symbols"),
    ],
)
async def test_market_freshness_runtime_grace_boundary(age_seconds, expected_market_status):
    now = _now()
    engine, session_local = await build_session_factory()
    try:
        async with session_local() as session:
            for index, symbol in enumerate(SUPPORTED_SYMBOLS):
                session.add(
                    PriceState(
                        symbol=symbol.upper(),
                        last_price=1000.0 + index,
                        last_24h_change=1.0,
                        last_checked_at=now - timedelta(seconds=age_seconds),
                    )
                )
            await session.commit()

        async with session_local() as session:
            health = await system_status._market_data_health(
                session,
                interval_seconds=1800,
                now=now,
            )
        assert f"{system_status._STATUS_ICON[health.status]} Market data — {health.summary}" == (
            expected_market_status
        )
    finally:
        await engine.dispose()
