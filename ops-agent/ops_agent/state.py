from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ops_agent.schemas import Period


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def load_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"schema_version": 1, "recent_runs": []}
    with path.open(encoding="utf-8") as file:
        state = json.load(file)
    if not isinstance(state, dict):
        return {"schema_version": 1, "recent_runs": []}
    state.setdefault("schema_version", 1)
    state.setdefault("recent_runs", [])
    return state


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as file:
        json.dump(state, file, indent=2, sort_keys=True)
        file.write("\n")
    tmp_path.replace(path)


def resolve_period(
    *,
    state: dict[str, Any],
    period: str | None,
    since: str | None,
    until: str | None,
    now: datetime | None = None,
) -> Period:
    end = parse_timestamp(until) if until else (now or utc_now())
    if since:
        return Period(start=parse_timestamp(since), end=end, source="explicit")
    if period and period != "auto":
        hours = int(period.removesuffix("h")) if period.endswith("h") else 24
        return Period(start=end - timedelta(hours=hours), end=end, source=period)
    last_success = state.get("last_successful_report")
    if isinstance(last_success, dict) and last_success.get("period_end"):
        return Period(
            start=parse_timestamp(str(last_success["period_end"])),
            end=end,
            source="auto",
        )
    return Period(start=end - timedelta(hours=24), end=end, source="auto")


def record_collection(
    state: dict[str, Any],
    *,
    bundle_id: str,
    status: str,
    period: Period,
) -> dict[str, Any]:
    state = dict(state)
    state["schema_version"] = 1
    state["last_collection"] = {
        "bundle_id": bundle_id,
        "status": status,
        "period_start": period.as_dict()["start"],
        "period_end": period.as_dict()["end"],
    }
    recent_runs = list(state.get("recent_runs") or [])
    recent_runs.insert(0, state["last_collection"])
    state["recent_runs"] = recent_runs[:20]
    return state


def record_report_success(
    state: dict[str, Any],
    *,
    report_id: str,
    bundle_id: str,
    period: Period,
    report_path: Path,
    bundle_path: Path,
    bundle_sha256: str,
    completed_at: datetime | None = None,
) -> dict[str, Any]:
    state = dict(state)
    state["schema_version"] = 1
    state["last_successful_report"] = {
        "report_id": report_id,
        "bundle_id": bundle_id,
        "period_start": period.as_dict()["start"],
        "period_end": period.as_dict()["end"],
        "completed_at": (completed_at or utc_now()).isoformat().replace("+00:00", "Z"),
        "report_path": str(report_path),
        "bundle_path": str(bundle_path),
        "bundle_sha256": bundle_sha256,
    }
    return state
