"""Model identifiers the shipped bot defaults to, for drift detection.

The ops-agent runs from its own image, which does not contain ``bot/`` (see
``ops-agent/Dockerfile``), so it cannot import the bot's configuration to learn what the
current defaults are. These constants are therefore a deliberate copy.

The copy is kept honest by ``tests/ops_agent/test_expected_models_match_bot_defaults.py``,
which imports both and fails if they diverge — so a model default changed in the bot without
updating this table breaks the build rather than silently disabling the drift detector.

An operator whose ``.env`` intentionally pins a different model can set
``OPS_AGENT_EXPECTED_EVENT_ANALYSIS_MODEL`` to silence the expected drift.
"""

from __future__ import annotations

import os
import re

# Model identifiers use a narrow character set. The override is written into
# detector_results.json and the rendered report, which are shared artifacts, and detector
# details do not pass through the evidence redaction. Validating the shape means a single
# operator slip -- pasting a key or a DSN onto that line -- cannot be published.
_MODEL_NAME_RE = re.compile(r"^[A-Za-z0-9._/@-]{1,120}$")

# Mirrors bot/services/llm/config.py `_GROQ_MODEL_ENV_BY_CALL_TYPE` defaults.
SHIPPED_DEFAULT_MODELS: dict[str, str] = {
    "event_analysis": "llama-3.3-70b-versatile",
    "market_heartbeat": "llama-3.1-8b-instant",
    "daily_report": "llama-3.1-8b-instant",
    "weekly_report": "llama-3.1-8b-instant",
    "market_report": "llama-3.1-8b-instant",
    "news_intelligence": "llama-3.1-8b-instant",
}

# Models the provider has withdrawn. A recorded call against one of these is not drift, it is
# an outage in progress, and is reported at a higher severity.
KNOWN_DECOMMISSIONED_MODELS: frozenset[str] = frozenset(
    {
        "meta-llama/llama-4-scout-17b-16e-instruct",
    }
)


def expected_model(call_type: str) -> str | None:
    """Return the expected model for a call type, honouring an explicit operator override.

    Only known call types are looked up, so the env var name can never be derived from
    database content, and an override that does not look like a model identifier is ignored.
    """
    if call_type not in SHIPPED_DEFAULT_MODELS:
        return None
    override = (os.getenv(f"OPS_AGENT_EXPECTED_{call_type.upper()}_MODEL") or "").strip()
    if override and _MODEL_NAME_RE.match(override):
        return override
    return SHIPPED_DEFAULT_MODELS.get(call_type)
