"""Premium, watchlist, frequency, and payment persistence.

Belongs here: coin subscription rows, Premium grant/revoke/payment activation,
and user alert frequency preferences.
Does not belong here: Telegram command authorization, payment provider API calls,
alert delivery rows, or schema/model declarations.
"""

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.database import Payment, User, UserCoinSubscription, UserPremiumSubscription, utc_now
from bot.db.users import get_user_by_telegram_user_id
from bot.domain.supported_coins import (
    PREMIUM_ALERT_FREQUENCY_SECONDS,
    SUPPORTED_SYMBOLS,
    is_symbol_free,
    normalize_symbol,
)

TELEGRAM_STARS_PROVIDER = "telegram_stars"
PREMIUM_PAYMENT_STATUS_PAID = "paid"
PREMIUM_PAYMENT_PERIOD_DAYS = 30
_payment_activation_locks: dict[int, asyncio.Lock] = {}


async def ensure_default_coin_subscriptions(
    session: AsyncSession,
    *,
    user_id: int,
) -> list[UserCoinSubscription]:
    """Ensure one subscription row per supported symbol for a user."""
    existing_rows = list(
        (
            await session.scalars(
                select(UserCoinSubscription).where(UserCoinSubscription.user_id == user_id)
            )
        ).all()
    )
    active_rows = [row for row in existing_rows if row.symbol in SUPPORTED_SYMBOLS]
    existing_symbols = {row.symbol for row in active_rows}
    rows_to_add = []
    for symbol in SUPPORTED_SYMBOLS:
        if symbol in existing_symbols:
            continue
        rows_to_add.append(
            UserCoinSubscription(
                user_id=user_id,
                symbol=symbol,
                is_enabled=is_symbol_free(symbol),
            )
        )
    if rows_to_add:
        session.add_all(rows_to_add)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
        existing_rows = list(
            (
                await session.scalars(
                    select(UserCoinSubscription).where(UserCoinSubscription.user_id == user_id)
                )
            ).all()
        )
        active_rows = [row for row in existing_rows if row.symbol in SUPPORTED_SYMBOLS]
    return sorted(active_rows, key=lambda row: SUPPORTED_SYMBOLS.index(row.symbol))


async def set_user_coin_subscription(
    session: AsyncSession,
    *,
    user_id: int,
    symbol: str,
    is_enabled: bool,
) -> UserCoinSubscription:
    normalized_symbol = normalize_symbol(symbol)
    if normalized_symbol not in SUPPORTED_SYMBOLS:
        raise ValueError("Unsupported coin symbol.")
    row = await session.scalar(
        select(UserCoinSubscription)
        .where(UserCoinSubscription.user_id == user_id)
        .where(UserCoinSubscription.symbol == normalized_symbol)
        .limit(1)
    )
    if row is None:
        row = UserCoinSubscription(
            user_id=user_id,
            symbol=normalized_symbol,
            is_enabled=is_enabled,
        )
        session.add(row)
    else:
        row.is_enabled = is_enabled
        row.updated_at = utc_now()
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        row = await session.scalar(
            select(UserCoinSubscription)
            .where(UserCoinSubscription.user_id == user_id)
            .where(UserCoinSubscription.symbol == normalized_symbol)
            .limit(1)
        )
        if row is None:
            raise
        row.is_enabled = is_enabled
        row.updated_at = utc_now()
        await session.commit()
    await session.refresh(row)
    return row


async def set_user_alert_frequency(
    session: AsyncSession,
    *,
    user_id: int,
    frequency_seconds: int,
) -> User:
    if frequency_seconds not in PREMIUM_ALERT_FREQUENCY_SECONDS:
        raise ValueError("Unsupported alert frequency.")
    user = await session.get(User, user_id)
    if user is None:
        raise ValueError("User not found.")
    user.alert_frequency_seconds = int(frequency_seconds)
    user.updated_at = utc_now()
    await session.commit()
    await session.refresh(user)
    return user


async def get_user_premium_subscription(
    session: AsyncSession,
    *,
    user_id: int,
) -> UserPremiumSubscription | None:
    return await session.scalar(
        select(UserPremiumSubscription).where(UserPremiumSubscription.user_id == user_id).limit(1)
    )


