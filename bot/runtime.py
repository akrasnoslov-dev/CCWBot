import logging
from typing import Any

from config import DATABASE_URL
from database import init_db

logger = logging.getLogger(__name__)


def log(message: str) -> None:
    logger.info(message)


# Optional DB bootstrap: PostgreSQL stores runtime state when configured.
DB_ENABLED = bool(DATABASE_URL)


class SessionFactoryRef:
    def __init__(self) -> None:
        self._factory = None

    def set(self, factory) -> None:
        self._factory = factory

    def clear(self) -> None:
        self._factory = None

    def __bool__(self) -> bool:
        return self._factory is not None

    def __call__(self, *args: Any, **kwargs: Any):
        if self._factory is None:
            raise RuntimeError("Database session factory has not been initialized.")
        return self._factory(*args, **kwargs)


DB_SESSION_LOCAL = SessionFactoryRef()
DB_ENGINE = None


async def initialize_database() -> None:
    global DB_ENGINE
    if not DB_ENABLED:
        log("DATABASE_URL is not configured. Using local JSON state.")
        return
    if DB_SESSION_LOCAL:
        return

    log("Database configured. Using PostgreSQL state.")
    DB_ENGINE, session_local = await init_db(DATABASE_URL)
    DB_SESSION_LOCAL.set(session_local)


async def close_database() -> None:
    """Dispose database resources created during startup."""
    global DB_ENGINE
    if DB_ENGINE is None:
        return

    await DB_ENGINE.dispose()
    DB_ENGINE = None
    DB_SESSION_LOCAL.clear()
    log("Database resources closed.")
