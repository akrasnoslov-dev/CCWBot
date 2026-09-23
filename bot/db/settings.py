"""Global and legacy per-user settings persistence.

Belongs here: app-wide alert settings and legacy user settings rows.
Does not belong here: Premium/watchlist state, alert delivery records, market
snapshots, or schema/model declarations.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.database import AppSettings, UserSettings, utc_now


async def _get_app_settings_row(session: AsyncSession, *, default_interval: int):
    settings = await session.scalar(select(AppSettings).order_by(AppSettings.id.asc()).limit(1))
    if settings is None:
        settings = AppSettings(
            automatic_check_interval_seconds=default_interval,
            error_file_logging_enabled=False,
        )
        session.add(settings)
        await session.commit()
        await session.refresh(settings)
        return settings

    changed = False
    if settings.automatic_check_interval_seconds is None:
        settings.automatic_check_interval_seconds = default_interval
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
    default_interval: int,
) -> dict:
    settings = await _get_app_settings_row(
        session,
        default_interval=default_interval,
    )
    return {
        "automatic_check_interval_seconds": int(settings.automatic_check_interval_seconds),
        "error_file_logging_enabled": bool(settings.error_file_logging_enabled),
    }



async def update_app_settings(
    session: AsyncSession,
    *,
    default_interval: int,
    interval_seconds: int | None = None,
    error_file_logging_enabled: bool | None = None,
) -> dict:
    settings = await _get_app_settings_row(
        session,
        default_interval=default_interval,
    )
    if interval_seconds is not None:
        settings.automatic_check_interval_seconds = interval_seconds
    if error_file_logging_enabled is not None:
        settings.error_file_logging_enabled = error_file_logging_enabled
    settings.updated_at = utc_now()
    await session.commit()
    await session.refresh(settings)
    return await get_or_create_app_settings(
        session,
        default_interval=default_interval,
    )



async def get_or_create_user_settings(
    session: AsyncSession,
    *,
    user_id: int,
    default_interval: int,
):
    settings = await session.scalar(
        select(UserSettings).where(UserSettings.user_id == user_id).limit(1)
    )
    if settings is None:
        settings = UserSettings(
            user_id=user_id,
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
    interval_seconds: int | None = None,
):
    settings = await session.scalar(
        select(UserSettings).where(UserSettings.user_id == user_id).limit(1)
    )
    if settings is None:
        raise ValueError("User settings row not found.")
    if interval_seconds is not None:
        settings.automatic_check_interval_seconds = interval_seconds
    settings.updated_at = utc_now()
    await session.commit()
    await session.refresh(settings)
    return settings
