# Codex Agent Workflow

CCWBot has two separate agent concepts:

- Runtime LLM services used by the Telegram bot.
- Repository task-review agents used during development.

Task-review agent definitions live in `agents/*.toml`. The authoritative routing rules live in
`agents/routing.toml`.

This document is explanatory only. Do not copy routing triggers, mandatory-agent lists, or standing
workflow rules here. If this document disagrees with `agents/routing.toml` or
`docs/codex_instructions.md`, those canonical owners win according to
`docs/source_of_truth.md`.

## How to use repository review agents

Before non-trivial work:

1. Read `agents/routing.toml`.
2. Select the required agents for the task.
3. Use Codex subagent/delegation support when available.
4. If delegation is unavailable, read and apply the relevant `agents/*.toml` definitions
   manually.
5. Record task-specific findings in the PR; do not copy the standing routing rules into the PR.

Platform adapters such as `.claude/agents/*.md` may expose equivalent review lenses for other
tools. They must not redefine project policy or routing.

Codex skills are separate developer tooling. Their canonical location/usage notes are in
`docs/codex_skills.md`.

PR-readiness and review policy, including external review behavior, is owned by
`docs/codex_instructions.md`.
