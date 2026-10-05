# ChatGPT / Bridge / Codex Workflow

This file is the canonical owner for CCWBot implementation workflow, review gates, and repository
execution policy.

## 1. Execution hierarchy

ChatGPT is the primary decision centre and orchestrator for CCWBot.

Use this order:
1. ChatGPT inspects evidence, decides scope, decomposes work, and accepts the result.
2. If repository/local-workspace actions are needed, use the available ChatGPT bridge/tools first.
3. Use Codex only when the task cannot be completed with available ChatGPT/bridge capabilities or
   when the user explicitly requests a Codex-specific capability.
4. Codex is therefore a fallback execution environment, not the default orchestrator.
5. If Codex is used, ChatGPT still owns task intent, decisions, scope, and final acceptance unless
   the user explicitly delegates ownership.

Default bridge policy when `codex-chatgpt-bridge` is available:
- mode: `CHATGPT_ARCHITECT`
- permission: `L3_WORKSPACE_WRITE`
- approved scope: the narrow CCWBot workspace only
- ChatGPT may read/write project source and run project-local verification needed for the task
- L3 does not authorize secrets/credential stores, dependency installation, broad unrelated
  deletion, git history mutation, or irreversible/external actions
- if bridge execution is unavailable, use the next available safe tool; Codex is the final fallback

## 2. Evidence-first gate

Before a material claim about implementation, behavior, root cause, configuration, production, or
GitHub state:
- inspect current primary evidence;
- use `dev` for development state unless the task concerns `main`/production;
- trace the full relevant path for bugs/incidents;
- search before claiming functionality is missing;
- classify diagnostic conclusions as `CONFIRMED`, `LIKELY`, or `UNKNOWN`;
- if code and canonical docs disagree, state the drift;
- never replace inaccessible evidence with a guess.

## 3. Planning without task-spec clutter

Do not create `docs/task_specs/` files as a routine workflow step.

For non-trivial work:
- keep a short working plan in the active task/chat/PR;
- record durable product or workflow decisions in the proper canonical document;
- use tests and Git history as the implementation record;
- create a standalone design/spec document only when it has long-lived value beyond one task.

Do not block straightforward work on unnecessary clarification. Ask only when a missing answer
materially changes the safe/correct implementation.

## 4. Test-first and verification

For behavior changes and bug fixes:
- define or add a focused regression test before the production change when practical;
- verify that it covers the failure/new behavior;
- run focused checks after the change;
- run repository-required verification before declaring completion.

For docs/config/infrastructure where a failing unit test is not meaningful, use the strongest
applicable contract/lint/configuration check.

**No green verification, no completion.**

## 5. Repository workflow

- Work from current `dev` or a focused branch based on `dev`.
- Normal PRs target `dev`.
- `dev -> main` is only for explicit production releases.
- Use one normal checkout; do not create worktrees by default.
- Do not overwrite uncommitted user work.
- One implementation writer at a time unless the owner explicitly approves parallel writers.
- Never commit secrets, logs, generated reports, dumps, caches, or local state.

## 6. Agents and model routing

When Codex/subagents are actually used, `agents/routing.toml` owns routing policy and
`.codex/config.toml` is its executable adapter.

Current routing:
- Codex fallback/orchestrator model: `gpt-5.6-sol`
- default worker: `gpt-5.6-terra`
- low-cost worker: `gpt-5.6-luna`
- Sol worker: escalation only
- worker count: adaptive
- implementation writers: one

Required review agents from `agents/routing.toml` still apply when that execution path is used.

## 7. PR readiness

Before calling a non-trivial PR ready:
- review the full diff;
- run required verification from `docs/development.md`;
- inspect existing automated review findings;
- address valid P0/P1/P2 findings;
- document schema/data/rollback risks when relevant;
- state skipped checks and remaining risk explicitly.

External GitHub `@codex review` is optional, not a recursive gate; do not automatically trigger it after every fix.

A PR description should include:
- summary;
- behavior impact;
- files/areas changed;
- DB/schema impact;
- verification;
- known limitations/follow-ups;
- `Self-review / risk check`.

## 8. Tooling safety

- Do not automatically install or upgrade Graphify or other developer-tool packages.
- Do not send repository content to external semantic-extraction providers without explicit approval.
- Do not add global Codex hooks or custom Git merge drivers unless the repository provisions and
  tests them.
- Production forensic SQL uses only the read-only `ccwbot_investigator` path.
- Scheduled Dependabot version-update PRs are disabled. Dependency upgrades are explicit maintenance tasks so incompatible grouped upgrades are reviewed and tested intentionally.

Feature-specific rules live in their canonical docs:
- `docs/alert_logic.md`
- `docs/market_reports.md`
- `docs/product_analytics.md`
- `docs/ops_agent_service.md`
