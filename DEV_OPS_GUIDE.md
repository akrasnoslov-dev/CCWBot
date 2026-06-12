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
python -m pytest tests/ -v
```

Do not publish expanded Compose output from a real `.env`.

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
