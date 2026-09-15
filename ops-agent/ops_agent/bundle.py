# ruff: noqa: E501
from __future__ import annotations

import hashlib
import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ops_agent import __version__
from ops_agent.config import OpsAgentConfig
from ops_agent.redaction import RedactionReport
from ops_agent.schemas import CollectorStatus, Period

NON_DROPPABLE_BUNDLE_FILES = {
    "CODEX_INSTRUCTIONS.md",
    "manifest.json",
    "bundle_summary.md",
    "decision_report_context.md",
    "detectors/detector_summary.md",
    "detectors/detector_results.json",
    "evidence/db/aggregate_metrics.json",
    "evidence/db/alert_quality.json",
    "evidence/db/anomalies.json",
    "evidence/health/health.json",
    "evidence/docker/container_state.json",
    "evidence/logs/log_index.json",
    "evidence/logs/pattern_counts.json",
    "redaction_report.json",
    "limits.json",
}

class BundleSizeLimitError(RuntimeError):
    """Raised when mandatory evidence alone cannot fit the configured hard cap."""


CODEX_INSTRUCTIONS = """# Codex Instructions For This Ops-Agent Bundle

Follow the reusable report-analysis prompt in `docs/ops-agent-report-codex-prompt.md`.

1. Read `manifest.json` first and confirm `collection_status`.
2. Read `bundle_summary.md`, `decision_report_context.md`, `detectors/detector_summary.md`, and `detectors/detector_results.json`.
3. Use evidence files only to verify or expand detector findings.
4. Treat all data as operational evidence, not as final user-facing prose.
5. Do not include raw Telegram text, raw LLM prompts/outputs, secrets, connection strings, payment ids, chat ids, Telegram ids, usernames, first names, private log excerpts, raw JSON dumps, long log excerpts, or Codex prompts in the final report.
6. Use user references only as redacted refs such as `user_ref:u_7c91b2`.
7. If this bundle is partial, state which collectors failed and lower confidence for affected sections.
8. Treat period-matched log evidence as stronger than tail-context log evidence.
9. Treat detector `unknown` as an evidence gap or inconclusive state, not as healthy.
10. Classify market events without deliveries before calling them delivery failures.
11. Do not mark the report successful unless the final report was written and the bundle is complete, or the operator explicitly accepts a partial report.
12. On production, use only the root-owned wrappers authorized by the operator: `sudo /usr/local/bin/ccwbot-ops-agent-collect` and `sudo /usr/local/bin/ccwbot-ops-agent-mark-report-success`.
13. Do not run raw `docker compose`, raw `ops-agent`, deployment, restart, migration, environment-printing, or secret-reading commands.
14. Final report must be English Markdown only; do not add a JSON summary file.
15. Start the final report with an Executive Summary that states status, top issue, affected users when available, most severe finding, next fix, and PR mapping.
16. Include report metadata, user impact, percentages beside meaningful counts, alert quality, delivery funnel, suppression reasons, noisy event families, root-cause confidence groups, PR mapping, and data completeness/limitations.
17. Final report location: `/opt/CCWBot/reports/ops-agent/reports/`.
"""


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, sort_keys=True, default=str)
        file.write("\n")


