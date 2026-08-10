# Dev Ops Guide

Production runs from `main` on the Hetzner VPS at `/opt/CCWBot`. Local development runs from
`dev` or a focused branch based on `dev`.

## Environment Rules

- Local and production `.env` files are environment-local and must never be committed.
- Local development uses a development Telegram bot token.
- Production uses a separate production Telegram bot token.
- Never use the production bot token locally.
- Never overwrite production `.env`.
- PostgreSQL and the bot health endpoint are bound to localhost by Compose.

## Local Checks

```bash
docker compose config >/dev/null
python -m pytest tests/ -v -ra --durations=20
```

Do not publish expanded Compose output from a real `.env`.

## PostgreSQL Backups

Production database backups live under `/opt/backups`. Existing backups may already be present
there; do not delete or move them unless the operator has verified they are obsolete.

The repo-managed manual backup command is:

```bash
cd /opt/CCWBot
sudo scripts/backup_postgres.sh
```

The script writes compressed SQL backups named:

```text
/opt/backups/ccwbot-postgres-YYYYMMDDTHHMMSSZ.sql.gz
```

It keeps the newest 14 matching `ccwbot-postgres-*.sql.gz` files by default, never deletes
unrelated files in `/opt/backups`, creates files with owner-only permissions, and does not print
`.env` values or connection strings. Override retention only when needed:

```bash
sudo CCWBOT_BACKUP_RETENTION_COUNT=14 scripts/backup_postgres.sh
```

Verify the latest backup exists:

```bash
sudo find /opt/backups -maxdepth 1 -type f -name 'ccwbot-postgres-*.sql.gz' -printf '%TY-%Tm-%Td %TH:%TM %p\n' | sort | tail -n 1
```

Verify a backup file is readable:

```bash
gzip -t /opt/backups/ccwbot-postgres-YYYYMMDDTHHMMSSZ.sql.gz
```

Test restore into a temporary/local PostgreSQL database, never production:

```bash
createdb ccwbot_restore_test
gzip -dc /opt/backups/ccwbot-postgres-YYYYMMDDTHHMMSSZ.sql.gz | psql ccwbot_restore_test
psql ccwbot_restore_test -c "select count(*) from users;"
dropdb ccwbot_restore_test
```

Before production migrations, verify a recent backup exists or create a fresh one. If the VPS is
lost but `/opt/backups` is available from server storage or an external copy, provision a new VPS,
clone the repository, restore the latest verified backup into PostgreSQL, recreate the production
`.env` manually, run any required migrations, then start the bot and verify `/health` and Telegram.

Scheduling is a manual operator step. Example crontab:

```cron
15 2 * * * cd /opt/CCWBot && /usr/bin/sudo /opt/CCWBot/scripts/backup_postgres.sh >> /var/log/ccwbot-backup.log 2>&1
```

Example systemd service template:

```ini
[Unit]
Description=CCWBot PostgreSQL backup

[Service]
Type=oneshot
WorkingDirectory=/opt/CCWBot
ExecStart=/opt/CCWBot/scripts/backup_postgres.sh
```

Example systemd timer template:

```ini
[Unit]
Description=Run CCWBot PostgreSQL backup daily

[Timer]
OnCalendar=*-*-* 02:15:00
Persistent=true

[Install]
WantedBy=timers.target
```

Install either cron or systemd on the VPS manually; this repository does not auto-install a backup
schedule.

## Deploying Ops-Agent Changes

Ops-agent code does not reach production the way bot code does. Two steps are easy to miss, and
both have caused real deployment gaps where an operator believed a fix was live and it was not.

**1. The `ops-agent` image must be rebuilt explicitly.** The ops-agent is not declared in the
root `docker-compose.yml` at all — it lives in the `ops-agent/docker-compose.ops-agent.yml`
overlay under the `ops` profile. A plain `docker compose up -d --build`, which is what the deploy
checklist runs, therefore never sees the service and never rebuilds it. After any change under
`ops-agent/`, rebuild it explicitly with the overlay:

```bash
cd /opt/CCWBot
docker compose -f docker-compose.yml -f ops-agent/docker-compose.ops-agent.yml build ops-agent
```

