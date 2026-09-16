# Documentation

Start with [source_of_truth.md](source_of_truth.md). It defines document ownership and resolves
conflicts. Durable CCWBot rules belong in their canonical owner, not in prompts, chat, PR comments,
or copied files.

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

## Core documentation

| Topic | Canonical document |
|---|---|
| Documentation ownership | `source_of_truth.md` |
| Product boundaries and system context | `project_context.md` |
| Event Alerts | `alert_logic.md` |
| Daily and weekly reports | `market_reports.md` |
| Acquisition attribution | `product_analytics.md` |
| Codex implementation and PR workflow | `codex_instructions.md` |
| Task-prompt shape | `codex_task_prompt_template.md` |
| Claude workflow | root `CLAUDE.md` |

## Research And Strategy

- `research/growth_strategy_2026-09-01.md`: dated 0 → 1 Premium growth analysis and experiment
  plan. It is research/strategy context, not a canonical owner of product or workflow rules.

## Development and release

- `development.md`: local development notes, runtime behavior, and verification.
- `market_reports.md`: daily and weekly report data sources and report-specific guardrails.
- `release_checklist.md`: `dev` -> `main` release checklist.
- `dev_ops_guide.md`: environment, backup, recovery, and production deployment guide.

## Operations

- `observability.md`: read-only SQL, investigator session checks, and operational diagnostics.
- `llm_usage.md`: LLM usage and rate-limit reporting snippets.
- `ops_agent_service.md`: current ops-agent service contract and report flow.
- `ops-agent-report-codex-prompt.md`: reusable Codex prompt for ops-agent bundle analysis.

Historical incident/remediation records are kept in Git history rather than as standing project
documentation.
