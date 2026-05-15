from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.db.database import Base, User, get_or_create_user


async def build_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    return engine, SessionLocal()


@pytest.mark.asyncio
async def test_get_or_create_user_saves_username_for_new_user():
    engine, session = await build_session()
    try:
        user = await get_or_create_user(
            session,
            telegram_user_id=1001,
            telegram_chat_id=2001,
            username="satoshi",
            first_name="Satoshi",
            admin_user_id=None,
        )

        assert user.telegram_user_id == 1001
        assert user.telegram_chat_id == 2001
        assert user.username == "satoshi"
        assert user.first_name == "Satoshi"
        assert user.role == "user"
        assert user.is_active is True
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_get_or_create_user_updates_existing_profile_without_resetting_settings():
    engine, session = await build_session()
    try:
        user = User(
            telegram_user_id=1001,
            telegram_chat_id=2001,
            username=None,
            first_name="Old",
            role="reviewer",
            is_active=False,
            alert_frequency_seconds=900,
            updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        session.add(user)
        await session.commit()

        updated = await get_or_create_user(
            session,
            telegram_user_id=1001,
            telegram_chat_id=3001,
            username="new_name",
            first_name="New",
            admin_user_id=None,
        )

        assert updated.id == user.id
        assert updated.telegram_chat_id == 3001
        assert updated.username == "new_name"
        assert updated.first_name == "New"
        assert updated.role == "reviewer"
        assert updated.is_active is False
        assert updated.alert_frequency_seconds == 900
        assert updated.updated_at != datetime(2024, 1, 1, tzinfo=timezone.utc)
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_get_or_create_user_allows_missing_username():
    engine, session = await build_session()
    try:
        user = await get_or_create_user(
            session,
            telegram_user_id=1001,
            telegram_chat_id=2001,
            username=None,
            first_name="NoUsername",
            admin_user_id=None,
        )

        assert user.username is None
        assert user.first_name == "NoUsername"
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_get_or_create_user_updates_changed_username():
    engine, session = await build_session()
    try:
        await get_or_create_user(
            session,
            telegram_user_id=1001,
            telegram_chat_id=2001,
            username="old_name",
            first_name="Old",
            admin_user_id=None,
        )

        updated = await get_or_create_user(
            session,
            telegram_user_id=1001,
            telegram_chat_id=2001,
            username="changed_name",
            first_name="Changed",
            admin_user_id=None,
        )

        assert updated.username == "changed_name"
        assert updated.first_name == "Changed"
    finally:
        await session.close()
        await engine.dispose()
