# CCWBot

CCWBot is a Python Telegram crypto watcher bot. It provides manual crypto price checks,
BTC reports, and automatic movement alerts with Groq-backed AI context and deterministic
fallbacks.

## Features

- Manual `/price` checks for `btc`, `eth`, `sol`, `xrp`, `bnb`, `doge`, `ada`, `ton`,
  `link`, and `trx`.
- Automatic movement alerts use global polling: BTC is free, while enabled non-BTC watchlist
  alerts require active Premium.
- One coin market event creates or reuses one AI analysis, then sends it to many recipients.
- Premium-aware `/watchlist`, `/myplan`, and `/subscribe` foundation commands.
- `/reports`, `/dailyreport`, and `/weeklyreport` report flows.
- Admin-only `/settings`, `/status`, `/chatid`, `/grantpremium`, and `/revokepremium`
  commands.
- Hidden `/userid` utility command.
- Related news links from `news_service.py` data.
- Health endpoint for runtime checks.

Alert and report text is informational and keeps `Not financial advice.` guidance.

## Current Limitations

- Automatic monitoring uses one global admin-controlled threshold for all supported coins.
- Premium payment is not implemented yet; manual admin grants/revokes are the current testing
  path.
- No Telegram Stars payment processing yet.
- No paid LLM provider abstraction yet; Groq remains the current AI provider.
- Local `state.json` fallback is single-instance oriented.

## Architecture Overview

- `main.py` wires startup, handlers, scheduled jobs, health server, and shutdown.
- `bot/` contains Telegram handlers, alerts, reports, permissions, keyboards, setup, and runtime helpers.
- `database.py` defines async SQLAlchemy models, Premium/watchlist persistence, and migration
  startup.
- `alembic/` contains database migrations.
- `price_service.py` wraps CoinGecko calls, caching, retry, and stale fallback handling.
- `news_service.py` fetches RSS news used by news context helpers.
- `ai_agent_groq.py` builds Groq prompts, validates JSON, sanitizes alert text, and creates fallback messages.
- `health.py` serves `/health`.
- `tests/` contains unit tests that avoid real Telegram, Groq, CoinGecko, and PostgreSQL calls.

PostgreSQL is the primary runtime store when `DATABASE_URL` is configured. The bot uses async
SQLAlchemy with `asyncpg`, and Alembic manages schema changes. If `DATABASE_URL` is missing,
the bot falls back to local `state.json`.

## Environment Variables

Copy `.env.example` to `.env` and fill real values locally. Do not commit `.env`.

Required:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `TELEGRAM_ADMIN_USER_ID`
- `GROQ_API_KEY`

Common configuration:

- `DATABASE_URL`
- `GROQ_MODEL`
- `GROQ_JSON_MODE`
- `PRICE_MOVE_ALERT_PERCENT`
- `AUTOMATIC_CHECK_INTERVAL_SECONDS`
- `ALERT_COOLDOWN_MINUTES`
- `PRICE_CACHE_TTL_SECONDS`
- `HEALTH_PORT`
- `ENABLE_WEEKLY_REPORT`
- `WEEKLY_REPORT_DAY`
- `WEEKLY_REPORT_HOUR`
- `ENABLE_STRONG_SIGNAL_ALERTS`
- `STRONG_SIGNAL_CHECK_INTERVAL_SECONDS`
- `STRONG_SIGNAL_COOLDOWN_HOURS`

## Local Development Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
```

Start PostgreSQL and run the bot:

```bash
docker compose up -d postgres
alembic upgrade head
python main.py
```

## Database Migrations

Run migrations before local startup when using PostgreSQL:

```bash
alembic upgrade head
```

Docker Compose runs Alembic migrations before starting the bot service. Do not add migrations
unless a task explicitly changes the database schema.

The Premium foundation stores:

- `users.alert_frequency_seconds`
- `user_coin_subscriptions` with one lowercase symbol row per user and coin
- `user_premium_subscriptions` for current Premium entitlement state

Premium access is based primarily on `active_until > now`. Manual admin grants use
`/grantpremium <telegram_user_id> <days>`, and revokes use `/revokepremium <telegram_user_id>`.
Revoking Premium preserves saved coin choices.

## Docker Compose

Docker Compose defines both the bot and PostgreSQL services. The bot service publishes the
health endpoint and depends on the PostgreSQL health check.

Useful commands:

```bash
docker compose config
docker compose up --build
docker compose down
```

## Health Check

The bot starts a lightweight HTTP endpoint:

- `GET /health`
- Port is configured with `HEALTH_PORT` (default `8080`)

Example:

```json
{
  "status": "ok",
  "last_btc_check_at": "2026-05-08T12:00:00+00:00",
  "uptime_seconds": 42
}
```

If runtime state cannot be read, the endpoint returns `status: degraded` without exposing
internal error details.

## Testing And Linting

Run these before opening a pull request:

```bash
python -m py_compile main.py config.py database.py storage.py alert_rules.py price_service.py news_service.py ai_agent_groq.py health.py
ruff check .
python -m pytest tests/ -v
docker compose config
```

CI runs Ruff and the test suite on pull requests.

## Troubleshooting

- Missing bot token, admin ID, or alert chat configuration stops startup with a clear error.
- If PostgreSQL is not configured, the bot uses `state.json` fallback storage.
- If `/health` returns `degraded`, check storage or database availability.
- If dependency tools such as Ruff or pytest are missing, install with
  `pip install -r requirements.txt -r requirements-dev.txt`.

## Roadmap

- Per-user subscriptions.
- Telegram Stars payment flow.
- Additional provider abstraction when there is a clear product need.

More developer notes are in [docs/development.md](docs/development.md).
