# Codex Task Prompt Template

Use this template for normal CCWBot Codex tasks.

Standing project/workflow rules must not be copied into task prompts. They live only in the
canonical repository owners defined by `docs/source_of_truth.md`.

A task prompt should describe only the requested delta. Codex must load standing rules from the
repository before implementation.

```markdown
Task: <short task title>

Problem:
- <what is wrong or missing>

Goal:
- <what should be true after this task>

Scope:
- <files, modules, docs, commands, or behavior that may change>

Out of scope:
- <explicit non-goals>

Evidence / acceptance criteria:
- <task-specific facts, reproduced failure, or expected result>

Verification:
- <task-specific checks beyond the repository defaults, or why a check is not applicable>

PR notes:
- <task-specific PR notes only>
```

Do not restate branch policy, product guardrails, agent routing, review policy, verification
defaults, release rules, deployment rules, or other standing CCWBot rules in the prompt.

For production releases, the task-specific delta may explicitly say that this task is a
`dev` -> `main` release.
