# Codex Instructions

This file is the canonical owner for CCWBot agent-assisted implementation workflow across ChatGPT Work,
Codex, and Claude, including branch/PR rules, PR-readiness gates, and review policy.

Read `docs/source_of_truth.md` first. `AGENTS.md` and external task prompts are bootstrap/context
only and must not contain independent standing workflow or project rules.

Do not copy durable CCWBot rules into ChatGPT/Codex/Claude project instructions, chat memory,
PR comments, or generated task prompts. A task prompt may define only the requested delta.

## Evidence-first verification

This gate is mandatory for diagnosis, implementation planning, repository-status claims, and
production conclusions. Accuracy and primary evidence take priority over speed or a convenient
answer.

Before stating a material claim about current implementation, behavior, root cause, configuration,
production state, GitHub state, or available functionality:

1. Inspect the relevant current primary evidence instead of relying on memory, inference, naming,
   stale documentation, or prior conversation context:
   - current `dev` code for implementation behavior;
   - canonical repository documentation for intended behavior;
   - production logs/database/ops evidence for actual production behavior;
   - current GitHub PR/CI/branch state for repository status;
   - current provider/vendor documentation or production telemetry for external capabilities,
     models, limits, or API behavior that may change over time.
2. For bugs, incidents, reports, or suspicious behavior, trace the complete relevant execution path.
   Do not stop at one symptom or intermediate stage and present it as the cause.
3. Before proposing that functionality is missing or needs to be added, verify repository-wide that
   it is not already implemented, and verify how the existing path behaves.
4. Classify every material diagnostic conclusion as one of:
   - `CONFIRMED` - directly demonstrated by primary evidence;
   - `LIKELY` - supported by evidence but not fully proven;
   - `UNKNOWN` - evidence is insufficient.
5. If code and canonical documentation disagree, report the implementation/design drift explicitly.
   Runtime code is evidence of what exists; canonical docs own what is intended.
6. If evidence sources conflict, do not reconcile them by assumption. Identify the contradiction and
   inspect the source needed to resolve it.
7. If primary evidence is available but has not yet been checked, check it before answering or
   proposing a fix. If it cannot be accessed, state exactly what remains unverified.
8. Never propose a behavioral fix until the existing behavior and failure path have been verified.
   A hypothesis may guide investigation, but it must not be presented as an established defect.

## Mandatory agentic execution pipeline

Apply this pipeline to every non-trivial feature, bug fix, refactor, or project task, regardless of
whether the request initially appears clear.

### Clarification gate

Before implementation, ask the user one compact batch of clarification questions that resolves
requirements, constraints, success criteria, important edge cases, and explicit non-goals. Wait for
the answers before changing implementation files. Read-only repository inspection may happen first
when needed to ask better questions.

### Task specification and plan

After clarification and before coding:

1. Create one task-specific specification under `docs/task_specs/YYYY-MM-DD-<task-slug>.md`.
2. Record the goal, clarified requirements, out-of-scope items, acceptance criteria, expected
   files/areas, risks, migration/data impact, test strategy, and proposed decomposition.
3. Write a short implementation plan derived from that specification.
4. Keep the specification current during long-running work when accepted scope or decisions change.

Task specifications are task-specific records, not canonical owners of standing project policy.
After the task is complete they may remain as historical implementation context, but durable rules
must be moved to the canonical owner defined by `docs/source_of_truth.md`.

### Test-first gate

Define validation before production implementation.

- For behavior changes and bug fixes, add or modify the focused automated test first and run it
  before the implementation change. The expected new behavior should fail for the intended reason
  on the old implementation.
- For documentation, configuration, migration, or infrastructure work where a normal unit/regression
  test is not meaningful, create the strongest applicable contract, validation, lint, migration,
  or configuration check first and document why a conventional failing test is not applicable.
- Keep tests as an executable contract throughout implementation.
- Run focused checks after each meaningful slice and the repository-required verification before
  final acceptance.

**No green verification, no completion.** Never describe a task as done while an applicable required
check is failing, was skipped without an explicit reason, or has not been run.

### Worktree isolation

Use isolated Git branches plus `git worktree` for implementation workers.

- Create an integration/task branch from current `dev`.
- Give each parallel worker its own branch and worktree based on the task/integration state it needs.
- Do not let multiple workers edit the same worktree.
- Scope workers to independent files or boundaries where practical.
- Merge accepted worker branches into the integration branch one at a time, resolving conflicts and
  rerunning affected tests after each integration.
- A single-worker task may use one isolated task worktree; do not create parallel workers when they
  do not improve throughput or quality.

### Orchestrator and workers

The orchestrator owns decomposition, routing, integration, review, and final acceptance.

- Orchestrator and final acceptance model: `gpt-5.6-sol`.
- Default implementation worker: `gpt-5.6-terra`.
- Use `gpt-5.6-luna` for simple, mechanical, low-risk, well-specified subtasks.
- Use Sol as an implementation worker only as an escalation when task complexity, risk, or a failed
  lower-tier attempt justifies the extra cost.
- Worker count is adaptive. The orchestrator decides how many workers are useful for the task and
  available platform capacity; do not impose a fixed project-level worker count.
- Give each worker only the task specification, relevant canonical rules, assigned scope, acceptance
  criteria, and evidence needed for its subtask.
