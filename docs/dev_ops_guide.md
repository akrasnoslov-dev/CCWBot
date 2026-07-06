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

## Ops-Agent Diagnostics

The production ops-agent wrapper should point at the repo-managed `ops-agent/` source. Use only the
safe wrapper for collection:

```bash
sudo /usr/local/bin/ccwbot-ops-agent-collect --since <UTC> --until now
```

Do not run raw deployment, restart, migration, environment-printing, or secret-reading commands as
part of diagnostics. A partial bundle means at least one collector failed; inspect the collector
status table and rerun after the named collector is fixed.

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
docker compose up -d --build
docker compose ps
docker compose logs -f
```

After every deploy:

1. Check container status.
2. Check bot logs.
3. Check `/health` from the VPS.
4. Verify basic Telegram functionality.

For migrations, test locally first and verify a current backup before production.
