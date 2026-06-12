"""Global and legacy per-user settings persistence.

Belongs here: app-wide alert settings and legacy user settings rows.
Does not belong here: Premium/watchlist state, alert delivery records, market
snapshots, or schema/model declarations.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.database import AppSettings, UserSettings, utc_now


async def _get_app_settings_row(
    session: AsyncSession, *, default_threshold: float, default_interval: int
):
    settings = await session.scalar(select(AppSettings).order_by(AppSettings.id.asc()).limit(1))
    if settings is None:
        settings = AppSettings(
            btc_alert_threshold_percent=default_threshold,
            major_movement_threshold_percent=1.0,
            alt_movement_threshold_percent=2.0,
            major_24h_medium_threshold_percent=3.0,
            major_24h_high_threshold_percent=5.0,
            alt_24h_medium_threshold_percent=5.0,
            alt_24h_high_threshold_percent=8.0,
            automatic_check_interval_seconds=default_interval,
            error_file_logging_enabled=False,
        )
        session.add(settings)
        await session.commit()
        await session.refresh(settings)
        return settings

    changed = False
    if settings.btc_alert_threshold_percent is None:
        settings.btc_alert_threshold_percent = default_threshold
        changed = True
    if settings.automatic_check_interval_seconds is None:
        settings.automatic_check_interval_seconds = default_interval
        changed = True
    threshold_defaults = {
        "major_movement_threshold_percent": 1.0,
        "alt_movement_threshold_percent": 2.0,
        "major_24h_medium_threshold_percent": 3.0,
        "major_24h_high_threshold_percent": 5.0,
        "alt_24h_medium_threshold_percent": 5.0,
        "alt_24h_high_threshold_percent": 8.0,
    }
    for name, default_value in threshold_defaults.items():
        if getattr(settings, name, None) is None:
            setattr(settings, name, default_value)
            changed = True
    if settings.error_file_logging_enabled is None:
        settings.error_file_logging_enabled = False
        changed = True
    if changed:
        settings.updated_at = utc_now()
        await session.commit()
        await session.refresh(settings)
    return settings



async def get_or_create_app_settings(
    session: AsyncSession,
    *,
    default_threshold: float,
    default_interval: int,
) -> dict:
    settings = await _get_app_settings_row(
        session,
        default_threshold=default_threshold,
        default_interval=default_interval,
    )
    return {
        "btc_alert_threshold_percent": float(settings.btc_alert_threshold_percent),
        "automatic_check_interval_seconds": int(settings.automatic_check_interval_seconds),
        "error_file_logging_enabled": bool(settings.error_file_logging_enabled),
        "major_movement_threshold_percent": float(settings.major_movement_threshold_percent),
        "alt_movement_threshold_percent": float(settings.alt_movement_threshold_percent),
        "major_24h_medium_threshold_percent": float(settings.major_24h_medium_threshold_percent),
        "major_24h_high_threshold_percent": float(settings.major_24h_high_threshold_percent),
        "alt_24h_medium_threshold_percent": float(settings.alt_24h_medium_threshold_percent),
        "alt_24h_high_threshold_percent": float(settings.alt_24h_high_threshold_percent),
    }



async def update_app_settings(
    session: AsyncSession,
    *,
    default_threshold: float,
    default_interval: int,
    threshold: float | None = None,
    interval_seconds: int | None = None,
    error_file_logging_enabled: bool | None = None,
    threshold_updates: dict[str, float] | None = None,
) -> dict:
    settings = await _get_app_settings_row(
        session,
        default_threshold=default_threshold,
        default_interval=default_interval,
    )
    if threshold is not None:
        settings.btc_alert_threshold_percent = threshold
    if interval_seconds is not None:
        settings.automatic_check_interval_seconds = interval_seconds
    if error_file_logging_enabled is not None:
        settings.error_file_logging_enabled = error_file_logging_enabled
    for name, value in (threshold_updates or {}).items():
        if hasattr(settings, name):
            setattr(settings, name, float(value))
    settings.updated_at = utc_now()
    await session.commit()
    await session.refresh(settings)
    return await get_or_create_app_settings(
        session,
        default_threshold=default_threshold,
        default_interval=default_interval,
    )



async def get_or_create_user_settings(
    session: AsyncSession,
    *,
    user_id: int,
    default_threshold: float,
    default_interval: int,
):
    settings = await session.scalar(
        select(UserSettings).where(UserSettings.user_id == user_id).limit(1)
    )
    if settings is None:
        settings = UserSettings(
            user_id=user_id,
            price_move_alert_percent=default_threshold,
            automatic_check_interval_seconds=default_interval,
        )
        session.add(settings)
        await session.commit()
        await session.refresh(settings)
    return settings



async def update_user_settings(
    session: AsyncSession,
    *,
    user_id: int,
    threshold: float | None = None,
    interval_seconds: int | None = None,
):
    settings = await session.scalar(
        select(UserSettings).where(UserSettings.user_id == user_id).limit(1)
    )
    if settings is None:
        raise ValueError("User settings row not found.")
    if threshold is not None:
        settings.price_move_alert_percent = threshold
    if interval_seconds is not None:
        settings.automatic_check_interval_seconds = interval_seconds
    settings.updated_at = utc_now()
    await session.commit()
    await session.refresh(settings)
    return settings
