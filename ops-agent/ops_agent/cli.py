from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from ops_agent.bundle import NON_DROPPABLE_BUNDLE_FILES, BundleWriter, sha256_file, sha256_tree
from ops_agent.collectors.db import collect_db
from ops_agent.collectors.health import collect_health
from ops_agent.collectors.local_state import collect_local_state
from ops_agent.collectors.logs import collect_logs
from ops_agent.config import load_config
from ops_agent.detectors import detector_payload, detector_summary, run_detectors
from ops_agent.redaction import RedactionReport, ReferenceMapper, redact_error_message
from ops_agent.retention import apply_retention
from ops_agent.state import (
    load_state,
    record_collection,
    record_report_success,
    resolve_period,
    save_state,
)


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, sort_keys=True, default=str))


async def _collect(args: argparse.Namespace) -> int:
    config = load_config(args.output_dir)
    state = load_state(config.state_path)
    try:
        period = resolve_period(
            state=state,
            period=args.period,
            since=args.since,
            until=args.until,
        )
    except ValueError as error:
        _print_json({"status": "failed", "error": str(error)})
        return 2
    mapper = ReferenceMapper()
    redaction_report = RedactionReport()
    writer = BundleWriter(config, period)
    evidence: dict[str, Any] = {}
    protected_identity_map = False
    writer.initialize()

    try:
        db_payloads, db_statuses = await collect_db(
            config=config,
            period=period,
            mapper=mapper,
            redaction_report=redaction_report,
            include_raw_llm_samples=args.include_raw_llm_samples,
        )
        for path, payload in db_payloads.items():
            writer.write_json(path, payload)
            evidence[path] = payload
        for status in db_statuses:
            writer.add_status(str(status["name"]), str(status["status"]), status.get("error"))
    except Exception as error:
        writer.add_status("db", "partial", redact_error_message(error, mapper, redaction_report))

    health_payload, health_status = await collect_health(
        config=config,
        period=period,
        mapper=mapper,
        redaction_report=redaction_report,
    )
    writer.write_json("evidence/health/health.json", health_payload)
    evidence["evidence/health/health.json"] = health_payload
    writer.add_status(
        str(health_status["name"]), str(health_status["status"]), health_status.get("error")
    )

    log_index, pattern_counts, excerpts, log_statuses = collect_logs(
        config=config,
        period=period,
        mapper=mapper,
        redaction_report=redaction_report,
    )
    writer.write_json("evidence/logs/log_index.json", log_index)
    writer.write_json("evidence/logs/pattern_counts.json", pattern_counts)
    evidence["evidence/logs/log_index.json"] = log_index
    evidence["evidence/logs/pattern_counts.json"] = pattern_counts
    for path, payload in excerpts.items():
        writer.write_text(path, payload["text"])
    for status in log_statuses:
        writer.add_status(str(status["name"]), str(status["status"]), status.get("error"))

    local_state = collect_local_state(
        config=config,
        mapper=mapper,
        redaction_report=redaction_report,
    )
    writer.write_json(
        "evidence/local_state/ops_agent_state_snapshot.json",
        local_state["ops_agent_state_snapshot"],
    )
    writer.write_json(
        "evidence/local_state/legacy_state_snapshot.json",
        local_state["legacy_state_snapshot"],
    )
    writer.add_status("local_state", "ok", None)

    if args.include_protected_identity_map:
        writer.write_protected_json("private/identity_map.protected.json", mapper.identity_map)
        protected_identity_map = True

    results = run_detectors(evidence, period)
    writer.write_json("detectors/detector_results.json", detector_payload(period, results))
    writer.write_text("detectors/detector_summary.md", detector_summary(results))
    detector_status_counts: dict[str, int] = {}
    for result in results:
        detector_status_counts[result.status] = detector_status_counts.get(result.status, 0) + 1
    log_evidence_summary = _summarize_log_evidence(log_index)

    partial = any(status.status != "ok" for status in writer.collector_status)
    collection_status = "partial" if partial else "complete"
    collection_status = writer.finalize(
        collection_status=collection_status,
        redaction_report=redaction_report,
        detector_count=len(results),
        protected_identity_map=protected_identity_map,
        detector_status_counts=detector_status_counts,
        log_evidence_summary=log_evidence_summary,
    )

    if not args.no_state_update:
        save_state(
            config.state_path,
            record_collection(
                state,
                bundle_id=writer.bundle_id,
                status=collection_status,
                period=period,
            ),
        )
    apply_retention(config)
    _print_json(
        {
            "status": collection_status,
            "bundle_path": str(writer.path),
            "codex_instructions_path": str(writer.path / "CODEX_INSTRUCTIONS.md"),
            "manifest_path": str(writer.path / "manifest.json"),
            "period_start": period.as_dict()["start"],
            "period_end": period.as_dict()["end"],
        }
    )
    return 0