- The orchestrator must review worker diffs and test evidence before integration; worker completion
  is not final acceptance.

Execution model policy is canonical in `agents/routing.toml`. Codex project defaults in
`.codex/config.toml` are an executable adapter and must remain consistent with that policy.

### Token-efficiency objective

Minimize token use while preserving correctness and evidence quality.

- Use Sol mainly for clarification synthesis, planning, decomposition, risky decisions, review, and
  final acceptance rather than routine implementation.
- Prefer Terra or Luna for bounded worker tasks according to complexity.
- Avoid repeatedly loading the whole repository. Search first, then read only relevant files and
  canonical docs.
- Reuse the task specification as compact shared context instead of restating the full conversation
  to every worker.
- Parallelize only independent work. Do not create workers whose coordination cost exceeds their
  expected benefit.
- Avoid recursive or duplicate reviews and reruns when evidence has not changed.

Before non-trivial work:

1. Read `AGENTS.md`, this file, `docs/project_context.md`, and `agents/routing.toml`.
2. Inspect installed skills under `C:\Users\Loki\.codex\skills\`,
   `C:\Users\Loki\.agents\skills\`, and `.agents/skills/` when present.
3. Read and apply every relevant skill instruction file (`SKILL.md`, `README.md`, or equivalent).
4. If no installed skill applies, state that explicitly in the final response and PR body.
5. Use required review agents when routing says they apply.
6. Check current branch and worktree status.
7. Do not overwrite uncommitted user work.

Mandatory implementation and PR-readiness workflow for every non-trivial task:

1. Write a short implementation plan before changing files. Cover expected files or areas to
   change, risky edge cases, DB/schema/data migration impact, tests to add, and what belongs in
   the current PR versus follow-up work.
2. Search repository-wide for affected concepts before coding, not only obvious files. For
   migrations or renames, explicitly search for direct columns/fields, lowercase supported-symbol
   fields, JSON metadata fields, docs/tests/ops-agent queries, user-facing copy, and
   historical/cache tables.
3. Add at least one regression test for every bug fix or behavior change that would fail on the
   old behavior, unless the task is documentation-only or tests are genuinely not applicable.
4. Before saying a PR is ready, review the full diff and update the PR body with a section named
   `Self-review / risk check`. Include risky assumptions checked, edge cases tested, files
   intentionally not changed and why, data migration coverage when relevant, rollback/downgrade
   considerations when relevant, and known limitations or follow-ups.
5. Check existing automated PR review comments or threads before saying the PR is ready.
   Address all valid P0/P1/P2 findings and do not claim merge readiness while a valid blocking
   thread remains unresolved. External GitHub `@codex review` is optional, not a recursive gate:
   do not automatically trigger it after every fix. By default, use internal task-review agents
   plus self-review as the primary review mechanism. If an external review is explicitly requested
   or already running, inspect that result once. After a narrow review-fix, do not start another
   external review unless the user explicitly asks or the fix materially changes architecture,
   security, database behavior, or product logic.
6. Run the required verification commands from the project docs. If a command cannot be run, state
   exactly which command was not run, why it was not run, and what risk remains.
7. Do not claim a PR is ready to merge when there are unresolved valid review threads, untested
   migrations, failed checks, missing required verification, or known CI/test gaps, unless those
   limitations are explicitly documented and the user is asked to decide.

Safe defaults:

- Work from `dev` or a focused branch based on `dev`.
- Open normal PRs against `dev`.
- Open `dev` -> `main` PRs only for explicit production releases.
- Never commit `.env`, `.ops-agent.env`, local state, caches, logs, generated reports, DB dumps,
  or secrets.
- Do not change product behavior unless explicitly requested.
- Do not rename `bot/services/ai_agent_groq.py`.
- Put new project/process documentation under `docs/`; keep only `README.md` and `AGENTS.md`
  at the repository root, plus `CLAUDE.md` for Claude Code. Use subtree README.md files only
  when the content belongs to that local tool or package directory.
- Codex skills are developer tooling only. Local user skills live under
  `C:\Users\Loki\.codex\skills\` and `C:\Users\Loki\.agents\skills\`; project-copied skills
  live under `.agents/skills/` when present and may be pinned by `skills-lock.json`.
- For production forensic SQL, connect only through the SSH tunnel with `ccwbot_investigator`.
  Verify the session is read-only before evidence queries. If a required table returns
  `permission denied`, stop and report the missing grant; never switch to the application/admin
  role or modify privileges from the investigation session.

Follow `project_context.md`, `alert_logic.md`, `market_reports.md`, and
`product_analytics.md` for product guardrails. Follow `ops_agent_service.md` for ops-agent/report
boundaries. These rules are not repeated here.

Use the default verification and migration checks from `development.md`; use
`release_checklist.md` for release-only gates. Short future prompts can use
`codex_task_prompt_template.md` and only describe the concrete task-specific problem, goal, scope,
verification, and PR notes.


## PR description and merge ownership

Every non-trivial PR should state: summary, files changed, behavior impact, database/schema impact,
verification performed, manual verification status, protected-file changes when relevant, known
limitations/follow-ups, and `Self-review / risk check`.

Normal task PRs target `dev`. Production release PRs target `main` only when explicitly
requested. Do not auto-merge unless the user explicitly asks for the merge.
