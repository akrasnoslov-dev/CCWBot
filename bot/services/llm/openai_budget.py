"""Persistent, fail-closed admission control for optional paid OpenAI calls."""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import ROUND_CEILING, Decimal, InvalidOperation
from uuid import uuid4

from sqlalchemy import func, select, text

logger = logging.getLogger(__name__)
MILLION = Decimal("1000000")
DEFAULT_MONTHLY_BUDGET_USD = Decimal("2.50")
MIN_CONFIG_DECIMAL = Decimal("0.0000000001")
MAX_CONFIG_DECIMAL = Decimal("99999999")
MAX_VERIFIED_INPUT_TOKENS = 10_000_000
_POSTGRES_ADVISORY_LOCK_ID = 0x4343574F504149  # "CCWOPAI", stable across workers.


def _utc_now() -> datetime:
    """Return the admission clock; isolated for deterministic rollover coverage."""
    return datetime.now(timezone.utc)


class OpenAIBudgetExhausted(RuntimeError):
    """OpenAI was skipped before HTTP because safe authorization was unavailable."""

    def __init__(self, reason: str):
        super().__init__(f"OpenAI request blocked by local budget guard: {reason}")
        self.reason = reason
        self.provider = "openai"


@dataclass(frozen=True)
class OpenAIBudgetLease:
    reservation_id: str
    reserved_usd: Decimal
    input_rate: Decimal
    output_rate: Decimal


def _positive_decimal_env(name: str, default: Decimal | None = None) -> Decimal | None:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = Decimal(raw.strip())
    except InvalidOperation:
        return None
    if not value.is_finite() or value < MIN_CONFIG_DECIMAL or value > MAX_CONFIG_DECIMAL:
        return None
    return value


def _positive_int_env(name: str, *, maximum: int) -> int | None:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return None
    try:
        value = int(raw.strip())
    except ValueError:
        return None
    return value if 0 < value <= maximum else None


def monthly_budget_usd() -> Decimal | None:
    """Return a cap at or below the owner-approved hard maximum of $2.50."""
    configured = _positive_decimal_env(
        "OPENAI_MONTHLY_BUDGET_USD", DEFAULT_MONTHLY_BUDGET_USD
    )
    if configured is None or configured > DEFAULT_MONTHLY_BUDGET_USD:
        return None
    return configured


def pricing_usd_per_million() -> tuple[Decimal, Decimal] | None:
    """Require activation-time verified prices instead of embedding a guessed future price."""
    input_rate = _positive_decimal_env("OPENAI_INPUT_USD_PER_1M_TOKENS")
    output_rate = _positive_decimal_env("OPENAI_OUTPUT_USD_PER_1M_TOKENS")
    if input_rate is None or output_rate is None:
        return None
    return input_rate, output_rate


def verified_input_token_ceiling(model: str) -> int | None:
    """Return the activation-time verified input ceiling for exactly ``model``."""
    priced_model = os.getenv("OPENAI_PRICED_MODEL", "").strip()
    if not priced_model or priced_model != model:
        return None
    return _positive_int_env(
        "OPENAI_MAX_INPUT_TOKENS", maximum=MAX_VERIFIED_INPUT_TOKENS
    )


def _cost(tokens: int, rate: Decimal) -> Decimal:
    return (Decimal(max(0, tokens)) * rate / MILLION).quantize(
        Decimal("0.0000000001"), rounding=ROUND_CEILING
    )


