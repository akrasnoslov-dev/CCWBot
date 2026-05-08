# CCWBot

CCWBot is a Python Telegram crypto watcher bot. It provides manual crypto price checks, BTC reports, and automatic BTC movement alerts with Groq-backed AI context and deterministic fallbacks.

## Current Behaviour

- Manual `/price` supports `btc`, `eth`, `ton`, and `usdt`.
- Automatic monitoring and automatic alerts are BTC-only.
- Automatic BTC alerts are delivered to active users with chat IDs.
- One BTC market event creates or reuses one AI analysis, then sends that analysis to many recipients.
- `/settings`, `/status`, and `/chatid` are admin-only.
- `/reports`, `/dailyreport`, `/weeklyreport`, `/price`, `/start`, and `/userid` are available to normal users.
- Alert/report text is informational and keeps `Not financial advice.` guidance.
- Related news links come from `news_service.py` data, not generated AI URLs.

## Runtime Storage

PostgreSQL is the primary runtime store when `DATABASE_URL` is configured. The bot uses async SQLAlchemy with `asyncpg`, and Alembic migrations manage the schema. If `DATABASE_URL` is missing, the bot falls back to local `state.json`.

Runtime tables include `users`, `user_settings`, `app_settings`, `price_state`, `alerts`, `seen_news`, `market_events`, and `event_ai_analyses`. Telegram IDs are stored as `BIGINT`.

## Health Check

The bot starts a lightweight HTTP health endpoint:

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

If runtime state cannot be read, the endpoint returns `status: degraded` without exposing internal error details.

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

## Local Startup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Start PostgreSQL and run the bot:

```bash
docker compose up -d postgres
alembic upgrade head
python main.py
```

Check health while the bot is running:

```bash
curl http://localhost:8080/health
```

## Docker Compose

Docker Compose defines both the bot and PostgreSQL services. The bot service runs Alembic migrations before `python main.py`, publishes the health endpoint, and depends on the PostgreSQL health check.

Useful commands:

```bash
docker compose config
docker compose up --build
docker compose down
```

## Development And CI

Run these before opening a PR:

```bash
python -m py_compile main.py config.py database.py storage.py alert_rules.py price_service.py news_service.py ai_agent_groq.py health.py
ruff check .
python -m pytest tests/ -v
docker compose config
```

## Project Layout

- `main.py` wires startup, handlers, scheduled jobs, health server, and shutdown.
- `bot/` contains Telegram handlers, alerts, reports, permissions, keyboards, setup, and runtime helpers.
- `database.py` defines async SQLAlchemy models and migration startup.
- `price_service.py` wraps CoinGecko calls, caching, retry, and stale fallback handling.
- `news_service.py` fetches RSS news used by news context helpers.
- `ai_agent_groq.py` builds Groq prompts, validates JSON, sanitizes alert text, and creates fallback messages.
- `health.py` serves `/health`.
- `tests/` contains unit tests that avoid real Telegram, Groq, CoinGecko, and PostgreSQL calls.

## Current Limitations

- Automatic monitoring is BTC-only.
- No per-user subscriptions yet.
- No multi-coin automatic alerts yet.
- No paid LLM provider abstraction yet; Groq remains the current AI provider.
- Local `state.json` fallback is single-instance oriented.
