from __future__ import annotations

import ast
import asyncio
import os
import re
from decimal import Decimal
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import command

ALEMBIC_VERSION_LIMIT = 32
ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = ROOT / "alembic" / "versions"
LONG_REVISION_MESSAGE = (
    "Alembic revision ids must fit alembic_version.version_num VARCHAR(32); "
    "long ids can break migration execution."
)
EVENT_ALERT_POLICY_REVISION = "0030_event_alert_policy_cleanup"
PREVIOUS_EVENT_ALERT_POLICY_REVISION = "0029_llm_operation_outcomes"
POSTGRES_MIGRATION_TEST_DATABASE_URL = "ALEMBIC_POSTGRES_TEST_DATABASE_URL"

RETIRED_DOWNGRADE_COLUMNS = {
    ("alerts", "thresholds_used"): (
        "text",
        "JSON alert thresholds used for this alert decision.",
    ),
    ("user_settings", "price_move_alert_percent"): (
        "double precision",
        "Legacy per-user price movement threshold percent.",
    ),
    ("app_settings", "btc_alert_threshold_percent"): (
        "double precision",
        "Global BTC movement percent that triggers automatic alerts.",
    ),
    ("app_settings", "major_movement_threshold_percent"): (
        "double precision",
        "Admin-controlled movement percent threshold for BTC and ETH alerts.",
    ),
    ("app_settings", "alt_movement_threshold_percent"): (
        "double precision",
        "Admin-controlled movement percent threshold for non-BTC and non-ETH alerts.",
    ),
    ("app_settings", "major_24h_medium_threshold_percent"): (
        "double precision",
        "Admin-controlled 24 hour medium trend threshold for BTC and ETH alerts.",
    ),
    ("app_settings", "major_24h_high_threshold_percent"): (
        "double precision",
        "Admin-controlled 24 hour high trend threshold for BTC and ETH alerts.",
    ),
    ("app_settings", "alt_24h_medium_threshold_percent"): (
        "double precision",
        "Admin-controlled 24 hour medium trend threshold for altcoin alerts.",
    ),
    ("app_settings", "alt_24h_high_threshold_percent"): (
        "double precision",
        "Admin-controlled 24 hour high trend threshold for altcoin alerts.",
    ),
}

HEAD_PRICE_COLUMNS = {
    ("price_state", "last_price"): (
        "numeric(38, 18)",
        "Full-precision most recent market price used for detection.",
    ),
    ("price_snapshots", "price"): (
        "numeric(38, 18)",
        "Full-precision market price captured at this snapshot time.",
    ),
    ("market_events", "price"): (
        "numeric(38, 18)",
        "Full-precision current price captured for the event.",
    ),
    ("market_events", "previous_price"): (
        "numeric(38, 18)",
        "Full-precision prior price used to calculate movement.",
    ),
}

DOWNGRADED_PRICE_COLUMNS = {
    ("price_state", "last_price"): (
        "double precision",
        "Most recent market price stored for movement detection.",
    ),
    ("price_snapshots", "price"): (
        "double precision",
        "Market price captured at this snapshot time.",
    ),
    ("market_events", "price"): (
        "double precision",
        "Current price captured for the event.",
    ),
    ("market_events", "previous_price"): (
        "double precision",
        "Previous stored price used to calculate movement.",
    ),
}

PRICE_COLUMN_NULLABILITY = {
    ("price_state", "last_price"): False,
    ("price_snapshots", "price"): False,
    ("market_events", "price"): False,
    ("market_events", "previous_price"): True,
}
PRICE_COLUMN_DEFAULTS = {key: None for key in PRICE_COLUMN_NULLABILITY}

RETIRED_DOWNGRADE_NULLABILITY = {
    key: key != ("alerts", "thresholds_used") for key in RETIRED_DOWNGRADE_COLUMNS
}
NO_DEFAULT_AT_0029 = {
    ("user_settings", "price_move_alert_percent"),
    ("app_settings", "btc_alert_threshold_percent"),
}
RETIRED_DOWNGRADE_DEFAULTS = {
    **{key: None for key in NO_DEFAULT_AT_0029},
    ("alerts", "thresholds_used"): None,
    ("app_settings", "major_movement_threshold_percent"): Decimal("1.0"),
    ("app_settings", "alt_movement_threshold_percent"): Decimal("2.0"),
    ("app_settings", "major_24h_medium_threshold_percent"): Decimal("3.0"),
    ("app_settings", "major_24h_high_threshold_percent"): Decimal("5.0"),
    ("app_settings", "alt_24h_medium_threshold_percent"): Decimal("5.0"),
    ("app_settings", "alt_24h_high_threshold_percent"): Decimal("8.0"),
}


