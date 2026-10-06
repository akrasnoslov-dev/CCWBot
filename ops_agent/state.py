from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ops_agent.schemas import Period

MAX_COLLECTION_PERIOD = timedelta(hours=720)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(
            "timestamp must use UTC ISO format YYYY-MM-DDTHH:MM:SSZ, "
            "for example 2026-06-06T00:00:00Z; slash dates are not accepted"
        ) from error
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _validated_period(start: datetime, end: datetime, source: str) -> Period:
    if start >= end:
        raise ValueError("collection period start must be before end")
    if end - start > MAX_COLLECTION_PERIOD:
        raise ValueError("collection period must not exceed 720 hours")
    return Period(start=start, end=end, source=source)


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
    end = parse_timestamp(until) if until and until.lower() != "now" else (now or utc_now())
    if since:
        return _validated_period(parse_timestamp(since), end, "explicit")
    if period and period != "auto":
        hours = int(period.removesuffix("h")) if period.endswith("h") else 24
        return _validated_period(end - timedelta(hours=hours), end, period)
    last_success = state.get("last_successful_report")
    if isinstance(last_success, dict) and last_success.get("period_end"):
        return _validated_period(
            parse_timestamp(str(last_success["period_end"])),
            end,
            "auto",
        )
    return _validated_period(end - timedelta(hours=24), end, "auto")


def record_collection(
    state: dict[str, Any],
    *,
    bundle_id: str,
    status: str,
    period: Period,
    failed_collectors: list[str] | None = None,
    event_analysis: dict[str, int] | None = None,
) -> dict[str, Any]:
    state = dict(state)
    state["schema_version"] = 1
    state["last_collection"] = {
        "bundle_id": bundle_id,
        "status": status,
        "period_start": period.as_dict()["start"],
        "period_end": period.as_dict()["end"],
        # Collector names only (e.g. "db.alerts_summary") so recurring partial runs are
        # diagnosable from the state snapshot alone; never error text or evidence content.
        "failed_collectors": sorted(failed_collectors or []),
    }
    if event_analysis is not None:
        # Two counters only, so "zero successes for N cycles running" is answerable across
        # collections instead of only within the current period. No identifiers, no content.
        state["last_collection"]["event_analysis"] = {
            "successful_calls": int(event_analysis.get("successful_calls") or 0),
            "total_calls": int(event_analysis.get("total_calls") or 0),
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
