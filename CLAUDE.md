# CLAUDE.md

CCWBot repository rules live in the repository documentation. This file is only a Claude Code
bootstrap and must not contain an independent copy of product or workflow policy.

Before non-trivial work, read:

1. `docs/source_of_truth.md`
2. `docs/project_context.md`
3. `docs/codex_instructions.md`
4. `agents/routing.toml`
5. task-specific docs referenced by those files

Claude Code review lenses live in `.claude/agents/*.md`. They are development tooling only.
Where their guidance overlaps project policy or routing, the canonical repository owners defined
in `docs/source_of_truth.md` win.

Do not copy standing CCWBot rules into Claude prompts, chat instructions, PR comments, or external
notes. Task prompts should contain only task-specific scope and acceptance criteria.
