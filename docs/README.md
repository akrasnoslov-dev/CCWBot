# Documentation

Start with [source_of_truth.md](source_of_truth.md). It defines document ownership and conflict
resolution.

Keep durable rules in one canonical owner. Temporary task plans belong in the active chat/task or PR.
Routine `docs/task_specs/` files are not used; Git history and PRs preserve implementation history.

## Core documentation

| Topic | Canonical document |
|---|---|
| Documentation ownership | `source_of_truth.md` |
| Product boundaries and current system context | `project_context.md` |
| Event Alerts | `alert_logic.md` |
| Daily and weekly reports | `market_reports.md` |
| Acquisition attribution and funnel analytics | `product_analytics.md` |
| ChatGPT-first workflow, Codex fallback, PR policy | `codex_instructions.md` |
| Fallback Codex task-prompt shape | `codex_task_prompt_template.md` |
| ChatGPT Project bootstrap copy | `CCWBot_Project_Instructions.md` |
| Claude bootstrap | root `CLAUDE.md` |

## Research and strategy

- `research/growth_strategy_2026-09-01.md`: current execution status of the original 0 -> 1 Premium
  growth research, including what is implemented and the next recommended experiment.

## Development and release

- `development.md`: local development, repository structure, migration notes, and verification.
- `release_checklist.md`: `dev` -> `main` release checklist.
- `dev_ops_guide.md`: production deployment, backup, recovery, and environment operations.

## Operations

- `observability.md`: read-only SQL and operational diagnostics.
- `llm_usage.md`: LLM provider/configuration and usage diagnostics.
- `ops_agent_service.md`: ops-agent service contract and bundle/report flow.
- `ops-agent-report-codex-prompt.md`: fallback Codex prompt for bundle analysis when ChatGPT cannot
  perform the required local analysis directly.

Historical incident/remediation detail belongs in Git history and PRs unless it remains an active
operational contract.
