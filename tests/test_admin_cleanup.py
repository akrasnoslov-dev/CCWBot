from types import SimpleNamespace

import pytest

from bot.handlers import button_router
from bot.keyboards import build_admin_alert_settings_keyboard


def _callback_values(markup):
    return [
        button.callback_data
        for row in markup.inline_keyboard
        for button in row
        if button.callback_data
    ]


def test_admin_alert_settings_keyboard_has_no_threshold_controls():
    callbacks = _callback_values(build_admin_alert_settings_keyboard())

    assert callbacks == ["admin:current", "admin:interval_menu"]
    assert all("threshold" not in callback for callback in callbacks)


@pytest.mark.asyncio
async def test_threshold_callbacks_return_disabled_message(monkeypatch):
    replies = []
    answers = []

    class FakeQuery:
        data = "settings:set_threshold:2.0"
        from_user = SimpleNamespace(id=1001)
        message = SimpleNamespace(reply_text=lambda text, **kwargs: replies.append(text))

        async def answer(self, text=None):
            answers.append(text)

    async def reply_text(text, **kwargs):
        replies.append(text)

    query = FakeQuery()
    query.message.reply_text = reply_text
    update = SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1001))
    context = SimpleNamespace(application=SimpleNamespace(), user_data={})

    async def is_admin_user(user_id):
        return True

    monkeypatch.setattr("bot.handlers.is_admin_user", is_admin_user)

    await button_router(update, context)

    assert replies == [
        "Price movement thresholds are disabled for automatic Event Alerts. "
        "Use /setinterval to change the check interval."
    ]
