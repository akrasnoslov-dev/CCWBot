# Codex Task Prompt Template

Use this template only when the ChatGPT orchestrator has determined that a task cannot be completed
or reliably verified with ChatGPT's available tools and Codex is required as a fallback executor.

Standing project/workflow rules must not be copied into task prompts. They live in the canonical
repository owners defined by `docs/source_of_truth.md`.

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

Return to ChatGPT:
- <diff/result, verification evidence, unresolved risks>
```

Do not restate branch policy, product guardrails, routing, review policy, release rules, or deployment
rules in the prompt. Codex does not become the final acceptance owner merely because this template
is used.
