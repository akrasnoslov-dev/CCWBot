"""Pure Premium entitlement and heartbeat silence rules."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bot.domain.supported_coins import (
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


def get_user_trial(user: Any) -> Any:
    trial = getattr(user, "premium_trial", None)
    if isinstance(trial, list):
        return trial[0] if trial else None
    return trial


def is_user_trial_active(user_or_trial: Any, now: datetime | None = None) -> bool:
    if user_or_trial is None:
        return False
    now = _as_aware_utc(now) or datetime.now(timezone.utc)
    active_until = _as_aware_utc(getattr(user_or_trial, "active_until", None))
    return active_until is not None and active_until > now


def has_premium_entitlement(user: Any, now: datetime | None = None) -> bool:
    return is_user_premium_active(get_user_plan(user), now) or is_user_trial_active(
        get_user_trial(user), now
    )


def is_coin_unlocked_for_user(user: Any, symbol: str, now: datetime | None = None) -> bool:
    normalized_symbol = normalize_symbol(symbol)
    if is_symbol_free(normalized_symbol):
        return True
    return has_premium_entitlement(user, now)


HEARTBEAT_SILENCE_SECONDS = 86400


def heartbeat_activation_baseline(user: Any, symbol: str, now: datetime) -> datetime | None:
    """Use persisted onboarding/watchlist/entitlement times; fail closed if absent.

    Entitlement updates are conservative: renewal may postpone a first heartbeat,
    but can never cause an early one. Existing successful deliveries use their
    own rolling clock instead.
    """
    normalized = normalize_symbol(symbol)
    subscription = next(
        (
            row
            for row in getattr(user, "coin_subscriptions", [])
            if normalize_symbol(row.symbol) == normalized
        ),
        None,
    )
    if subscription is None or not subscription.is_enabled:
        return None
    dates = [
        getattr(user, "created_at", None),
        getattr(subscription, "updated_at", None) or getattr(subscription, "created_at", None),
    ]
    if not is_symbol_free(normalized):
        active = [
            plan
            for plan in (get_user_plan(user), get_user_trial(user))
            if is_user_premium_active(plan, now)
        ]
        starts = [
            _as_aware_utc(
                getattr(plan, "updated_at", None)
                or getattr(plan, "started_at", None)
                or getattr(plan, "created_at", None)
            )
            for plan in active
        ]
        if not starts or any(value is None for value in starts):
            return None
        # Either active entitlement is sufficient; use the earliest available one.
        dates.append(min(starts))
    dates = [_as_aware_utc(value) for value in dates if value is not None]
    return max(dates) if dates else None


def can_deliver_market_heartbeat_now(
    user: Any,
    symbol: str,
    now: datetime,
    last_sent_at: datetime | None,
) -> bool:
    if not is_coin_unlocked_for_user(user, symbol, now):
        return False
    now = _as_aware_utc(now) or datetime.now(timezone.utc)
    baseline = _as_aware_utc(last_sent_at) or heartbeat_activation_baseline(user, symbol, now)
    return baseline is not None and (now - baseline).total_seconds() >= HEARTBEAT_SILENCE_SECONDS
