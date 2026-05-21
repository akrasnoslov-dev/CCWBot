from __future__ import annotations

import re
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = ROOT / "agents"
AGENT_NAME_RE = re.compile(r"`([a-z][a-z0-9_]*(?:_agent|_guardian))`")

MANDATORY_RULE_IDS = {
    "security_sensitive",
    "database_schema",
    "alert_report_logic",
    "llm_prompt_output",
    "production_debugging",
    "multi_module_refactor",
    "api_token_rate_limit",
    "premium_payments",
    "broad_repository_review",
}


def _load_toml(path: Path) -> dict:
    with path.open("rb") as file:
        return tomllib.load(file)


def _agent_paths() -> list[Path]:
    return sorted(path for path in AGENTS_DIR.glob("*.toml") if path.name != "routing.toml")


def _agent_names() -> set[str]:
    return {path.stem for path in _agent_paths()}


def test_agent_definitions_have_required_schema():
    for path in _agent_paths():
        data = _load_toml(path)

        assert data["name"] == path.stem
        assert isinstance(data.get("role"), str) and data["role"].strip()
        assert isinstance(data.get("mission"), str) and data["mission"].strip()

        instructions = data.get("instructions")
        assert isinstance(instructions, dict)
        assert isinstance(instructions.get("system"), str)
        assert instructions["system"].strip()

        deliverables = data.get("deliverables")
        assert isinstance(deliverables, dict)
        assert isinstance(deliverables.get("items"), list)
        assert all(isinstance(item, str) and item.strip() for item in deliverables["items"])


def test_agent_routing_references_existing_agents():
    data = _load_toml(AGENTS_DIR / "routing.toml")
    agent_names = _agent_names()

    defaults = data.get("defaults")
    assert isinstance(defaults, dict)
    assert defaults["runtime_bot_loads_agents"] is False
    assert defaults["non_trivial_task_requires_agent_check"] is True
    assert defaults["high_risk_skip_requires_written_reason"] is True

    rules = data.get("rules")
    assert isinstance(rules, list)
    assert MANDATORY_RULE_IDS <= {rule["id"] for rule in rules}

    for rule in rules:
        assert isinstance(rule.get("description"), str) and rule["description"].strip()
        assert isinstance(rule.get("triggers"), list) and rule["triggers"]
        assert isinstance(rule.get("must_use"), list) and rule["must_use"]
        assert set(rule["must_use"]) <= agent_names
        assert set(rule.get("also_consider", [])) <= agent_names


def test_agent_docs_match_definition_files():
    agent_names = _agent_names()

    for relative_path in (
        "AGENTS.md",
        "agents/README.md",
        "docs/codex_agent_workflow.md",
    ):
        content = (ROOT / relative_path).read_text(encoding="utf-8")
        documented_names = set(AGENT_NAME_RE.findall(content))
        assert documented_names == agent_names


def test_development_docs_link_to_agent_workflow():
    content = (ROOT / "docs/development.md").read_text(encoding="utf-8")

    assert "agents/routing.toml" in content
    assert "docs/codex_agent_workflow.md" in content
    assert "Before starting any non-trivial task" in content
