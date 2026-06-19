# Codex Task Prompt Template

Use this template for normal CCWBot Codex tasks. The standing workflow, branch rules, product
guardrails, agent routing, verification defaults, and PR requirements live in `AGENTS.md`,
`docs/codex_instructions.md`, `docs/project_context.md`, and `agents/routing.toml`.

```markdown
Task: <short task title>

Problem:
- <what is wrong or missing>

Goal:
- <what should be true after this task>

Scope:
- <files, modules, docs, commands, or behavior that may change>

Out of scope:
- <explicit non-goals and protected behavior>

Verification:
- <default checks, focused tests, or why a check is not applicable>

PR notes:
- <anything the PR body must explicitly confirm>
```

For production releases, explicitly say the PR is `dev` -> `main`. Otherwise, Codex opens PRs
against `dev`.
