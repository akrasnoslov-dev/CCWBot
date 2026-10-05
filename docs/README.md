# Documentation

Start with `source_of_truth.md`. It says which document owns each durable rule.

## Core

| Topic | Document |
|---|---|
| Documentation ownership | `source_of_truth.md` |
| Product/system context | `project_context.md` |
| Event Alert flow | `alert_logic.md` |
| Daily/weekly reports | `market_reports.md` |
| Growth attribution/funnel | `product_analytics.md` |
| ChatGPT/bridge/Codex workflow | `codex_instructions.md` |
| Task prompt template | `codex_task_prompt_template.md` |

## Development and operations

- `development.md` - local setup, repository layout, verification.
- `release_checklist.md` - `dev -> main` release gates.
- `dev_ops_guide.md` - production deployment, backup, recovery.
- `observability.md` - read-only diagnostics.
- `llm_usage.md` - LLM usage/rate-limit diagnostics.
- `ops_agent_service.md` - ops-agent contract.
- `ops-agent-report-codex-prompt.md` - reusable ops report prompt.

## Research

- `research/growth_strategy_2026-09-01.md` - original 0→1 Premium research, updated with current
  implementation status and next recommended growth steps.

## What is intentionally not here

There is no routine `task_specs/` archive. Per-task plans belong in the active task/PR; durable
rules go into the canonical docs; implementation history stays in Git.

Root `README.md`, `AGENTS.md`, and `CLAUDE.md` remain at repository root because tooling/public
entry points require them. Local tool/package README files may live with their subtree.
