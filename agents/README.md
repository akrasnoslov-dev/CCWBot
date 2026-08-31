# CCWBot Codex subagents

Codex task-review subagent definitions live in this directory.

The authoritative routing rules are in `agents/routing.toml`. Do not duplicate routing triggers,
mandatory-agent lists, project guardrails, or general workflow policy in this README, task prompts,
or external instructions.

For repository authority and conflict resolution, read `docs/source_of_truth.md`.
For implementation/PR workflow, read `docs/codex_instructions.md`.
For skill locations and usage notes, read `docs/codex_skills.md`.

These agent definitions are development tooling only and are not loaded by the Telegram bot at
runtime.
