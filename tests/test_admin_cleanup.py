from importlib import import_module
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from telegram.ext import CommandHandler

from bot.handlers import button_router
from bot.keyboards import (
    build_admin_alert_settings_keyboard,
    build_admin_keyboard,
    build_admin_logs_keyboard,
    build_admin_premium_keyboard,
    build_interval_keyboard,
)
from main import register_handlers


def _callback_values(markup):
    return [
        button.callback_data
        for row in markup.inline_keyboard
        for button in row
        if button.callback_data
    ]


def test_admin_alert_settings_keyboard_has_no_threshold_controls():
    callbacks = _callback_values(build_admin_alert_settings_keyboard())
    labels = [
        button.text
        for row in build_admin_alert_settings_keyboard().inline_keyboard
        for button in row
    ]

    assert callbacks == ["admin:current", "admin:interval_menu", "admin:back"]
    assert labels == ["Current settings", "Event analysis interval", "Back"]
    assert all("threshold" not in callback for callback in callbacks)


def test_interval_keyboard_only_offers_supported_event_analysis_cadence():
    buttons = [
        (button.text, button.callback_data)
        for row in build_interval_keyboard().inline_keyboard
        for button in row
    ]

    assert buttons == [
        ("1800 sec", "admin:set_interval:1800"),
        ("Back", "admin:alert_settings"),
    ]


def test_admin_keyboards_have_expected_items():
    keyboard_expectations = [
        (
            build_admin_keyboard(),
            [
                ("Alert settings", "admin:alert_settings"),
                ("System status", "admin:system_status"),
                ("LLM diagnostics", "admin:llm_diagnostics"),
                ("Premium management", "admin:premium_menu"),
                ("Logs", "admin:logs_menu"),
            ],
        ),
        (
            build_admin_premium_keyboard(),
            [
                ("Grant premium", "admin:premium_grant"),
                ("Revoke premium", "admin:premium_revoke"),
                ("Back", "admin:back"),
            ],
        ),
        (
            build_admin_logs_keyboard(),
            [
                ("ON / OFF", "admin:logs_toggle"),
                ("Status", "admin:logs_status"),
                ("Export logs", "admin:logs_export"),
                ("Back", "admin:back"),
            ],
        ),
    ]

    for markup, expected_buttons in keyboard_expectations:
        buttons = [
            (button.text, button.callback_data)
            for row in markup.inline_keyboard
            for button in row
        ]
        assert buttons == expected_buttons


def test_legacy_alert_commands_are_not_registered():
    handlers = []
    error_handlers = []
    app = SimpleNamespace(
        add_handler=handlers.append,
        add_error_handler=error_handlers.append,
    )

    register_handlers(app)

    assert len(error_handlers) == 1  # the global log-only error handler is registered

    commands = {
        command
        for handler in handlers
        if isinstance(handler, CommandHandler)
        for command in handler.commands
    }
    assert "plan" in commands
    assert "myplan" in commands
    assert "subscribe" in commands
    assert "setinterval" in commands
    assert "status" not in commands
    assert "grantpremium" in commands
    assert "revokepremium" in commands
    assert "error_logging_on" in commands
    assert "error_logging_off" in commands
    assert "error_logging_status" in commands
    assert "acquisitionlink" in commands
    assert "acquisitionlinks" in commands
    assert "setcooldown" not in commands
    assert "setthreshold" not in commands


@pytest.mark.asyncio
async def test_premium_menu_usage_callbacks(monkeypatch):
    replies = []

    update, context = _callback_update("admin:premium_grant", replies=replies)
    monkeypatch.setattr("bot.handlers.is_admin_user", AsyncTrue())

    await button_router(update, context)

    assert replies == [
        (
            "Grant premium\n\n"
            "Usage:\n"
            "/grantpremium <telegram_user_id|me> <days>\n\n"
            "Examples:\n"
            "/grantpremium 123456789 30\n"
            "/grantpremium me 7"
        )
    ]

    replies.clear()
    update, context = _callback_update("admin:premium_revoke", replies=replies)

    await button_router(update, context)

    assert replies == [
        (
            "Revoke premium\n\n"
            "Usage:\n"
            "/revokepremium <telegram_user_id|me>\n\n"
            "Examples:\n"
            "/revokepremium 123456789\n"
            "/revokepremium me"
        )
    ]


