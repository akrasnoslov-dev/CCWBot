from importlib import import_module
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from telegram.error import BadRequest

from bot.handlers.common import safe_delete_command_invocation, safe_edit_callback_message
from bot.handlers.settings import settings


@pytest.mark.asyncio
async def test_command_invocation_is_deleted_only_in_private_chat():
    private_message = SimpleNamespace(delete=AsyncMock())
    private_update = SimpleNamespace(
        message=private_message,
        effective_chat=SimpleNamespace(type="private"),
    )
    group_message = SimpleNamespace(delete=AsyncMock())
    group_update = SimpleNamespace(
        message=group_message,
        effective_chat=SimpleNamespace(type="group"),
    )

    assert await safe_delete_command_invocation(private_update) is True
    assert await safe_delete_command_invocation(group_update) is False
    private_message.delete.assert_awaited_once()
    group_message.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_command_deletion_failure_does_not_escape():
    message = SimpleNamespace(delete=AsyncMock(side_effect=BadRequest("cannot delete")))
    update = SimpleNamespace(message=message, effective_chat=SimpleNamespace(type="private"))

    assert await safe_delete_command_invocation(update) is False

    message.delete = AsyncMock(side_effect=RuntimeError("unexpected"))
    assert await safe_delete_command_invocation(update) is False


@pytest.mark.asyncio
async def test_callback_navigation_edits_existing_message():
    query = SimpleNamespace(edit_message_text=AsyncMock())

    assert await safe_edit_callback_message(query, "System status") is True
    query.edit_message_text.assert_awaited_once_with(text="System status")


@pytest.mark.asyncio
async def test_settings_denies_non_admin_without_loading_settings(monkeypatch):
    reply = AsyncMock()
    update = SimpleNamespace(
        message=SimpleNamespace(reply_text=reply),
        effective_user=SimpleNamespace(id=1001),
        effective_chat=SimpleNamespace(type="group"),
    )
    context = SimpleNamespace(user_data={})
    monkeypatch.setattr("bot.handlers.sync_user_from_update", AsyncMock())
    monkeypatch.setattr("bot.handlers.is_admin_update", AsyncMock(return_value=False))
    monkeypatch.setattr("bot.handlers.is_admin_user", AsyncMock(return_value=False))
    loader = AsyncMock()
    monkeypatch.setattr("bot.handlers.settings_command", loader)

    await settings(update, context)

    loader.assert_not_awaited()
    assert "only the bot admin" in reply.await_args.args[0]


@pytest.mark.asyncio
async def test_admin_settings_renders_global_alert_controls(monkeypatch):
    reply = AsyncMock()
    update = SimpleNamespace(
        message=SimpleNamespace(reply_text=reply, delete=AsyncMock()),
        effective_user=SimpleNamespace(id=1001),
        effective_chat=SimpleNamespace(type="private"),
    )
    context = SimpleNamespace(user_data={})
    monkeypatch.setattr("bot.handlers.sync_user_from_update", AsyncMock())
    monkeypatch.setattr("bot.handlers.is_admin_update", AsyncMock(return_value=True))
    monkeypatch.setattr("bot.handlers.is_admin_user", AsyncMock(return_value=True))
    monkeypatch.setattr("bot.handlers.DB_ENABLED", False)
    settings_module = import_module("bot.handlers.settings")
    monkeypatch.setattr(
        settings_module, "get_state_alert_settings",
        lambda state: {"automatic_check_interval_seconds": 1800}
    )
    monkeypatch.setattr(settings_module, "load_state", lambda: {})

    await settings(update, context)

    text = reply.await_args.args[0]
    markup = reply.await_args.kwargs["reply_markup"]
    callbacks = [button.callback_data for row in markup.inline_keyboard for button in row]
    assert "Current alert settings" in text
    assert callbacks == ["admin:current", "admin:interval_menu", "admin:back"]
