from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest
from ops_agent.bundle import BundleWriter
from ops_agent.cli import _mark_report_success, _validate_bundle, build_parser
from ops_agent.config import OpsAgentConfig, OpsAgentLimits
from ops_agent.redaction import RedactionReport
from ops_agent.schemas import Period
from ops_agent.state import load_state, parse_timestamp, resolve_period

from ops_agent import cli


def _write_mandatory_evidence(writer: BundleWriter) -> None:
    writer.write_json(
        "evidence/db/aggregate_metrics.json",
        {"schema_version": 1, "queries": {}},
    )
    writer.write_json("evidence/db/alert_quality.json", {"schema_version": 1, "issues": []})
    writer.write_json("evidence/db/anomalies.json", {"schema_version": 1, "queries": {}})
    writer.write_json("evidence/health/health.json", {"schema_version": 1, "status": "ok"})
    writer.write_json("evidence/docker/container_state.json", {"schema_version": 1, "services": []})
    writer.write_json("evidence/logs/log_index.json", {"schema_version": 1, "files": []})
    writer.write_json(
        "evidence/logs/pattern_counts.json",
        {"schema_version": 1, "candidate_crossing_evidence": {"status": "unknown"}},
    )
    writer.write_json("detectors/detector_results.json", {"schema_version": 1, "results": []})
    writer.write_text("detectors/detector_summary.md", "# Detector Summary\n")
    writer.write_text("decision_report_context.md", "# Decision Context\n")


def _collect_args(tmp_path: Path, *, no_state_update: bool = True) -> argparse.Namespace:
    return argparse.Namespace(
        output_dir=str(tmp_path),
        period=None,
        since="2026-06-01T00:00:00Z",
        until="2026-06-01T01:00:00Z",
        no_state_update=no_state_update,
        include_raw_llm_samples=False,
        include_protected_identity_map=False,
    )


def _stub_collectors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    calls: list[str],
    *,
    limits: OpsAgentLimits | None = None,
) -> None:
    config = OpsAgentConfig(
        database_url=None,
        health_url=None,
        output_dir=tmp_path,
        logs_dir=tmp_path / "logs",
        legacy_state_path=tmp_path / "state.json",
        limits=limits or OpsAgentLimits(),
    )

    async def fake_db(**_kwargs):
        calls.append("db")
        return (
            {
                "evidence/db/aggregate_metrics.json": {"schema_version": 1, "queries": {}},
                "evidence/db/alert_quality.json": {"schema_version": 1, "issues": []},
                "evidence/db/anomalies.json": {"schema_version": 1, "queries": {}},
            },
            [{"name": "db.aggregate", "status": "ok", "error": None}],
        )

    async def fake_health(**_kwargs):
        calls.append("health")
        return (
            {"schema_version": 1, "status": "ok"},
            {"name": "health", "status": "ok", "error": None},
        )

    def fake_logs(**_kwargs):
        calls.append("logs")
        return (
            {"schema_version": 1, "files": []},
            {"schema_version": 1, "pattern_counts": {}},
            {},
            [{"name": "logs", "status": "ok", "error": None}],
        )

    def fake_docker(**_kwargs):
        calls.append("docker")
        return (
            {"schema_version": 1, "status": "ok", "services": []},
            {"name": "docker", "status": "ok", "error": None},
        )

    def fake_local_state(**_kwargs):
        calls.append("local_state")
        return {"ops_agent_state_snapshot": {}, "legacy_state_snapshot": {}}

    monkeypatch.setattr(cli, "load_config", lambda _output_dir: config)
    monkeypatch.setattr(cli, "collect_db", fake_db)
    monkeypatch.setattr(cli, "collect_health", fake_health)
    monkeypatch.setattr(cli, "collect_logs", fake_logs)
    monkeypatch.setattr(cli, "collect_docker", fake_docker)
    monkeypatch.setattr(cli, "collect_local_state", fake_local_state)
    monkeypatch.setattr(cli, "run_detectors", lambda _evidence, _period: [])
    monkeypatch.setattr(
        cli, "detector_payload", lambda _period, _results: {"schema_version": 1, "results": []}
    )
    monkeypatch.setattr(cli, "detector_summary", lambda _results: "# Detector Summary\n")
    monkeypatch.setattr(
        cli,
        "render_decision_report_context",
        lambda **kwargs: f"# Context\nStatus: {kwargs['collection_status']}\n",
    )


