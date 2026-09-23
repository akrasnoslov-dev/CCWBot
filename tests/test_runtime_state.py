from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.runtime import state


@pytest.fixture(autouse=True)
def reset_runtime_database_state():
    state.DB_SESSION_LOCAL.clear()
    state.DB_ENGINE = None
    state._sync_package_database_engine()
    yield
    state.DB_SESSION_LOCAL.clear()
    state.DB_ENGINE = None
    state._sync_package_database_engine()


@pytest.mark.asyncio
async def test_initialize_database_uses_local_state_when_database_is_disabled(monkeypatch):
    logs = []
    init_db = AsyncMock()
    monkeypatch.setattr(state, "DB_ENABLED", False)
    monkeypatch.setattr(state, "init_db", init_db)
    monkeypatch.setattr(state, "log", logs.append)

    await state.initialize_database()

    init_db.assert_not_awaited()
    assert not state.DB_SESSION_LOCAL
    assert logs == ["ops_event=db_configured backend=local_json"]


@pytest.mark.asyncio
async def test_initialize_database_is_idempotent_and_exports_engine(monkeypatch):
    engine = object()

    def session_factory():
        return SimpleNamespace()

    init_db = AsyncMock(return_value=(engine, session_factory))
    monkeypatch.setattr(state, "DB_ENABLED", True)
    monkeypatch.setattr(state, "init_db", init_db)

    await state.initialize_database()
    await state.initialize_database()

    init_db.assert_awaited_once_with(state.DATABASE_URL)
    assert state.DB_ENGINE is engine
    assert state.DB_SESSION_LOCAL() is not None


@pytest.mark.asyncio
async def test_close_database_disposes_engine_and_clears_shared_references(monkeypatch):
    engine = SimpleNamespace(dispose=AsyncMock())
    state.DB_ENGINE = engine
    state.DB_SESSION_LOCAL.set(lambda: SimpleNamespace())
    state._sync_package_database_engine()
    logs = []
    monkeypatch.setattr(state, "log", logs.append)

    await state.close_database()

    engine.dispose.assert_awaited_once()
    assert state.DB_ENGINE is None
    assert not state.DB_SESSION_LOCAL
    assert logs == ["ops_event=db_closed"]
