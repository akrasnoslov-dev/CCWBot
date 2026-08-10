"""Admin-only system status rendering from persisted runtime telemetry."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from enum import StrEnum

from sqlalchemy import case, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.database import (
    Alert,
    AppSettings,
    EventAiAnalysis,
    LlmUsageLog,
    NewsItem,
    PriceState,
    User,
)
from bot.domain.supported_coins import SUPPORTED_COINS, SUPPORTED_SYMBOLS, display_symbol
from bot.services.llm.telemetry import get_active_llm_rate_limit_backoffs
from bot.settings import DEFAULT_AUTOMATIC_CHECK_INTERVAL_SECONDS
from bot.storage import load_state
from bot.telegram_errors import is_bot_blocked_error


class ComponentStatus(StrEnum):
    OK = "OK"
    WARN = "WARN"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


_STATUS_RANK = {
    ComponentStatus.OK: 0,
    ComponentStatus.UNKNOWN: 1,
    ComponentStatus.WARN: 2,
    ComponentStatus.FAIL: 3,
}
MAX_LLM_PROVIDER_BREAKDOWN_ROWS = 8
_SECRET_DETAIL_RE = re.compile(
    r"(?i)\b("
    r"api[_ -]?key|authorization|auth[_ -]?header|bearer|token|"
    r"database[_ -]?url|db[_ -]?url|connection[_ -]?string|"
    r"postgres(?:ql)?://|asyncpg://"
    r")\b"
)
_STACK_DETAIL_RE = re.compile(
    r"(?i)(traceback|stack trace|^\s*file\s+\".*?\",\s+line\s+\d+|\n\s*at\s+\S+)"
)
_PROVIDER_PAYLOAD_RE = re.compile(
    r"(?i)\b("
    r"response body|response headers|request headers|raw response|error response|"
    r"status_code|x-ratelimit|cf-ray|openai|groq"
    r")\b"
)

_NETWORK_DELIVERY_ERROR_RE = re.compile(
    r"(?i)\b(timeout|timed out|network|connection|connect|temporary|unavailable)\b"
)
_BAD_REQUEST_DELIVERY_ERROR_RE = re.compile(
    r"(?i)\b(bad request|can't parse|cannot parse|message.*invalid|message.*too long|"
    r"entity|entities|markup)\b"
)
_CHAT_UNAVAILABLE_DELIVERY_ERROR_RE = re.compile(
    r"(?i)\b(chat unavailable|chat is unavailable|chat.*unavailable)\b"
)


@dataclass(frozen=True)
class ComponentHealth:
    name: str
    status: ComponentStatus
    detail: str
    rows: tuple[str, ...] = field(default_factory=tuple)
    summary: str | None = None
    problem_rows: tuple[str, ...] = field(default_factory=tuple)
    info_rows: tuple[str, ...] = field(default_factory=tuple)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _format_utc(value: datetime | None) -> str:
    value = _as_utc(value)
    if value is None:
        return "not recorded"
    return value.strftime("%Y-%m-%d %H:%M UTC")


def _age_label(value: datetime | None, *, now: datetime) -> str:
    value = _as_utc(value)
    if value is None:
        return "unknown age"
    seconds = max(int((now - value).total_seconds()), 0)
    if seconds < 120:
        return "just now"
    minutes = seconds // 60
    if minutes < 120:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 72:
        return f"{hours}h ago"
    days = hours // 24
    return f"{days}d ago"


def _format_price(value: float | None) -> str:
    if value is None:
        return "price unavailable"
    return f"${value:,.2f}"


def _safe_detail(value: str | None, *, max_chars: int = 120) -> str | None:
    if not value:
        return None
    raw_value = str(value).strip()
    text_value = " ".join(raw_value.split())
    if _SECRET_DETAIL_RE.search(raw_value):
        return "internal error detail redacted"
    if _STACK_DETAIL_RE.search(raw_value):
        return "internal error detail redacted"
    if "\n" in raw_value or "\r" in raw_value:
        return "internal error detail redacted"
    if _looks_like_payload(raw_value):
        return "provider response redacted"
    if _PROVIDER_PAYLOAD_RE.search(raw_value):
        return "provider response redacted"
    if len(text_value) > max_chars * 2:
        return "internal error detail redacted"
    return text_value[:max_chars]


def _looks_like_payload(value: str) -> bool:
    stripped = value.strip()
    if stripped.startswith(("{", "[")) or stripped.endswith(("}", "]")):
        return True
    return any(marker in stripped for marker in ("{", "}", "[", "]"))


def _delivery_failure_category(last_error: str | None, error_message: str | None) -> str:
    text = " ".join(part for part in (last_error, error_message) if part)
    if _NETWORK_DELIVERY_ERROR_RE.search(text):
        return "Network/timeouts"
    if _BAD_REQUEST_DELIVERY_ERROR_RE.search(text):
        return "Bad request/message format"
    return "Other delivery failures"


def _is_expected_blocked_delivery_failure(
    last_error: str | None,
    error_message: str | None,
) -> bool:
    if is_bot_blocked_error(last_error) or is_bot_blocked_error(error_message):
        return True
    text = " ".join(part for part in (last_error, error_message) if part)
    return bool(_CHAT_UNAVAILABLE_DELIVERY_ERROR_RE.search(text))


def _worst_status(statuses: list[ComponentStatus]) -> ComponentStatus:
    if not statuses:
        return ComponentStatus.UNKNOWN
    return max(statuses, key=lambda status: _STATUS_RANK[status])


async def build_admin_system_status_text(
    *,
    db_enabled: bool,
    session_factory,
    state_loader: Callable[[], dict] = load_state,
    now: datetime | None = None,
) -> str:
    """Return concise admin-safe status text without live provider probes."""
    now = _as_utc(now) or _utc_now()

    if not db_enabled:
        state = state_loader()
        last_checked = state.get("last_checked_at")
        market_problem_rows = (
            (f"Local BTC state last checked: {last_checked}",) if last_checked else ()
        )
        sections = [
            ComponentHealth(
                "Database",
                ComponentStatus.WARN,
                "database disabled; using local JSON fallback",
                summary="local JSON fallback",
            ),
            ComponentHealth(
                "Market data",
                ComponentStatus.UNKNOWN,
                "PostgreSQL price telemetry unavailable",
                summary="no price telemetry",
                problem_rows=market_problem_rows,
            ),
            ComponentHealth(
                "AI analysis",
                ComponentStatus.UNKNOWN,
                "PostgreSQL AI telemetry unavailable",
                summary="no analysis telemetry",
            ),
            ComponentHealth(
                "LLM rate limit",
                ComponentStatus.UNKNOWN,
                "PostgreSQL usage telemetry unavailable",
                summary="no usage telemetry",
            ),
            ComponentHealth(
                "News",
                ComponentStatus.UNKNOWN,
                "PostgreSQL news telemetry unavailable",
                summary="no cache telemetry",
            ),
            ComponentHealth(
                "Telegram delivery",
                ComponentStatus.UNKNOWN,
                "PostgreSQL delivery telemetry unavailable",
                summary="no delivery telemetry",
            ),
        ]
        return _render_status(now=now, sections=sections)

    if not session_factory:
        sections = [
            ComponentHealth(
                "Database",
                ComponentStatus.FAIL,
                "database enabled but session factory is missing",
                summary="session unavailable",
            )
        ]
        return _render_status(now=now, sections=sections)

    try:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
            interval_seconds = await _get_status_interval_seconds(session)
            price_health = await _market_data_health(
                session,
                interval_seconds=interval_seconds,
                now=now,
            )
            ai_health = await _ai_health(session, now=now)
            rate_limit_health = await _rate_limit_health(session, now=now)
            provider_rows = await _llm_provider_breakdown_rows(session, now=now)
            if provider_rows:
                rate_limit_health = replace(
                    rate_limit_health,
                    info_rows=rate_limit_health.info_rows + provider_rows,
                )
            news_health = await _news_health(session, now=now)
            delivery_health = await _delivery_health(session, now=now)
    except Exception:
        return _render_status(
            now=now,
            sections=[
                ComponentHealth(
                    "Database",
                    ComponentStatus.FAIL,
                    "query failed",
                    summary="query failed",
                )
            ],
        )

    database_health = ComponentHealth(
        "Database",
        ComponentStatus.OK,
        "PostgreSQL query successful",
        summary="connected",
    )
    return _render_status(
        now=now,
        sections=[
            database_health,
            price_health,
            ai_health,
            rate_limit_health,
            news_health,
            delivery_health,
        ],
    )


async def _get_status_interval_seconds(session: AsyncSession) -> int:
    row = await session.scalar(select(AppSettings).order_by(AppSettings.id.desc()).limit(1))
    if row is None:
        return DEFAULT_AUTOMATIC_CHECK_INTERVAL_SECONDS
    try:
        interval = int(row.automatic_check_interval_seconds)
    except (TypeError, ValueError):
        return DEFAULT_AUTOMATIC_CHECK_INTERVAL_SECONDS
    return interval if interval > 0 else DEFAULT_AUTOMATIC_CHECK_INTERVAL_SECONDS


async def _market_data_health(
    session: AsyncSession,
    *,
    interval_seconds: int,
    now: datetime,
) -> ComponentHealth:
    symbols = [symbol.upper() for symbol in SUPPORTED_SYMBOLS]
    rows = await session.scalars(select(PriceState).where(PriceState.symbol.in_(symbols)))
    states = {row.symbol.upper(): row for row in rows.all()}
    stale_after = timedelta(seconds=max(interval_seconds * 2, interval_seconds + 900))
    details: list[str] = []
    problem_rows: list[str] = []
    fresh_symbols: list[str] = []
    missing_symbols: list[str] = []
    statuses: list[ComponentStatus] = []

    for symbol in SUPPORTED_SYMBOLS:
        row = states.get(symbol.upper())
        display = display_symbol(symbol)
        expected_id = SUPPORTED_COINS[symbol]["coingecko_id"]
        if row is None:
            statuses.append(ComponentStatus.FAIL)
            missing_symbols.append(display)
            details.append(
                f"{display}: FAIL - missing price_state; expected CoinGecko id {expected_id}"
            )
            continue
        checked_at = _as_utc(row.last_checked_at)
        age = now - checked_at if checked_at is not None else None
        if checked_at is None:
            status = ComponentStatus.FAIL
            detail = "last check missing"
            problem_rows.append(f"{display} stale: last check missing")
        elif age is not None and age > stale_after:
            status = ComponentStatus.WARN
            detail = (
                f"stale, last checked {_format_utc(checked_at)} "
                f"({_age_label(checked_at, now=now)})"
            )
            problem_rows.append(f"{display} stale: last check {_age_label(checked_at, now=now)}")
        else:
            status = ComponentStatus.OK
            detail = (
                f"fresh, last checked {_format_utc(checked_at)} "
                f"({_age_label(checked_at, now=now)})"
            )
            fresh_symbols.append(display)
        statuses.append(status)
        details.append(
            f"{display}: {status.value} - {detail}, price {_format_price(row.last_price)}, "
            f"CoinGecko id {expected_id}"
        )

    if missing_symbols:
        problem_rows.append(f"Missing: {', '.join(missing_symbols)}")

    component_status = ComponentStatus.OK
    if all(status == ComponentStatus.FAIL for status in statuses):
        component_status = ComponentStatus.FAIL
    elif any(status in {ComponentStatus.FAIL, ComponentStatus.WARN} for status in statuses):
        component_status = ComponentStatus.WARN

    if component_status == ComponentStatus.OK:
        summary = f"{', '.join(fresh_symbols)} fresh"
    elif component_status == ComponentStatus.FAIL:
        summary = "no fresh price telemetry"
    else:
        summary = "stale/missing symbols"

    return ComponentHealth(
        "Market data",
        component_status,
        "persisted price_state freshness by active symbol",
        tuple(details),
        summary=summary,
        problem_rows=tuple(problem_rows),
    )


async def _ai_health(session: AsyncSession, *, now: datetime) -> ComponentHealth:
    latest = await session.scalar(
        select(EventAiAnalysis)
        .where(EventAiAnalysis.analysis_type == "event_analysis")
        .order_by(EventAiAnalysis.created_at.desc(), EventAiAnalysis.id.desc())
        .limit(1)
    )
    latest_success = await session.scalar(
        select(EventAiAnalysis)
        .where(EventAiAnalysis.analysis_type == "event_analysis")
        .where(EventAiAnalysis.status.in_(["success", "no_alert"]))
        .order_by(EventAiAnalysis.created_at.desc(), EventAiAnalysis.id.desc())
        .limit(1)
    )
    latest_failure = await session.scalar(
        select(EventAiAnalysis)
        .where(EventAiAnalysis.analysis_type == "event_analysis")
        .where(EventAiAnalysis.status.not_in(["success", "no_alert"]))
        .order_by(EventAiAnalysis.created_at.desc(), EventAiAnalysis.id.desc())
        .limit(1)
    )

    if latest is None:
        return ComponentHealth(
            "AI analysis",
            ComponentStatus.UNKNOWN,
            "no event-analysis attempt recorded yet",
            summary="no analysis telemetry",
        )

    if latest.status in {"success", "no_alert"}:
        status = ComponentStatus.OK
        detail = f"latest attempt {latest.status} at {_format_utc(latest.created_at)}"
        summary = f"latest success {_age_label(latest.created_at, now=now)}"
    elif latest.status in {"skipped_due_to_rate_limit", "schema_error", "invalid_json"}:
        status = ComponentStatus.WARN
        detail = f"latest attempt {latest.status} at {_format_utc(latest.created_at)}"
        summary = f"latest {latest.status}"
    else:
        status = ComponentStatus.FAIL
        detail = f"latest attempt {latest.status} at {_format_utc(latest.created_at)}"
        safe_reason = _safe_detail(latest.error_reason or latest.status, max_chars=60)
        summary = f"latest failed: {safe_reason}"

    rows = [f"Latest attempt: {latest.status} at {_format_utc(latest.created_at)}"]
    problem_rows: list[str] = []
    if latest_success is not None:
        rows.append(
            f"Latest success: {latest_success.status} "
            f"at {_format_utc(latest_success.created_at)}"
        )
    if latest_failure is not None:
        reason = latest_failure.error_reason or latest_failure.status
        resolved = (
            latest_success is not None
            and _as_utc(latest_success.created_at) is not None
            and _as_utc(latest_failure.created_at) is not None
            and _as_utc(latest_success.created_at) > _as_utc(latest_failure.created_at)
        )
        suffix = " - resolved by newer success" if resolved else ""
        rows.append(
            f"Latest failure: {reason} at {_format_utc(latest_failure.created_at)}{suffix}"
        )
        safe_detail = _safe_detail(latest_failure.error_message)
        if safe_detail:
            rows.append(f"Failure detail: {safe_detail}")
        if not resolved and latest_failure.id == latest.id:
            problem_reason = _safe_detail(
                latest_failure.error_reason or latest_failure.status,
                max_chars=60,
            )
            if safe_detail:
                problem_reason = safe_detail
            if problem_reason:
                problem_rows.append(f"Reason: {problem_reason}")

    return ComponentHealth(
        "AI analysis",
        status,
        detail,
        tuple(rows),
        summary=summary,
        problem_rows=tuple(problem_rows),
    )


async def _llm_provider_breakdown_rows(
    session: AsyncSession, *, now: datetime
) -> tuple[str, ...]:
    """Compact per-call-type/provider attempt counts over the last 24h.

    These are provider-attempt diagnostics, not final product outcomes. Event Analysis health
    remains authoritative in ``_ai_health`` even when another call type is degraded. Only
    normalized categories are rendered; raw errors and provider payloads never reach Telegram.
    """
    since = now - timedelta(hours=24)
    rate_limit_attempt = or_(
        LlmUsageLog.status == "rate_limit",
        LlmUsageLog.error_reason == "rate_limit",
    )
    backoff_skip = or_(
        LlmUsageLog.status == "skipped_due_to_rate_limit",
        LlmUsageLog.error_reason == "rate_limit_backoff_active",
    )
    circuit_skip = or_(
        LlmUsageLog.status == "skipped_due_to_circuit_breaker",
        LlmUsageLog.error_reason == "provider_circuit_broken",
    )
    schema_invalid = or_(
        LlmUsageLog.status.in_(["invalid_json", "schema_error", "invalid_output"]),
        LlmUsageLog.error_reason.in_(
            ["invalid_json", "schema_validation_failed", "invalid_output"]
        ),
    )
    rows = (
        await session.execute(
            select(
                LlmUsageLog.call_type,
                LlmUsageLog.provider,
                func.count().label("calls"),
                func.sum(case((LlmUsageLog.status == "success", 1), else_=0)).label(
                    "successful"
                ),
                func.sum(case((rate_limit_attempt, 1), else_=0)).label("rate_limited"),
                func.sum(case((backoff_skip, 1), else_=0)).label("backoff_skips"),
                func.sum(case((circuit_skip, 1), else_=0)).label("circuit_skips"),
                func.sum(case((schema_invalid, 1), else_=0)).label("schema_invalid"),
            )
            .where(LlmUsageLog.created_at >= since)
            .group_by(LlmUsageLog.call_type, LlmUsageLog.provider)
            .order_by(LlmUsageLog.call_type, func.count().desc(), LlmUsageLog.provider)
        )
    ).all()
    breakdown: list[str] = []
    for row in rows:
        call_type = _llm_call_type_label(row.call_type)
        provider = _llm_provider_label(row.provider)
        calls = int(row.calls or 0)
        successful = int(row.successful or 0)
        rate_limited = int(row.rate_limited or 0)
        backoff_skips = int(row.backoff_skips or 0)
        circuit_skips = int(row.circuit_skips or 0)
        schema_invalid_count = int(row.schema_invalid or 0)
        provider_failures = max(
            calls
            - successful
            - rate_limited
            - backoff_skips
            - circuit_skips
            - schema_invalid_count,
            0,
        )
        attempt_label = "attempt" if calls == 1 else "attempts"
        breakdown.append(
            f"{call_type} / {provider}: {calls} {attempt_label} "
            f"({successful} success, {rate_limited} rate-limit, "
            f"{backoff_skips} backoff, {circuit_skips} circuit, "
            f"{schema_invalid_count} schema-invalid, {provider_failures} provider failure) in 24h"
        )
    omitted = max(len(breakdown) - MAX_LLM_PROVIDER_BREAKDOWN_ROWS, 0)
    visible = breakdown[:MAX_LLM_PROVIDER_BREAKDOWN_ROWS]
    if omitted:
        visible.append(f"{omitted} additional call-type/provider rows omitted")
    return tuple(visible)


def _llm_call_type_label(value: str | None) -> str:
    return {
        "event_analysis": "Event Analysis",
        "market_heartbeat": "Market Heartbeat",
        "daily_report": "Daily report",
        "weekly_report": "Weekly report",
        "news_intelligence": "News intelligence",
    }.get(str(value or "").strip().lower(), "Other LLM")


def _llm_provider_label(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    return {
        "groq": "groq",
        "cerebras": "cerebras",
        "gemini": "gemini",
        "mistral": "mistral",
    }.get(normalized, "other provider")


async def _rate_limit_health(session: AsyncSession, *, now: datetime) -> ComponentHealth:
    active_backoffs: list[str] = []
    active_call_types: set[str] = set()
    active_until: datetime | None = None
    for backoff in get_active_llm_rate_limit_backoffs(now=now):
        limited_until = backoff["limited_until"]
        if not isinstance(limited_until, datetime):
            continue
        active_until = max(active_until, limited_until) if active_until else limited_until
        provider = _llm_provider_label(str(backoff.get("provider") or ""))
        call_types = backoff.get("call_types") or ("unknown",)
        labels = [_llm_call_type_label(str(call_type)) for call_type in call_types]
        active_call_types.update(labels)
        active_backoffs.append(
            f"{', '.join(labels)}: {provider} backoff active until {_format_utc(limited_until)}"
        )
    if active_backoffs:
        summary = (
            f"{next(iter(active_call_types))} backoff active until "
            f"{_format_utc(active_until)[11:16]} UTC"
            if len(active_call_types) == 1
            else (
                f"{len(active_call_types)} call types in backoff until "
                f"{_format_utc(active_until)[11:16]} UTC"
            )
        )
        return ComponentHealth(
            "LLM rate limit",
            ComponentStatus.WARN,
            active_backoffs[0],
            summary=summary,
            info_rows=tuple(active_backoffs),
        )

    # Provider-agnostic: reflect the whole fallback chain (Groq + Cerebras/Gemini/Mistral),
    # not just Groq. Per-provider breakdown lives in the ops-agent llm_usage_summary collector.
    latest_usage = await session.scalar(
        select(LlmUsageLog)
        .order_by(LlmUsageLog.created_at.desc(), LlmUsageLog.id.desc())
        .limit(1)
    )
    since = now - timedelta(hours=24)
    latest_rate_limit = await session.scalar(
        select(LlmUsageLog)
        .where(LlmUsageLog.created_at >= since)
        .where(
            or_(
                LlmUsageLog.status.in_(["rate_limit", "skipped_due_to_rate_limit"]),
                LlmUsageLog.error_reason.in_(["rate_limit", "rate_limit_backoff_active"]),
            )
        )
        .order_by(LlmUsageLog.created_at.desc(), LlmUsageLog.id.desc())
        .limit(1)
    )
    if latest_rate_limit is not None:
        call_type = _llm_call_type_label(latest_rate_limit.call_type)
        provider = _llm_provider_label(latest_rate_limit.provider)
        category = (
            "backoff"
            if latest_rate_limit.status == "skipped_due_to_rate_limit"
            or latest_rate_limit.error_reason == "rate_limit_backoff_active"
            else "rate-limit"
        )
        safe_retry_after = _safe_detail(latest_rate_limit.retry_after, max_chars=24)
        retry_after = (
            f", retry_after {safe_retry_after}" if safe_retry_after else ""
        )
        detail = (
            f"{call_type}: recent {provider} {category} "
            f"at {_format_utc(latest_rate_limit.created_at)}{retry_after}"
        )
        return ComponentHealth(
            "LLM rate limit",
            ComponentStatus.WARN,
            detail,
            summary=f"{call_type} recent limit{retry_after}",
            info_rows=(detail,),
        )
    if latest_usage is None:
        return ComponentHealth(
            "LLM rate limit",
            ComponentStatus.UNKNOWN,
            "no LLM usage telemetry",
            summary="no usage telemetry",
        )
    if latest_usage.status == "success":
        return ComponentHealth(
            "LLM rate limit",
            ComponentStatus.OK,
            f"latest usage success at {_format_utc(latest_usage.created_at)}",
            summary="no active limit",
        )
    return ComponentHealth(
        "LLM rate limit",
        ComponentStatus.UNKNOWN,
        f"latest usage status {latest_usage.status} at {_format_utc(latest_usage.created_at)}",
        summary="no usage telemetry",
    )


async def _news_health(session: AsyncSession, *, now: datetime) -> ComponentHealth:
    latest = await session.scalar(
        select(NewsItem).order_by(NewsItem.fetched_at.desc(), NewsItem.id.desc()).limit(1)
    )
    if latest is None:
        return ComponentHealth(
            "News",
            ComponentStatus.UNKNOWN,
            "no news cache telemetry",
            summary="no cache telemetry",
        )

    since = now - timedelta(hours=24)
    usable_count = int(
        await session.scalar(
            select(func.count())
            .select_from(NewsItem)
            .where(NewsItem.fetched_at >= since)
            .where(NewsItem.is_noise.is_(False))
            .where(NewsItem.is_duplicate.is_(False))
        )
        or 0
    )
    latest_intel = await session.scalar(
        select(NewsItem)
        .where(
            NewsItem.llm_status.in_(
                ["success", "failed", "skipped_noise", "skipped_duplicate", "skipped_budget"]
            )
        )
        .order_by(NewsItem.updated_at.desc(), NewsItem.id.desc())
        .limit(1)
    )
    fresh = (_as_utc(latest.fetched_at) or now) >= since
    status = ComponentStatus.OK if fresh and usable_count > 0 else ComponentStatus.WARN
    detail = (
        f"latest news cache {_format_utc(latest.fetched_at)}; "
        f"usable items {usable_count} in last 24h"
    )
    rows = [
        f"Latest news cache: {_format_utc(latest.fetched_at)}",
        f"Recent usable news items: {usable_count} in last 24h",
    ]
    if latest_intel is None:
        rows.append("News intelligence: UNKNOWN - no enrichment telemetry")
    elif latest_intel.llm_status == "failed":
        rows.append(
            f"News intelligence: WARN - latest failed "
            f"at {_format_utc(latest_intel.updated_at)}"
        )
        status = ComponentStatus.WARN
    else:
        rows.append(
            f"News intelligence: OK - latest {latest_intel.llm_status} "
            f"at {_format_utc(latest_intel.updated_at)}"
        )
    if fresh and usable_count > 0:
        summary = f"{usable_count} usable items in 24h"
        problem_rows = (
            ("News intelligence: latest failed",)
            if latest_intel is not None and latest_intel.llm_status == "failed"
            else ()
        )
    else:
        summary = "stale or empty"
        problem_rows = (f"Usable items in 24h: {usable_count}",)
    return ComponentHealth(
        "News",
        status,
        detail,
        tuple(rows),
        summary=summary,
        problem_rows=problem_rows,
    )


async def _delivery_health(session: AsyncSession, *, now: datetime) -> ComponentHealth:
    since = now - timedelta(hours=24)
    result = await session.execute(
        select(Alert.status, func.count())
        .where(Alert.created_at >= since)
        .group_by(Alert.status)
    )
    counts = {str(status or "unknown"): int(count) for status, count in result.all()}
    final_failed = int(
        await session.scalar(
            select(func.count())
            .select_from(Alert)
            .where(Alert.final_failed_at.is_not(None))
            .where(Alert.final_failed_at >= since)
        )
        or 0
    )
    final_failure_rows = (
        await session.execute(
            select(Alert.last_error, Alert.error_message)
            .where(Alert.final_failed_at.is_not(None))
            .where(Alert.final_failed_at >= since)
        )
    ).all()
    blocked_final_failed = 0
    real_final_failed = 0
    real_failure_categories: dict[str, int] = {}
    for last_error, error_message in final_failure_rows:
        if _is_expected_blocked_delivery_failure(last_error, error_message):
            blocked_final_failed += 1
            continue
        real_final_failed += 1
        category = _delivery_failure_category(last_error, error_message)
        real_failure_categories[category] = real_failure_categories.get(category, 0) + 1

    blocked_users = int(
        await session.scalar(
            select(func.count()).select_from(User).where(User.bot_blocked.is_(True))
        )
        or 0
    )
    total = sum(counts.values())
    if total == 0 and final_failed == 0:
        if blocked_users > 0:
            return ComponentHealth(
                "Telegram delivery",
                ComponentStatus.WARN,
                f"no delivery rows in last 24h, blocked_users {blocked_users}",
                summary="no delivery rows in 24h",
                info_rows=(f"Blocked users: {blocked_users}",),
            )
        return ComponentHealth(
            "Telegram delivery",
            ComponentStatus.WARN,
            f"no delivery rows in last 24h, blocked_users {blocked_users}",
            summary="no delivery rows in 24h",
        )

    sent = counts.get("sent", 0)
    pending = counts.get("pending", 0)
    retry_pending = counts.get("retry_pending", 0)
    failed = counts.get("failed", 0)
    non_final_failed = max(failed - final_failed, 0)
    if real_final_failed > 0:
        status = ComponentStatus.FAIL
    elif non_final_failed > 0 or pending > 0 or retry_pending > 0:
        status = ComponentStatus.WARN
    elif sent > 0 or blocked_final_failed > 0:
        status = ComponentStatus.OK
    else:
        status = ComponentStatus.UNKNOWN

    detail = (
        f"Last 24h: sent {sent}, pending {pending}, retry_pending {retry_pending}, "
        f"failed {failed}, final_failed {final_failed}, "
        f"blocked_final_failed {blocked_final_failed}, real_final_failed {real_final_failed}, "
        f"blocked_users {blocked_users}"
    )
    info_rows = []
    problem_rows = []
    if real_final_failed > 0 and blocked_final_failed > 0:
        problem_rows.append(f"Real delivery failures: {real_final_failed}")
        info_rows.append(f"Blocked-user failures: {blocked_final_failed}")
    elif blocked_final_failed > 0:
        info_rows.append(f"Blocked-user failures: {blocked_final_failed} in 24h")
    if real_final_failed > 0:
        for category in sorted(real_failure_categories):
            problem_rows.append(f"{category}: {real_failure_categories[category]}")
    if blocked_users > 0:
        info_rows.append(f"Blocked users: {blocked_users}")
    if real_final_failed > 0:
        summary = f"final_failed {final_failed} in 24h"
    elif pending > 0 or retry_pending > 0:
        summary = "retry/pending deliveries"
    elif non_final_failed > 0:
        summary = "failed deliveries"
    elif blocked_final_failed > 0:
        summary = "no system delivery issue"
    elif sent > 0:
        summary = f"sent {sent} in 24h"
    else:
        summary = "no delivery rows in 24h"
    return ComponentHealth(
        "Telegram delivery",
        status,
        detail,
        summary=summary,
        problem_rows=tuple(problem_rows),
        info_rows=tuple(info_rows),
    )


_STATUS_ICON = {
    ComponentStatus.OK: "✅",
    ComponentStatus.WARN: "⚠️",
    ComponentStatus.UNKNOWN: "⚠️",
    ComponentStatus.FAIL: "❌",
}

_OVERALL_LABEL = {
    ComponentStatus.OK: "OK",
    ComponentStatus.UNKNOWN: "Needs attention",
    ComponentStatus.WARN: "Needs attention",
    ComponentStatus.FAIL: "Problems detected",
}


def _render_status(
    *,
    now: datetime,
    sections: list[ComponentHealth],
) -> str:
    overall = _worst_status([section.status for section in sections])
    lines = [
        f"System status — {_format_utc(now)}",
        f"Overall: {_STATUS_ICON[overall]} {_OVERALL_LABEL[overall]}",
        "",
        "✅ Bot — running",
    ]
    for section in sections:
        summary = section.summary or section.detail
        lines.append(f"{_STATUS_ICON[section.status]} {section.name} — {summary}")
        if section.status != ComponentStatus.OK:
            lines.extend(f"   {row}" for row in section.problem_rows)
        lines.extend(f"   {row}" for row in section.info_rows)
    return "\n".join(lines).strip()
