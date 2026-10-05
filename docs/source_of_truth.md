# Repository Source of Truth

This repository is the only durable source of truth for CCWBot product rules, architecture,
development workflow, release process, operations, and agent routing. External prompts, chat memory,
PR comments, copied files, and generated task prompts are context only.

## Canonical ownership

- Product boundaries and architecture invariants: `docs/project_context.md`
- Event Alert behavior: `docs/alert_logic.md`
- Daily/weekly reports: `docs/market_reports.md`
- Acquisition attribution and funnel analytics: `docs/product_analytics.md`
- ChatGPT/bridge/Codex implementation workflow and PR readiness: `docs/codex_instructions.md`
- Agent routing: `agents/routing.toml`
- Codex executable model defaults: `.codex/config.toml`
- Local development and verification: `docs/development.md`
- Release gates: `docs/release_checklist.md`
- Production deployment/recovery: `docs/dev_ops_guide.md`
- Read-only diagnostics: `docs/observability.md`
- Ops-agent behavior: `docs/ops_agent_service.md` and `docs/ops-agent-report-codex-prompt.md`
- LLM usage diagnostics: `docs/llm_usage.md`
- Public project overview: root `README.md`

`AGENTS.md` and `CLAUDE.md` are bootstrap files. They point to canonical docs and must not become
independent policy copies.

## No standing rules outside canonical docs

Do not store durable CCWBot rules in:
- task prompts;
- chat memory;
- PR/issue comments;
- personal notes;
- copied project-instruction files.

Do not create a `docs/task_specs/` record for every task. Git history, the PR body, tests, and the
canonical documents already preserve the useful record. Create a dedicated design/spec document only
when the document itself is a useful long-lived project artifact.

If a permanent rule changes, update its canonical owner in the same change.

## Conflict resolution

1. Use the canonical owner above for intended behavior.
2. Treat runtime code/schema as evidence of current implementation.
3. If code and docs disagree, record the drift and fix the inconsistency.
4. Prefer links to the canonical owner over duplicated normative text.

## Repository bootstrap

For repository-sensitive work read:
1. `docs/source_of_truth.md`
2. `docs/project_context.md`
3. `docs/codex_instructions.md`
4. `agents/routing.toml`
5. the relevant feature/operations document

Do not rely on cached external copies while the repository is accessible.