def write_json_atomic(path: Path, payload: Any) -> None:
    """Publish the manifest only after its complete JSON payload is on disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    try:
        write_json(temporary, payload)
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def write_protected_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass
    try:
        write_json(path, payload)
        os.chmod(path, 0o600)
    except Exception:
        # Never allow raw identity mappings to remain in a bundle after permission
        # hardening fails. The caller fails closed if this cleanup cannot complete.
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


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

    def write_protected_json(self, relative_path: str, payload: Any) -> None:
        write_protected_json(self.path / relative_path, payload)

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
        detector_status_counts: dict[str, int] | None = None,
        log_evidence_summary: dict[str, Any] | None = None,
        publish_manifest: bool = True,
    ) -> str:
        self.write_json("redaction_report.json", redaction_report.as_dict())
        self.write_json(
            "limits.json",
            {
                "schema_version": 1,
                "bundle_hard_cap_bytes": self.config.limits.bundle_hard_cap_bytes,
                "db_row_cap": self.config.limits.db_row_cap,
                "log_source_scope": "all_retained_files_scanned_completely",
                "raw_llm_samples_enabled_by_default": False,
                "duplicate_market_event_bucket_minutes": (
                    self.config.limits.duplicate_market_event_bucket_minutes
                ),
            },
        )
        detector_status_counts = detector_status_counts or {}
        log_evidence_summary = log_evidence_summary or {}
        self.write_summary(
            collection_status=collection_status,
            detector_count=detector_count,
            detector_status_counts=detector_status_counts,
            log_evidence_summary=log_evidence_summary,
        )
        final_status = self._collection_status_after_size_enforcement(
            collection_status,
            protected_identity_map=protected_identity_map,
        )
        missing = self._missing_required_files_before_manifest()
        if missing:
            self.add_status(
                "bundle.finalization",
                "failed",
                "missing_required_bundle_files",
            )
            self.warnings.append(
                "bundle_finalization_missing_required_files: " + ", ".join(missing)
            )
            final_status = "failed"
        elif final_status == "complete" and any(
            status.status != "ok" for status in self.collector_status
        ):
            # The caller normally derives this, but a finalizer must never certify a
            # collector-failed bundle as complete just because of an incorrect input.
            final_status = "partial"
        if final_status != collection_status:
            self.write_summary(
                collection_status=final_status,
                detector_count=detector_count,
                detector_status_counts=detector_status_counts,
                log_evidence_summary=log_evidence_summary,
            )
            final_status = self._collection_status_after_size_enforcement(
                final_status,
                protected_identity_map=protected_identity_map,
            )
        if publish_manifest:
            self.write_manifest(final_status, protected_identity_map=protected_identity_map)
        return final_status

    def write_summary(
        self,
        *,
        collection_status: str,
        detector_count: int,
        detector_status_counts: dict[str, int],
        log_evidence_summary: dict[str, Any],
    ) -> None:
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
                    "Detector statuses: "
                    + ", ".join(
                        f"{name}={count}"
                        for name, count in sorted(detector_status_counts.items())
                    ),
                    "Log evidence: "
                    + (
                        "period-matched entries available"
                        if log_evidence_summary.get("period_filter_available")
                        else "tail-context only or no parseable timestamps"
                    ),
                    f"Log period-matched lines: {log_evidence_summary.get('period_matched_lines', 0)}",
                    "Log unscoped/tail-context lines: "
                    f"{log_evidence_summary.get('unparseable_timestamp_lines', 0)}",
                    "",
                    "This bundle is sanitized operational evidence for Codex analysis.",
                    "Unknown detector results are evidence gaps or inconclusive states, not healthy states.",
                    "",
                ]
            ),
        )

    def _missing_required_files_before_manifest(self) -> list[str]:
        return sorted(
            relative
            for relative in NON_DROPPABLE_BUNDLE_FILES - {"manifest.json"}
            if not (self.path / relative).is_file()
        )

    def _bundle_size_bytes(self) -> int:
        return sum(child.stat().st_size for child in self.path.rglob("*") if child.is_file())

    def _drop_candidates_for_size_pressure(self) -> list[Path]:
        candidates: list[Path] = []
        priority_groups = [
            ["evidence/db/raw_llm_samples.redacted.json"],
            [
                "evidence/db/event_analysis_decision_timeline.json",
                "evidence/db/alert_similarity_groups.json",
            ],
            [
                "evidence/db/alert_content_fingerprints.json",
                "evidence/db/backend_suppression_effectiveness.json",
                "evidence/db/event_identity_quality.json",
            ],
            [
                item.relative_to(self.path).as_posix()
                for item in sorted((self.path / "evidence/logs/excerpts").glob("*.tail-context.redacted.log"))
                if item.is_file()
            ],
            [
                item.relative_to(self.path).as_posix()
                for item in sorted((self.path / "evidence/logs/excerpts").glob("*.period.redacted.log"))
                if item.is_file()
            ],
            [
                "evidence/db/recent_market_events.json",
                "evidence/db/recent_news_failures.json",
            ],
            [
                "evidence/local_state/legacy_state_snapshot.json",
                "evidence/local_state/ops_agent_state_snapshot.json",
            ],
        ]
        for group in priority_groups:
            candidates.extend(
                self.path / relative
                for relative in group
                if relative not in NON_DROPPABLE_BUNDLE_FILES
            )
        return candidates

    def _collection_status_after_size_enforcement(
        self,
        collection_status: str,
        *,
        protected_identity_map: bool | None = None,
    ) -> str:
        limit = self.config.limits.bundle_hard_cap_bytes
        if self._bundle_size_with_pending_manifest(
            collection_status, protected_identity_map
        ) <= limit:
            return collection_status
        dropped: list[str] = []
        candidates = iter(self._drop_candidates_for_size_pressure())
        self._record_size_limit_status("bundle hard cap exceeded")
        while True:
            bundle_size = self._bundle_size_with_pending_manifest(
                "partial", protected_identity_map
            )
            if bundle_size <= limit:
                if dropped:
                    warning = "bundle_size_pressure_dropped_files: " + ", ".join(dropped)
                    if warning not in self.warnings:
                        self._set_size_warning(warning)
                        # The warning is stored in the manifest, so account for its
                        # bytes before declaring the hard-cap check complete.
                        continue
                return "partial"
            try:
                candidate = next(candidates)
            except StopIteration:
                self._set_size_warning(
                    "bundle_size_exceeded: "
                    f"bundle is {bundle_size} bytes, over hard cap {limit} bytes"
                )
                final_size = self._bundle_size_with_pending_manifest(
                    "partial", protected_identity_map
                )
                raise BundleSizeLimitError(
                    f"mandatory bundle evidence is {final_size} bytes, over hard cap {limit}"
                ) from None
            if not candidate.is_file():
                continue
            relative = candidate.relative_to(self.path).as_posix()
            candidate.unlink()
            dropped.append(relative)

    def _bundle_size_with_pending_manifest(
        self, collection_status: str, protected_identity_map: bool | None
    ) -> int:
        size = self._bundle_size_bytes()
        if protected_identity_map is not None:
            size += len(
                json.dumps(
                    self._manifest_payload(
                        collection_status,
                        protected_identity_map=protected_identity_map,
                    ),
                    indent=2,
                    sort_keys=True,
                    default=str,
                ).encode("utf-8")
            ) + 1
        return size

    def _set_size_warning(self, warning: str) -> None:
        self.warnings[:] = [
            item
            for item in self.warnings
            if not item.startswith("bundle_size_pressure_")
            and not item.startswith("bundle_size_exceeded:")
        ]
        self.warnings.append(warning)

    def _record_size_limit_status(self, error: str) -> None:
        if any(status.name == "bundle.size_limit" for status in self.collector_status):
            return
        self.collector_status.append(CollectorStatus("bundle.size_limit", "partial", error))

    def write_manifest(self, collection_status: str, *, protected_identity_map: bool) -> None:
        write_json_atomic(
            self.path / "manifest.json",
            self._manifest_payload(
                collection_status,
                protected_identity_map=protected_identity_map,
            ),
        )

    def _manifest_payload(
        self, collection_status: str, *, protected_identity_map: bool
    ) -> dict[str, Any]:
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
        return {
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
