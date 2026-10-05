# Codex Instructions

This file owns CCWBot's ChatGPT-first implementation workflow, Codex fallback policy, branch/PR
rules, PR-readiness gates, and review policy.

Read `docs/source_of_truth.md` first. Product behavior belongs to the feature-specific canonical
docs, not here.

## Evidence-first verification

Before stating a material claim about current implementation, behavior, root cause, configuration,
production state, GitHub state, or available functionality:

1. Inspect the relevant current primary evidence:
   - current `dev` code for implementation behavior;
   - canonical repository docs for intended behavior;
   - production logs/database/ops evidence for actual production behavior;
   - current GitHub PR/CI/branch state for repository status;
   - current provider/vendor docs or telemetry for external capabilities that may change.
2. For bugs or incidents, trace the complete relevant execution path.
3. Before proposing missing functionality, verify repository-wide that it is not already present.
4. Classify material diagnostic conclusions as `CONFIRMED`, `LIKELY`, or `UNKNOWN`.
5. If code and canonical docs disagree, report the drift. Do not resolve it by assumption.
6. If primary evidence is available, inspect it before proposing a behavioral fix.

Accuracy and evidence quality take priority over speed.

## ChatGPT-first orchestration

For CCWBot work initiated in ChatGPT:

1. ChatGPT is the primary decision center, orchestrator, and final acceptance owner.
2. Use capabilities available directly from ChatGPT first: repository connectors, file tools,
   browser/research tools, connected apps, and approved workspace/bridge access.
3. Do not invoke Codex merely because a task touches code, files, GitHub, a terminal, or multiple
   steps.
4. Use Codex only when a required action cannot be completed or reliably verified with the tools
   available to ChatGPT in the current session.
5. When Codex is needed, delegate a narrow task with explicit scope and acceptance criteria.
   ChatGPT reviews the returned diff/evidence and keeps the final decision.
6. Codex output is execution evidence, not a new source of truth.
7. If ChatGPT can complete the task directly, keep the work in ChatGPT.

This is the default CCWBot bridge policy. Do not invert it by making Codex the default orchestrator.

### Bridge permissions

When approved bridge/workspace access is available:

- Default operating intent is `CHATGPT_ARCHITECT`.
- Default permission level is `L3_WORKSPACE_WRITE` for the approved narrow CCWBot workspace only.
- L3 permits task-scoped source reads, source writes, and project-local verification needed for the
  assigned work.
- L3 does not authorize secrets/credential reads, dependency installation, unrelated broad deletes,
  git history mutation, access outside the approved workspace, or irreversible external actions.
- L4/L5 actions still require explicit owner approval for the exact action.
- Never widen roots or permissions just to make a tool path work.

## Plan and task context

For non-trivial work, write a short plan before changing files. Keep task-specific requirements,
risks, acceptance criteria, and temporary notes in the active chat/task or PR.

Do not create routine files under `docs/task_specs/`. Durable rules belong in their canonical
owners; historical task detail belongs in Git history and PRs.

Ask clarification only when missing information materially changes the implementation. Read-only
inspection may happen first to resolve uncertainty.

## Test-first gate

Define validation before production implementation.

- For behavior changes and bug fixes, add or modify focused automated tests first when practical.
- For docs/config/migration/infrastructure work, use the strongest applicable contract, lint,
  migration, or configuration check.
- Run focused checks after meaningful changes and repository-required verification before final
  acceptance.

**No green verification, no completion.** If a required check cannot be run, state exactly which
check was not run, why, and what risk remains.

## Single-checkout branch workflow

- Start normal task branches from current `dev`.
- Use one implementation writer at a time.
- Do not create Git worktrees by default.
- Preserve intentional uncommitted user work.
- Merge accepted task branches through the normal PR flow.
- Create a worktree only when the owner explicitly requests one.

## Codex fallback and worker routing

When ChatGPT decides Codex is required, `agents/routing.toml` owns delegated execution/review
routing and `.codex/config.toml` is its executable model adapter.

Current fallback routing:

- Codex orchestration/final worker model: `gpt-5.6-sol`.
- Default implementation worker: `gpt-5.6-terra`.
- Low-cost mechanical worker: `gpt-5.6-luna`.
- Sol as implementation worker is escalation-only.
- Worker count may be adaptive for analysis/review, but implementation defaults to one writer.
- Required review agents come from `agents/routing.toml`.

These settings apply only after Codex has actually been delegated work. They do not make Codex the
primary CCWBot control plane.

## Token-efficiency objective

- Search first, then read only relevant code and canonical docs.
- Reuse already inspected evidence instead of repeatedly loading the repository.
- Keep delegated tasks narrow.
- Parallelize only independent read/review work.
- Avoid duplicate reviews and reruns when evidence has not changed.

## PR-readiness workflow

For every non-trivial repository change:

1. Search repository-wide for affected concepts before editing.
2. Add regression coverage for behavior changes unless genuinely not applicable.
3. Review the full diff.
4. PR body must include `Self-review / risk check` with risky assumptions, edge cases, intentionally
   untouched areas, migration/rollback notes when relevant, and known follow-ups.
5. Check existing automated PR review threads. Address valid P0/P1/P2 findings.
6. External GitHub `@codex review` is optional, not a recursive gate; do not automatically trigger
   it after every fix.
7. Run required verification from `docs/development.md`.
8. Do not claim merge readiness with failed checks, unresolved blocking findings, or untested
   migrations unless the limitation is explicitly documented.

## Safe defaults

- Normal task PRs target `dev`.
- `dev` -> `main` PRs are production releases only when explicitly requested.
- Never commit `.env`, `.ops-agent.env`, local state, caches, logs, generated reports, DB dumps,
  or secrets.
- Do not change product behavior unless explicitly requested.
- Do not rename `bot/services/ai_agent_groq.py`.
- Keep project/process documentation under `docs/`; root bootstrap exceptions are `README.md`,
  `AGENTS.md`, and `CLAUDE.md`.
- Do not automatically install or upgrade Graphify or other developer-tool packages.
- Do not send repository content to external semantic-extraction providers without explicit user
  approval for that specific run.
- Do not add global Codex hooks or custom Git merge drivers unless the repository provisions and
  tests them.
- Production forensic SQL uses only the read-only `ccwbot_investigator` role through the approved
  SSH tunnel. A permission error is an access-provisioning issue, not permission to switch roles.

Follow `project_context.md`, `alert_logic.md`, `market_reports.md`, and
`product_analytics.md` for product rules. Follow `ops_agent_service.md` for ops-agent boundaries.

## PR description and merge ownership

Every non-trivial PR should state: summary, files changed, behavior impact, database/schema impact,
verification performed, manual verification status, known limitations/follow-ups, and
`Self-review / risk check`.

Do not auto-merge unless the user explicitly asks.
