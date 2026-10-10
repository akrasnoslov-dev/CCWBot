"""Read-only rolling health of *terminal logical operations*, never provider attempts.

Only narrow sanitized columns are read. A provider retry that recovers is one
successful logical operation, regardless of failed rows in llm_usage_logs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.database import (
    EventAiAnalysis,
    LlmOperationOutcome,
    LlmUsageLog,
    MarketHeartbeat,
    MarketReport,
)
from bot.domain.supported_coins import SUPPORTED_SYMBOLS

WINDOW_HOURS = 24
MIN_RATE_SAMPLES = 20
MIN_ALERT_FAILURES = 5
MIN_LOW_SAMPLE_FAILURES = 10
FAIL_RATE = 70.0
DEGRADED_RATE = 95.0
# Ignore in-flight operations and avoid out-of-window boundary false gaps.
COVERAGE_GRACE = timedelta(minutes=10)

CALL_TYPES = (
    "event_analysis",
    "event_alert_render",
    "market_heartbeat",
    "daily_report",
    "weekly_report",
    "news_intelligence",
)
SUCCESS_STATUSES = {
    "event_analysis": frozenset({"success", "no_alert"}),
    "event_alert_render": frozenset({"success"}),
    "market_heartbeat": frozenset({"completed"}),
    "daily_report": frozenset({"completed"}),
    "weekly_report": frozenset({"completed"}),
    "news_intelligence": frozenset({"success"}),
}
INCOMPLETE_STATUSES = frozenset({"", "pending", "running", "unknown"})


@dataclass(frozen=True)
class LogicalHealth:
    call_type: str
    state: str
    operations: int
    successes: int
    terminal_failures: int
    unknown_outcomes: int
    missing_outcomes: int
    success_rate_percent: float | None
    # Only problem symbols meeting the same minimum-confidence gates.
    problem_symbols: tuple[str, ...] = ()
    recovered_operations: int = 0


def _state(successes: int, failures: int, unknown: int, gaps: int) -> str:
    completed = successes + failures
    if completed >= MIN_RATE_SAMPLES:
        rate = successes * 100.0 / completed
        if failures >= MIN_ALERT_FAILURES and rate < DEGRADED_RATE:
            if failures >= MIN_LOW_SAMPLE_FAILURES and rate < FAIL_RATE:
                return "failed"
            return "degraded"
        if unknown or gaps or (failures and rate < DEGRADED_RATE):
            # Below the failure-count alert gate, a poor rate is inconclusive,
            # not evidence of a healthy feature.
            return "unknown"
        return "ok"
    if completed >= MIN_LOW_SAMPLE_FAILURES and failures >= MIN_LOW_SAMPLE_FAILURES:
        return "degraded"
    return "unknown"


def _summarize(call_type: str, rows: list[tuple[str | None, str | None]],
               gaps: int = 0, recovered: int = 0) -> LogicalHealth:
    successes = failures = unknown = 0
    for status, _symbol in rows:
        normalized = str(status or "").lower()
        if normalized in SUCCESS_STATUSES[call_type]:
            successes += 1
        elif normalized in INCOMPLETE_STATUSES:
            unknown += 1
        else:
            failures += 1
    completed = successes + failures
    symbols: list[str] = []
    if call_type in {"event_analysis", "event_alert_render", "market_heartbeat"}:
        symbols_present = {s for _, s in rows if isinstance(s, str)
                           and s.lower() in SUPPORTED_SYMBOLS}
        for symbol in sorted(symbols_present):
            scoped = [(status, s) for status, s in rows if s == symbol]
            good = sum(str(status or "").lower() in SUCCESS_STATUSES[call_type]
                       for status, _ in scoped)
            bad = sum(str(status or "").lower() not in SUCCESS_STATUSES[call_type]
                      and str(status or "").lower() not in INCOMPLETE_STATUSES
                      for status, _ in scoped)
            if _state(good, bad, 0, 0) in {"degraded", "failed"}:
                symbols.append(symbol)
    return LogicalHealth(
        call_type=call_type,
        state=_state(successes, failures, unknown, gaps),
        operations=len(rows),
        successes=successes,
        terminal_failures=failures,
        unknown_outcomes=unknown,
        missing_outcomes=gaps,
        success_rate_percent=round(100.0 * successes / completed, 1) if completed else None,
        problem_symbols=tuple(symbols),
        recovered_operations=recovered,
    )


async def read_logical_llm_health(
    session: AsyncSession, *, now: datetime | None = None,
    call_types: tuple[str, ...] = CALL_TYPES,
) -> dict[str, LogicalHealth]:
    """Compute 24h terminal outcomes. Raises on DB errors; never returns fake OK."""
    now = now or datetime.now(timezone.utc)
    since = now - timedelta(hours=WINDOW_HOURS)
    outcomes: dict[str, list[tuple[str | None, str | None]]] = {
        name: [] for name in call_types
    }
    operation_ids: dict[str, set[str]] = {name: set() for name in call_types}
    successful_ids: dict[str, set[str]] = {name: set() for name in call_types}

    if "event_analysis" in call_types:
        for status, symbol, op_id in (
            await session.execute(
                select(
                    EventAiAnalysis.status, EventAiAnalysis.symbol,
                    EventAiAnalysis.llm_operation_id,
                )
                .where(EventAiAnalysis.analysis_type == "event_analysis")
                .where(EventAiAnalysis.created_at >= since)
                .where(EventAiAnalysis.created_at <= now)
            )
        ).all():
            outcomes["event_analysis"].append((status, symbol))
            if op_id:
                operation_ids["event_analysis"].add(op_id)
                if str(status or "").lower() in SUCCESS_STATUSES["event_analysis"]:
                    successful_ids["event_analysis"].add(op_id)

    if {"event_alert_render", "news_intelligence"}.intersection(call_types):
        for call_type, status, symbol, op_id in (
            await session.execute(
                select(LlmOperationOutcome.call_type, LlmOperationOutcome.status,
                       LlmOperationOutcome.symbol, LlmOperationOutcome.llm_operation_id)
                .where(LlmOperationOutcome.created_at >= since)
                .where(LlmOperationOutcome.created_at <= now)
                .where(LlmOperationOutcome.call_type.in_(call_types))
            )
        ).all():
            outcomes[call_type].append((status, symbol))
            if op_id:
                operation_ids[call_type].add(op_id)
                if str(status or "").lower() in SUCCESS_STATUSES[call_type]:
                    successful_ids[call_type].add(op_id)

    if "market_heartbeat" in call_types:
        for status, symbol, op_id in (
            await session.execute(
                select(MarketHeartbeat.status, MarketHeartbeat.symbol,
                       MarketHeartbeat.llm_operation_id)
                .where(MarketHeartbeat.created_at >= since)
                .where(MarketHeartbeat.created_at <= now)
            )
        ).all():
            outcomes["market_heartbeat"].append((status, symbol))
            if op_id:
                operation_ids["market_heartbeat"].add(op_id)
                if str(status or "").lower() in SUCCESS_STATUSES["market_heartbeat"]:
                    successful_ids["market_heartbeat"].add(op_id)

    if {"daily_report", "weekly_report"}.intersection(call_types):
        for report_type, status, op_id in (
            await session.execute(
                select(MarketReport.report_type, MarketReport.status,
                       MarketReport.llm_operation_id)
                .where(MarketReport.created_at >= since)
                .where(MarketReport.created_at <= now)
                .where(MarketReport.report_type.in_(
                    tuple(t.removesuffix("_report") for t in call_types if t.endswith("_report"))
                ))
            )
        ).all():
            call_type = f"{report_type}_report"
            outcomes[call_type].append((status, None))
            if op_id:
                operation_ids[call_type].add(op_id)
                if str(status or "").lower() in SUCCESS_STATUSES[call_type]:
                    successful_ids[call_type].add(op_id)

    # Missing persisted terminal rows for finished correlated provider operations
    # are unknown evidence, not a success or a terminal failure.
    missing: dict[str, set[str]] = {name: set() for name in call_types}
    recovered: dict[str, set[str]] = {name: set() for name in call_types}
    for call_type, op_id, status in (
        await session.execute(
            select(LlmUsageLog.call_type, LlmUsageLog.llm_operation_id, LlmUsageLog.status)
            .where(LlmUsageLog.created_at >= since + COVERAGE_GRACE)
            .where(LlmUsageLog.created_at <= now - COVERAGE_GRACE)
            .where(LlmUsageLog.llm_operation_id.is_not(None))
            .where(LlmUsageLog.call_type.in_(call_types))
            .distinct()
        )
    ).all():
        if op_id not in operation_ids[call_type]:
            missing[call_type].add(op_id)
        elif op_id in successful_ids[call_type] and status != "success":
            recovered[call_type].add(op_id)

    return {
        call_type: _summarize(
            call_type, rows, len(missing[call_type]), len(recovered[call_type])
        )
        for call_type, rows in outcomes.items()
    }
