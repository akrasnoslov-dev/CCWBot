import logging
import sys
from typing import Any

from bot.config import DATABASE_URL
from bot.db.database import init_db

logger = logging.getLogger("bot.runtime")


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


def _sync_package_database_engine() -> None:
    runtime_package = sys.modules.get("bot.runtime")
    if runtime_package is not None:
        runtime_package.DB_ENGINE = DB_ENGINE


async def initialize_database() -> None:
    global DB_ENGINE
    if not DB_ENABLED:
        log("ops_event=db_configured backend=local_json")
        return
    if DB_SESSION_LOCAL:
        return

    log("ops_event=db_configured backend=postgres")
    DB_ENGINE, session_local = await init_db(DATABASE_URL)
    DB_SESSION_LOCAL.set(session_local)
    _sync_package_database_engine()


async def close_database() -> None:
    """Dispose database resources created during startup."""
    global DB_ENGINE
    if DB_ENGINE is None:
        return

    await DB_ENGINE.dispose()
    DB_ENGINE = None
    DB_SESSION_LOCAL.clear()
    _sync_package_database_engine()
    log("ops_event=db_closed")
