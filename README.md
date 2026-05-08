# CCWBot

CCWBot is a Telegram crypto watcher bot focused on automatic **BTC movement alerts** with optional AI-assisted context.

## What the bot does
- Monitors BTC on a schedule.
- Sends automatic alerts to a configured Telegram chat when movement crosses a threshold.
- Provides manual price checks for supported coins.
- Adds optional AI summaries and optional weekly/strong-signal reporting.

## Current features
- Manual `/price` checks and inline coin buttons.
- Automatic BTC checks with configurable interval and movement threshold.
- Automatic BTC alerts separate **since last check** movement from **24h trend** (and 7d trend when available).
- AI-assisted alert/report text generation (Groq provider) with safe fallback messages.
- RSS news context filtering for crypto/BTC relevance.
- Public reports menu, with admin-only settings and status.
- PostgreSQL runtime state and global `app_settings` when `DATABASE_URL` is configured, with local `state.json` fallback.

## Supported coins
- `btc`
- `eth`
- `ton`
- `usdt`

## Commands and menus
### Main commands
- `/start`
- `/price` (or `/price <symbol>`)
- `/settings` (admin only)
- `/status` (admin only)
- `/reports`

### Hidden utility commands
- `/userid` - returns your Telegram user ID.
- `/chatid` - admin utility to show current chat ID.
- `/dailyreport` and `/weeklyreport` - report shortcuts.

### Menus
- Price menu: BTC / ETH / TON / USDT.
- Settings menu: current settings, threshold presets, interval presets.
- Reports menu: daily report, weekly report.

## Admin policy
- `TELEGRAM_ADMIN_USER_ID` controls admin permissions.
- `TELEGRAM_CHAT_ID` controls destination for automatic alerts and scheduled bot messages.
- Non-admin users can use non-admin commands only.

## Environment variables
Required core values:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `TELEGRAM_ADMIN_USER_ID`
- `GROQ_API_KEY`

Common runtime values:
- `GROQ_MODEL`
- `PRICE_MOVE_ALERT_PERCENT`
- `AUTOMATIC_CHECK_INTERVAL_SECONDS`
- `PRICE_CACHE_TTL_SECONDS`
- `HEALTH_PORT` (default `8080`)
- `ALERT_COOLDOWN_MINUTES` (legacy; currently not used in alert decision)

Optional report/signal values:
- `ENABLE_WEEKLY_REPORT`
- `WEEKLY_REPORT_DAY`
- `WEEKLY_REPORT_HOUR`
- `ENABLE_STRONG_SIGNAL_ALERTS`
- `STRONG_SIGNAL_CHECK_INTERVAL_SECONDS`
- `STRONG_SIGNAL_COOLDOWN_HOURS`

## Local setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Then fill `.env` and run:
```bash
alembic upgrade head
python main.py
```

## Development
```bash
ruff check .
python -m pytest tests/ -v
```

## Health check
CCWBot exposes a lightweight HTTP health endpoint while the bot process is running:
```bash
curl http://localhost:8080/health
```

Example response:
```json
{
  "status": "ok",
  "last_btc_check_at": "2026-05-08T12:00:00+00:00",
  "uptime_seconds": 42
}
```

Set `HEALTH_PORT` to change the port. Docker Compose publishes `8080:8080` and uses
`/health` for the bot container healthcheck, which also works for local or VPS monitoring.

## Project structure
- `main.py` starts the Telegram bot and wires handlers/jobs.
- `bot/` contains Telegram handlers, keyboards, scheduled jobs, permissions, reports, and runtime settings helpers.
- Root service modules such as `database.py`, `storage.py`, `price_service.py`, `news_service.py`, and `ai_agent_groq.py` keep shared runtime, API, and AI logic.
- `tests/test_seen_news_dedup.py` is a lightweight direct Python test for news deduplication and app settings.

## How to find your Telegram user ID
Use `/userid` in a private chat with the bot.

## Notes
- CoinGecko can return HTTP 429 rate-limit errors.
- The bot uses in-memory price caching (`PRICE_CACHE_TTL_SECONDS`) to reduce API calls.
- AI text generation uses Groq via an OpenAI-compatible client.
- Bot output is informational only and includes **Not financial advice** guidance.

## Runtime storage
- Primary: PostgreSQL when `DATABASE_URL` is configured.
- Fallback: local `state.json` only when `DATABASE_URL` is missing.
- Runtime tables used: `users`, `user_settings`, `app_settings`, `price_state`, `alerts`, `seen_news`.
- Telegram user/chat IDs are stored as `BIGINT` in PostgreSQL.
- Global alert settings are stored in `app_settings` in PostgreSQL mode.
- `seen_news` tracks processed RSS items by stable link/title keys to help avoid duplicate news processing.
- Non-DB mode keeps using the local `state.json` fallback and existing local behaviour.
- You can inspect these tables with DBeaver when PostgreSQL is running.

## Database migrations
CCWBot uses Alembic for PostgreSQL schema changes.

For local database setup or after pulling schema changes, run:
```bash
alembic upgrade head
```

The bot also runs migrations during database startup, and the Docker Compose bot service runs:
```bash
alembic upgrade head && python main.py
```

If an existing PostgreSQL volume was created before Alembic, the initial migration upgrades the known legacy `app_settings` and `alerts` layouts in place. No volume recreation is expected for this migration.

## Current limitations
- Automatic monitoring targets BTC only.
- JSON fallback is local-file persistence (single-instance oriented).
- No database/backend queue in this version.
- Depends on third-party APIs/services.

## Planned improvements
- Multi-coin automatic monitoring.
- More granular admin settings.
- Stronger resilience/observability.
- Optional shared/distributed state storage.

## Local PostgreSQL setup
1. Install Docker Desktop (includes Docker Compose).
2. Start PostgreSQL locally:
   ```bash
   docker compose up -d postgres
   ```
3. Add `DATABASE_URL` to your `.env` (see `.env.example`).
4. Run the bot:
   ```bash
   alembic upgrade head
   python main.py
   ```

Notes:
- If `DATABASE_URL` is not set, CCWBot continues to use local `state.json`.