Until that runs, collection keeps using the previously built image: old queries, old collectors,
old detectors. The bundle will look healthy and current, because nothing reports which image
version produced it.

**2. The host wrapper is not updated by Git.** `/usr/local/bin/ccwbot-ops-agent-collect` is an
installed copy. `git pull` updates only `ops-agent/scripts/ccwbot-ops-agent-collect` in the repo,
and `docker compose up -d --build` never touches `/usr/local/bin` at all. Reinstall it manually
whenever that script changes:

```bash
sudo install -m 755 /opt/CCWBot/ops-agent/scripts/ccwbot-ops-agent-collect /usr/local/bin/ccwbot-ops-agent-collect
```

A stale installed wrapper was the root cause of the July 2026 partial-bundle streak.

Checklist after deploying an ops-agent change:

1. Rebuild the image with the overlay (command above).
2. Reinstall the host wrapper if `ops-agent/scripts/ccwbot-ops-agent-collect` changed.
3. Collect a short no-state bundle and confirm the expected new collectors or detectors appear.
4. Confirm `Collector Status` lists no failures.

## Ops-Agent Diagnostics

The production ops-agent wrapper should point at the repo-managed `ops-agent/` source. Use only the
safe wrapper for collection:

```bash
sudo /usr/local/bin/ccwbot-ops-agent-collect --since <UTC> --until now
```

Do not run raw deployment, restart, migration, environment-printing, or secret-reading commands as
part of diagnostics. A partial bundle means at least one collector failed; inspect the collector
status table and rerun after the named collector is fixed.

Both deployment steps that ops-agent changes require — the explicit image rebuild and the manual
host-wrapper reinstall — are documented above under **Deploying Ops-Agent Changes**.

For post-deploy Event Alert verification, rebuild the `ops-agent` Docker image with the deploy and
collect a short no-state bundle:

```bash
sudo /usr/local/bin/ccwbot-ops-agent-collect --period 2h --until now --no-state-update
```

Review only the sanitized report context and detector summary. Confirm `/health` is OK,
`market_events_without_alert_deliveries` is clear or has only explicit expected skip reasons, no
new critical/high unexplained Event Alert detector is triggered, and basic Telegram functionality
works in a private smoke check without recording user ids or private text.

## Production Deploy

Deploy tracked-file changes only through Git:

```bash
cd /opt/CCWBot
git checkout main
git pull
sudo scripts/backup_postgres.sh
docker compose run --rm migrate  # only when migrations are needed
docker compose up -d --build
docker compose ps
docker compose logs -f
```

After every deploy:

1. Check container status.
2. Check bot logs.
3. Check `/health` from the VPS.
4. Verify basic Telegram functionality.

When a release changes shipped LLM model defaults, inspect the existing production `.env`
before restarting. A pinned value overrides the new code default. Edit only the affected model
variables in place; never copy `.env.example` over production `.env`. For the 2026-08 gpt-oss
migration, the intended values are:

```dotenv
GROQ_MODEL=openai/gpt-oss-20b
GROQ_EVENT_ANALYSIS_MODEL=openai/gpt-oss-120b
GROQ_MARKET_HEARTBEAT_MODEL=openai/gpt-oss-20b
GROQ_REPORT_MODEL=openai/gpt-oss-20b
GROQ_NEWS_INTELLIGENCE_MODEL=openai/gpt-oss-20b
```

After restart, inspect the sanitized `ops_event=llm_config` startup lines. Confirm every call type
uses the intended model, `effort=low`, and the expected effective completion budget; confirm no old
Llama model, `llm_config_invalid`, or `llm_config_budget_risk` remains.

Normal bot restarts do not run migrations. For migrations, test locally first, confirm CI migration
validation passed, verify a current backup, run `docker compose run --rm migrate` explicitly, then
start or restart the bot.

## Dependabot

Dependabot is configured in `.github/dependabot.yml` for Python dependencies and GitHub Actions.
Do not merge Dependabot PRs blindly. Review the changelog/risk, run tests, and confirm CI is green.
Dependabot Alerts and security updates may also require repository settings in GitHub; enable them
manually if they are not already active.
