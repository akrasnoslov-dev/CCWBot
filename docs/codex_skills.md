# Codex Skills

Codex skills are local developer tooling. They are not runtime Telegram bot agents, are not
imported by `main.py` or `bot/`, and runtime code must not depend on them.

Last audited: 2026-06-19 from on-disk `SKILL.md` files.

## Skill Locations

- Codex user skills: `C:\Users\Loki\.codex\skills\`
- Agents user skills: `C:\Users\Loki\.agents\skills\`
- Project-copied skills: `.agents/skills/` when present
- Project skill lockfile: `skills-lock.json` when present

No project-copied `SKILL.md` files were present under `.agents/skills/` during this audit.

## Current User-Level Skills

| Skill | Location | Use When |
|---|---|---|
| `imagegen` | `C:\Users\Loki\.codex\skills\.system\imagegen` | Generating or editing bitmap images. |
| `openai-docs` | `C:\Users\Loki\.codex\skills\.system\openai-docs` | Answering OpenAI product/API or Codex documentation questions from official sources. |
| `plugin-creator` | `C:\Users\Loki\.codex\skills\.system\plugin-creator` | Creating Codex plugin directories and manifests. |
| `skill-creator` | `C:\Users\Loki\.codex\skills\.system\skill-creator` | Creating or updating Codex skills. |
| `skill-installer` | `C:\Users\Loki\.codex\skills\.system\skill-installer` | Installing curated or repo-based skills. |
| `agents-md` | `C:\Users\Loki\.codex\skills\agents-md` | Maintaining concise `AGENTS.md`, `CLAUDE.md`, and agent-facing instructions. |
| `caveman` | `C:\Users\Loki\.codex\skills\caveman` | Ultra-compressed communication when explicitly requested. |
| `documentation-writer` | `C:\Users\Loki\.codex\skills\documentation-writer` | General documentation quality, structure, guides, references, and explanations. |
| `playwright` | `C:\Users\Loki\.codex\skills\playwright` | Browser automation through Playwright. |
| `requesting-code-review` | `C:\Users\Loki\.codex\skills\requesting-code-review` | Review checkpoints after major features or before merge/PR finalization. |
| `supabase-postgres-best-practices` | `C:\Users\Loki\.codex\skills\supabase-postgres-best-practices` | PostgreSQL query, schema, index, connection, RLS/security, and performance work. |

Additional user-level skill copies:

| Skill | Location | Notes |
|---|---|---|
| `agents-md` | `C:\Users\Loki\.agents\skills\agents-md` | Duplicate user-level copy for agent-facing docs. |
| `caveman` | `C:\Users\Loki\.agents\skills\caveman` | Duplicate user-level compressed-communication skill. |
| `documentation-writer` | `C:\Users\Loki\.agents\skills\documentation-writer` | Duplicate user-level documentation skill. |
| `find-skills` | `C:\Users\Loki\.agents\skills\find-skills` | Discovering installable skills when the user asks for new capabilities. |

Codex may also expose plugin-provided skills in a session. Do not treat plugin cache paths as
project-installed skills unless a task explicitly asks to audit plugin bundles.

## Documentation Work

For documentation updates:

1. Read `AGENTS.md`, `docs/codex_instructions.md`, `docs/project_context.md`, and
   `agents/routing.toml`.
2. Inspect the skill locations above before editing.
3. Read every matching `SKILL.md`; if relevant, also read `SOURCES.md`, `SPEC.md`, or README-like
   files in that skill directory.
4. Use `documentation-writer` for README/docs structure, clarity, Diataxis-style document purpose,
   guides, references, and explanations.
5. Use `agents-md` for `AGENTS.md`, Codex-facing workflow docs, and instructions intended for
   coding agents.
6. If duplicate user-level copies of the same skill exist, read them during the audit, apply the
   guidance once if equivalent, and note any material conflict.

Keep root `README.md` user/developer-facing. Keep root `AGENTS.md` agent-facing. Put detailed
project and process docs under `docs/`.

## Relationship To Project Agents

Before non-trivial work, still check `agents/routing.toml`.

Required project agents remain mandatory for their domains. Skills provide extra guidance and
workflow support, while `agents/*.toml` and `agents/routing.toml` remain the project-specific
review contract.

For database or schema changes, use both:

- `db_migration_guardian` from `agents/routing.toml`;
- `supabase-postgres-best-practices` for PostgreSQL best-practice review.

For review checkpoints, use both:

- the required agents from `agents/routing.toml`;
- `requesting-code-review` when a code-review subagent or equivalent review workflow is available.

After installing, removing, or updating skills, restart Codex so new skill metadata is picked up,
then refresh this inventory if the project docs depend on it.
