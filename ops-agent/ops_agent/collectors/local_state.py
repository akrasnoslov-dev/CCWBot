from __future__ import annotations

import json
from typing import Any

from ops_agent.config import OpsAgentConfig
from ops_agent.redaction import RedactionReport, ReferenceMapper, redact_value
from ops_agent.state import load_state


def collect_local_state(
    *,
    config: OpsAgentConfig,
    mapper: ReferenceMapper,
    redaction_report: RedactionReport,
) -> dict[str, Any]:
    legacy = None
    if config.legacy_state_path.is_file():
        try:
            with config.legacy_state_path.open(encoding="utf-8") as file:
                legacy = json.load(file)
        except json.JSONDecodeError:
            legacy = {"error": "legacy state file is not valid JSON"}
    return {
        "ops_agent_state_snapshot": redact_value(
            load_state(config.state_path),
            mapper,
            redaction_report,
        ),
        "legacy_state_snapshot": redact_value(legacy or {}, mapper, redaction_report),
    }
