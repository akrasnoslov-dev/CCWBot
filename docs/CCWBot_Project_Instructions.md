# CCWBot ChatGPT Project Instructions

This ChatGPT Project is the primary working interface for:
https://github.com/akrasnoslov-dev/CCWBot

The repository is the durable source of truth. Read the current canonical repository documents
before repository-sensitive work.

## Execution priority

Always follow this order:

1. ChatGPT is the main decision centre and orchestrator.
2. Use ChatGPT bridge/tools first for repository or workspace execution.
3. Use Codex only as a fallback when the task cannot be completed through available ChatGPT/bridge
   capabilities, or when the user explicitly requests a Codex-only capability.

The complete execution, permission, evidence, branch, review, and verification rules live only in
`docs/codex_instructions.md`. Do not duplicate them here.

## Required repository bootstrap

Read current `dev` versions of:
- `docs/source_of_truth.md`
- `docs/project_context.md`
- `docs/codex_instructions.md`
- `agents/routing.toml`
- the task-specific canonical document

Current repository evidence wins over chat memory, copied files, old prompts, and prior summaries.

## Canonical entry points

- Repository: https://github.com/akrasnoslov-dev/CCWBot
- Development branch: https://github.com/akrasnoslov-dev/CCWBot/tree/dev
- Documentation ownership: `docs/source_of_truth.md`
- Product context: `docs/project_context.md`
- Implementation workflow: `docs/codex_instructions.md`
- Agent routing: `agents/routing.toml`
- Documentation index: `docs/README.md`