def test_cli_parses_collect_auto():
    parser = build_parser()
    args = parser.parse_args(["collect", "--period", "auto", "--no-state-update"])

    assert args.command == "collect"
    assert args.period == "auto"
    assert args.no_state_update is True


def test_resolve_period_accepts_until_now_for_explicit_window():
    now = datetime(2026, 6, 3, 9, 51, 35, tzinfo=timezone.utc)

    period = resolve_period(
        state={},
        period=None,
        since="2026-05-27T00:00:00Z",
        until="now",
        now=now,
    )

    assert period.start == datetime(2026, 5, 27, tzinfo=timezone.utc)
    assert period.end == now
    assert period.source == "explicit"


def test_resolve_period_rejects_reversed_or_overlong_explicit_window():
    with pytest.raises(ValueError, match="start must be before end"):
        resolve_period(
            state={},
            period=None,
            since="2026-06-03T00:00:00Z",
            until="2026-06-02T00:00:00Z",
        )

    with pytest.raises(ValueError, match="720 hours"):
        resolve_period(
            state={},
            period=None,
            since="2026-05-01T00:00:00Z",
            until="2026-06-03T00:00:00Z",
        )


def test_parse_timestamp_rejects_ambiguous_slash_dates_with_operator_message():
    with pytest.raises(ValueError, match="YYYY-MM-DDTHH:MM:SSZ"):
        parse_timestamp("06/06/2026")


def test_ops_agent_compose_overlay_passes_only_explicit_ops_agent_env():
    compose = Path("ops-agent/docker-compose.ops-agent.yml").read_text(encoding="utf-8")

    assert ".ops-agent.env" in compose
    assert "- .env" not in compose
    assert "TELEGRAM_BOT_TOKEN" not in compose
    assert "GROQ_API_KEY" not in compose


def test_production_collect_wrapper_restricts_arguments():
    script = Path("ops-agent/scripts/ccwbot-ops-agent-collect").read_text(encoding="utf-8")

    assert "DOCKER=/usr/bin/docker" in script
    assert "env -i" in script
    assert "collect --period auto \"$@\"" not in script
    assert "unsupported argument" in script
    assert "--since" in script
    assert "--until" in script
    assert "--no-state-update" in script
    assert "YYYY-MM-DDTHH:MM:SSZ" in script
    assert "slash dates are not accepted" in script
    assert "--include-raw-llm-samples" not in script
    assert "--include-protected-identity-map" not in script
    assert "--output-dir" not in script
    assert "eval " not in script
    assert "printenv" not in script
    assert "ps --all --format json" in script
    assert "OPS_AGENT_DOCKER_STATUS_JSON_PATH=/tmp/ops-agent-docker-status.json" in script
    assert '$docker_status_file:/tmp/ops-agent-docker-status.json:ro' in script
    # docker inspect is allowed for exactly one sanitized read-only purpose: container
    # name + RestartCount, mounted read-only into the collector. No other inspect use.
    assert script.count('"$DOCKER" inspect') == 1
    assert (
        '"$DOCKER" inspect --format '
        "'{\"Name\": {{json .Name}}, \"RestartCount\": {{json .RestartCount}}}'"
    ) in script
    assert "OPS_AGENT_DOCKER_RESTARTS_JSON_PATH=/tmp/ops-agent-docker-restarts.json" in script
    assert '$docker_restarts_file:/tmp/ops-agent-docker-restarts.json:ro' in script
    assert " compose config" not in script


