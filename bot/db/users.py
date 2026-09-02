"""User profile and Telegram delivery-state persistence.

Belongs here: user profile upserts, role lookup, active-recipient queries,
and bot-blocked delivery state.
Does not belong here: Premium entitlement math, alert delivery rows, market
analysis persistence, or schema/model declarations.
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.db.database import Alert, User, utc_now


def _same_telegram_user_id(left: int | str | None, right: int | str | None) -> bool:
    if left is None or right is None:
        return False
    try:
        return int(str(left).strip()) == int(str(right).strip())
    except ValueError:
        return False


def _telegram_user_id_in(
    telegram_user_id: int | str | None,
    admin_user_ids: tuple[int | str, ...] | list[int | str] | set[int | str] | None,
) -> bool:
    if admin_user_ids is None:
        return False
    return any(_same_telegram_user_id(telegram_user_id, admin_id) for admin_id in admin_user_ids)


async def get_or_create_user(
    session: AsyncSession,
    *,
    telegram_user_id: int,
    telegram_chat_id: int,
    username: str | None,
    first_name: str | None,
    admin_user_id: int | str | None = None,
    admin_user_ids: tuple[int | str, ...] | list[int | str] | set[int | str] | None = None,
):
    """Create or update profile fields for the current Telegram interaction."""
    user = await session.scalar(
        select(User).where(User.telegram_user_id == telegram_user_id).limit(1)
    )
    allowed_admin_user_ids = admin_user_ids or (() if admin_user_id is None else (admin_user_id,))
    role = "admin" if _telegram_user_id_in(telegram_user_id, allowed_admin_user_ids) else "user"
    created = user is None
    if user is None:
        user = User(
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
            username=username,
            first_name=first_name,
            role=role,
            is_active=True,
        )
        session.add(user)
    else:
        user.telegram_chat_id = telegram_chat_id
        user.username = username
        user.first_name = first_name
        if role == "admin":
            user.role = role
        elif user.role == "admin":
            user.role = "user"
        user.updated_at = utc_now()
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        user = await session.scalar(
            select(User).where(User.telegram_user_id == telegram_user_id).limit(1)
        )
        if user is None:
            raise
        user.telegram_chat_id = telegram_chat_id
        user.username = username
        user.first_name = first_name
        if role == "admin":
            user.role = role
        elif user.role == "admin":
            user.role = "user"
        user.updated_at = utc_now()
        await session.commit()
    await session.refresh(user)
    if created:
        from bot.db.premium import ensure_default_coin_subscriptions

        await ensure_default_coin_subscriptions(session, user_id=user.id)
    return user


async def get_user_role(session: AsyncSession, telegram_user_id: int) -> str | None:
    user = await session.scalar(
        select(User).where(User.telegram_user_id == telegram_user_id).limit(1)
    )
    return user.role if user else None


async def get_user_by_telegram_user_id(
    session: AsyncSession,
    telegram_user_id: int,
    *,
    include_plan: bool = False,
) -> User | None:
    statement = select(User).where(User.telegram_user_id == telegram_user_id).limit(1)
    if include_plan:
        statement = statement.options(
            selectinload(User.premium_subscription),
            selectinload(User.premium_trial),
        )
    return await session.scalar(statement)


async def get_active_users_with_chat_ids(session: AsyncSession) -> list[User]:
    """Return active users that can receive automatic Telegram alerts."""
    result = await session.scalars(
        select(User)
        .where(User.telegram_chat_id.isnot(None))
        .where(User.is_active.is_(True))
        .where(User.bot_blocked.is_(False))
        .order_by(User.id.asc())
    )
    return list(result.all())


async def get_active_users_with_alert_preferences(session: AsyncSession) -> list[User]:
    """Return active users with watchlist and Premium data loaded."""
    result = await session.scalars(
        select(User)
        .options(
            selectinload(User.coin_subscriptions),
            selectinload(User.premium_subscription),
            selectinload(User.premium_trial),
        )
        .where(User.telegram_chat_id.isnot(None))
        .where(User.is_active.is_(True))
        .where(User.bot_blocked.is_(False))
        .order_by(User.id.asc())
    )
    return list(result.all())


async def get_user_by_telegram_chat_id(session: AsyncSession, telegram_chat_id: int) -> User | None:
    """Return one user row for a Telegram chat id, if known."""
    return await session.scalar(
        select(User)
        .where(User.telegram_chat_id == telegram_chat_id)
        .order_by(User.id.asc())
        .limit(1)
    )


async def is_telegram_chat_delivery_enabled(session: AsyncSession, telegram_chat_id: int) -> bool:
    """Return whether a known chat can receive automatic bot messages."""
    user = await get_user_by_telegram_chat_id(session, telegram_chat_id)
    if user is None:
        return True
    return bool(user.is_active and not user.bot_blocked)


async def mark_user_bot_blocked(
    session: AsyncSession,
    *,
    user_id: int | None = None,
    telegram_chat_id: int | None = None,
    blocked_at: datetime | None = None,
) -> tuple[User | None, bool]:
    """Mark a user inactive after Telegram reports that the bot was blocked."""
    user = None
    if user_id is not None:
        user = await session.get(User, user_id)
    if user is None and telegram_chat_id is not None:
        user = await get_user_by_telegram_chat_id(session, telegram_chat_id)
    if user is None:
        return None, False

    changed = False
    if user.is_active:
        user.is_active = False
        changed = True
    if not user.bot_blocked:
        user.bot_blocked = True
        changed = True
    if user.blocked_at is None:
        user.blocked_at = blocked_at or utc_now()
        changed = True
    if changed:
        user.updated_at = utc_now()
        await session.commit()
        await session.refresh(user)
    return user, changed


async def backfill_blocked_users_from_alerts(session: AsyncSession) -> tuple[int, int]:
    """Disable users with historical failed Telegram blocked-user delivery records."""
    result = await session.execute(
        select(Alert.user_id, Alert.sent_to_chat_id, Alert.created_at)
        .where(Alert.error_message.isnot(None))
        .where(func.lower(Alert.error_message).contains("bot was blocked by the user"))
        .order_by(Alert.created_at.asc(), Alert.id.asc())
    )
    rows = list(result.all())
    updated_user_ids: set[int] = set()
    seen_user_ids: set[int] = set()

    for user_id, sent_to_chat_id, created_at in rows:
        user = None
        if user_id is not None:
            user = await session.get(User, user_id)
        if user is None and sent_to_chat_id is not None:
            user = await get_user_by_telegram_chat_id(session, int(sent_to_chat_id))
        if user is None or user.id in seen_user_ids:
            continue
        seen_user_ids.add(user.id)
        _, changed = await mark_user_bot_blocked(
            session,
            user_id=user.id,
            telegram_chat_id=int(sent_to_chat_id) if sent_to_chat_id is not None else None,
            blocked_at=created_at,
        )
        if changed:
            updated_user_ids.add(user.id)

    return len(rows), len(updated_user_ids)
