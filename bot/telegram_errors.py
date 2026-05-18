"""Helpers for classifying Telegram delivery failures."""

from __future__ import annotations


def is_bot_blocked_error(error: BaseException | str | None) -> bool:
    """Return True when Telegram reports a permanent user/chat delivery failure."""
    if error is None:
        return False
    message = " ".join(str(error).lower().split())
    permanent_terms = (
        "chat not found",
        "bot was blocked by the user",
        "user is deactivated",
    )
    if any(term in message for term in permanent_terms):
        return True
    return "forbidden" in message
