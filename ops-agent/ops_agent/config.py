from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class OpsAgentLimits:
    bundle_hard_cap_bytes: int = 25 * 1024 * 1024
    db_query_timeout_seconds: int = 15
    db_row_cap: int = 500
    anomaly_row_cap: int = 200
    recent_sample_row_cap: int = 100
    max_log_tail_bytes: int = 5 * 1024 * 1024
    max_log_export_bytes_per_file: int = 2 * 1024 * 1024
    max_log_export_bytes_total: int = 8 * 1024 * 1024
    raw_llm_sample_cap: int = 5
    raw_llm_preview_bytes: int = 2048
    duplicate_market_event_bucket_minutes: int = 15
    alert_evidence_row_cap: int = 500
    event_alert_semantic_cooldown_seconds: int = 4 * 60 * 60


@dataclass(frozen=True)
class OpsAgentConfig:
    database_url: str | None
    health_url: str | None
    output_dir: Path
    logs_dir: Path
    legacy_state_path: Path
    docker_status_json_path: Path | None = None
    retention_days: int = 60
    max_bundles: int = 30
    max_reports: int = 30
    limits: OpsAgentLimits = OpsAgentLimits()

    @property
    def state_path(self) -> Path:
        return self.output_dir / "state" / "state.json"

    @property
    def bundles_dir(self) -> Path:
        return self.output_dir / "bundles"

    @property
    def reports_dir(self) -> Path:
        return self.output_dir / "reports"


def _int_env(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value >= minimum else default


def load_config(output_dir: str | None = None) -> OpsAgentConfig:
    limits = OpsAgentLimits(
        bundle_hard_cap_bytes=_int_env("OPS_AGENT_BUNDLE_MAX_BYTES", 25 * 1024 * 1024),
        db_query_timeout_seconds=_int_env("OPS_AGENT_DB_QUERY_TIMEOUT_SECONDS", 15),
        db_row_cap=_int_env("OPS_AGENT_DB_ROW_CAP", 500),
        anomaly_row_cap=_int_env("OPS_AGENT_ANOMALY_ROW_CAP", 200),
        recent_sample_row_cap=_int_env("OPS_AGENT_RECENT_SAMPLE_ROW_CAP", 100),
        max_log_tail_bytes=_int_env("OPS_AGENT_MAX_LOG_TAIL_BYTES", 5 * 1024 * 1024),
        max_log_export_bytes_per_file=_int_env(
            "OPS_AGENT_MAX_LOG_EXPORT_BYTES_PER_FILE", 2 * 1024 * 1024
        ),
        max_log_export_bytes_total=_int_env(
            "OPS_AGENT_MAX_LOG_EXPORT_BYTES_TOTAL", 8 * 1024 * 1024
        ),
        raw_llm_sample_cap=_int_env("OPS_AGENT_RAW_LLM_SAMPLE_CAP", 5),
        raw_llm_preview_bytes=_int_env("OPS_AGENT_RAW_LLM_PREVIEW_BYTES", 2048),
        duplicate_market_event_bucket_minutes=_int_env(
            "OPS_AGENT_DUPLICATE_MARKET_EVENT_BUCKET_MINUTES", 15
        ),
        alert_evidence_row_cap=_int_env("OPS_AGENT_ALERT_EVIDENCE_ROW_CAP", 500),
        event_alert_semantic_cooldown_seconds=_int_env(
            "OPS_AGENT_EVENT_ALERT_SEMANTIC_COOLDOWN_SECONDS", 4 * 60 * 60, minimum=0
        ),
    )
    return OpsAgentConfig(
        database_url=os.getenv("OPS_AGENT_DATABASE_URL") or None,
        health_url=os.getenv("OPS_AGENT_HEALTH_URL", "http://bot:8080/health"),
        docker_status_json_path=(
            Path(path) if (path := os.getenv("OPS_AGENT_DOCKER_STATUS_JSON_PATH")) else None
        ),
        output_dir=Path(output_dir or os.getenv("OPS_AGENT_OUTPUT_DIR", "/app/reports/ops-agent")),
        logs_dir=Path(os.getenv("OPS_AGENT_LOGS_DIR", "/app/logs")),
        legacy_state_path=Path(os.getenv("OPS_AGENT_LEGACY_STATE_PATH", "/app/state.json")),
        retention_days=_int_env("OPS_AGENT_RETENTION_DAYS", 60),
        max_bundles=_int_env("OPS_AGENT_MAX_BUNDLES", 30),
        max_reports=_int_env("OPS_AGENT_MAX_REPORTS", 30),
        limits=limits,
    )


def database_role_warning(database_url: str | None) -> str | None:
    if not database_url:
        return "OPS_AGENT_DATABASE_URL is not configured; DB collectors will be skipped."
    username = urlsplit(database_url.replace("+asyncpg", "", 1)).username
    if username != "ccwbot_ops_reader":
        return "OPS_AGENT_DATABASE_URL user is not ccwbot_ops_reader; use the read-only role."
    return None