def _literal_assignment(module: ast.Module, name: str) -> object:
    for node in module.body:
        if not isinstance(node, ast.AnnAssign | ast.Assign):
            continue

        value = node.value
        targets: list[ast.expr]
        if isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            targets = list(node.targets)

        if any(isinstance(target, ast.Name) and target.id == name for target in targets):
            return ast.literal_eval(value)

    msg = f"Missing {name!r} assignment"
    raise AssertionError(msg)


def _down_revisions(value: object) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {value}
    if isinstance(value, (tuple, list)):
        return {item for item in value if isinstance(item, str)}

    msg = f"Unsupported down_revision literal: {value!r}"
    raise AssertionError(msg)


def _migration_config(database_url: str) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.attributes["database_url"] = database_url
    config.attributes["configure_logger"] = False
    return config


async def _postgres_column_contract(
    database_url: str,
    keys: set[tuple[str, str]],
) -> dict[tuple[str, str], tuple[str, str | None, bool, str | None]]:
    engine = create_async_engine(database_url, future=True)
    try:
        async with engine.connect() as connection:
            def inspect_columns(sync_connection):
                inspector = sa.inspect(sync_connection)
                columns_by_table = {
                    table_name: {
                        column["name"]: column
                        for column in inspector.get_columns(table_name)
                    }
                    for table_name in {table_name for table_name, _ in keys}
                }
                return {
                    (table_name, column_name): (
                        str(
                            columns_by_table[table_name][column_name]["type"].compile(
                                dialect=postgresql.dialect()
                            )
                        ).lower(),
                        columns_by_table[table_name][column_name].get("comment"),
                        bool(columns_by_table[table_name][column_name]["nullable"]),
                        columns_by_table[table_name][column_name].get("default"),
                    )
                    for table_name, column_name in keys
                    if column_name in columns_by_table[table_name]
                }

            return await connection.run_sync(inspect_columns)
    finally:
        await engine.dispose()


def _type_comment_contract(
    columns: dict[tuple[str, str], tuple[str, str | None, bool, str | None]],
    keys: set[tuple[str, str]],
) -> dict[tuple[str, str], tuple[str, str | None]]:
    return {key: columns[key][:2] for key in keys}


def _normalized_numeric_default(value: str | None) -> Decimal | None:
    if value is None:
        return None
    value_without_cast = re.sub(r"::[a-z_ ]+", "", value, flags=re.IGNORECASE)
    return Decimal(value_without_cast.strip().strip("()'").strip())


def _nullability_contract(
    columns: dict[tuple[str, str], tuple[str, str | None, bool, str | None]],
    keys: set[tuple[str, str]],
) -> dict[tuple[str, str], bool]:
    return {key: columns[key][2] for key in keys}


def _default_contract(
    columns: dict[tuple[str, str], tuple[str, str | None, bool, str | None]],
    keys: set[tuple[str, str]],
) -> dict[tuple[str, str], str | None]:
    return {key: columns[key][3] for key in keys}


async def _postgres_revision(database_url: str) -> str:
    engine = create_async_engine(database_url, future=True)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                sa.text("SELECT version_num FROM alembic_version")
            )
            return str(
                result.scalar_one()
            )
    finally:
        await engine.dispose()


def test_alembic_revision_ids_fit_version_table_and_chain_is_valid() -> None:
    revisions: dict[str, Path] = {}
    down_revisions: dict[Path, set[str]] = {}

    for path in sorted(MIGRATIONS_DIR.glob("*.py")):
        module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        revision = _literal_assignment(module, "revision")
        assert isinstance(revision, str), f"{path.name}: revision must be a string"
        assert len(revision) <= ALEMBIC_VERSION_LIMIT, (
            f"{path.name}: {revision!r} is {len(revision)} chars. "
            f"{LONG_REVISION_MESSAGE}"
        )
        assert revision not in revisions, (
            f"{path.name}: duplicate revision {revision!r}; first seen in "
            f"{revisions[revision].name}"
        )

        revisions[revision] = path
        down_revisions[path] = _down_revisions(
            _literal_assignment(module, "down_revision")
        )

    for path, references in down_revisions.items():
        missing = sorted(reference for reference in references if reference not in revisions)
        assert not missing, (
            f"{path.name}: down_revision references missing Alembic revision ids "
            f"{missing}. {LONG_REVISION_MESSAGE}"
        )


