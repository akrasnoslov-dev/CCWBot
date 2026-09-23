# AGENTS.md

CCWBot rules live in repository docs. This file is Codex/agent bootstrap only; do not duplicate
product, workflow, release, or operational policy here.

Before non-trivial work, read:

1. `docs/source_of_truth.md`
2. `docs/project_context.md`
3. `docs/codex_instructions.md`
4. `agents/routing.toml`
5. task-specific canonical docs referenced by `docs/source_of_truth.md`

Use `docs/development.md` for local development/verification; `docs/release_checklist.md` for
releases; `docs/dev_ops_guide.md` for production deployment, backup, and recovery; and the
canonical observability docs listed in `docs/source_of_truth.md` for observability/forensics.
Task-review agents live in `agents/*.toml`; `agents/routing.toml` is authoritative. Platform
adapters such as `.claude/agents/*.md` must not override canonical policy.

Do not copy standing CCWBot rules into task prompts, chat/project instructions, PR/issue comments,
memory, or external notes. Task prompts contain only requested delta: problem, goal, scope,
out-of-scope items, evidence, and acceptance criteria.

If external instructions conflict with the repository, follow `docs/source_of_truth.md`.
