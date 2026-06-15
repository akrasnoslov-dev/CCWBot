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

        assert "Overall: OK" in text
        assert "CoinGecko status: OK" not in text
        assert "RSS/news status: OK" not in text
        assert "Rate limit status: no active rate limit recorded" not in text
        assert "GRAM: OK" in text
        assert "CoinGecko id the-open-network" in text
        assert "Groq event analysis: OK" in text
        assert "Telegram alerts: OK" in text
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

    assert "Overall: WARN" in text
    assert "Database: WARN - database disabled; using local JSON fallback" in text
    assert "CoinGecko / price data: UNKNOWN" in text
    assert "Groq event analysis: UNKNOWN" in text


@pytest.mark.asyncio
async def test_system_status_shows_missing_gram_price_state():
    now = _now()
    engine, session_local = await build_session_factory()
    try:
        async with session_local() as session:
            await _seed_fresh_prices(session, now, skip={"ton"})
            await session.commit()

        text = await build_admin_system_status_text(
            db_enabled=True,
            session_factory=session_local,
            now=now,
        )

        assert "CoinGecko / price data: WARN" in text
        assert "GRAM: FAIL - missing price_state; expected CoinGecko id the-open-network" in text
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

        assert "Groq event analysis: OK" in text
        assert (
            "Latest failure: other_error at 2026-06-14 16:55 UTC "
            "- resolved by newer success"
        ) in text
        assert "Failure detail: APIConnectionError - connection failed" in text
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

        assert "Groq event analysis: WARN - latest attempt invalid_json" in text
        assert "Latest failure: invalid_json at 2026-06-15 16:54 UTC" in text
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
            "get_llm_rate_limit_backoff",
            lambda **kwargs: limited_until if kwargs["model"] == "event-model" else None,
        )
        monkeypatch.setattr(system_status, "GROQ_EVENT_ANALYSIS_MODEL", "event-model")

        text = await build_admin_system_status_text(
            db_enabled=True,
            session_factory=session_local,
            now=now,
        )

        assert (
            "Groq rate limit: WARN - event-analysis event-model limited until "
            "2026-06-15 17:00 UTC"
        ) in text
    finally:
        reset_llm_rate_limit_backoffs()
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
            "Groq rate limit: WARN - recent rate_limit at 2026-06-15 16:25 UTC, "
            "retry_after 10"
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
        assert "RSS/news: UNKNOWN - no news cache telemetry" in text

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
        assert "RSS/news: WARN" in text
        assert "Recent usable news items: 0 in last 24h" in text
        assert "News intelligence: WARN - latest failed" in text
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_system_status_delivery_counts():
    now = _now()
    engine, session_local = await build_session_factory()
    try:
        async with session_local() as session:
            session.add_all(
                [
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

        assert "Telegram alerts: WARN" in text
        assert "Last 24h: sent 1, pending 0, retry_pending 1, failed 0, final_failed 0" in text
    finally:
        await engine.dispose()
