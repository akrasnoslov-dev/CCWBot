from __future__ import annotations

import ast
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

ALEMBIC_VERSION_LIMIT = 32
ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = ROOT / "alembic" / "versions"
LONG_REVISION_MESSAGE = (
    "Alembic revision ids must fit alembic_version.version_num VARCHAR(32); "
    "long ids can break migration execution."
)


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
