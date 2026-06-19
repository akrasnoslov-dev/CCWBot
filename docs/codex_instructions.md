# Codex Instructions

Follow `AGENTS.md` first. This file is a short context pointer for ChatGPT/Codex sessions.

Before non-trivial work:

1. Read `AGENTS.md`, this file, `docs/project_context.md`, and `agents/routing.toml`.
2. Inspect installed skills under `C:\Users\Loki\.codex\skills\` and `.agents/skills/`.
3. Read and apply every relevant skill instruction file (`SKILL.md`, `README.md`, or equivalent).
4. If no installed skill applies, state that explicitly in the final response and PR body.
5. Use required review agents when routing says they apply.
6. Check current branch and worktree status.
7. Do not overwrite uncommitted user work.

Safe defaults:

- Work from `dev` or a focused branch based on `dev`.
- Open normal PRs against `dev`.
- Open `dev` -> `main` PRs only for explicit production releases.
- Never commit `.env`, `.ops-agent.env`, local state, caches, logs, generated reports, DB dumps,
  or secrets.
- Do not change product behavior unless explicitly requested.
- Do not change Event Alert business logic unless explicitly requested.
- Do not change Premium, watchlist, subscription, payment, or grant/revoke behavior unless explicitly requested.
- Do not rename `bot/services/ai_agent_groq.py`.
- Put new project/process documentation under `docs/`; keep only `README.md` and `AGENTS.md`
  at the repository root. Use subtree README.md files only when the content belongs to that
  local tool or package directory.
- Codex skills are developer tooling only. Local user skills live under
  `C:\Users\Loki\.codex\skills\`; project-copied skills live under `.agents/skills/` and are
  pinned by `skills-lock.json`.

Product guardrails:

- Preserve `1 coin market event = 1 AI analysis = many alert deliveries`.
- Never place LLM/Groq calls inside recipient loops.
- Manual `/price` remains free.
- BTC automatic alerts remain free.
- Non-BTC automatic alerts require active Premium and enabled watchlist choices.
- Reports remain available to all users.
- Admin-only commands stay protected.
- `/userid` stays hidden from menus/help.
- Telegram messages must not expose raw JSON, stack traces, DB internals, debug fields,
  diagnostic labels, secrets, tokens, Telegram IDs, or payment IDs.

Ops-agent/reporting guardrails:

- Ops-agent/report PRs are observability-only unless the task explicitly asks otherwise.
- Collectors must stay isolated and sanitized; a failed collector must not prevent later
  collectors from running.
- Partial reports must list failed collectors in `Collector Status`.
- Missing or `unknown` evidence is incomplete evidence, not a healthy result.
- After ops-agent code changes, production deploy requires explicitly rebuilding the `ops-agent`
  Docker image.
- Generated bundles and reports must stay out of Git.

Default verification:

```bash
python -m py_compile main.py bot/config.py bot/storage.py bot/health.py bot/alerting/alert_rules.py bot/alerting/alert_severity.py bot/db/database.py bot/domain/premium.py bot/domain/supported_coins.py bot/services/price_service.py bot/services/news_service.py bot/services/ai_agent_groq.py
ruff check .
python -m pytest tests/ -v -ra --durations=20
docker compose config >/dev/null
```

For ops-agent changes, run the relevant focused suite:

```bash
python -m pytest tests/ops_agent/ -v -ra
```

When PostgreSQL is available and ops-agent DB queries changed, also run the PostgreSQL
query-contract test from `docs/development.md`.

For Alembic migration changes, add:

```bash
python -m pytest tests/test_alembic_migrations.py -v
docker compose up -d postgres
docker compose run --rm bot alembic upgrade head
```

Alembic revision ids must be 32 characters or shorter because
`alembic_version.version_num` is `VARCHAR(32)`. Use compact ids such as
`0022_unique_event_analysis`; `docker compose config` alone does not validate migrations.

Short future prompts can use `docs/codex_task_prompt_template.md` and only describe the concrete
task-specific problem, goal, scope, verification, and PR notes.
