"""Read-only OpenAI Platform Costs API monitoring for the admin screen.

Never used for OpenAI admission: official daily data can lag behind requests.
No response payload, credential, URL parameters, or exception text is logged.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import select

from bot.services.llm.openai_budget import monthly_budget_usd

COSTS_URL = "https://api.openai.com/v1/organization/costs"
CACHE_TTL = timedelta(hours=1)
MAX_PAGES = 10  # A single UTC month needs at most 31 one-day buckets.
PROJECT_ID_PATTERN = re.compile(r"^proj_[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class ProviderCosts:
    project_id: str
    month_start: datetime
    coverage_end: datetime
    refreshed_at: datetime
    total_usd: Decimal


@dataclass(frozen=True)
class InternalCosts:
    used: Decimal
    limit: Decimal
    remaining: Decimal
    settled: Decimal
    pending: Decimal
    conservative: Decimal
    cap_breach: bool
    comparable_used: Decimal


class CostsDataError(ValueError):
    """A response cannot be trusted for a per-project comparison."""


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("UTC-aware datetime required")
    return value.astimezone(timezone.utc)


def _window(now: datetime) -> tuple[datetime, datetime]:
    now = _utc(now)
    return (
        datetime(now.year, now.month, 1, tzinfo=timezone.utc),
        datetime(now.year, now.month, now.day, tzinfo=timezone.utc),
    )


def _amount(value: Any) -> Decimal:
    # JSON decoded with parse_float=Decimal; reject strings, booleans and nonfinite values.
    if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
        raise CostsDataError("invalid amount")
    result = Decimal(value)
    if not result.is_finite():
        raise CostsDataError("invalid amount")
    return result


def _parse_page(
    payload: Any,
    *, project_id: str, next_bucket: int, end_time: int,
) -> tuple[Decimal, int, bool, str | None]:
    if not isinstance(payload, dict) or payload.get("object") != "page":
        raise CostsDataError("invalid page")
    data = payload.get("data")
    if not isinstance(data, list) or type(payload.get("has_more")) is not bool:
        raise CostsDataError("invalid page fields")
    total = Decimal("0")
    for bucket in data:
        if not isinstance(bucket, dict) or bucket.get("object") != "bucket":
            raise CostsDataError("invalid bucket")
        begin, finish, results = (
            bucket.get("start_time"), bucket.get("end_time"), bucket.get("results")
        )
        if (
            type(begin) is not int or type(finish) is not int
            or begin != next_bucket or finish != begin + 86400
            or finish > end_time or not isinstance(results, list)
        ):
            raise CostsDataError("missing or inconsistent daily coverage")
        next_bucket = finish
        for entry in results:
            if (
                not isinstance(entry, dict)
                or entry.get("object") != "organization.costs.result"
                or entry.get("project_id") != project_id
            ):
                raise CostsDataError("unverified project attribution")
            amount = entry.get("amount")
            if not isinstance(amount, dict) or amount.get("currency") != "usd":
                raise CostsDataError("invalid USD currency")
            total += _amount(amount.get("value"))
    more = payload["has_more"]
    cursor = payload.get("next_page")
    if more and (not isinstance(cursor, str) or not cursor or len(cursor) > 1024):
        raise CostsDataError("missing pagination cursor")
    if not more and cursor is not None:
        raise CostsDataError("unexpected pagination cursor")
    return total, next_bucket, more, cursor


async def _fetch(
    *, key: str, project_id: str, start: datetime, end: datetime, now: datetime,
) -> ProviderCosts:
    start_s, end_s = int(start.timestamp()), int(end.timestamp())
    cursor: str | None = None
    seen: set[str] = set()
    next_bucket = start_s
    total = Decimal("0")
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(8.0, connect=3.0),
        follow_redirects=False,
        trust_env=False,
    ) as client:
        for _ in range(MAX_PAGES):
            params: dict[str, Any] = {
                "start_time": start_s,
                "end_time": end_s,
                "bucket_width": "1d",
                "limit": 31,
                "project_ids": [project_id],
                "group_by": ["project_id"],
            }
            if cursor is not None:
                params["page"] = cursor
            response = await client.get(
                COSTS_URL, params=params, headers={"Authorization": f"Bearer {key}"}
            )
            response.raise_for_status()
            if len(response.content) > 512_000:
                raise CostsDataError("oversized response")
            payload = json.loads(response.content, parse_float=Decimal)
            amount, next_bucket, more, cursor = _parse_page(
                payload, project_id=project_id, next_bucket=next_bucket, end_time=end_s
            )
            total += amount
            if not more:
                if next_bucket != end_s:
                    raise CostsDataError("incomplete daily coverage")
                return ProviderCosts(project_id, start, end, now, total)
            if cursor in seen:
                raise CostsDataError("cyclic pagination")
            seen.add(cursor)
    raise CostsDataError("too many pages")


class OpenAICostsMonitor:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._cached: ProviderCosts | None = None

    async def get(self, *, now: datetime | None = None) -> tuple[str, ProviderCosts | None]:
        now = _utc(now or datetime.now(timezone.utc))
        key = os.getenv("OPENAI_COSTS_ADMIN_KEY", "").strip()
        project_id = os.getenv("OPENAI_COSTS_PROJECT_ID", "").strip()
        if (
            not key or key == os.getenv("OPENAI_API_KEY", "").strip()
            or not PROJECT_ID_PATTERN.fullmatch(project_id)
        ):
            return "NOT CONFIGURED", None
        start, end = _window(now)
        if end <= start:
            return "UNAVAILABLE", None  # First UTC day: no completed daily bucket.
        async with self._lock:
            cache = self._cached
            if (
                cache is not None and cache.project_id == project_id
                and cache.month_start == start and cache.coverage_end == end
                and timedelta(0) <= now - cache.refreshed_at < CACHE_TTL
            ):
                return "OK", cache
            try:
                async with asyncio.timeout(12):
                    snapshot = await _fetch(
                        key=key, project_id=project_id, start=start, end=end, now=now,
                    )
            except (httpx.HTTPError, ValueError, UnicodeError, OverflowError, TimeoutError):
                return "UNAVAILABLE", None
            # No raw error/response logging, even if the provider sends secrets.
            self._cached = snapshot
            return "OK", snapshot


async def read_internal_costs(
    session_factory: Any, *, start: datetime, end: datetime,
) -> InternalCosts:
    """Read the exact same month ledger used by admission; never write to it."""
    from bot.db.database import OpenAIBudgetReservation

    limit = monthly_budget_usd()
    if limit is None:
        raise CostsDataError("invalid local cap")
    month = date(start.year, start.month, 1)
    async with session_factory() as session:
        rows = (
            await session.execute(
                select(
                    OpenAIBudgetReservation.status,
                    OpenAIBudgetReservation.actual_usd,
                    OpenAIBudgetReservation.reserved_usd,
                    OpenAIBudgetReservation.created_at,
                ).where(OpenAIBudgetReservation.month_start == month)
            )
        ).all()
    used = settled = pending = conservative = comparable = Decimal("0")
    breach = False
    for status, actual, reserved, created in rows:
        if (
            status not in {"settled", "reserved", "conservative", "cap_breach"}
            or reserved is None or created is None
            or (status in {"reserved", "conservative"} and actual is not None)
            or (status in {"settled", "cap_breach"} and actual is None)
        ):
            raise CostsDataError("invalid ledger state")
        charge = Decimal(actual if actual is not None else reserved)
        if not charge.is_finite() or charge < 0:
            raise CostsDataError("invalid ledger amount")
        used += charge
        if status in {"settled", "cap_breach"}:
            settled += charge
        elif status == "reserved":
            pending += charge
        else:
            conservative += charge
        breach |= status == "cap_breach"
        timestamp = (
            created.replace(tzinfo=timezone.utc)
            if created.tzinfo is None else _utc(created)
        )
        if start <= timestamp < end:
            comparable += charge
    return InternalCosts(
        used=used, limit=limit, remaining=max(Decimal("0"), limit - used),
        settled=settled, pending=pending, conservative=conservative,
        cap_breach=breach, comparable_used=comparable,
    )


def format_costs_screen(
    *, now: datetime, state: str, provider: ProviderCosts | None,
    internal: InternalCosts | None, scope_confirmed: bool,
) -> str:
    now = _utc(now)
    lines = [f"OpenAI Costs — {now.strftime('%B %Y')} (UTC)", ""]
    if internal is None:
        lines += ["Internal budget: UNAVAILABLE", "Local budget database or cap is unavailable."]
    else:
        lines += [
            "Internal budget (current UTC month):",
            f"Used: ${internal.used:.4f}",
            f"Limit: ${internal.limit:.4f}",
            f"Remaining: ${internal.remaining:.4f}",
            "",
            "Internal accounting (no double counting):",
            f"Settled estimated charges: ${internal.settled:.4f}",
            f"Pending reservations: ${internal.pending:.4f}",
            f"Conservative unreconciled: ${internal.conservative:.4f}",
        ]
        if internal.cap_breach:
            lines.append("WARNING: local budget cap invariant breach recorded.")
    lines += ["", "OpenAI Platform (official, delayed daily data):"]
    if state != "OK" or provider is None:
        lines += [
            f"Reported cost: {state}",
            "Last successful refresh: UNAVAILABLE",
            "Coverage: UNAVAILABLE",
        ]
    else:
        lines += [
            f"Reported cost MTD: ${provider.total_usd:.4f}",
            f"Last successful refresh: {provider.refreshed_at:%Y-%m-%d %H:%M} UTC",
            f"Data coverage: {provider.month_start:%Y-%m-%d} to "
            f"{provider.coverage_end:%Y-%m-%d} 00:00 UTC (end exclusive)",
        ]
    if state == "OK" and provider and internal and scope_confirmed:
        difference = provider.total_usd - internal.comparable_used
        lines.append(f"Difference (provider - local, same window): ${difference:+.4f}")
    else:
        lines.append("Difference: NOT COMPARABLE (coverage, data, or project scope unverified)")
    lines += [
        "",
        "OpenAI daily costs can lag. Current UTC day is excluded; this is not live billing.",
        "Local reservations include today and are conservative. "
        "Provider amounts may include non-token charges.",
        "The hard local budget guard uses only its own ledger, never this report.",
    ]
    return "\n".join(lines)


openai_costs_monitor = OpenAICostsMonitor()
