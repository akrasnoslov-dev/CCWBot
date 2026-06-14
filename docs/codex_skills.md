# Codex Skills

Codex skills are local developer tooling. They are not runtime Telegram bot agents, are not
imported by `main.py` or `bot/`, and runtime code must not depend on them.

Skill locations used by this project:

- Local user skills: `C:\Users\Loki\.codex\skills\`
- Project-copied skills: `.agents/skills/`
- Project skill lockfile: `skills-lock.json`

Installed skills:

- `C:\Users\Loki\.codex\skills\supabase-postgres-best-practices`
- `C:\Users\Loki\.codex\skills\requesting-code-review`
- `.agents/skills/md-docs`

## When To Use

- `supabase-postgres-best-practices`: use for PostgreSQL query writing, schema review, index
  design, RLS/security review, connection management, and database performance work. Keep this
  aligned with the project database rules: async SQLAlchemy, asyncpg, Alembic, PostgreSQL, DB
  comments for new tables/columns, and local migration testing before production.
- `requesting-code-review`: use after major features, after subagent-driven development tasks,
  and before merge or PR finalization when review support is available. It complements, but does
  not replace, the project review agents in `agents/*.toml`.
- `md-docs`: use for README.md and AGENTS.md maintenance. It checks project structure before
  changing docs and keeps README.md focused on human readers while AGENTS.md owns commands,
  workflow rules, and agent/developer context. It is not a general-purpose updater for every
  Markdown file in `docs/`.

After installing or updating skills, restart Codex so new skill metadata is picked up.

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
- `requesting-code-review` when a code-review subagent or equivalent review workflow is
  available.

For README.md or AGENTS.md refreshes, use `md-docs` first. For other Markdown files, apply the
same verification standard manually: read the relevant code or config, then keep the text short
and factual.
