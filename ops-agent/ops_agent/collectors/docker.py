from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ops_agent.config import OpsAgentConfig
from ops_agent.schemas import Period

SAFE_ERROR_CATEGORIES = {
    "docker_status_unavailable",
    "permission_denied",
    "docker_status_invalid_json",
}


def _error_category(value: object) -> str:
    if isinstance(value, PermissionError):
        return "permission_denied"
    if isinstance(value, FileNotFoundError):
        return "docker_status_unavailable"
    text = str(value or "").lower()
    if "permission" in text or "denied" in text:
        return "permission_denied"
    if "json" in text:
        return "docker_status_invalid_json"
    if text in SAFE_ERROR_CATEGORIES:
        return text
    return "docker_status_unavailable"


def _load_status_payload(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        rows = []
        try:
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
        except json.JSONDecodeError as error:
            raise RuntimeError("docker_status_invalid_json") from error
        return rows


def _rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        if payload.get("status") == "failed":
            raise RuntimeError(_error_category(payload.get("error")))
        services = payload.get("services") or payload.get("containers")
        if isinstance(services, list):
            return [item for item in services if isinstance(item, dict)]
        return [payload]
    return []


def _clean_text(value: object, *, limit: int = 120) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    if not text:
        return None
    return text[:limit]


def _is_running(row: dict[str, Any]) -> bool:
    state = str(row.get("State") or row.get("state") or row.get("Status") or "").lower()
    return state == "running" or state.startswith("up")


def _service_name(row: dict[str, Any]) -> str | None:
    return _clean_text(
        row.get("Service")
        or row.get("service")
        or row.get("Name")
        or row.get("name")
        or row.get("Names")
    )


def _container_name(row: dict[str, Any]) -> str | None:
    name = _clean_text(row.get("Name") or row.get("name") or row.get("Names"))
    return name.lstrip("/") if name else None


def _load_restart_counts(path: Path | None) -> dict[str, int] | None:
    """Load {container_name: restart_count} from the sanitized inspect snapshot.

    The snapshot is JSONL/JSON of ``{"Name": "/ccwbot-bot-1", "RestartCount": 0}`` rows
    written by the collect wrapper. Returns None when the snapshot is not configured or
    unreadable, so missing restart evidence stays "unknown" instead of a fake zero.
    """
    if path is None:
        return None
    try:
        rows = _rows(_load_status_payload(path))
    except Exception:
        return None
    counts: dict[str, int] = {}
    for row in rows:
        name = _clean_text(row.get("Name") or row.get("name"))
        raw_count = row.get("RestartCount", row.get("restart_count"))
        try:
            count = int(raw_count)
        except (TypeError, ValueError):
            continue
        if name and count >= 0:
            counts[name.lstrip("/")] = count
    return counts or None


def _sanitize_service(row: dict[str, Any]) -> dict[str, Any] | None:
    service = _service_name(row)
    if not service:
        return None
    restart_count = row.get("RestartCount") or row.get("restart_count")
    try:
        restart_count = int(restart_count) if restart_count is not None else None
    except (TypeError, ValueError):
        restart_count = None
    return {
        "service": service,
        "container_status": _clean_text(row.get("Status") or row.get("status")),
        "running_state": _clean_text(row.get("State") or row.get("state")),
        "is_running": _is_running(row),
        "health": _clean_text(row.get("Health") or row.get("health")),
        "restart_count": restart_count,
    }


def collect_docker(
    *,
    config: OpsAgentConfig,
    period: Period,
) -> tuple[dict[str, Any], dict[str, str | None]]:
    base_payload: dict[str, Any] = {
        "schema_version": 1,
        "period": period.as_dict(),
        "privacy_mode": "safe_compose_ps_status_only",
        "services": [],
        "warnings": [],
    }
    path = config.docker_status_json_path
    if path is None:
        message = "docker_status_unavailable"
        base_payload.update({"status": "unknown", "error": message, "warnings": [message]})
        return base_payload, {"name": "docker", "status": "skipped", "error": message}
    try:
        rows = _rows(_load_status_payload(path))
        restart_counts = _load_restart_counts(config.docker_restarts_json_path)
        services = []
        for row in rows:
            service = _sanitize_service(row)
            if service is None:
                continue
            if service.get("restart_count") is None and restart_counts is not None:
                container = _container_name(row)
                if container is not None and container in restart_counts:
                    service["restart_count"] = restart_counts[container]
            services.append(service)
    except Exception as error:
        message = _error_category(error)
        base_payload.update({"status": "failed", "error": message, "warnings": [message]})
        return base_payload, {"name": "docker", "status": "partial", "error": message}

    stopped = [service for service in services if not service.get("is_running")]
    unhealthy = [
        service
        for service in services
        if str(service.get("health") or "").lower() in {"unhealthy", "starting"}
    ]
    status = "ok" if services and not stopped and not unhealthy else "failed"
    status_warnings = []
    if not services:
        status_warnings.append("docker_status_empty")
    if stopped:
        status_warnings.append("container_not_running")
    if unhealthy:
        status_warnings.append("container_health_not_ok")
    warnings = list(status_warnings)
    if services and any(service.get("restart_count") is None for service in services):
        # Missing restart evidence is incomplete, not healthy; the report renders it as
        # "unknown". This does not fail the collector — container state itself is intact.
        warnings.append("restart_counts_unavailable")
    base_payload.update(
        {
            "status": status,
            "service_count": len(services),
            "running_count": sum(1 for service in services if service.get("is_running")),
            "unhealthy_count": len(unhealthy),
            "services": services,
            "warnings": warnings,
        }
    )
    collector_status = "ok" if status == "ok" else "partial"
    return (
        base_payload,
        {
            "name": "docker",
            "status": collector_status,
            "error": "; ".join(status_warnings) if status_warnings else None,
        },
    )
