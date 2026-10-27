"""One-shot, local-only PostgreSQL advisory lock tests in a fresh disposable DB."""
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
load_dotenv(ROOT / ".env")
source = make_url(os.environ["DATABASE_URL"])
if source.host not in {"localhost", "127.0.0.1"}:
    raise RuntimeError("Refusing non-local PostgreSQL test destination")
db_name = "ccwbot_pr2_test_20261016_temp"
dsn = source.set(drivername="postgresql", database="postgres").render_as_string(hide_password=False)


async def prepare():
    import asyncpg
    c = await asyncpg.connect(dsn)
    try:
        exists = await c.fetchval("SELECT 1 FROM pg_database WHERE datname=$1", db_name)
        if exists:
            raise RuntimeError("Test database already exists; refusing to overwrite it")
        await c.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        await c.close()


async def teardown():
    import asyncpg
    c = await asyncpg.connect(dsn)
    try:
        # Only the uniquely named DB created by this process is ever dropped.
        await c.execute(f'DROP DATABASE "{db_name}" WITH (FORCE)')
    finally:
        await c.close()


asyncio.run(prepare())
try:
    os.environ["ALEMBIC_POSTGRES_TEST_DATABASE_URL"] = source.set(
        database=db_name
    ).render_as_string(hide_password=False)
    # Existing tests only acquire PG advisory xact locks; no market/user data.
    import pytest
    result = pytest.main(["tests/test_heartbeat_postgres.py", "tests/test_event_alert_pr2_postgres.py", "-q", "--tb=short"])
finally:
    asyncio.run(teardown())
print("LOCAL_PG_LOCK_TEST_RESULT", result)
sys.exit(result)