def _summarize_log_evidence(log_index: dict[str, Any]) -> dict[str, Any]:
    files = log_index.get("files") or []
    period_matched_lines = 0
    unparseable_timestamp_lines = 0
    period_filter_available = False
    for item in files:
        if not isinstance(item, dict):
            continue
        timestamp_parse = item.get("timestamp_parse") or {}
        period_matched_lines += int(timestamp_parse.get("period_matched_lines") or 0)
        unparseable_timestamp_lines += int(
            timestamp_parse.get("unparseable_timestamp_lines") or 0
        )
        period_filter_available = period_filter_available or bool(
            timestamp_parse.get("period_filter_applied")
        )
    return {
        "period_filter_available": period_filter_available,
        "period_matched_lines": period_matched_lines,
        "unparseable_timestamp_lines": unparseable_timestamp_lines,
    }


def _resolve_under(path: Path, root: Path) -> Path | None:
    resolved_path = path.resolve()
    resolved_root = root.resolve()
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError:
        return None
    return resolved_path


def _mandatory_bundle_file_errors(bundle: Path) -> list[str]:
    missing: list[str] = []
    for relative in sorted(NON_DROPPABLE_BUNDLE_FILES):
        safe_path = _resolve_under(bundle / relative, bundle)
        if safe_path is None or not safe_path.is_file():
            missing.append(relative)
    return missing


def _manifest_checksum_errors(bundle: Path, manifest: dict[str, Any]) -> list[str]:
    bad_hashes: list[str] = []
    inventory = manifest.get("file_inventory")
    if not isinstance(inventory, list) or not inventory:
        return ["<missing file inventory>"]
    for item in inventory:
        if not isinstance(item, dict):
            bad_hashes.append("<invalid inventory item>")
            continue
        relative = item.get("path")
        if not isinstance(relative, str):
            bad_hashes.append("<invalid inventory path>")
            continue
        safe_path = _resolve_under(bundle / relative, bundle)
        if safe_path is None or not safe_path.is_file():
            bad_hashes.append(relative)
            continue
        if sha256_file(safe_path) != item.get("sha256"):
            bad_hashes.append(relative)
    return bad_hashes


def _validate_bundle_contents(bundle: Path) -> tuple[dict[str, Any] | None, list[str], list[str]]:
    missing = _mandatory_bundle_file_errors(bundle)
    manifest_path = _resolve_under(bundle / "manifest.json", bundle)
    if manifest_path is None or not manifest_path.is_file():
        return None, missing, ["manifest.json"]
    with manifest_path.open(encoding="utf-8") as file:
        manifest = json.load(file)
    bad_hashes = _manifest_checksum_errors(bundle, manifest)
    return manifest, missing, bad_hashes


def _validate_bundle(args: argparse.Namespace) -> int:
    bundle = Path(args.bundle).resolve()
    if not bundle.is_dir():
        _print_json({"status": "failed", "missing": ["<bundle directory>"], "bad": []})
        return 1
    _, missing, bad_hashes = _validate_bundle_contents(bundle)
    status = "ok" if not missing and not bad_hashes else "failed"
    _print_json({"status": status, "missing": missing, "bad": bad_hashes})
    return 0 if status == "ok" else 1