def test_production_mark_success_wrapper_restricts_paths_and_arguments():
    script = Path("ops-agent/scripts/ccwbot-ops-agent-mark-report-success").read_text(
        encoding="utf-8"
    )

    assert "DOCKER=/usr/bin/docker" in script
    assert "env -i" in script
    assert "mark-report-success" in script
    assert "unsupported argument" in script
    assert "/opt/CCWBot/reports/ops-agent/bundles/" in script
    assert "/opt/CCWBot/reports/ops-agent/reports/*.md" in script
    assert "--accept-partial" in script
    assert "--output-dir" not in script
    assert "eval " not in script
    assert "printenv" not in script


def test_ops_agent_runbook_documents_safe_production_report_tree():
    readme = Path("ops-agent/README.md").read_text(encoding="utf-8")

    assert "install -d -m 750 -o root -g ccwbot_ops /opt/CCWBot/reports/ops-agent" in readme
    assert "install -d -m 750 -o root -g ccwbot_ops /opt/CCWBot/reports/ops-agent/bundles" in readme
    assert (
        "install -d -m 770 -o root -g ccwbot_ops /opt/CCWBot/reports/ops-agent/reports"
        in readme
    )
    assert "sudo -u ccwbot_ops test ! -r /opt/CCWBot/.env" in readme
    assert "sudo -u ccwbot_ops test ! -r /opt/CCWBot/.ops-agent.env" in readme
    assert "sudo -u ccwbot_ops test -r /opt/CCWBot/reports/ops-agent/bundles" in readme
    assert "ccwbot_ops` can read generated bundles" in readme
    assert "write only final Markdown reports" in readme
    assert "Post-deploy verification after Event Alert delivery-gap changes" in readme
    assert (
        "sudo /usr/local/bin/ccwbot-ops-agent-collect --since <deploy-start-UTC> "
        "--until now --no-state-update"
        in readme
    )
    assert "rebuild the `ops-agent` Docker image" in readme
    assert "market_events_without_alert_deliveries" in readme


def test_gitignore_excludes_ops_agent_secrets_and_generated_artifacts():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert ".ops-agent.env" in gitignore
    assert "reports/ops-agent/bundles/" in gitignore
    assert "reports/ops-agent/reports/" in gitignore


def test_bundle_manifest_contains_required_files(tmp_path):
    config = OpsAgentConfig(
        database_url=None,
        health_url=None,
        output_dir=tmp_path,
        logs_dir=tmp_path / "logs",
        legacy_state_path=tmp_path / "state.json",
    )
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    writer = BundleWriter(config, period)
    writer.initialize()
    _write_mandatory_evidence(writer)
    writer.finalize(
        collection_status="complete",
        redaction_report=RedactionReport(),
        detector_count=0,
        protected_identity_map=False,
    )

    assert (writer.path / "CODEX_INSTRUCTIONS.md").is_file()
    manifest = json.loads((writer.path / "manifest.json").read_text(encoding="utf-8"))
    inventory_paths = {item["path"] for item in manifest["file_inventory"]}
    assert "CODEX_INSTRUCTIONS.md" in inventory_paths
    assert "bundle_summary.md" in inventory_paths
    assert "decision_report_context.md" in inventory_paths
    assert "evidence/docker/container_state.json" in inventory_paths
    assert "evidence/logs/log_index.json" in inventory_paths
    assert "evidence/logs/pattern_counts.json" in inventory_paths
    assert manifest["collection_status"] == "complete"


