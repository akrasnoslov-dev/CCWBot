from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from bot.observability.error_file_logging import (
    BACKUP_COUNT,
    MAX_BYTES,
    RedactingFormatter,
    _find_named_file_handler,
)

OPERATIONAL_FILE_HANDLER_NAME = "ccwbot_operational_file"
OPERATIONAL_LOG_FILE = Path(os.getenv("OPERATIONAL_LOG_FILE", "logs/ccwbot-operational.log"))


def enable_operational_file_logging(log_file: Path | None = None) -> Path:
    existing_handler = _find_named_file_handler(OPERATIONAL_FILE_HANDLER_NAME)
    target = Path(log_file or OPERATIONAL_LOG_FILE)
    if existing_handler is not None:
        return Path(getattr(existing_handler, "baseFilename", target))

    target.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        target,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.name = OPERATIONAL_FILE_HANDLER_NAME
    handler.setLevel(logging.INFO)
    handler.setFormatter(
        RedactingFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    logging.getLogger().addHandler(handler)
    return target