@pytest.mark.asyncio
async def test_llm_diagnostics_callback_denies_non_admin_before_render(monkeypatch):
    replies = []
    update, context = _callback_update("admin:llm_diagnostics", replies=replies)
    builder = AsyncMock(return_value="must not render")
    monkeypatch.setattr("bot.handlers.is_admin_user", AsyncFalse())
    monkeypatch.setattr(
        import_module("bot.handlers.admin"), "_build_admin_llm_diagnostics_text", builder
    )

    await button_router(update, context)

    builder.assert_not_awaited()
    assert all("must not render" not in reply for reply in replies)

@pytest.mark.asyncio
async def test_logs_status_callback_matches_error_logging_status(monkeypatch):
    replies = []
    update, context = _callback_update("admin:logs_status", replies=replies)
    monkeypatch.setattr("bot.handlers.is_admin_user", AsyncTrue())
    monkeypatch.setattr("bot.handlers.get_runtime_error_file_logging_enabled", AsyncTrue())
    monkeypatch.setattr("bot.handlers.is_error_file_logging_enabled", lambda: True)

    await button_router(update, context)

    assert replies == ["Warning/error file logging: enabled (active)."]


@pytest.mark.asyncio
async def test_logs_toggle_callback_uses_error_logging_toggle(monkeypatch):
    replies = []
    saved_states = []
    update, context = _callback_update("admin:logs_toggle", replies=replies)
    monkeypatch.setattr("bot.handlers.is_admin_user", AsyncTrue())
    monkeypatch.setattr("bot.handlers.get_runtime_error_file_logging_enabled", AsyncFalse())

    async def save_enabled(enabled):
        saved_states.append(enabled)

    monkeypatch.setattr("bot.handlers.save_error_file_logging_enabled", save_enabled)
    monkeypatch.setattr("bot.handlers.enable_error_file_logging", lambda: "logs/test.log")

    await button_router(update, context)

    assert saved_states == [True]
    assert replies == ["Warning/error file logging enabled.\nPath: logs/test.log"]


@pytest.mark.asyncio
async def test_logs_export_sends_sanitized_files(monkeypatch):
    documents = []
    update, context = _callback_update("admin:logs_export", documents=documents)
    monkeypatch.setattr("bot.handlers.is_admin_user", AsyncTrue())
    monkeypatch.setattr(
        "bot.handlers.build_sanitized_log_exports",
        lambda: [SimpleNamespace(file_name="ccwbot-warnings-errors.log", content=b"safe")],
    )

    await button_router(update, context)

    assert len(documents) == 1
    assert documents[0]["filename"] == "ccwbot-warnings-errors.log"
    assert documents[0]["document"].getvalue() == b"safe"


@pytest.mark.asyncio
async def test_logs_export_reports_when_no_files(monkeypatch):
    replies = []
    update, context = _callback_update("admin:logs_export", replies=replies)
    monkeypatch.setattr("bot.handlers.is_admin_user", AsyncTrue())
    monkeypatch.setattr("bot.handlers.build_sanitized_log_exports", lambda: [])

    await button_router(update, context)

    assert replies == [
        "No log files are available. Enable warning/error file logging and try again "
        "after a warning or error is recorded."
    ]


def _callback_update(data, *, replies=None, documents=None):
    message = FakeMessage(
        replies if replies is not None else [],
        documents if documents is not None else [],
    )
    query = FakeQuery(data, message)
    return (
        SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1001)),
        SimpleNamespace(application=SimpleNamespace(), user_data={}),
    )


class FakeQuery:
    def __init__(self, data, message):
        self.data = data
        self.from_user = SimpleNamespace(id=1001)
        self.message = message
        self.answers = []

    async def answer(self, text=None):
        self.answers.append(text)

    async def edit_message_text(self, text, **kwargs):
        self.message.replies.append(text)


class FakeMessage:
    def __init__(self, replies, documents):
        self.replies = replies
        self.documents = documents

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)

    async def reply_document(self, document, filename=None, caption=None, **kwargs):
        self.documents.append(
            {"document": document, "filename": filename, "caption": caption}
        )


class AsyncFalse:
    async def __call__(self, *args, **kwargs):
        return False


class AsyncTrue:
    async def __call__(self, *args, **kwargs):
        return True
