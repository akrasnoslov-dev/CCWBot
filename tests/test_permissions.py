from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock

import pytest

import bot.permissions as permissions


class SessionContext:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False


@pytest.mark.asyncio
async def test_db_admin_check_requires_env_allowlist_and_admin_role(monkeypatch):
    get_user_role = AsyncMock(return_value="admin")
    monkeypatch.setattr(permissions, "TELEGRAM_ADMIN_USER_IDS", (1001,))
    monkeypatch.setattr(permissions, "DB_ENABLED", True)
    monkeypatch.setattr(permissions, "DB_SESSION_LOCAL", lambda: SessionContext())
    monkeypatch.setattr(permissions, "get_user_role", get_user_role)

    assert await permissions.is_admin_user(1001) is True
    get_user_role.assert_awaited_once()


@pytest.mark.asyncio
async def test_db_admin_check_rejects_db_admin_when_env_id_does_not_match(monkeypatch):
    get_user_role = AsyncMock(return_value="admin")
    monkeypatch.setattr(permissions, "TELEGRAM_ADMIN_USER_IDS", (1001,))
    monkeypatch.setattr(permissions, "DB_ENABLED", True)
    monkeypatch.setattr(permissions, "DB_SESSION_LOCAL", lambda: SessionContext())
    monkeypatch.setattr(permissions, "get_user_role", get_user_role)

    assert await permissions.is_admin_user(2002) is False
    get_user_role.assert_not_awaited()


@pytest.mark.asyncio
async def test_db_admin_check_rejects_env_admin_without_db_admin_role(monkeypatch):
    monkeypatch.setattr(permissions, "TELEGRAM_ADMIN_USER_IDS", (1001,))
    monkeypatch.setattr(permissions, "DB_ENABLED", True)
    monkeypatch.setattr(permissions, "DB_SESSION_LOCAL", lambda: SessionContext())
    monkeypatch.setattr(permissions, "get_user_role", AsyncMock(return_value="user"))

    assert await permissions.is_admin_user(1001) is False


@pytest.mark.asyncio
async def test_db_admin_check_accepts_second_admin_from_combined_allowlist(monkeypatch):
    get_user_role = AsyncMock(return_value="admin")
    monkeypatch.setattr(permissions, "TELEGRAM_ADMIN_USER_IDS", (1001, 2002))
    monkeypatch.setattr(permissions, "DB_ENABLED", True)
    monkeypatch.setattr(permissions, "DB_SESSION_LOCAL", lambda: SessionContext())
    monkeypatch.setattr(permissions, "get_user_role", get_user_role)

    assert await permissions.is_admin_user("2002") is True
    get_user_role.assert_awaited_once()


@pytest.mark.asyncio
async def test_admin_check_ignores_invalid_user_id(monkeypatch):
    get_user_role = AsyncMock(return_value="admin")
    monkeypatch.setattr(permissions, "TELEGRAM_ADMIN_USER_IDS", (1001,))
    monkeypatch.setattr(permissions, "DB_ENABLED", True)
    monkeypatch.setattr(permissions, "DB_SESSION_LOCAL", lambda: SessionContext())
    monkeypatch.setattr(permissions, "get_user_role", get_user_role)

    assert await permissions.is_admin_user("not-a-user-id") is False
    get_user_role.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_user_from_update_does_not_store_group_chat(monkeypatch):
    get_or_create_user = AsyncMock()
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=1001, username="admin", first_name="Admin"),
        effective_chat=SimpleNamespace(id=-2001, type="group"),
    )
    monkeypatch.setattr(permissions, "DB_ENABLED", True)
    monkeypatch.setattr(permissions, "DB_SESSION_LOCAL", lambda: SessionContext())
    monkeypatch.setattr(permissions, "get_or_create_user", get_or_create_user)

    await permissions.sync_user_from_update(update)

    get_or_create_user.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_user_from_update_passes_optional_username(monkeypatch):
    get_or_create_user = AsyncMock()
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=1001, username=None, first_name="NoUsername"),
        effective_chat=SimpleNamespace(id=2001, type="private"),
    )
    monkeypatch.setattr(permissions, "TELEGRAM_ADMIN_USER_IDS", (9999,))
    monkeypatch.setattr(permissions, "DB_ENABLED", True)
    monkeypatch.setattr(permissions, "DB_SESSION_LOCAL", lambda: SessionContext())
    monkeypatch.setattr(permissions, "get_or_create_user", get_or_create_user)

    await permissions.sync_user_from_update(update)

    get_or_create_user.assert_awaited_once_with(
        ANY,
        telegram_user_id=1001,
        telegram_chat_id=2001,
        username=None,
        first_name="NoUsername",
        admin_user_ids=(9999,),
    )