def test_alembic_history_has_one_reachable_head() -> None:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    script = ScriptDirectory.from_config(config)

    heads = script.get_heads()
    assert len(heads) == 1, f"Expected one Alembic head, found {heads}"
    revisions = list(script.walk_revisions(base="base", head=heads[0]))
    assert revisions[-1].down_revision is None, "Alembic history has no root revision"
    assert len({revision.revision for revision in revisions}) == len(revisions)


def test_0030_postgresql_downgrade_round_trip_restores_contract() -> None:
    database_url = os.getenv(POSTGRES_MIGRATION_TEST_DATABASE_URL)
    if not database_url or not database_url.startswith("postgresql+asyncpg://"):
        pytest.skip(f"set {POSTGRES_MIGRATION_TEST_DATABASE_URL} to a PostgreSQL test database")

    config = _migration_config(database_url)
    inspected_keys = (
        set(RETIRED_DOWNGRADE_COLUMNS)
        | set(HEAD_PRICE_COLUMNS)
        | {("event_ai_analyses", "context_fingerprint")}
    )

    command.upgrade(config, EVENT_ALERT_POLICY_REVISION)
    assert asyncio.run(_postgres_revision(database_url)) == EVENT_ALERT_POLICY_REVISION
    upgraded_columns = asyncio.run(_postgres_column_contract(database_url, inspected_keys))
    assert _type_comment_contract(upgraded_columns, set(HEAD_PRICE_COLUMNS)) == HEAD_PRICE_COLUMNS
    assert (
        _nullability_contract(upgraded_columns, set(HEAD_PRICE_COLUMNS))
        == PRICE_COLUMN_NULLABILITY
    )
    assert _default_contract(upgraded_columns, set(HEAD_PRICE_COLUMNS)) == PRICE_COLUMN_DEFAULTS
    assert not set(RETIRED_DOWNGRADE_COLUMNS) & set(upgraded_columns)
    assert upgraded_columns[("event_ai_analyses", "context_fingerprint")] == (
        "varchar(128)",
        "Hash of the exact semantic Event Analysis input used for pre-LLM reuse.",
        True,
        None,
    )

    command.downgrade(config, PREVIOUS_EVENT_ALERT_POLICY_REVISION)
    assert asyncio.run(_postgres_revision(database_url)) == PREVIOUS_EVENT_ALERT_POLICY_REVISION
    downgraded_columns = asyncio.run(_postgres_column_contract(database_url, inspected_keys))
    assert (
        _type_comment_contract(downgraded_columns, set(RETIRED_DOWNGRADE_COLUMNS))
        == RETIRED_DOWNGRADE_COLUMNS
    )
    assert (
        _type_comment_contract(downgraded_columns, set(DOWNGRADED_PRICE_COLUMNS))
        == DOWNGRADED_PRICE_COLUMNS
    )
    assert (
        _nullability_contract(downgraded_columns, set(DOWNGRADED_PRICE_COLUMNS))
        == PRICE_COLUMN_NULLABILITY
    )
    assert (
        _default_contract(downgraded_columns, set(DOWNGRADED_PRICE_COLUMNS))
        == PRICE_COLUMN_DEFAULTS
    )
    assert {
        key: downgraded_columns[key][2] for key in RETIRED_DOWNGRADE_NULLABILITY
    } == RETIRED_DOWNGRADE_NULLABILITY
    assert {
        key: _normalized_numeric_default(downgraded_columns[key][3])
        for key in RETIRED_DOWNGRADE_DEFAULTS
    } == RETIRED_DOWNGRADE_DEFAULTS
    assert ("event_ai_analyses", "context_fingerprint") not in downgraded_columns

    command.upgrade(config, "head")
    assert asyncio.run(_postgres_revision(database_url)) == EVENT_ALERT_POLICY_REVISION
    reupgraded_columns = asyncio.run(_postgres_column_contract(database_url, inspected_keys))
    assert _type_comment_contract(reupgraded_columns, set(HEAD_PRICE_COLUMNS)) == HEAD_PRICE_COLUMNS
    assert (
        _nullability_contract(reupgraded_columns, set(HEAD_PRICE_COLUMNS))
        == PRICE_COLUMN_NULLABILITY
    )
    assert _default_contract(reupgraded_columns, set(HEAD_PRICE_COLUMNS)) == PRICE_COLUMN_DEFAULTS
    assert not set(RETIRED_DOWNGRADE_COLUMNS) & set(reupgraded_columns)
    assert reupgraded_columns[("event_ai_analyses", "context_fingerprint")] == (
        "varchar(128)",
        "Hash of the exact semantic Event Analysis input used for pre-LLM reuse.",
        True,
        None,
    )