def test_finalization_marks_bundle_failed_when_required_evidence_is_absent(tmp_path):
    config = OpsAgentConfig(
        database_url=None,
        health_url=None,
        output_dir=tmp_path,
        logs_dir=tmp_path / "logs",
        legacy_state_path=tmp_path / "state.json",
    )
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    writer = BundleWriter(config, period)
    writer.initialize()
    writer.write_json("detectors/detector_results.json", {"schema_version": 1, "results": []})
    writer.write_text("detectors/detector_summary.md", "# Detector Summary\n")

    status = writer.finalize(
        collection_status="complete",
        redaction_report=RedactionReport(),
        detector_count=0,
        protected_identity_map=False,
    )

    manifest = json.loads((writer.path / "manifest.json").read_text(encoding="utf-8"))
    assert status == "failed"
    assert manifest["collection_status"] == "failed"
    assert {item["name"] for item in manifest["collector_status"]} >= {"bundle.finalization"}


def test_collect_log_failure_finalizes_partial_bundle_and_runs_later_collectors(
    tmp_path, monkeypatch, capsys
):
    calls: list[str] = []
    _stub_collectors(monkeypatch, tmp_path, calls)

    def failed_logs(**_kwargs):
        calls.append("logs")
        raise RuntimeError("log reader failed")

    monkeypatch.setattr(cli, "collect_logs", failed_logs)

    result = asyncio.run(cli._collect(_collect_args(tmp_path)))

    payload = json.loads(capsys.readouterr().out)
    manifest_path = Path(payload["manifest_path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required_files = {
        "manifest.json",
        "bundle_summary.md",
        "decision_report_context.md",
        "detectors/detector_summary.md",
        "detectors/detector_results.json",
        "redaction_report.json",
        "limits.json",
        "evidence/docker/container_state.json",
        "evidence/logs/log_index.json",
        "evidence/logs/pattern_counts.json",
    }

    assert result == 1
    assert payload["status"] == "partial"
    assert calls == ["db", "health", "logs", "docker", "local_state"]
    assert manifest["collection_status"] == "partial"
    assert {item["name"] for item in manifest["collector_status"]} >= {"logs", "docker"}
    assert (manifest_path.parent / "evidence/logs/pattern_counts.json").is_file()
    assert "Status: `partial`" in (manifest_path.parent / "bundle_summary.md").read_text(
        encoding="utf-8"
    )
    assert required_files <= {
        path.relative_to(manifest_path.parent).as_posix()
        for path in manifest_path.parent.rglob("*")
        if path.is_file()
    }


def test_collect_db_failure_writes_required_placeholders_and_runs_later_collectors(
    tmp_path, monkeypatch, capsys
):
    calls: list[str] = []
    _stub_collectors(monkeypatch, tmp_path, calls)

    async def failed_db(**_kwargs):
        calls.append("db")
        raise RuntimeError("db response content must not be retained")

    monkeypatch.setattr(cli, "collect_db", failed_db)

    result = asyncio.run(cli._collect(_collect_args(tmp_path)))

    payload = json.loads(capsys.readouterr().out)
    manifest_path = Path(payload["manifest_path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert result == 1
    assert calls == ["db", "health", "logs", "docker", "local_state"]
    assert next(item for item in manifest["collector_status"] if item["name"] == "db") == {
        "name": "db",
        "status": "partial",
        "error": "collector_error",
    }
    for path in (
        "evidence/db/aggregate_metrics.json",
        "evidence/db/alert_quality.json",
        "evidence/db/anomalies.json",
    ):
        evidence = json.loads((manifest_path.parent / path).read_text(encoding="utf-8"))
        assert evidence["status"] == "failed"
        assert evidence["error"] == "collector_error"


def test_collect_state_reflects_final_size_downgrade(tmp_path, monkeypatch, capsys):
    _stub_collectors(
        monkeypatch,
        tmp_path,
        [],
        limits=OpsAgentLimits(bundle_hard_cap_bytes=1),
    )

    result = asyncio.run(cli._collect(_collect_args(tmp_path, no_state_update=False)))

    payload = json.loads(capsys.readouterr().out)
    manifest = json.loads(Path(payload["manifest_path"]).read_text(encoding="utf-8"))
    state = load_state(tmp_path / "state" / "state.json")

    assert result == 1
    assert payload["status"] == "partial"
    assert manifest["collection_status"] == "partial"
    assert "Status: partial" in Path(payload["manifest_path"]).with_name(
        "decision_report_context.md"
    ).read_text(encoding="utf-8")
    assert state["last_collection"]["status"] == "partial"
    assert "bundle.size_limit" in state["last_collection"]["failed_collectors"]


def test_collect_orchestration_error_does_not_export_exception_content(
    tmp_path, monkeypatch, capsys
):
    _stub_collectors(monkeypatch, tmp_path, [])
    secret = "Authorization: Bearer short-private-token"

    def failed_logs(**_kwargs):
        raise RuntimeError(secret)

    monkeypatch.setattr(cli, "collect_logs", failed_logs)

    result = asyncio.run(cli._collect(_collect_args(tmp_path)))

    output = capsys.readouterr().out
    payload = json.loads(output)
    manifest_text = Path(payload["manifest_path"]).read_text(encoding="utf-8")

    assert result == 1
    assert secret not in output
    assert secret not in manifest_text
    assert "collector_error" in manifest_text


def test_collect_finalization_failure_cannot_return_success(tmp_path, monkeypatch, capsys):
    _stub_collectors(monkeypatch, tmp_path, [])

    def failed_manifest(*_args, **_kwargs):
        raise OSError("finalization storage failure")

    monkeypatch.setattr(cli.BundleWriter, "write_manifest", failed_manifest)

    result = asyncio.run(cli._collect(_collect_args(tmp_path)))

    payload = json.loads(capsys.readouterr().out)

    assert result == 2
    assert payload["status"] == "failed"
    assert not Path(payload["manifest_path"]).exists()


def test_final_manifest_failure_does_not_record_a_successful_state(
    tmp_path, monkeypatch, capsys
):
    _stub_collectors(monkeypatch, tmp_path, [])
    state_writes: list[object] = []

    def tracked_state(*args, **_kwargs):
        state_writes.append(args)

    def failed_manifest(*_args, **_kwargs):
        raise OSError("finalization storage failure")

    monkeypatch.setattr(cli, "save_state", tracked_state)
    monkeypatch.setattr(cli.BundleWriter, "write_manifest", failed_manifest)

    result = asyncio.run(cli._collect(_collect_args(tmp_path, no_state_update=False)))

    payload = json.loads(capsys.readouterr().out)

    assert result == 2
    assert payload["status"] == "failed"
    assert not Path(payload["manifest_path"]).exists()
    assert state_writes == []


def test_state_write_failure_after_manifest_does_not_change_bundle_status(
    tmp_path, monkeypatch, capsys
):
    _stub_collectors(monkeypatch, tmp_path, [])

    def failed_state(*_args, **_kwargs):
        raise OSError("state storage failure")

    monkeypatch.setattr(cli, "save_state", failed_state)

    result = asyncio.run(cli._collect(_collect_args(tmp_path, no_state_update=False)))

    payload = json.loads(capsys.readouterr().out)
    manifest = json.loads(Path(payload["manifest_path"]).read_text(encoding="utf-8"))

    assert result == 0
    assert payload["status"] == "complete"
    assert payload["state_update_status"] == "failed"
    assert manifest["collection_status"] == "complete"


def test_bundle_manifest_marks_partial_when_size_cap_is_exceeded(tmp_path):
    config = OpsAgentConfig(
        database_url=None,
        health_url=None,
        output_dir=tmp_path,
        logs_dir=tmp_path / "logs",
        legacy_state_path=tmp_path / "state.json",
        limits=OpsAgentLimits(bundle_hard_cap_bytes=1),
    )
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    writer = BundleWriter(config, period)
    writer.initialize()
    _write_mandatory_evidence(writer)

    status = writer.finalize(
        collection_status="complete",
        redaction_report=RedactionReport(),
        detector_count=0,
        protected_identity_map=False,
    )

    manifest = json.loads((writer.path / "manifest.json").read_text(encoding="utf-8"))
    assert status == "partial"
    assert manifest["collection_status"] == "partial"
    assert "Status: `partial`" in (writer.path / "bundle_summary.md").read_text(
        encoding="utf-8"
    )
    assert any("bundle_size_exceeded" in warning for warning in manifest["warnings"])


def test_bundle_size_pressure_drops_lower_priority_files_first(tmp_path):
    config = OpsAgentConfig(
        database_url=None,
        health_url=None,
        output_dir=tmp_path,
        logs_dir=tmp_path / "logs",
        legacy_state_path=tmp_path / "state.json",
        limits=OpsAgentLimits(bundle_hard_cap_bytes=999_999),
    )
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    writer = BundleWriter(config, period)
    writer.initialize()
    _write_mandatory_evidence(writer)
    writer.write_text("evidence/db/raw_llm_samples.redacted.json", "x" * 5000)
    writer.write_text("evidence/db/event_analysis_decision_timeline.json", "a" * 2000)
    writer.write_text("evidence/logs/excerpts/app.tail-context.redacted.log", "y" * 1000)
    writer.write_text("evidence/health/health.json", "z" * 1000)
    size_before = writer._bundle_size_bytes()
    writer.config = OpsAgentConfig(
        database_url=None,
        health_url=None,
        output_dir=tmp_path,
        logs_dir=tmp_path / "logs",
        legacy_state_path=tmp_path / "state.json",
        limits=OpsAgentLimits(bundle_hard_cap_bytes=size_before - 6000),
    )

    status = writer._collection_status_after_size_enforcement("complete")

    assert status == "partial"
    assert not (writer.path / "evidence/db/raw_llm_samples.redacted.json").exists()
    assert not (writer.path / "evidence/db/event_analysis_decision_timeline.json").exists()
    assert (writer.path / "evidence/logs/excerpts/app.tail-context.redacted.log").exists()
    assert (writer.path / "detectors/detector_results.json").exists()
    assert (writer.path / "evidence/health/health.json").exists()


def test_protected_identity_map_uses_owner_only_permissions(tmp_path):
    config = OpsAgentConfig(
        database_url=None,
        health_url=None,
        output_dir=tmp_path,
        logs_dir=tmp_path / "logs",
        legacy_state_path=tmp_path / "state.json",
    )
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    writer = BundleWriter(config, period)
    writer.initialize()
    writer.write_protected_json("private/identity_map.protected.json", {"user": {"1": "u"}})
    _write_mandatory_evidence(writer)
    writer.finalize(
        collection_status="complete",
        redaction_report=RedactionReport(),
        detector_count=0,
        protected_identity_map=True,
    )

    protected_path = writer.path / "private/identity_map.protected.json"
    manifest = json.loads((writer.path / "manifest.json").read_text(encoding="utf-8"))
    inventory = {item["path"]: item for item in manifest["file_inventory"]}
    assert inventory["private/identity_map.protected.json"]["protected"] is True
    if os.name != "nt":
        assert protected_path.stat().st_mode & 0o777 == 0o600


def test_validate_bundle_detects_hash_mismatch(tmp_path):
    config = OpsAgentConfig(
        database_url=None,
        health_url=None,
        output_dir=tmp_path,
        logs_dir=tmp_path / "logs",
        legacy_state_path=tmp_path / "state.json",
    )
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    writer = BundleWriter(config, period)
    writer.initialize()
    _write_mandatory_evidence(writer)
    writer.finalize(
        collection_status="complete",
        redaction_report=RedactionReport(),
        detector_count=0,
        protected_identity_map=False,
    )
    (writer.path / "detectors" / "detector_summary.md").write_text(
        "# Tampered\n",
        encoding="utf-8",
    )

    result = _validate_bundle(type("Args", (), {"bundle": str(writer.path)})())

    assert result == 1


def test_validate_bundle_requires_mandatory_core_evidence(tmp_path):
    config = OpsAgentConfig(
        database_url=None,
        health_url=None,
        output_dir=tmp_path,
        logs_dir=tmp_path / "logs",
        legacy_state_path=tmp_path / "state.json",
    )
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    writer = BundleWriter(config, period)
    writer.initialize()
    writer.write_json("detectors/detector_results.json", {"schema_version": 1, "results": []})
    writer.write_text("detectors/detector_summary.md", "# Detector Summary\n")
    writer.finalize(
        collection_status="complete",
        redaction_report=RedactionReport(),
        detector_count=0,
        protected_identity_map=False,
    )

    result = _validate_bundle(type("Args", (), {"bundle": str(writer.path)})())

    assert result == 1


def test_validate_bundle_rejects_manifest_inventory_path_traversal(tmp_path):
    writer = _write_valid_bundle(tmp_path)
    manifest_path = writer.path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["file_inventory"].append(
        {
            "path": "../outside.txt",
            "bytes": 1,
            "sha256": "abc",
            "protected": False,
        }
    )
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = _validate_bundle(type("Args", (), {"bundle": str(writer.path)})())

    assert result == 1


def _write_valid_bundle(tmp_path: Path) -> BundleWriter:
    config = OpsAgentConfig(
        database_url=None,
        health_url=None,
        output_dir=tmp_path,
        logs_dir=tmp_path / "logs",
        legacy_state_path=tmp_path / "state.json",
    )
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    writer = BundleWriter(config, period)
    writer.initialize()
    _write_mandatory_evidence(writer)
    writer.finalize(
        collection_status="complete",
        redaction_report=RedactionReport(),
        detector_count=0,
        protected_identity_map=False,
    )
    return writer


def test_mark_report_success_rejects_paths_outside_ops_agent_dirs(tmp_path):
    writer = _write_valid_bundle(tmp_path)
    report = tmp_path / "reports" / "report.md"
    report.parent.mkdir(parents=True)
    report.write_text("# Report\n", encoding="utf-8")

    result = _mark_report_success(
        type(
            "Args",
            (),
            {
                "bundle": str(writer.path.parent.parent / "other"),
                "report": str(report),
                "accept_partial": False,
                "output_dir": str(tmp_path),
            },
        )()
    )

    assert result == 1


def test_mark_report_success_rejects_tampered_bundle(tmp_path):
    writer = _write_valid_bundle(tmp_path)
    report = tmp_path / "reports" / "report.md"
    report.parent.mkdir(parents=True)
    report.write_text("# Report\n", encoding="utf-8")
    (writer.path / "detectors" / "detector_summary.md").write_text(
        "# Tampered\n",
        encoding="utf-8",
    )

    result = _mark_report_success(
        type(
            "Args",
            (),
            {
                "bundle": str(writer.path),
                "report": str(report),
                "accept_partial": False,
                "output_dir": str(tmp_path),
            },
        )()
    )

    assert result == 1
    assert "last_successful_report" not in load_state(tmp_path / "state" / "state.json")


def test_mark_report_success_acceptance_advances_auto_period(tmp_path):
    writer = _write_valid_bundle(tmp_path)
    report = tmp_path / "reports" / "report.md"
    report.parent.mkdir(parents=True)
    report.write_text("# Report\n", encoding="utf-8")

    result = _mark_report_success(
        type(
            "Args",
            (),
            {
                "bundle": str(writer.path),
                "report": str(report),
                "accept_partial": False,
                "output_dir": str(tmp_path),
            },
        )()
    )

    state = load_state(tmp_path / "state" / "state.json")
    next_period = resolve_period(
        state=state,
        period="auto",
        since=None,
        until="2026-06-03T00:00:00Z",
    )
    assert result == 0
    assert state["last_successful_report"]["period_end"] == "2026-06-02T00:00:00Z"
    assert next_period.start == datetime(2026, 6, 2, tzinfo=timezone.utc)
