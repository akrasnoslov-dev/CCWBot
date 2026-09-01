# Documentation

`source_of_truth.md` defines repository documentation authority and canonical ownership. Durable
CCWBot project/workflow rules must live in their canonical repository owner, not in external
prompts, chat/project instructions, PR comments, or copied source files.

All project and process documentation belongs in `docs/`, except:

- root `README.md`, which is the public project entry point;
- root `AGENTS.md`, which stays at the repository root because Codex/agent tooling reads it
  from there;
- root `CLAUDE.md`, which stays at the repository root because Claude Code reads it from there;
- local README.md files inside tool or package directories, such as `agents/` and `ops-agent/`,
  when they document only that subtree.

Do not add new standalone project documentation at the repository root. Add it here, or add a
subtree README.md when the documentation belongs only to that directory. Link new docs from this
index or from `README.md` when they are useful for users.

## Source of Truth

- `source_of_truth.md`: authority, ownership map, conflict resolution, and the rule against
  standing project/workflow policy outside the repository.

## Project Context

- `project_context.md`: product, stack, invariants, and primary context map.
- `codex_instructions.md`: short Codex operating rules for this repository.
- `codex_task_prompt_template.md`: short future-task prompt shape that relies on repo guardrails.
- `codex_agent_workflow.md`: task-review agent routing and review workflow.
- `codex_skills.md`: user-level and project-copied Codex skills, locations, and when to use them.
- root `CLAUDE.md`: Claude Code workflow and native review lenses.

## Research And Strategy

- `research/growth_strategy_2026-09-01.md`: dated 0 → 1 Premium growth analysis and experiment
  plan. It is research/strategy context, not a canonical owner of product or workflow rules.

## Development And Release

- `development.md`: local development notes, runtime behavior, and verification.
- `market_reports.md`: daily and weekly report data sources and report-specific guardrails.
- `release_checklist.md`: `dev` -> `main` release checklist.
- `dev_ops_guide.md`: environment, backup, recovery, and production deployment guide.

## Operations

- `observability.md`: read-only SQL, investigator session checks, and operational diagnostics.
- `llm_usage.md`: LLM usage and rate-limit reporting snippets.
- `ops_agent_service.md`: current ops-agent service contract and report flow.
- `ops-agent-report-codex-prompt.md`: reusable Codex prompt for ops-agent bundle analysis.
