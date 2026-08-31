# AGENTS.md

CCWBot repository rules live in the repository documentation. This file is only a Codex/agent
bootstrap and must not become an independent copy of product, workflow, release, or operational
policy.

Before non-trivial work, read:

1. `docs/source_of_truth.md`
2. `docs/project_context.md`
3. `docs/codex_instructions.md`
4. `agents/routing.toml`
5. task-specific canonical docs referenced by `docs/source_of_truth.md`

For local development and verification, use `docs/development.md`.
For releases, use `docs/release_checklist.md`.
For production deployment/backup/recovery, use `docs/dev_ops_guide.md`.
For observability and forensic work, use the canonical observability docs listed in
`docs/source_of_truth.md`.
For Codex skill locations and usage notes, use `docs/codex_skills.md`.

Task-review agents live in `agents/*.toml`; routing is authoritative in
`agents/routing.toml`. Platform-specific adapters such as `.claude/agents/*.md` must not
override canonical repository policy.

Do not copy standing CCWBot rules into task prompts, chat/project instructions, PR comments, issue
comments, memory, or external notes. Task prompts should contain only the requested delta:
problem, goal, scope, out-of-scope items, evidence, and acceptance criteria.

If an external instruction conflicts with the repository, follow `docs/source_of_truth.md`.
