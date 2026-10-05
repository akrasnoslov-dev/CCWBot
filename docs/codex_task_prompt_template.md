# Codex Task Prompt Template

Use this only when Codex is actually needed as the fallback execution environment.

ChatGPT remains the primary CCWBot decision centre and orchestrator. Do not create a Codex task just
because work involves code; use available ChatGPT/bridge capabilities first.

Standing project/workflow rules must not be copied into task prompts. They live in the canonical
repository owners defined by `docs/source_of_truth.md`.

A Codex task prompt should describe only the requested delta. Codex must load standing rules from
the repository before implementation.

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
- <task-specific checks beyond repository defaults, or why a check is not applicable>

PR notes:
- <task-specific PR notes only>
```

Do not restate branch policy, product guardrails, routing, review policy, release rules, deployment
rules, or other standing CCWBot rules in the prompt.

For production releases, the task-specific delta may explicitly say that this task is a
`dev -> main` release.
