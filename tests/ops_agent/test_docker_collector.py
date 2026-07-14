from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ops_agent.collectors.docker import collect_docker
from ops_agent.config import OpsAgentConfig
from ops_agent.schemas import Period


def _period() -> Period:
    return Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )


def _config(
    tmp_path: Path,
    docker_status_json_path: Path | None,
    docker_restarts_json_path: Path | None = None,
) -> OpsAgentConfig:
    return OpsAgentConfig(
        database_url=None,
        health_url=None,
        output_dir=tmp_path,
        logs_dir=tmp_path / "logs",
        legacy_state_path=tmp_path / "state.json",
        docker_status_json_path=docker_status_json_path,
        docker_restarts_json_path=docker_restarts_json_path,
    )


def test_docker_collector_sanitizes_healthy_container_summary(tmp_path):
    path = tmp_path / "docker-status.json"
    path.write_text(
        json.dumps(
            [
                {
                    "Service": "bot",
                    "State": "running",
                    "Status": "running",
                    "Health": "healthy",
                    "RestartCount": 0,
                    "Command": "--token super-secret",
                    "Environment": ["DATABASE_URL=postgresql://secret"],
                    "Mounts": ["/opt/CCWBot/.env"],
                },
                {"Service": "postgres", "State": "running", "Health": "healthy"},
            ]
        ),
        encoding="utf-8",
    )

    payload, status = collect_docker(config=_config(tmp_path, path), period=_period())

    encoded = json.dumps(payload, sort_keys=True)
    assert status == {"name": "docker", "status": "ok", "error": None}
    assert payload["status"] == "ok"
    assert payload["service_count"] == 2
    assert payload["running_count"] == 2
    assert payload["services"][0]["service"] == "bot"
    assert "--token" not in encoded
    assert "DATABASE_URL" not in encoded
    assert ".env" not in encoded
    assert "super-secret" not in encoded


def test_docker_collector_handles_newline_delimited_compose_output(tmp_path):
    path = tmp_path / "docker-status.json"
    path.write_text(
        '{"Service":"bot","State":"running","Health":"healthy"}\n'
        '{"Service":"ops-agent","State":"exited","Health":"none"}\n',
        encoding="utf-8",
    )

    payload, status = collect_docker(config=_config(tmp_path, path), period=_period())

    assert payload["service_count"] == 2
    assert payload["running_count"] == 1
    # No restart snapshot was provided, so restart evidence is explicitly incomplete.
    assert payload["warnings"] == ["container_not_running", "restart_counts_unavailable"]
    assert payload["services"][1]["service"] == "ops-agent"
    assert payload["services"][1]["is_running"] is False
    assert status["status"] == "partial"
    assert status["error"] == "container_not_running"


def test_docker_collector_populates_restart_counts_from_inspect_snapshot(tmp_path):
    status_path = tmp_path / "docker-status.json"
    status_path.write_text(
        '{"Service":"bot","Name":"ccwbot-bot-1","State":"running","Health":"healthy"}\n'
        '{"Service":"postgres","Name":"ccwbot-postgres-1","State":"running","Health":"healthy"}\n',
        encoding="utf-8",
    )
    restarts_path = tmp_path / "docker-restarts.json"
    restarts_path.write_text(
        '{"Name": "/ccwbot-bot-1", "RestartCount": 3}\n'
        '{"Name": "/ccwbot-postgres-1", "RestartCount": 0}\n',
        encoding="utf-8",
    )

    payload, status = collect_docker(
        config=_config(tmp_path, status_path, restarts_path), period=_period()
    )

    by_service = {service["service"]: service for service in payload["services"]}
    assert by_service["bot"]["restart_count"] == 3
    assert by_service["postgres"]["restart_count"] == 0
    assert "restart_counts_unavailable" not in payload["warnings"]
    assert status == {"name": "docker", "status": "ok", "error": None}


def test_docker_collector_missing_restart_snapshot_keeps_unknown_not_healthy(tmp_path):
    status_path = tmp_path / "docker-status.json"
    status_path.write_text(
        '{"Service":"bot","Name":"ccwbot-bot-1","State":"running","Health":"healthy"}\n',
        encoding="utf-8",
    )

    payload, status = collect_docker(
        config=_config(tmp_path, status_path, tmp_path / "missing-restarts.json"),
        period=_period(),
    )

    assert payload["services"][0]["restart_count"] is None
    assert "restart_counts_unavailable" in payload["warnings"]
    # The container-state collector itself stays ok; missing restart evidence is a
    # payload warning, and the report renders restart counts as unknown.
    assert status == {"name": "docker", "status": "ok", "error": None}


def test_docker_collector_reports_unavailable_without_stopping_collection(tmp_path):
    path = tmp_path / "missing.json"

    payload, status = collect_docker(config=_config(tmp_path, path), period=_period())

    assert payload["status"] == "failed"
    assert payload["error"] == "docker_status_unavailable"
    assert status == {"name": "docker", "status": "partial", "error": "docker_status_unavailable"}


def test_docker_collector_reports_permission_denied_from_wrapper_payload(tmp_path):
    path = tmp_path / "docker-status.json"
    path.write_text(
        json.dumps({"status": "failed", "error": "permission denied opening docker socket"}),
        encoding="utf-8",
    )

    payload, status = collect_docker(config=_config(tmp_path, path), period=_period())

    assert payload["status"] == "failed"
    assert payload["error"] == "permission_denied"
    assert status == {"name": "docker", "status": "partial", "error": "permission_denied"}


def test_docker_collector_does_not_leak_invalid_payload_contents(tmp_path):
    path = tmp_path / "docker-status.json"
    path.write_text("not json TOKEN=super-secret", encoding="utf-8")

    payload, status = collect_docker(config=_config(tmp_path, path), period=_period())

    encoded = json.dumps(payload, sort_keys=True)
    assert payload["status"] == "failed"
    assert payload["error"] == "docker_status_invalid_json"
    assert status["error"] == "docker_status_invalid_json"
    assert "super-secret" not in encoded
    assert "TOKEN" not in encoded
