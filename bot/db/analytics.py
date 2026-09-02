"""Durable, allowlisted product analytics persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.database import (
    AcquisitionLink,
    Payment,
    ProductEvent,
    UserAcquisitionAttribution,
    utc_now,
)
from bot.domain.attribution import (
    AttributionLinkToken,
    generate_acquisition_link_code,
    validate_acquisition_link_metadata,
)
from bot.domain.supported_coins import SUPPORTED_SYMBOLS, normalize_symbol

PRODUCT_EVENT_NAMES = frozenset(
    {
        "bot_started",
        "onboarding_started",
        "coin_interest_selected",
        "onboarding_completed",
        "instant_brief_viewed",
        "watchlist_updated",
        "trial_offered",
        "trial_started",
        "trial_expired",
        "paywall_viewed",
        "checkout_started",
        "payment_succeeded",
        "premium_value_delivered",
    }
)

_EVENT_FIELDS = {
    "bot_started": frozenset(),
    "onboarding_started": frozenset({"event_key"}),
    "coin_interest_selected": frozenset({"event_key", "symbol", "selected_coin_count"}),
    "onboarding_completed": frozenset({"event_key", "selected_coin_count"}),
    "instant_brief_viewed": frozenset({"event_key", "selected_coin_count"}),
    "watchlist_updated": frozenset({"event_key", "symbol", "selected_coin_count"}),
    "trial_offered": frozenset({"event_key", "selected_coin_count"}),
    "trial_started": frozenset({"event_key", "selected_coin_count"}),
    "trial_expired": frozenset({"event_key"}),
    "paywall_viewed": frozenset({"event_key", "selected_coin_count"}),
    "checkout_started": frozenset({"event_key"}),
    "payment_succeeded": frozenset({"event_key", "payment_id"}),
    "premium_value_delivered": frozenset({"event_key", "selected_coin_count"}),
}
ACQUISITION_LINK_CREATION_ATTEMPTS = 5


def _is_acquisition_link_code_collision(error: IntegrityError) -> bool:
    message = str(error.orig).lower()
    return (
        "uq_acquisition_links_link_code" in message
        or "acquisition_links.link_code" in message
    )


@dataclass(frozen=True)
class AcquisitionAttribution:
    """Trusted attribution resolved from an operator-managed acquisition link."""

    source: str
    campaign: str | None
    creative: str | None
    referrer_code: str | None


async def create_acquisition_link(
    session: AsyncSession,
    *,
    source: object,
    campaign: object = None,
    creative: object = None,
    referrer_code: object = None,
) -> AcquisitionLink:
    """Create one collision-safe, validated operator acquisition link."""

    metadata = validate_acquisition_link_metadata(
        source=source,
        campaign=campaign,
        creative=creative,
        referrer_code=referrer_code,
    )
    for _ in range(ACQUISITION_LINK_CREATION_ATTEMPTS):
        row = AcquisitionLink(
            link_code=generate_acquisition_link_code(),
            source=metadata.source,
            campaign=metadata.campaign,
            creative=metadata.creative,
            referrer_code=metadata.referrer_code,
            is_active=True,
        )
        try:
            async with session.begin_nested():
                session.add(row)
                await session.flush()
        except IntegrityError as error:
            if _is_acquisition_link_code_collision(error):
                continue
            raise
        await session.commit()
        await session.refresh(row)
        return row
    raise RuntimeError("Unable to allocate an acquisition link code.")


async def list_active_acquisition_links(
    session: AsyncSession,
    *,
    limit: int = 20,
    now: datetime | None = None,
) -> list[AcquisitionLink]:
    """List a bounded set of links which may currently attribute a start."""

    if not 1 <= limit <= 100:
        raise ValueError("Acquisition link list limit must be between 1 and 100.")
    active_at = now or utc_now()
    rows = await session.scalars(
        select(AcquisitionLink)
        .where(AcquisitionLink.is_active.is_(True))
        .where(or_(AcquisitionLink.expires_at.is_(None), AcquisitionLink.expires_at > active_at))
        .order_by(AcquisitionLink.created_at.desc(), AcquisitionLink.id.desc())
        .limit(limit)
    )
    return list(rows)


async def resolve_start_attribution(
    session: AsyncSession,
    *,
    token: AttributionLinkToken | None,
    now: datetime | None = None,
) -> AcquisitionAttribution | None:
    """Resolve an active opaque deep-link token into configured attribution."""
    if token is None:
        return None
    captured_at = now or utc_now()
    link = await session.scalar(
        select(AcquisitionLink)
        .where(AcquisitionLink.link_code == token.link_code)
        .where(AcquisitionLink.is_active.is_(True))
        .where((AcquisitionLink.expires_at.is_(None)) | (AcquisitionLink.expires_at > captured_at))
        .limit(1)
    )
    if link is None:
        return None
    return AcquisitionAttribution(
        source=link.source,
        campaign=link.campaign,
        creative=link.creative,
        referrer_code=link.referrer_code,
    )


def _validate_event(
    *,
    event_name: str,
    event_key: str | None,
    symbol: str | None,
    selected_coin_count: int | None,
    payment_id: int | None,
) -> tuple[str, str | None, int | None]:
    if event_name not in PRODUCT_EVENT_NAMES:
        raise ValueError("Unsupported product event.")
    if event_key is not None and (not event_key or len(event_key) > 128):
        raise ValueError("Invalid product event key.")
    allowed_fields = _EVENT_FIELDS[event_name]
    provided_fields = {
        name
        for name, value in (
            ("event_key", event_key),
            ("symbol", symbol),
            ("selected_coin_count", selected_coin_count),
            ("payment_id", payment_id),
        )
        if value is not None
    }
    if not provided_fields.issubset(allowed_fields):
        raise ValueError("Unsupported product event properties.")
    normalized_symbol = None
    if symbol is not None:
        normalized_symbol = normalize_symbol(symbol)
        if normalized_symbol not in SUPPORTED_SYMBOLS:
            raise ValueError("Unsupported product event symbol.")
    if selected_coin_count is not None and not 0 <= selected_coin_count <= len(SUPPORTED_SYMBOLS):
        raise ValueError("Invalid selected coin count.")
    if payment_id is not None and event_name != "payment_succeeded":
        raise ValueError("Only payment_succeeded may reference a payment.")
    return event_name, normalized_symbol, selected_coin_count


async def capture_first_touch_attribution(
    session: AsyncSession,
    *,
    user_id: int,
    attribution: AcquisitionAttribution | None,
    now: datetime | None = None,
) -> UserAcquisitionAttribution | None:
    """Persist first-touch attribution without replacing a prior acquisition."""
    if attribution is None:
        return None
    existing = await session.scalar(
        select(UserAcquisitionAttribution)
        .where(UserAcquisitionAttribution.user_id == user_id)
        .limit(1)
    )
    if existing is not None:
        return existing
    row = UserAcquisitionAttribution(
        user_id=user_id,
        source=attribution.source,
        campaign=attribution.campaign,
        creative=attribution.creative,
        referrer_code=attribution.referrer_code,
        captured_at=now or utc_now(),
    )
    try:
        async with session.begin_nested():
            session.add(row)
            await session.flush()
    except IntegrityError:
        existing = await session.scalar(
            select(UserAcquisitionAttribution)
            .where(UserAcquisitionAttribution.user_id == user_id)
            .limit(1)
        )
        if existing is None:
            raise
        return existing
    return row


async def record_product_event(
    session: AsyncSession,
    *,
    user_id: int,
    event_name: str,
    event_key: str | None = None,
    symbol: str | None = None,
    selected_coin_count: int | None = None,
    payment_id: int | None = None,
    occurred_at: datetime | None = None,
) -> tuple[ProductEvent, bool]:
    """Record one typed event; a duplicate lifecycle key returns the original."""
    event_name, normalized_symbol, selected_coin_count = _validate_event(
        event_name=event_name,
        event_key=event_key,
        symbol=symbol,
        selected_coin_count=selected_coin_count,
        payment_id=payment_id,
    )
    if event_key is not None:
        existing = await session.scalar(
            select(ProductEvent)
            .where(ProductEvent.user_id == user_id)
            .where(ProductEvent.event_name == event_name)
            .where(ProductEvent.event_key == event_key)
            .limit(1)
        )
        if existing is not None:
            return existing, False
    if payment_id is not None:
        payment = await session.get(Payment, payment_id)
        if payment is None or payment.user_id != user_id:
            raise ValueError("Product event payment does not belong to this user.")
        existing = await session.scalar(
            select(ProductEvent).where(ProductEvent.payment_id == payment_id).limit(1)
        )
        if existing is not None:
            return existing, False
    row = ProductEvent(
        user_id=user_id,
        event_name=event_name,
        event_key=event_key,
        symbol=normalized_symbol,
        selected_coin_count=selected_coin_count,
        payment_id=payment_id,
        occurred_at=occurred_at or utc_now(),
    )
    try:
        async with session.begin_nested():
            session.add(row)
            await session.flush()
    except IntegrityError:
        if event_key is not None:
            existing = await session.scalar(
                select(ProductEvent)
                .where(ProductEvent.user_id == user_id)
                .where(ProductEvent.event_name == event_name)
                .where(ProductEvent.event_key == event_key)
                .limit(1)
            )
            if existing is not None:
                return existing, False
        if payment_id is not None:
            existing = await session.scalar(
                select(ProductEvent).where(ProductEvent.payment_id == payment_id).limit(1)
            )
            if existing is not None:
                return existing, False
        raise
    return row, True


async def record_bot_started(
    session: AsyncSession,
    *,
    user_id: int,
    attribution: AcquisitionAttribution | None,
) -> ProductEvent:
    """Atomically save eligible first-touch attribution and a bot start event."""
    await capture_first_touch_attribution(session, user_id=user_id, attribution=attribution)
    event, _ = await record_product_event(session, user_id=user_id, event_name="bot_started")
    await session.commit()
    await session.refresh(event)
    return event
