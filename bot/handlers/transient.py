"""Manage command-generated Telegram replies without touching passive notifications."""
import asyncio
import logging
from collections import deque
from contextvars import ContextVar
from itertools import count

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ExtBot

logger = logging.getLogger(__name__)
CLOSE_DATA = "transient:close"
_active = ContextVar("ccwbot_manual_ui", default=None)


class TransientSessions:
    def __init__(self):
        self._sessions = {}
        self._origins = {}
        self._sequence = count(1)
        self._retired = set()
        self._retired_order = deque()

    def _retire(self, chat_id, message_id):
        pair = (chat_id, message_id)
        if pair not in self._retired:
            self._retired.add(pair)
            self._retired_order.append(pair)
        if len(self._retired_order) > 4096:
            self._retired.discard(self._retired_order.popleft())

    async def _delete(self, chat_id, ids, bot):
        for message_id in ids:
            self._retire(chat_id, message_id)
            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except Exception as error:
                logger.debug("Transient deletion failed: %s", type(error).__name__)

    async def begin(self, key, bot, origin=None):
        previous = self._sessions.pop(key, None)
        if previous is not None:
            await self._delete(key[0], previous[1], bot)
        generation = next(self._sequence)
        self._sessions[key] = (generation, set())
        self._origins[key] = origin
        return generation

    def origin_for(self, chat_id, user_id):
        return self._origins.get((chat_id, user_id))

    def add(self, key, generation, message_id):
        current = self._sessions.get(key)
        if current is not None and current[0] == generation:
            current[1].add(message_id)

    def token_for(self, chat_id, user_id, message_id):
        session = self._sessions.get((chat_id, user_id))
        if session and message_id in session[1]:
            return session[0]
        return None

    def is_active(self, chat_id, user_id, message_id):
        return self.token_for(chat_id, user_id, message_id) is not None

    def is_retired(self, chat_id, message_id):
        return (chat_id, message_id) in self._retired

    async def close(self, chat_id, user_id, message_id, bot):
        key = (chat_id, user_id)
        if not self.is_active(chat_id, user_id, message_id):
            return False
        session = self._sessions.pop(key)
        self._origins.pop(key, None)
        await self._delete(chat_id, session[1], bot)
        return True


sessions = TransientSessions()


def with_close_button(markup):
    if markup is not None and not isinstance(markup, InlineKeyboardMarkup):
        return markup
    rows = [list(row) for row in markup.inline_keyboard] if markup else []
    if not any(button.callback_data == CLOSE_DATA for row in rows for button in row):
        rows.append([InlineKeyboardButton("Close", callback_data=CLOSE_DATA)])
    return InlineKeyboardMarkup(rows)


def _tracking(chat_id, message_id=None):
    active = _active.get()
    if active is None or active[0][0] != chat_id or active[2] is not asyncio.current_task():
        return None
    if message_id is not None and not sessions.is_active(*active[0], message_id):
        return None
    return active


def rich_reply_markup(chat_id) -> dict | None:
    """Manual rich sends bypass PTB's normal send_message override."""
    return with_close_button(None).to_dict() if _tracking(chat_id) else None


def register_rich_reply(chat_id, message_id: int) -> None:
    """Track acknowledged rich output for Close and next-command cleanup."""
    active = _tracking(chat_id)
    if active:
        sessions.add(active[0], active[1], message_id)


class TransientBot(ExtBot):
    """Intercept only messages sent in the scope of a manual command/callback."""

    async def send_message(self, chat_id, text, *args, **kwargs):
        active = _tracking(chat_id)
        if active:
            kwargs["reply_markup"] = with_close_button(kwargs.get("reply_markup"))
        message = await super().send_message(chat_id, text, *args, **kwargs)
        if active:
            sessions.add(active[0], active[1], message.message_id)
        return message

    async def send_document(self, chat_id, document, *args, **kwargs):
        active = _tracking(chat_id)
        if active:
            kwargs["reply_markup"] = with_close_button(kwargs.get("reply_markup"))
        message = await super().send_document(chat_id, document, *args, **kwargs)
        if active:
            sessions.add(active[0], active[1], message.message_id)
        return message

    async def edit_message_text(
        self, text, chat_id=None, message_id=None, inline_message_id=None, **kwargs
    ):
        if message_id is not None and _tracking(chat_id, message_id):
            kwargs["reply_markup"] = with_close_button(kwargs.get("reply_markup"))
        return await super().edit_message_text(
            text, chat_id=chat_id, message_id=message_id,
            inline_message_id=inline_message_id, **kwargs
        )


def private_key(update):
    chat = getattr(update, "effective_chat", None)
    user = getattr(update, "effective_user", None)
    if str(getattr(chat, "type", "")).lower() != "private":
        return None
    if getattr(chat, "id", None) is None or getattr(user, "id", None) is None:
        return None
    return (chat.id, user.id)


async def enter_command(update, context, origin=None):
    key = private_key(update)
    if key is None:
        return None
    generation = await sessions.begin(key, context.bot, origin=origin)
    return _active.set((key, generation, asyncio.current_task()))


def enter_callback(update):
    key = private_key(update)
    query = getattr(update, "callback_query", None)
    message_id = getattr(getattr(query, "message", None), "message_id", None)
    if key is None or message_id is None:
        return None
    generation = sessions.token_for(*key, message_id)
    if generation is None:
        return None
    return _active.set((key, generation, asyncio.current_task()))


def exit_request(context_token):
    if context_token is not None:
        _active.reset(context_token)
