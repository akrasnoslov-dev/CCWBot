"""Pure Premium entitlement and delivery-frequency rules."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bot.domain.supported_coins import (
    DEFAULT_PREMIUM_ALERT_FREQUENCY_SECONDS,
    FREE_ALERT_FREQUENCY_SECONDS,
    PREMIUM_ALERT_FREQUENCY_SECONDS,
    is_symbol_free,
    normalize_symbol,
)


def _as_aware_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def is_user_premium_active(user_or_plan: Any, now: datetime | None = None) -> bool:
    if user_or_plan is None:
        return False
    now = _as_aware_utc(now) or datetime.now(timezone.utc)
    active_until = _as_aware_utc(getattr(user_or_plan, "active_until", None))
    return active_until is not None and active_until > now


def get_user_plan(user: Any) -> Any:
    plan = getattr(user, "premium_subscription", None)
    if isinstance(plan, list):
        return plan[0] if plan else None
    return plan


def get_user_stored_frequency_seconds(user: Any) -> int | None:
    value = getattr(user, "alert_frequency_seconds", None)
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def is_coin_unlocked_for_user(user: Any, symbol: str, now: datetime | None = None) -> bool:
    normalized_symbol = normalize_symbol(symbol)
    if is_symbol_free(normalized_symbol):
        return True
    return is_user_premium_active(get_user_plan(user), now)


def get_effective_frequency_seconds(user: Any, now: datetime | None = None) -> int:
    if not is_user_premium_active(get_user_plan(user), now):
        return FREE_ALERT_FREQUENCY_SECONDS
    stored_frequency = get_user_stored_frequency_seconds(user)
    if stored_frequency in PREMIUM_ALERT_FREQUENCY_SECONDS:
        return stored_frequency
    return DEFAULT_PREMIUM_ALERT_FREQUENCY_SECONDS


def can_deliver_now(
    user: Any,
    symbol: str,
    now: datetime,
    last_sent_at: datetime | None,
) -> bool:
    if not is_coin_unlocked_for_user(user, symbol, now):
        return False
    if last_sent_at is None:
        return True
    last_sent_at = _as_aware_utc(last_sent_at)
    now = _as_aware_utc(now) or datetime.now(timezone.utc)
    if last_sent_at is None:
        return True
    elapsed_seconds = (now - last_sent_at).total_seconds()
    return elapsed_seconds >= get_effective_frequency_seconds(user, now)
