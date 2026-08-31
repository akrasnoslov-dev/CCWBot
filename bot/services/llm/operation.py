"""Async-safe correlation for one logical LLM operation.

The value is an opaque backend-generated UUID.  It deliberately carries no
request, provider, Telegram, or user-derived information.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from uuid import uuid4

_operation_id: ContextVar[str | None] = ContextVar("llm_operation_id", default=None)


def new_llm_operation_id() -> str:
    """Return an opaque identifier for exactly one logical LLM operation."""
    return str(uuid4())


def current_llm_operation_id() -> str | None:
    return _operation_id.get()


@contextmanager
def llm_operation_scope(operation_id: str | None = None):
    """Make one operation identifier visible to every nested provider attempt."""
    resolved = operation_id or new_llm_operation_id()
    token = _operation_id.set(resolved)
    try:
        yield resolved
    finally:
        _operation_id.reset(token)