async def get_payment_by_provider_id(
    session: AsyncSession,
    *,
    provider: str,
    provider_payment_id: str,
) -> Payment | None:
    return await session.scalar(
        select(Payment)
        .where(Payment.provider == provider)
        .where(Payment.provider_payment_id == provider_payment_id)
        .limit(1)
    )


def _normalize_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def activate_premium_from_telegram_stars_payment(
    session: AsyncSession,
    *,
    telegram_user_id: int,
    provider_payment_id: str,
    telegram_payment_charge_id: str | None,
    provider_payment_charge_id: str | None,
    amount: int,
    currency: str,
    payload: str,
    provider_subscription_id: str | None = None,
    is_recurring: bool | None = None,
    is_first_recurring: bool | None = None,
    subscription_expiration_date: datetime | None = None,
    now: datetime | None = None,
) -> tuple[Payment, UserPremiumSubscription, bool]:
    """Record one Stars payment and extend Premium once for that payment id."""
    lock = _payment_activation_locks.setdefault(int(telegram_user_id), asyncio.Lock())
    async with lock:
        return await _activate_premium_from_telegram_stars_payment_locked(
            session,
            telegram_user_id=telegram_user_id,
            provider_payment_id=provider_payment_id,
            telegram_payment_charge_id=telegram_payment_charge_id,
            provider_payment_charge_id=provider_payment_charge_id,
            amount=amount,
            currency=currency,
            payload=payload,
            provider_subscription_id=provider_subscription_id,
            is_recurring=is_recurring,
            is_first_recurring=is_first_recurring,
            subscription_expiration_date=subscription_expiration_date,
            now=now,
        )


