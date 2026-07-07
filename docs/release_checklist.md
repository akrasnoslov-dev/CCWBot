# Release Checklist

Use this checklist for explicit `dev` -> `main` production release PRs.

## Before Opening The PR

1. Confirm the worktree is clean.
2. Confirm `dev` is up to date with `origin/dev`.
3. Review `origin/main...origin/dev` with name/status and stat output.
4. Confirm no `.env`, local state, cache, log, report, DB dump, or secret file is tracked.
5. Run required agents from `agents/routing.toml` for the release payload.
6. Delete only branches that are clearly merged or obsolete. Keep unclear branches.

## Required Verification

```bash
python -m py_compile main.py bot/config.py bot/storage.py bot/health.py bot/alerting/alert_rules.py bot/alerting/alert_severity.py bot/db/database.py bot/domain/premium.py bot/domain/supported_coins.py bot/services/price_service.py bot/services/news_service.py bot/services/ai_agent_groq.py
ruff check .
python -m pytest tests/ -v -ra --durations=20
docker compose config >/dev/null
```

Use `.env.example` for Compose validation when possible. Do not paste expanded Compose output.
`docker compose config` is not migration verification.

For PRs that include Alembic migrations, also confirm:

```bash
python -m pytest tests/test_alembic_migrations.py -v
docker compose up -d postgres
docker compose run --rm migrate
```

CI also applies Alembic head to a temporary PostgreSQL service. That confirms basic migration
application, but it does not replace a fresh production backup before real migrations.

Alembic revision ids must be 32 characters or shorter because
`alembic_version.version_num` is `VARCHAR(32)`. Prefer compact numeric/descriptive ids, for example
`0022_unique_event_analysis`.

## PR Description Must Include

- Summary
- Files changed
- Behavior confirmation
- Database/schema confirmation
- Migration compatibility confirmation, when migrations are included
- Verification performed
- Manual verification status
- Protected files changed and why
- Agents used or not used
- Branch cleanup summary
- Known limitations and follow-ups

For sensitive releases, also confirm alert scope, recipient delivery behavior, LLM call
placement, payment/subscription impact, and no secrets exposed.

## Before Production Deploy

1. Confirm CI is green.
2. Confirm `/opt/backups` has a current backup, or create one with `sudo scripts/backup_postgres.sh`.
3. Merge `dev` into `main` through the release PR.
4. Deploy from Git on the VPS; do not edit tracked files manually.
5. Do not overwrite production `.env`.
6. Run `docker compose run --rm migrate` only when the release includes migrations.
7. Start or restart the bot with `docker compose up -d --build`.
8. After deploy, check containers, logs, health, and basic Telegram behavior.
