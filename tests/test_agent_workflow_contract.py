from __future__ import annotations

from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = ROOT / "agents"

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


def test_source_of_truth_declares_canonical_owners():
    content = (ROOT / "docs/source_of_truth.md").read_text(encoding="utf-8")

    for required_path in (
        "docs/project_context.md",
        "docs/codex_instructions.md",
        "agents/routing.toml",
        "docs/development.md",
        "docs/release_checklist.md",
        "docs/dev_ops_guide.md",
    ):
        assert required_path in content

    assert "only durable source of truth" in content
    assert "No standing rules outside the repository" in content


def test_bootstrap_docs_point_to_canonical_repository_owners():
    for relative_path in ("AGENTS.md", "CLAUDE.md"):
        content = (ROOT / relative_path).read_text(encoding="utf-8")

        assert "docs/source_of_truth.md" in content
        assert "docs/project_context.md" in content
        assert "docs/codex_instructions.md" in content
        assert "agents/routing.toml" in content


def test_supporting_docs_link_to_canonical_workflow_without_owning_routing():
    development = (ROOT / "docs/development.md").read_text(encoding="utf-8")
    agent_workflow = (ROOT / "docs/codex_agent_workflow.md").read_text(encoding="utf-8")
    agent_readme = (ROOT / "agents/README.md").read_text(encoding="utf-8")

    assert "docs/source_of_truth.md" in development
    assert "docs/codex_instructions.md" in development
    assert "agents/routing.toml" in development

    assert "agents/routing.toml" in agent_workflow
    assert "docs/codex_instructions.md" in agent_workflow
    assert "explanatory only" in agent_workflow

    assert "agents/routing.toml" in agent_readme
    assert "docs/source_of_truth.md" in agent_readme


def test_external_codex_review_is_non_recursive():
    content = (ROOT / "docs/codex_instructions.md").read_text(encoding="utf-8")

    assert "External GitHub `@codex review` is optional, not a recursive gate" in content
    assert "do not automatically trigger it after every fix" in content
