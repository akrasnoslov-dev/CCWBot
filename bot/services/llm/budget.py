"""Conservative zero-cost Groq admission control, shared across all call types.

A 429 is too late: the free plan enforces daily tokens even when remaining-token headers
only expose TPM. Seed the rolling window from existing attempt telemetry after restart.
This is a *soft* local safety guard, not an assertion of the account's exact limits.
Every rejection is surfaced to the router as a logged skip, never as a no-alert decision.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from bot.domain.supported_coins import SUPPORTED_SYMBOLS
from bot.services.llm.env import get_int_env
from bot.services.llm.errors import LLMRateLimitBackoffActive
from bot.services.llm.telemetry import _parse_retry_delay_text, header_value

logger = logging.getLogger(__name__)
DAY = timedelta(hours=24)
MINUTE = timedelta(seconds=60)
# 10% reserve for other activity and uncertainty in organization-level limits.
DEFAULT_TPD = 180_000
DEFAULT_RPD = 900
DEFAULT_RPM = 27
DEFAULT_TPM = 7_200
# Protect room for positive-event rendering and other tasks. Each of four event-analysis
# symbols gets an equal reserved share, irrespective of which job happens to run first.
EVENT_SYMBOL_SHARE = 0.20


class GroqBudgetExhausted(LLMRateLimitBackoffActive):
    def __init__(self, *, model: str, limited_until: datetime, dimension: str):
        super().__init__(provider="groq", model=model, limited_until=limited_until)
        self.budget_dimension = dimension


@dataclass
class _Charge:
    at: datetime
    symbol: str | None
    call_type: str
    tokens: int
    request: bool = True


@dataclass
class BudgetLease:
    model: str
    charge: _Charge


class GroqBudget:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._history: dict[str, list[_Charge]] = {}
        self._loaded: set[str] = set()
        self._headers: dict[str, dict[str, tuple[int, datetime]]] = {}

    def reset(self):
        """Test-only reset; production restarts reload persisted usage."""
        self._history.clear()
        self._loaded.clear()
        self._headers.clear()

    async def _load(self, model: str, now: datetime) -> None:
        if model in self._loaded:
            return
        # Do not mark loaded until the query finishes. This method runs under the lock.
        try:
            from sqlalchemy import select

            from bot.db.database import LlmUsageLog
            from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL

            if DB_ENABLED and DB_SESSION_LOCAL:
                async with DB_SESSION_LOCAL() as session:
                    result = await session.execute(
                        select(
                            LlmUsageLog.created_at,
                            LlmUsageLog.symbol,
                            LlmUsageLog.call_type,
                            LlmUsageLog.total_tokens,
                            LlmUsageLog.status,
                        ).where(
                            LlmUsageLog.provider == "groq",
                            LlmUsageLog.model == model,
                            LlmUsageLog.created_at >= now - DAY,
                        )
                    )
                    for at, symbol, call_type, total, status in result.all():
                        if str(status).startswith("skipped_due_to_"):
                            continue
                        if at.tzinfo is None:
                            at = at.replace(tzinfo=timezone.utc)
                        self._history.setdefault(model, []).append(
                            _Charge(at, symbol, call_type, max(0, int(total or 0)))
                        )
        except Exception as error:
            # Provider availability must never depend on diagnostic persistence.
            logger.warning(
                "ops_event=groq_budget_history_unavailable error_class=%s",
                type(error).__name__,
            )
        self._loaded.add(model)

    @staticmethod
    def _estimate(input_chars: int, max_tokens: int) -> int:
        # Reserve practical observed completion headroom, not the 6300-token hard ceiling.
        # Deliberately overestimate input (3 chars/token) and reserve 2000 completion tokens.
        return min(
            max(1, max_tokens) + max(1, input_chars // 3), max(2000, input_chars // 3 + 2000)
        )

    def _limit(self, name: str, default: int) -> int:
        return get_int_env(name, default, minimum=1)

    def _header_remaining(self, model: str, dimension: str, now: datetime):
        value = self._headers.get(model, {}).get(dimension)
        if value is None:
            return None
        remaining, expires = value
        if now >= expires:
            del self._headers[model][dimension]
            return None
        return remaining, expires

    async def reserve(
        self,
        *,
        model: str,
        symbol: str | None,
        call_type: str,
        input_chars: int,
        max_tokens: int,
    ) -> BudgetLease:
        now = datetime.now(timezone.utc)
        async with self._lock:
            await self._load(model, now)
            history = self._history.setdefault(model, [])
            history[:] = [h for h in history if h.at > now - DAY]
            expected = self._estimate(input_chars, max_tokens)
            daily_tokens = self._limit("GROQ_FREE_TOKEN_BUDGET_DAY", DEFAULT_TPD)
            daily_requests = self._limit("GROQ_FREE_REQUEST_BUDGET_DAY", DEFAULT_RPD)
            minute_requests = self._limit("GROQ_FREE_REQUEST_BUDGET_MINUTE", DEFAULT_RPM)
            minute_tokens = self._limit("GROQ_FREE_TOKEN_BUDGET_MINUTE", DEFAULT_TPM)

            dimension = None
            until = now + MINUTE
            if sum(h.tokens for h in history) + expected > daily_tokens:
                dimension = "local_tpd"
                until = min((h.at + DAY for h in history), default=now + DAY)
            elif sum(h.request for h in history) >= daily_requests:
                dimension = "local_rpd"
                until = min((h.at + DAY for h in history if h.request), default=now + DAY)
            elif (
                call_type == "event_analysis"
                and symbol
                and symbol.lower() in SUPPORTED_SYMBOLS
                and sum(
                    h.tokens
                    for h in history
                    if h.call_type == "event_analysis" and h.symbol == symbol.upper()
                )
                + expected
                > int(daily_tokens * EVENT_SYMBOL_SHARE)
            ):
                dimension = "symbol_fair_share"
                until = min(
                    (
                        h.at + DAY
                        for h in history
                        if h.call_type == "event_analysis" and h.symbol == symbol.upper()
                    ),
                    default=now + DAY,
                )
            elif sum(h.request for h in history if h.at > now - MINUTE) >= minute_requests:
                dimension = "local_rpm"
                until = min(
                    (h.at + MINUTE for h in history if h.request and h.at > now - MINUTE),
                    default=now + MINUTE,
                )
            elif sum(h.tokens for h in history if h.at > now - MINUTE) + expected > minute_tokens:
                dimension = "local_tpm"
                until = min(
                    (h.at + MINUTE for h in history if h.at > now - MINUTE), default=now + MINUTE
                )

            # Groq documents request headers as RPD, token headers as TPM.
            for header_dimension, charge in (("requests", 1), ("tokens", expected)):
                observed = self._header_remaining(model, header_dimension, now)
                if observed is not None and observed[0] < charge:
                    dimension = "header_rpd" if header_dimension == "requests" else "header_tpm"
                    until = observed[1]
                    break

            if dimension is not None:
                raise GroqBudgetExhausted(
                    model=model,
                    dimension=dimension,
                    limited_until=max(until, now + timedelta(seconds=1)),
                )
            lease = BudgetLease(
                model, _Charge(now, symbol.upper() if symbol else None, call_type, expected)
            )
            history.append(lease.charge)
            for header_dimension, charge in (("requests", 1), ("tokens", expected)):
                value = self._header_remaining(model, header_dimension, now)
                if value is not None:
                    self._headers[model][header_dimension] = (max(0, value[0] - charge), value[1])
            return lease

    async def settle(
        self, lease: BudgetLease, *, actual_tokens: int | None, headers, failed: bool = False
    ) -> None:
        now = datetime.now(timezone.utc)
        async with self._lock:
            # Unknown successful usage remains reserved (fail closed); unsuccessful HTTP calls
            # spend a request but no known output tokens.
            if failed:
                lease.charge.tokens = 0
            elif actual_tokens is not None:
                lease.charge.tokens = max(0, actual_tokens)
            stored = self._headers.setdefault(lease.model, {})
            for dimension, reset_name, remaining_name, default_window in (
                ("requests", "x-ratelimit-reset-requests", "x-ratelimit-remaining-requests", DAY),
                ("tokens", "x-ratelimit-reset-tokens", "x-ratelimit-remaining-tokens", MINUTE),
            ):
                raw = header_value(headers, remaining_name)
                try:
                    remaining = int(raw) if raw is not None else None
                except (ValueError, TypeError):
                    remaining = None
                if remaining is None or remaining < 0:
                    continue
                raw_reset = header_value(headers, reset_name)
                seconds = _parse_retry_delay_text(f"retry in {raw_reset}") if raw_reset else None
                expires = now + (timedelta(seconds=seconds) if seconds else default_window)
                stored[dimension] = (remaining, expires)


groq_budget = GroqBudget()
