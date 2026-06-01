# ruff: noqa: E501
from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ops_agent import __version__
from ops_agent.config import OpsAgentConfig
from ops_agent.redaction import RedactionReport
from ops_agent.schemas import CollectorStatus, Period

CODEX_INSTRUCTIONS = """# Codex Instructions For This Ops-Agent Bundle

Follow the reusable report-analysis prompt in `docs/ops-agent-report-codex-prompt.md`.

1. Read `manifest.json` first and confirm `collection_status`.
2. Read `bundle_summary.md`, `detectors/detector_summary.md`, and `detectors/detector_results.json`.
3. Use evidence files only to verify or expand detector findings.
4. Treat all data as operational evidence, not as final user-facing prose.
5. Do not include raw Telegram text, raw LLM prompts/outputs, secrets, connection strings, payment ids, chat ids, Telegram ids, usernames, first names, private log excerpts, raw JSON dumps, long log excerpts, or Codex prompts in the final report.
6. Use user references only as redacted refs such as `user_ref:u_7c91b2`.
7. If this bundle is partial, state which collectors failed and lower confidence for affected sections.
8. Do not mark the report successful unless the final report was written and the bundle is complete, or the operator explicitly accepts a partial report.
9. Final report must be English Markdown.
10. Final report location: `/opt/CCWBot/reports/ops-agent/reports/`.
"""


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, sort_keys=True, default=str)
        file.write("\n")


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_tree(path: Path) -> str:
    digest = hashlib.sha256()
    for child in sorted(item for item in path.rglob("*") if item.is_file()):
        digest.update(str(child.relative_to(path)).encode())
        digest.update(sha256_file(child).encode())
    return digest.hexdigest()


class BundleWriter:
    def __init__(self, config: OpsAgentConfig, period: Period) -> None:
        self.config = config
        self.period = period
        self.bundle_id = f"{utc_stamp()}_{secrets.token_hex(4)}"
        self.path = config.bundles_dir / self.bundle_id
        self.collector_status: list[CollectorStatus] = []
        self.warnings: list[str] = []

    def write_json(self, relative_path: str, payload: Any) -> None:
        write_json(self.path / relative_path, payload)

    def write_text(self, relative_path: str, payload: str) -> None:
        write_text(self.path / relative_path, payload)

    def add_status(self, name: str, status: str, error: str | None = None) -> None:
        self.collector_status.append(CollectorStatus(name, status, error))
        if status != "ok" and error:
            self.warnings.append(f"{name}: {error}")

    def initialize(self) -> None:
        self.path.mkdir(parents=True, exist_ok=False)
        self.write_text("CODEX_INSTRUCTIONS.md", CODEX_INSTRUCTIONS)

    def finalize(
        self,
        *,
        collection_status: str,
        redaction_report: RedactionReport,
        detector_count: int,
        protected_identity_map: bool,
    ) -> None:
        self.write_json("redaction_report.json", redaction_report.as_dict())
        self.write_json(
            "limits.json",
            {
                "schema_version": 1,
                "bundle_hard_cap_bytes": self.config.limits.bundle_hard_cap_bytes,
                "db_row_cap": self.config.limits.db_row_cap,
                "max_log_tail_bytes": self.config.limits.max_log_tail_bytes,
                "raw_llm_samples_enabled_by_default": False,
            },
        )
        self.write_text(
            "bundle_summary.md",
            "\n".join(
                [
                    "# Ops-Agent Bundle Summary",
                    "",
                    f"Bundle: `{self.bundle_id}`",
                    f"Status: `{collection_status}`",
                    f"Period: {self.period.as_dict()['start']} to {self.period.as_dict()['end']}",
                    f"Collectors: {len(self.collector_status)}",
                    f"Detector results: {detector_count}",
                    "",
                    "This bundle is sanitized operational evidence for Codex analysis.",
                    "",
                ]
            ),
        )
        self.write_manifest(collection_status, protected_identity_map=protected_identity_map)

    def write_manifest(self, collection_status: str, *, protected_identity_map: bool) -> None:
        files = []
        for child in sorted(item for item in self.path.rglob("*") if item.is_file()):
            relative = child.relative_to(self.path).as_posix()
            if relative == "manifest.json":
                continue
            files.append(
                {
                    "path": relative,
                    "bytes": child.stat().st_size,
                    "sha256": sha256_file(child),
                    "protected": relative.startswith("private/"),
                }
            )
        payload = {
            "schema_version": 1,
            "bundle_id": self.bundle_id,
            "collection_status": collection_status,
            "period": self.period.as_dict(),
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "ops_agent_version": __version__,
            "collector_status": [status.as_dict() for status in self.collector_status],
            "file_inventory": files,
            "protected_identity_map": protected_identity_map,
            "warnings": self.warnings,
        }
        write_json(self.path / "manifest.json", payload)