class OpenAIBudget:
    def __init__(self) -> None:
        self._process_lock = asyncio.Lock()

    async def reserve(
        self, *, model: str, call_type: str, input_chars: int, max_tokens: int
    ) -> OpenAIBudgetLease:
        cap = monthly_budget_usd()
        rates = pricing_usd_per_million()
        if cap is None:
            raise OpenAIBudgetExhausted("invalid_cap")
        if rates is None:
            raise OpenAIBudgetExhausted("unknown_pricing")
        input_token_ceiling = verified_input_token_ceiling(model)
        if input_token_ceiling is None:
            raise OpenAIBudgetExhausted("unverified_model_limits")

        try:
            from bot.db.database import OpenAIBudgetReservation
            from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL

            if not DB_ENABLED or not DB_SESSION_LOCAL:
                raise OpenAIBudgetExhausted("state_unavailable")
        except OpenAIBudgetExhausted:
            raise
        except Exception as error:
            logger.warning(
                "ops_event=openai_budget_unavailable error_class=%s", type(error).__name__
            )
            raise OpenAIBudgetExhausted("state_unavailable") from error

        input_rate, output_rate = rates
        # Reserve the verified model-wide input ceiling rather than estimating from
        # characters. This covers Unicode, provider framing, and response-schema tokens.
        reserved = _cost(input_token_ceiling, input_rate) + _cost(max_tokens, output_rate)
        reservation_id = str(uuid4())

        try:
            async with self._process_lock:
                async with DB_SESSION_LOCAL() as session:
                    async with session.begin():
                        bind = session.get_bind()
                        if bind.dialect.name == "postgresql":
                            await session.execute(
                                text("SELECT pg_advisory_xact_lock(:lock_id)"),
                                {"lock_id": _POSTGRES_ADVISORY_LOCK_ID},
                            )
                        # The ledger month is the UTC month when serialized admission
                        # actually begins, not when the request first started waiting.
                        # This prevents a request held across midnight on the first from
                        # consuming the previous bucket and leaving the new cap untouched.
                        now = _utc_now()
                        month_start = date(now.year, now.month, 1)
                        invariant_breach = await session.scalar(
                            select(func.count())
                            .select_from(OpenAIBudgetReservation)
                            .where(
                                OpenAIBudgetReservation.month_start == month_start,
                                OpenAIBudgetReservation.status == "cap_breach",
                            )
                        )
                        if invariant_breach:
                            raise OpenAIBudgetExhausted("invariant_breach")
                        used = await session.scalar(
                            select(
                                func.coalesce(
                                    func.sum(
                                        func.coalesce(
                                            OpenAIBudgetReservation.actual_usd,
                                            OpenAIBudgetReservation.reserved_usd,
                                        )
                                    ),
                                    Decimal("0"),
                                )
                            ).where(OpenAIBudgetReservation.month_start == month_start)
                        )
                        used_decimal = Decimal(used or 0)
                        if used_decimal + reserved > cap:
                            raise OpenAIBudgetExhausted("exhausted")
                        session.add(
                            OpenAIBudgetReservation(
                                id=reservation_id,
                                month_start=month_start,
                                model=model,
                                call_type=call_type,
                                reserved_usd=reserved,
                                input_rate_usd_per_million=input_rate,
                                output_rate_usd_per_million=output_rate,
                                actual_usd=None,
                                status="reserved",
                                created_at=now,
                            )
                        )
        except OpenAIBudgetExhausted:
            raise
        except Exception as error:
            logger.warning(
                "ops_event=openai_budget_unavailable error_class=%s", type(error).__name__
            )
            raise OpenAIBudgetExhausted("state_unavailable") from error

        logger.info(
            "ops_event=openai_budget_reserved month=%s reserved_usd=%s "
            "committed_usd=%s remaining_usd=%s",
            month_start.isoformat(),
            reserved,
            used_decimal,
            max(Decimal("0"), cap - used_decimal - reserved),
        )

        return OpenAIBudgetLease(reservation_id, reserved, input_rate, output_rate)

    async def settle(
        self,
        lease: OpenAIBudgetLease,
        *,
        prompt_tokens: int | None,
        completion_tokens: int | None,
    ) -> None:
        """Reconcile known usage; unknown usage retains the conservative reservation."""
        from bot.db.database import OpenAIBudgetReservation
        from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL

        if not DB_ENABLED or not DB_SESSION_LOCAL:
            return
        actual = None
        status = "conservative"
        if (
            prompt_tokens is not None
            and completion_tokens is not None
            and prompt_tokens >= 0
            and completion_tokens >= 0
        ):
            actual = _cost(prompt_tokens, lease.input_rate) + _cost(
                completion_tokens, lease.output_rate
            )
            if actual <= lease.reserved_usd:
                status = "settled"
            else:
                # A verified input ceiling and request output maximum should make
                # this impossible. Preserve the larger charge so future admission
                # fails closed and make the invariant violation operator-visible.
                status = "cap_breach"
                logger.critical(
                    "ops_event=openai_budget_invariant_breach reserved_usd=%s actual_usd=%s",
                    lease.reserved_usd,
                    actual,
                )
        recorded_status = status
        recorded_charge = actual if actual is not None else lease.reserved_usd
        try:
            async with self._process_lock:
                async with DB_SESSION_LOCAL() as session:
                    async with session.begin():
                        bind = session.get_bind()
                        if bind.dialect.name == "postgresql":
                            await session.execute(
                                text("SELECT pg_advisory_xact_lock(:lock_id)"),
                                {"lock_id": _POSTGRES_ADVISORY_LOCK_ID},
                            )
                        row = await session.get(
                            OpenAIBudgetReservation, lease.reservation_id
                        )
                        if row is not None and row.status == "reserved":
                            row.actual_usd = actual
                            row.status = status
                            row.settled_at = datetime.now(timezone.utc)
                        if row is not None:
                            recorded_status = row.status
                            recorded_charge = (
                                row.actual_usd
                                if row.actual_usd is not None
                                else row.reserved_usd
                            )
            logger.info(
                "ops_event=openai_budget_settled reserved_usd=%s charged_usd=%s status=%s",
                lease.reserved_usd,
                recorded_charge,
                recorded_status,
            )
        except Exception as error:
            # The pre-request reservation remains conservative if reconciliation fails.
            logger.warning(
                "ops_event=openai_budget_settlement_unavailable error_class=%s",
                type(error).__name__,
            )


openai_budget = OpenAIBudget()
