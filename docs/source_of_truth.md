# Repository Source of Truth

This repository is the only durable source of truth for CCWBot project rules, product guardrails,
architecture invariants, development workflow, release process, operational procedures, and agent
routing.

External prompts, ChatGPT/Codex/Claude project instructions, chat memory, PR/issue comments,
personal notes, and generated task prompts are not authoritative. They may contain only
task-specific context or a pointer back to the canonical repository files.

If external text conflicts with the repository, the repository wins.

## Canonical ownership

Each durable rule should have one primary owner:

- Product behavior, product boundaries, and architecture invariants:
  `docs/project_context.md`
- Codex/Claude implementation workflow, PR-readiness gates, branch rules, and review policy:
  `docs/codex_instructions.md`
- Agent/subagent routing:
  `agents/routing.toml`
- Agent definitions:
  `agents/*.toml` and platform adapters such as `.claude/agents/*.md`
- Local development and verification commands:
  `docs/development.md`
- Release gates:
  `docs/release_checklist.md`
- Production deployment, backup, recovery, and environment operations:
  `docs/dev_ops_guide.md`
- Observability and forensic operations:
  `docs/observability.md`, `docs/ops_agent_service.md`, and `docs/llm_usage.md`
- Public project overview:
  `README.md`

`AGENTS.md` and `CLAUDE.md` are bootstrap files for tooling. They must point to canonical
repository documentation and must not become independent forks of project policy.

## No standing rules outside the repository

Do not place durable CCWBot rules in:

- ChatGPT Project instructions or uploaded copies of repository docs;
- Codex task prompts;
- Claude task prompts;
- PR or issue comments;
- chat memory or conversation summaries;
- local notes outside the repository.

A task prompt may define only the requested delta: problem, goal, scope, out-of-scope items,
task-specific evidence, and task-specific acceptance criteria.

If a new permanent rule is needed, change the canonical repository owner in the same PR that
introduces the rule. Do not solve the problem by copying the rule into another prompt or external
instruction source.

## Conflict resolution

When two repository files disagree:

1. Use the canonical owner listed above for that subject.
2. Treat runtime code/schema as evidence of current implementation, not as permission to silently
   override intended documented behavior.
3. Fix the inconsistency in the repository instead of creating another copy of the rule.
4. Update non-owning docs to link to the owner rather than repeating normative text.

## Agent/session bootstrap

At the start of repository work, agents should read:

1. `docs/source_of_truth.md`
2. `docs/project_context.md`
3. `docs/codex_instructions.md`
4. `agents/routing.toml`
5. task-specific canonical docs as needed

Do not rely on cached external copies when the repository is accessible.
