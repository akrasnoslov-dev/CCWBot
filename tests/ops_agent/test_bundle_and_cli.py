from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from ops_agent.bundle import BundleWriter
from ops_agent.cli import _mark_report_success, _validate_bundle, build_parser
from ops_agent.config import OpsAgentConfig, OpsAgentLimits
from ops_agent.redaction import RedactionReport
from ops_agent.schemas import Period
from ops_agent.state import load_state, resolve_period


def _write_mandatory_evidence(writer: BundleWriter) -> None:
    writer.write_json(
        "evidence/db/aggregate_metrics.json",
        {"schema_version": 1, "queries": {}},
    )
    writer.write_json("evidence/db/anomalies.json", {"schema_version": 1, "queries": {}})
    writer.write_json("evidence/health/health.json", {"schema_version": 1, "status": "ok"})
    writer.write_json("detectors/detector_results.json", {"schema_version": 1, "results": []})
    writer.write_text("detectors/detector_summary.md", "# Detector Summary\n")


def test_cli_parses_collect_auto():
    parser = build_parser()
    args = parser.parse_args(["collect", "--period", "auto", "--no-state-update"])

    assert args.command == "collect"
    assert args.period == "auto"
    assert args.no_state_update is True


def test_ops_agent_compose_overlay_passes_only_explicit_ops_agent_env():
    compose = Path("ops-agent/docker-compose.ops-agent.yml").read_text(encoding="utf-8")

    assert "env_file" not in compose
    assert "- .env" not in compose
    assert "TELEGRAM_BOT_TOKEN" not in compose
    assert "GROQ_API_KEY" not in compose


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

    status = writer.finalize(
        collection_status="complete",
        redaction_report=RedactionReport(),
        detector_count=0,
        protected_identity_map=False,
    )

    manifest = json.loads((writer.path / "manifest.json").read_text(encoding="utf-8"))
    assert status == "partial"
    assert manifest["collection_status"] == "partial"
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
    writer.write_text("evidence/logs/excerpts/app.tail-context.redacted.log", "y" * 1000)
    writer.write_text("evidence/health/health.json", "z" * 1000)
    size_before = writer._bundle_size_bytes()
    writer.config = OpsAgentConfig(
        database_url=None,
        health_url=None,
        output_dir=tmp_path,
        logs_dir=tmp_path / "logs",
        legacy_state_path=tmp_path / "state.json",
        limits=OpsAgentLimits(bundle_hard_cap_bytes=size_before - 4000),
    )

    status = writer._collection_status_after_size_enforcement("complete")

    assert status == "partial"
    assert not (writer.path / "evidence/db/raw_llm_samples.redacted.json").exists()
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
