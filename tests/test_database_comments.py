from __future__ import annotations

from importlib import util
from pathlib import Path

import pytest
from sqlalchemy import text

from bot.db.database import Base, init_db


def _load_comments_migration():
    migration_path = (
        Path(__file__).resolve().parents[1] / "alembic/versions/0008_database_comments.py"
    )
    spec = util.spec_from_file_location("migration_0008_database_comments", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_market_heartbeat_migration():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic/versions/0027_market_heartbeat_defaults.py"
    )
    spec = util.spec_from_file_location("migration_0027_market_heartbeat", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_all_tables_and_columns_have_comments():
    for table in Base.metadata.sorted_tables:
        assert table.comment, f"{table.name} is missing a table comment"
        for column in table.columns:
            assert column.comment, f"{table.name}.{column.name} is missing a column comment"


def test_database_comments_migration_matches_model_metadata():
    migration = _load_comments_migration()
    heartbeat_migration = _load_market_heartbeat_migration()

    assert set(migration.TABLE_COMMENTS).issubset(Base.metadata.tables)
    assert set(migration.COLUMN_COMMENTS).issubset(Base.metadata.tables)

    for table_name in migration.TABLE_COMMENTS:
        table = Base.metadata.tables[table_name]
        assert migration.TABLE_COMMENTS[table_name] == table.comment
        for column_name, column_comment in migration.COLUMN_COMMENTS[table_name].items():
            column = table.columns[column_name]
            if table_name == "users" and column_name == "alert_frequency_seconds":
                assert column_comment == heartbeat_migration.PREVIOUS_ALERT_FREQUENCY_COMMENT
                assert column.comment == heartbeat_migration.MARKET_HEARTBEAT_FREQUENCY_COMMENT
                continue
            assert column_comment == column.comment


@pytest.mark.asyncio
async def test_database_comments_migration_applies_to_head(tmp_path):
    db_path = tmp_path / "comments_migration.sqlite"
    database_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"

    engine, session_local = await init_db(database_url, run_migrations=True)
    session = session_local()
    try:
        revision = await session.scalar(text("SELECT version_num FROM alembic_version"))
        assert revision == "0027_market_heartbeat_defaults"
    finally:
        await session.close()
        await engine.dispose()
