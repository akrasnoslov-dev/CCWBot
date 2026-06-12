"""Price snapshot and per-symbol alert-state persistence.

Belongs here: current price state, historical price snapshots, and per-user
symbol alert baselines.
Does not belong here: CoinGecko HTTP calls, alert delivery rows, news state,
or schema/model declarations.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.database import (
    PriceSnapshot,
    PriceState,
    UserSymbolAlertState,
    normalize_stored_severity,
    utc_now,
)
from bot.domain.supported_coins import normalize_symbol


async def get_price_state(session: AsyncSession, symbol: str):
    return await session.scalar(
        select(PriceState).where(PriceState.symbol == symbol.upper()).limit(1)
    )



async def update_price_state(
    session: AsyncSession,
    *,
    symbol: str,
    last_price: float,
    last_24h_change: float,
    last_checked_at: datetime | None,
    last_alert_at: datetime | None = None,
):
    row = await get_price_state(session, symbol)
    if row is None:
        row = PriceState(
            symbol=symbol.upper(),
            last_price=last_price,
            last_24h_change=last_24h_change,
            last_checked_at=last_checked_at,
            last_alert_at=last_alert_at,
        )
        session.add(row)
    else:
        row.last_price = last_price
        row.last_24h_change = last_24h_change
        row.last_checked_at = last_checked_at
        if last_alert_at is not None:
            row.last_alert_at = last_alert_at
    row.updated_at = utc_now()
    await session.commit()
    await session.refresh(row)
    return row



async def save_price_snapshot(
    session: AsyncSession,
    *,
    symbol: str,
    price: float,
    change_24h: float | None,
    checked_at: datetime,
    change_7d: float | None = None,
    source: str = "coingecko",
) -> PriceSnapshot:
    row = PriceSnapshot(
        symbol=symbol.upper(),
        price=price,
        change_24h=change_24h,
        change_7d=change_7d,
        source=source,
        checked_at=checked_at,
        created_at=checked_at,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row



async def get_reference_price_snapshot(
    session: AsyncSession,
    *,
    symbol: str,
    at_or_before: datetime,
) -> PriceSnapshot | None:
    return await session.scalar(
        select(PriceSnapshot)
        .where(PriceSnapshot.symbol == symbol.upper())
        .where(PriceSnapshot.checked_at <= at_or_before)
        .order_by(PriceSnapshot.checked_at.desc(), PriceSnapshot.id.desc())
        .limit(1)
    )



async def get_price_snapshots_since(
    session: AsyncSession,
    *,
    symbol: str,
    since: datetime,
) -> list[PriceSnapshot]:
    rows = await session.scalars(
        select(PriceSnapshot)
        .where(PriceSnapshot.symbol == symbol.upper())
        .where(PriceSnapshot.checked_at >= since)
        .order_by(PriceSnapshot.checked_at.asc(), PriceSnapshot.id.asc())
    )
    return list(rows.all())



async def get_user_symbol_alert_state(
    session: AsyncSession,
    *,
    user_id: int,
    symbol: str,
) -> UserSymbolAlertState | None:
    """Return per-user per-symbol alert state, if it exists."""
    return await session.scalar(
        select(UserSymbolAlertState)
        .where(UserSymbolAlertState.user_id == user_id)
        .where(UserSymbolAlertState.symbol == normalize_symbol(symbol))
        .limit(1)
    )



async def upsert_user_symbol_alert_state(
    session: AsyncSession,
    *,
    user_id: int,
    symbol: str,
    last_market_update_time: datetime | None = None,
    last_important_alert_time: datetime | None = None,
    last_critical_alert_time: datetime | None = None,
    last_notification_type: str | None = None,
    last_notification_severity: str | None = None,
    last_notification_direction: str | None = None,
    last_cumulative_movement_percent: float | None = None,
) -> UserSymbolAlertState:
    """Create or update per-user per-symbol alert state."""
    normalized_symbol = normalize_symbol(symbol)
    row = await get_user_symbol_alert_state(
        session,
        user_id=user_id,
        symbol=normalized_symbol,
    )
    if row is None:
        row = UserSymbolAlertState(user_id=user_id, symbol=normalized_symbol)
        session.add(row)
    if last_market_update_time is not None:
        row.last_market_update_time = last_market_update_time
    if last_important_alert_time is not None:
        row.last_important_alert_time = last_important_alert_time
    if last_critical_alert_time is not None:
        row.last_critical_alert_time = last_critical_alert_time
    if last_notification_type is not None:
        row.last_notification_type = last_notification_type
    if last_notification_severity is not None:
        row.last_notification_severity = normalize_stored_severity(last_notification_severity)
    if last_notification_direction is not None:
        row.last_notification_direction = last_notification_direction
    if last_cumulative_movement_percent is not None:
        row.last_cumulative_movement_percent = last_cumulative_movement_percent
    row.updated_at = utc_now()
    await session.commit()
    await session.refresh(row)
    return row
