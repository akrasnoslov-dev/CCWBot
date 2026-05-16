"""Runtime-controlled warning/error file logging."""

from __future__ import annotations

import logging
import os
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

from bot.config import ERROR_LOG_FILE

ERROR_FILE_HANDLER_NAME = "ccwbot_warning_error_file"
MAX_BYTES = 10 * 1024 * 1024
BACKUP_COUNT = 5

_SECRET_URL_RE = re.compile(r"([a-z][a-z0-9+.-]*://[^:\s/@]+:)([^@\s]+)(@)", re.IGNORECASE)
_KEY_VALUE_SECRET_RE = re.compile(
    r"(?i)\b(token|api[_-]?key|password|secret|session[_-]?token)=([^\s]+)"
)


class RedactingFormatter(logging.Formatter):
    """Formatter that masks common secret values before writing persistent logs."""

    def __init__(self, fmt: str):
        super().__init__(fmt)
        self._secret_values = _collect_secret_values()

    def format(self, record: logging.LogRecord) -> str:
        return _redact(super().format(record), self._secret_values)


def _collect_secret_values() -> tuple[str, ...]:
    secret_names = {
        "TELEGRAM_BOT_TOKEN",
        "GROQ_API_KEY",
        "DATABASE_URL",
        "POSTGRES_PASSWORD",
    }
    values = []
    for name in secret_names:
        value = os.getenv(name)
        if value and len(value) >= 6:
            values.append(value)
    return tuple(values)


def _redact(message: str, secret_values: tuple[str, ...]) -> str:
    redacted = message
    for value in secret_values:
        redacted = redacted.replace(value, "[REDACTED]")
    redacted = _SECRET_URL_RE.sub(r"\1[REDACTED]\3", redacted)
    return _KEY_VALUE_SECRET_RE.sub(r"\1=[REDACTED]", redacted)


def _find_file_handler() -> logging.Handler | None:
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        if getattr(handler, "name", None) == ERROR_FILE_HANDLER_NAME:
            return handler
    return None


def is_error_file_logging_enabled() -> bool:
    return _find_file_handler() is not None


def enable_error_file_logging(log_file: Path | None = None) -> Path:
    existing_handler = _find_file_handler()
    target = Path(log_file or ERROR_LOG_FILE)
    if existing_handler is not None:
        return Path(getattr(existing_handler, "baseFilename", target))

    target.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        target,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.name = ERROR_FILE_HANDLER_NAME
    handler.setLevel(logging.WARNING)
    handler.setFormatter(
        RedactingFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    logging.getLogger().addHandler(handler)
    return target


def disable_error_file_logging() -> None:
    handler = _find_file_handler()
    if handler is None:
        return

    logging.getLogger().removeHandler(handler)
    handler.close()


async def apply_persisted_error_file_logging_state() -> None:
    from bot.settings import get_runtime_error_file_logging_enabled

    if await get_runtime_error_file_logging_enabled():
        enable_error_file_logging()
    else:
        disable_error_file_logging()
