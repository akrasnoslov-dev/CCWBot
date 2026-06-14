# Codex Instructions

Follow `AGENTS.md` first. This file is a short context pointer for ChatGPT/Codex sessions.

Before non-trivial work:

1. Read `AGENTS.md` and `agents/routing.toml`.
2. Use required review agents when routing says they apply.
3. Use installed Codex skills from `docs/codex_skills.md` when they match the task.
4. Check current branch and worktree status.
5. Do not overwrite uncommitted user work.

Safe defaults:

- Work from `dev` or a focused branch based on `dev`.
- Open normal PRs against `dev`.
- Open `dev` -> `main` PRs only for explicit production releases.
- Never commit `.env`, local state, caches, logs, reports, DB dumps, or secrets.
- Do not change product behavior unless explicitly requested.
- Do not rename `bot/services/ai_agent_groq.py`.
- Put new project/process documentation under `docs/`; keep only `README.md` and `AGENTS.md`
  at the repository root. Use subtree README.md files only when the content belongs to that
  local tool or package directory.
- Codex skills are developer tooling only. Local user skills live under
  `C:\Users\Loki\.codex\skills\`; project-copied skills live under `.agents/skills/` and are
  pinned by `skills-lock.json`.

Product guardrails:

- Manual `/price` remains free.
- BTC automatic alerts remain free.
- Non-BTC automatic alerts require active Premium and enabled watchlist choices.
- Reports remain available to all users.
- Admin-only commands stay protected.
- `/userid` stays hidden from menus/help.
- Telegram messages must not expose raw JSON, stack traces, DB internals, debug fields, or
  diagnostic labels.

Default verification:

```bash
python -m py_compile main.py bot/config.py bot/storage.py bot/health.py bot/alerting/alert_rules.py bot/alerting/alert_severity.py bot/db/database.py bot/domain/premium.py bot/domain/supported_coins.py bot/services/price_service.py bot/services/news_service.py bot/services/ai_agent_groq.py
ruff check .
python -m pytest tests/ -v
docker compose config >/dev/null
```

For Alembic migration changes, add:

```bash
python -m pytest tests/test_alembic_migrations.py -v
docker compose up -d postgres
docker compose run --rm bot alembic upgrade head
```

Alembic revision ids must be 32 characters or shorter because
`alembic_version.version_num` is `VARCHAR(32)`. Use compact ids such as
`0022_unique_event_analysis`; `docker compose config` alone does not validate migrations.