async def _activate_premium_from_telegram_stars_payment_locked(
    session: AsyncSession,
    *,
    telegram_user_id: int,
    provider_payment_id: str,
    telegram_payment_charge_id: str | None,
    provider_payment_charge_id: str | None,
    amount: int,
    currency: str,
    payload: str,
    provider_subscription_id: str | None = None,
    is_recurring: bool | None = None,
    is_first_recurring: bool | None = None,
    subscription_expiration_date: datetime | None = None,
    now: datetime | None = None,
) -> tuple[Payment, UserPremiumSubscription, bool]:
    existing_payment = await get_payment_by_provider_id(
        session,
        provider=TELEGRAM_STARS_PROVIDER,
        provider_payment_id=provider_payment_id,
    )
    if existing_payment is not None:
        subscription = await get_user_premium_subscription(
            session,
            user_id=existing_payment.user_id,
        )
        return existing_payment, subscription, False

    user = await session.scalar(
        select(User).where(User.telegram_user_id == telegram_user_id).with_for_update().limit(1)
    )
    if user is None:
        raise ValueError("User not found.")

    now = now or utc_now()
    payment = Payment(
        user_id=user.id,
        provider=TELEGRAM_STARS_PROVIDER,
        provider_payment_id=provider_payment_id,
        provider_subscription_id=provider_subscription_id,
        telegram_payment_charge_id=telegram_payment_charge_id,
        provider_payment_charge_id=provider_payment_charge_id,
        is_recurring=is_recurring,
        is_first_recurring=is_first_recurring,
        subscription_expiration_date=_normalize_utc(subscription_expiration_date),
        amount=int(amount),
        currency=currency,
        payload=payload,
        status=PREMIUM_PAYMENT_STATUS_PAID,
    )
    session.add(payment)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        existing_payment = await get_payment_by_provider_id(
            session,
            provider=TELEGRAM_STARS_PROVIDER,
            provider_payment_id=provider_payment_id,
        )
        if existing_payment is None:
            raise
        subscription = await get_user_premium_subscription(
            session,
            user_id=existing_payment.user_id,
        )
        return existing_payment, subscription, False

    subscription = await session.scalar(
        select(UserPremiumSubscription)
        .where(UserPremiumSubscription.user_id == user.id)
        .with_for_update()
        .limit(1)
    )
    active_until = _normalize_utc(getattr(subscription, "active_until", None))
    active_from = max(now, active_until or now)
    if subscription is None:
        subscription = UserPremiumSubscription(
            user_id=user.id,
            plan="premium",
            status="active",
            active_until=active_from + timedelta(days=PREMIUM_PAYMENT_PERIOD_DAYS),
            started_at=now,
            cancelled_at=None,
            provider=TELEGRAM_STARS_PROVIDER,
            provider_subscription_id=provider_subscription_id,
            last_payment_id=str(payment.id),
        )
        session.add(subscription)
    else:
        subscription.plan = "premium"
        subscription.status = "active"
        subscription.active_until = active_from + timedelta(days=PREMIUM_PAYMENT_PERIOD_DAYS)
        subscription.started_at = subscription.started_at or now
        subscription.cancelled_at = None
        subscription.provider = TELEGRAM_STARS_PROVIDER
        subscription.provider_subscription_id = provider_subscription_id
        subscription.last_payment_id = str(payment.id)
        subscription.updated_at = now
    from bot.db.analytics import record_product_event

    await record_product_event(
        session,
        user_id=user.id,
        event_name="payment_succeeded",
        event_key=f"payment:{payment.id}",
        payment_id=payment.id,
        occurred_at=now,
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing_payment = await get_payment_by_provider_id(
            session,
            provider=TELEGRAM_STARS_PROVIDER,
            provider_payment_id=provider_payment_id,
        )
        if existing_payment is None:
            raise
        subscription = await get_user_premium_subscription(
            session,
            user_id=existing_payment.user_id,
        )
        return existing_payment, subscription, False
    await session.refresh(payment)
    await session.refresh(subscription)
    return payment, subscription, True


async def grant_user_premium(
    session: AsyncSession,
    *,
    telegram_user_id: int,
    days: int,
    now: datetime | None = None,
) -> UserPremiumSubscription:
    if days <= 0:
        raise ValueError("Premium grant days must be greater than 0.")
    user = await get_user_by_telegram_user_id(session, telegram_user_id)
    if user is None:
        raise ValueError("User not found.")

    now = now or utc_now()
    subscription = await get_user_premium_subscription(session, user_id=user.id)
    if subscription is None:
        active_from = now
        subscription = UserPremiumSubscription(
            user_id=user.id,
            plan="premium",
            status="active",
            active_until=active_from + timedelta(days=days),
            started_at=now,
            cancelled_at=None,
            provider="manual",
        )
        session.add(subscription)
    else:
        active_until = subscription.active_until
        if active_until is not None and active_until.tzinfo is None:
            active_until = active_until.replace(tzinfo=timezone.utc)
        active_from = max(now, active_until or now)
        subscription.plan = "premium"
        subscription.status = "active"
        subscription.active_until = active_from + timedelta(days=days)
        subscription.started_at = subscription.started_at or now
        subscription.cancelled_at = None
        subscription.provider = "manual"
        subscription.updated_at = now
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return await grant_user_premium(
            session,
            telegram_user_id=telegram_user_id,
            days=days,
            now=now,
        )
    await session.refresh(subscription)
    return subscription


async def revoke_user_premium(
    session: AsyncSession,
    *,
    telegram_user_id: int,
    now: datetime | None = None,
) -> UserPremiumSubscription:
    user = await get_user_by_telegram_user_id(session, telegram_user_id)
    if user is None:
        raise ValueError("User not found.")
    now = now or utc_now()
    subscription = await get_user_premium_subscription(session, user_id=user.id)
    if subscription is None:
        subscription = UserPremiumSubscription(
            user_id=user.id,
            plan="premium",
            status="revoked",
            active_until=now,
            started_at=None,
            cancelled_at=now,
            provider="manual",
        )
        session.add(subscription)
    else:
        subscription.status = "revoked"
        subscription.active_until = now
        subscription.cancelled_at = now
        subscription.provider = "manual"
        subscription.updated_at = now
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return await revoke_user_premium(session, telegram_user_id=telegram_user_id, now=now)
    await session.refresh(subscription)
    return subscription
