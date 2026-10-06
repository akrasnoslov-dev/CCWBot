from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from ops_agent.config import OpsAgentConfig


def _delete_old_paths(paths: list[Path], *, max_items: int, older_than: datetime) -> list[str]:
    removed: list[str] = []
    sorted_paths = sorted(paths, key=lambda path: path.stat().st_mtime, reverse=True)
    for index, path in enumerate(sorted_paths):
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        if index < max_items and mtime >= older_than:
            continue
        if path.is_dir():
            for child in sorted(path.rglob("*"), reverse=True):
                if child.is_file():
                    child.unlink()
                elif child.is_dir():
                    child.rmdir()
            path.rmdir()
        else:
            path.unlink()
        removed.append(str(path))
    return removed


def apply_retention(config: OpsAgentConfig) -> dict[str, list[str]]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=config.retention_days)
    bundles = [path for path in config.bundles_dir.glob("*") if path.is_dir()]
    reports = [path for path in config.reports_dir.glob("*.md") if path.is_file()]
    return {
        "bundles_removed": _delete_old_paths(
            bundles,
            max_items=config.max_bundles,
            older_than=cutoff,
        ),
        "reports_removed": _delete_old_paths(
            reports,
            max_items=config.max_reports,
            older_than=cutoff,
        ),
    }

