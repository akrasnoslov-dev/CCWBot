from __future__ import annotations

import json
from datetime import datetime, timezone

from ops_agent.bundle import BundleWriter
from ops_agent.cli import build_parser
from ops_agent.config import OpsAgentConfig
from ops_agent.redaction import RedactionReport
from ops_agent.schemas import Period


def test_cli_parses_collect_auto():
    parser = build_parser()
    args = parser.parse_args(["collect", "--period", "auto", "--no-state-update"])

    assert args.command == "collect"
    assert args.period == "auto"
    assert args.no_state_update is True


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
    writer.write_json("detectors/detector_results.json", {"schema_version": 1, "results": []})
    writer.write_text("detectors/detector_summary.md", "# Detector Summary\n")
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