def _mark_report_success(args: argparse.Namespace) -> int:
    config = load_config(args.output_dir)
    bundle = _resolve_under(Path(args.bundle), config.bundles_dir)
    report = _resolve_under(Path(args.report), config.reports_dir)
    if bundle is None:
        _print_json({"status": "failed", "error": "bundle path is outside ops-agent bundles"})
        return 1
    if report is None:
        _print_json({"status": "failed", "error": "report path is outside ops-agent reports"})
        return 1
    manifest_path = bundle / "manifest.json"
    if not report.is_file():
        _print_json({"status": "failed", "error": "report file does not exist"})
        return 1
    if not manifest_path.is_file():
        _print_json({"status": "failed", "error": "bundle manifest does not exist"})
        return 1
    manifest, missing, bad_hashes = _validate_bundle_contents(bundle)
    if missing:
        _print_json(
            {
                "status": "failed",
                "error": "mandatory bundle files are missing",
                "missing": missing,
            }
        )
        return 1
    if bad_hashes:
        _print_json(
            {
                "status": "failed",
                "error": "bundle checksum validation failed",
                "bad": bad_hashes,
            }
        )
        return 1
    if manifest is None:
        _print_json({"status": "failed", "error": "bundle manifest does not exist"})
        return 1
    if manifest.get("collection_status") != "complete" and not args.accept_partial:
        _print_json({"status": "failed", "error": "bundle is partial; pass --accept-partial"})
        return 1
    period_payload = manifest.get("period") or {}
    try:
        period = resolve_period(
            state={},
            period=None,
            since=str(period_payload["start"]),
            until=str(period_payload["end"]),
        )
    except (KeyError, ValueError) as error:
        _print_json({"status": "failed", "error": f"invalid bundle period: {error}"})
        return 1
    state = load_state(config.state_path)
    report_id = report.stem
    save_state(
        config.state_path,
        record_report_success(
            state,
            report_id=report_id,
            bundle_id=str(manifest.get("bundle_id") or bundle.name),
            period=period,
            report_path=report,
            bundle_path=bundle,
            bundle_sha256=sha256_tree(bundle),
        ),
    )
    _print_json({"status": "ok", "report_id": report_id})
    return 0


def _inspect_state(args: argparse.Namespace) -> int:
    config = load_config(args.output_dir)
    _print_json(load_state(config.state_path))
    return 0


def _retention(args: argparse.Namespace) -> int:
    config = load_config(args.output_dir)
    _print_json({"status": "ok", **apply_retention(config)})
    return 0


def _readonly_role_sql(_: argparse.Namespace) -> int:
    print(
        "CREATE ROLE ccwbot_ops_reader LOGIN PASSWORD '<set manually>';\n"
        "GRANT CONNECT ON DATABASE ccwbot TO ccwbot_ops_reader;\n"
        "GRANT USAGE ON SCHEMA public TO ccwbot_ops_reader;\n"
        "GRANT SELECT ON ALL TABLES IN SCHEMA public TO ccwbot_ops_reader;\n"
        "ALTER DEFAULT PRIVILEGES FOR ROLE ccwbot IN SCHEMA public "
        "GRANT SELECT ON TABLES TO ccwbot_ops_reader;\n"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ops-agent")
    parser.add_argument("--output-dir", default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser("collect")
    collect.add_argument("--period", default="auto")
    collect.add_argument("--since")
    collect.add_argument("--until")
    collect.add_argument("--output-dir", default=None)
    collect.add_argument("--no-state-update", action="store_true")
    collect.add_argument("--include-raw-llm-samples", action="store_true")
    collect.add_argument("--include-protected-identity-map", action="store_true")
    collect.set_defaults(func=lambda args: asyncio.run(_collect(args)))

    validate = subparsers.add_parser("validate-bundle")
    validate.add_argument("bundle")
    validate.set_defaults(func=_validate_bundle)

    mark = subparsers.add_parser("mark-report-success")
    mark.add_argument("--bundle", required=True)
    mark.add_argument("--report", required=True)
    mark.add_argument("--accept-partial", action="store_true")
    mark.add_argument("--output-dir", default=None)
    mark.set_defaults(func=_mark_report_success)

    inspect = subparsers.add_parser("inspect-state")
    inspect.add_argument("--output-dir", default=None)
    inspect.set_defaults(func=_inspect_state)

    retention = subparsers.add_parser("retention")
    retention.add_argument("--output-dir", default=None)
    retention.set_defaults(func=_retention)

    readonly_sql = subparsers.add_parser("print-readonly-role-sql")
    readonly_sql.set_defaults(func=_readonly_role_sql)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))
