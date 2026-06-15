"""Admin-only system status rendering from persisted runtime telemetry."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import StrEnum

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.database import (
    Alert,
    AppSettings,
    EventAiAnalysis,
    LlmUsageLog,
    NewsItem,
    PriceState,
)
from bot.domain.supported_coins import SUPPORTED_COINS, SUPPORTED_SYMBOLS, display_symbol
from bot.services.ai_agent_groq import (
    GROQ_EVENT_ANALYSIS_MODEL,
    GROQ_MARKET_HEARTBEAT_MODEL,
    get_llm_rate_limit_backoff,
)
from bot.settings import DEFAULT_AUTOMATIC_CHECK_INTERVAL_SECONDS
from bot.storage import load_state


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


@dataclass(frozen=True)
class ComponentHealth:
    name: str
    status: ComponentStatus
    detail: str
    rows: tuple[str, ...] = field(default_factory=tuple)


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
    text_value = " ".join(str(value).split())
    redacted_markers = ("api key", "authorization", "bearer ", "token", "database_url")
    lowered = text_value.lower()
    if any(marker in lowered for marker in redacted_markers):
        return "detail redacted"
    return text_value[:max_chars]


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
    runtime_rows = ["Bot: OK - admin command responded"]

    if not db_enabled:
        state = state_loader()
        last_checked = state.get("last_checked_at")
        runtime_rows.append(
            "Automatic market check: UNKNOWN - PostgreSQL telemetry unavailable"
            + (f"; local BTC state last checked {last_checked}" if last_checked else "")
        )
        sections = [
            ComponentHealth(
                "Database",
                ComponentStatus.WARN,
                "database disabled; using local JSON fallback",
            ),
            ComponentHealth(
                "CoinGecko / price data",
                ComponentStatus.UNKNOWN,
                "PostgreSQL price telemetry unavailable",
            ),
            ComponentHealth(
                "Groq event analysis",
                ComponentStatus.UNKNOWN,
                "PostgreSQL AI telemetry unavailable",
            ),
            ComponentHealth(
                "Groq rate limit",
                ComponentStatus.UNKNOWN,
                "PostgreSQL usage telemetry unavailable",
            ),
            ComponentHealth(
                "RSS/news",
                ComponentStatus.UNKNOWN,
                "PostgreSQL news telemetry unavailable",
            ),
            ComponentHealth(
                "Telegram alerts",
                ComponentStatus.UNKNOWN,
                "PostgreSQL delivery telemetry unavailable",
            ),
        ]
        return _render_status(now=now, runtime_rows=runtime_rows, sections=sections)

    if not session_factory:
        sections = [
            ComponentHealth(
                "Database",
                ComponentStatus.FAIL,
                "database enabled but session factory is missing",
            )
        ]
        runtime_rows.append("Automatic market check: UNKNOWN - database session unavailable")
        return _render_status(now=now, runtime_rows=runtime_rows, sections=sections)

    try:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
            interval_seconds = await _get_status_interval_seconds(session)
            price_health = await _market_data_health(
                session,
                interval_seconds=interval_seconds,
                now=now,
            )
            ai_health = await _ai_health(session)
            rate_limit_health = await _rate_limit_health(session, now=now)
            news_health = await _news_health(session, now=now)
            delivery_health = await _delivery_health(session, now=now)
    except Exception:
        runtime_rows.append("Automatic market check: UNKNOWN - database query failed")
        return _render_status(
            now=now,
            runtime_rows=runtime_rows,
            sections=[
                ComponentHealth(
                    "Database",
                    ComponentStatus.FAIL,
                    "query failed",
                )
            ],
        )

    database_health = ComponentHealth("Database", ComponentStatus.OK, "PostgreSQL query successful")
    automatic_detail = _automatic_market_check_detail(price_health)
    runtime_rows.append(f"Automatic market check: {automatic_detail}")
    return _render_status(
        now=now,
        runtime_rows=runtime_rows,
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
    statuses: list[ComponentStatus] = []

    for symbol in SUPPORTED_SYMBOLS:
        row = states.get(symbol.upper())
        display = display_symbol(symbol)
        expected_id = SUPPORTED_COINS[symbol]["coingecko_id"]
        if row is None:
            statuses.append(ComponentStatus.FAIL)
            details.append(
                f"{display}: FAIL - missing price_state; expected CoinGecko id {expected_id}"
            )
            continue
        checked_at = _as_utc(row.last_checked_at)
        age = now - checked_at if checked_at is not None else None
        if checked_at is None:
            status = ComponentStatus.FAIL
            detail = "last check missing"
        elif age is not None and age > stale_after:
            status = ComponentStatus.WARN
            detail = (
                f"stale, last checked {_format_utc(checked_at)} "
                f"({_age_label(checked_at, now=now)})"
            )
        else:
            status = ComponentStatus.OK
            detail = (
                f"fresh, last checked {_format_utc(checked_at)} "
                f"({_age_label(checked_at, now=now)})"
            )
        statuses.append(status)
        details.append(
            f"{display}: {status.value} - {detail}, price {_format_price(row.last_price)}, "
            f"CoinGecko id {expected_id}"
        )

    component_status = ComponentStatus.OK
    if all(status == ComponentStatus.FAIL for status in statuses):
        component_status = ComponentStatus.FAIL
    elif any(status in {ComponentStatus.FAIL, ComponentStatus.WARN} for status in statuses):
        component_status = ComponentStatus.WARN

    return ComponentHealth(
        "CoinGecko / price data",
        component_status,
        "persisted price_state freshness by active symbol",
        tuple(details),
    )


def _automatic_market_check_detail(price_health: ComponentHealth) -> str:
    btc_row = next((row for row in price_health.rows if row.startswith("BTC:")), None)
    if btc_row and btc_row.startswith("BTC: OK"):
        detail = btc_row.split(" - ", maxsplit=1)[1].split(", price", maxsplit=1)[0]
        return f"OK - last BTC check {detail}"
    if btc_row:
        status = "FAIL" if "FAIL" in btc_row else "WARN"
        detail = btc_row.split(" - ", maxsplit=1)[1]
        return f"{status} - BTC {detail}"
    return "UNKNOWN - no BTC price telemetry"


async def _ai_health(session: AsyncSession) -> ComponentHealth:
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
            "Groq event analysis",
            ComponentStatus.UNKNOWN,
            "no event-analysis attempt recorded yet",
        )

    if latest.status in {"success", "no_alert"}:
        status = ComponentStatus.OK
        detail = f"latest attempt {latest.status} at {_format_utc(latest.created_at)}"
    elif latest.status in {"skipped_due_to_rate_limit", "schema_error", "invalid_json"}:
        status = ComponentStatus.WARN
        detail = f"latest attempt {latest.status} at {_format_utc(latest.created_at)}"
    else:
        status = ComponentStatus.FAIL
        detail = f"latest attempt {latest.status} at {_format_utc(latest.created_at)}"

    rows = [f"Latest attempt: {latest.status} at {_format_utc(latest.created_at)}"]
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

    return ComponentHealth("Groq event analysis", status, detail, tuple(rows))


async def _rate_limit_health(session: AsyncSession, *, now: datetime) -> ComponentHealth:
    active_backoffs = []
    for label, model in (
        ("event-analysis", GROQ_EVENT_ANALYSIS_MODEL),
        ("heartbeat", GROQ_MARKET_HEARTBEAT_MODEL),
    ):
        limited_until = get_llm_rate_limit_backoff(model=model, now=now)
        if limited_until is not None:
            active_backoffs.append(f"{label} {model} limited until {_format_utc(limited_until)}")
    if active_backoffs:
        return ComponentHealth(
            "Groq rate limit",
            ComponentStatus.WARN,
            active_backoffs[0],
            tuple(active_backoffs),
        )

    latest_usage = await session.scalar(
        select(LlmUsageLog)
        .where(LlmUsageLog.provider == "groq")
        .order_by(LlmUsageLog.created_at.desc(), LlmUsageLog.id.desc())
        .limit(1)
    )
    since = now - timedelta(hours=24)
    latest_rate_limit = await session.scalar(
        select(LlmUsageLog)
        .where(LlmUsageLog.provider == "groq")
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
        retry_after = (
            f", retry_after {latest_rate_limit.retry_after}"
            if latest_rate_limit.retry_after
            else ""
        )
        return ComponentHealth(
            "Groq rate limit",
            ComponentStatus.WARN,
            (
                f"recent {latest_rate_limit.status} "
                f"at {_format_utc(latest_rate_limit.created_at)}{retry_after}"
            ),
        )
    if latest_usage is None:
        return ComponentHealth("Groq rate limit", ComponentStatus.UNKNOWN, "no LLM usage telemetry")
    if latest_usage.status == "success":
        return ComponentHealth(
            "Groq rate limit",
            ComponentStatus.OK,
            f"latest usage success at {_format_utc(latest_usage.created_at)}",
        )
    return ComponentHealth(
        "Groq rate limit",
        ComponentStatus.UNKNOWN,
        f"latest usage status {latest_usage.status} at {_format_utc(latest_usage.created_at)}",
    )


async def _news_health(session: AsyncSession, *, now: datetime) -> ComponentHealth:
    latest = await session.scalar(
        select(NewsItem).order_by(NewsItem.fetched_at.desc(), NewsItem.id.desc()).limit(1)
    )
    if latest is None:
        return ComponentHealth("RSS/news", ComponentStatus.UNKNOWN, "no news cache telemetry")

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
        if status == ComponentStatus.OK:
            status = ComponentStatus.WARN
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
    return ComponentHealth("RSS/news", status, detail, tuple(rows))


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
    total = sum(counts.values())
    if total == 0 and final_failed == 0:
        return ComponentHealth(
            "Telegram alerts",
            ComponentStatus.UNKNOWN,
            "no delivery rows in last 24h",
        )

    sent = counts.get("sent", 0)
    pending = counts.get("pending", 0)
    retry_pending = counts.get("retry_pending", 0)
    failed = counts.get("failed", 0)
    if final_failed > 0:
        status = ComponentStatus.FAIL
    elif failed > 0 or pending > 0 or retry_pending > 0:
        status = ComponentStatus.WARN
    elif sent > 0:
        status = ComponentStatus.OK
    else:
        status = ComponentStatus.UNKNOWN

    detail = (
        f"Last 24h: sent {sent}, pending {pending}, retry_pending {retry_pending}, "
        f"failed {failed}, final_failed {final_failed}"
    )
    return ComponentHealth("Telegram alerts", status, detail)


def _render_status(
    *,
    now: datetime,
    runtime_rows: list[str],
    sections: list[ComponentHealth],
) -> str:
    overall = _worst_status([section.status for section in sections])
    lines = [
        f"System status - {_format_utc(now)}",
        f"Overall: {overall.value}",
        "",
        "Runtime",
        *runtime_rows,
        "",
    ]
    for section in sections:
        lines.append(f"{section.name}: {section.status.value} - {section.detail}")
        lines.extend(section.rows)
        lines.append("")
    return "\n".join(lines).strip()
