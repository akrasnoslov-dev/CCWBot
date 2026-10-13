"""Real PostgreSQL locking checks; the SQLite process mutex cannot prove these contracts."""

import asyncio
import os
from importlib import import_module

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.db.database import automatic_delivery_lock

persistence = import_module("bot.db.alerts")


def postgres_url():
    url = (os.getenv("ALEMBIC_POSTGRES_TEST_DATABASE_URL")
           or os.getenv("OPS_AGENT_POSTGRES_TEST_DATABASE_URL"))
    if not url or not url.startswith("postgresql+asyncpg://"):
        pytest.skip("set ALEMBIC_POSTGRES_TEST_DATABASE_URL to a throwaway PostgreSQL database")
    return url


@pytest.mark.asyncio
async def test_postgres_lock_serializes_separate_workers_and_releases_on_cancellation(monkeypatch):
    # Emulate separate processes: each acquisition has its own local mutex and pool.
    class IndependentWorkerLocks:
        def setdefault(self, *args):
            return asyncio.Lock()

    monkeypatch.setattr(persistence, "_delivery_locks", IndependentWorkerLocks())
    first_engine = create_async_engine(postgres_url(), pool_size=4, max_overflow=0)
    second_engine = create_async_engine(postgres_url(), pool_size=2, max_overflow=0)
    first = async_sessionmaker(first_engine)
    second = async_sessionmaker(second_engine)
    acquired, attempted, entered = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def owner():
        async with automatic_delivery_lock(first, user_id=8765, symbol="btc"):
            acquired.set()
            await asyncio.Event().wait()

    async def contender():
        attempted.set()
        async with automatic_delivery_lock(second, user_id=8765, symbol="btc"):
            entered.set()

    task = asyncio.create_task(owner())
    waiter = None
    try:
        await asyncio.wait_for(acquired.wait(), 5)
        waiter = asyncio.create_task(contender())
        await attempted.wait()
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(entered.wait(), 0.1)
        # Another coin remains independent even while BTC is held.
        async with automatic_delivery_lock(first, user_id=8765, symbol="eth"):
            async with first() as session:
                assert await session.scalar(text("SELECT 1")) == 1
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await asyncio.wait_for(waiter, 5)
        assert entered.is_set()
    finally:
        task.cancel()
        if waiter:
            waiter.cancel()
        await asyncio.gather(task, *([waiter] if waiter else []), return_exceptions=True)
        await first_engine.dispose()
        await second_engine.dispose()


@pytest.mark.asyncio
async def test_small_pool_reserves_capacity_for_parallel_delivery_persistence():
    engine = create_async_engine(postgres_url(), pool_size=2, max_overflow=0, pool_timeout=0.5)
    factory = async_sessionmaker(engine)

    async def send(identifier):
        async with automatic_delivery_lock(factory, user_id=identifier, symbol="btc"):
            async with factory() as session:
                assert await session.scalar(text("SELECT 1")) == 1

    try:
        await asyncio.wait_for(asyncio.gather(*(send(i) for i in range(10))), 5)
    finally:
        await engine.dispose()
