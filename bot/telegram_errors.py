"""Helpers for classifying Telegram delivery failures."""

from __future__ import annotations


def is_bot_blocked_error(error: BaseException | str | None) -> bool:
    """Return True when Telegram says the user blocked the bot."""
    if error is None:
        return False
    message = " ".join(str(error).lower().split())
    return "forbidden" in message and "bot was blocked by the user" in message
