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
- Premium-aware `/watchlist`, `/myplan`, and Telegram Stars `/subscribe` commands.
- `/reports`, `/dailyreport`, and `/weeklyreport` report flows.
- Admin-only `/settings`, `/status`, `/chatid`, `/grantpremium`, and `/revokepremium`
  commands.
- Hidden `/userid` utility command.
- Related news links from `bot/services/news_service.py` data.
- Health endpoint for runtime checks.

Alert and report text is informational and keeps `Not financial advice.` guidance.

## Current Limitations

- Automatic monitoring uses one global admin-controlled threshold for all supported coins.
- Telegram Stars refunds/chargebacks and explicit cancellation updates are not automated yet;
  entitlement naturally expires when `active_until <= now`.
- No paid LLM provider abstraction yet; Groq remains the current AI provider.
- Local `state.json` fallback is single-instance oriented.

## Project Structure

- `main.py` remains the local and Docker entry point.
- `bot/` contains Telegram handlers, scheduled alert/report jobs, runtime setup, and `/health`.
- `bot/alerting/` contains alert rule and severity helpers.
- `bot/db/` contains async SQLAlchemy models, persistence helpers, and migration startup.
- `bot/domain/` contains pure domain rules such as supported coins and Premium entitlement.
- `bot/services/` contains external service integrations for CoinGecko, RSS news, and Groq.
- `alembic/` contains database migrations.
- `tests/` contains unit tests that avoid real Telegram, Groq, CoinGecko, and PostgreSQL calls.

PostgreSQL is the primary runtime store when `DATABASE_URL` is configured. The bot uses async
SQLAlchemy with `asyncpg`, and Alembic manages schema changes. If `DATABASE_URL` is missing,
the bot falls back to local `state.json`.

## Environment Variables

Copy `.env.example` to `.env` and fill real values locally. Do not commit `.env`.

Required:

- `ENVIRONMENT`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `TELEGRAM_ADMIN_USER_ID`
- `GROQ_API_KEY`

Common configuration:

- `DATABASE_URL`
- `POSTGRES_PASSWORD`
- `GROQ_MODEL`
- `GROQ_JSON_MODE`
- `GROQ_JSON_MODE_RETRY_PLAIN`
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
- `PREMIUM_MONTHLY_STARS`

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

Migration `0007_unique_telegram_user_id` adds uniqueness for `users.telegram_user_id`. It
intentionally stops if duplicate Telegram users already exist; merge duplicate user rows before
running that migration.

The Premium foundation stores:

- `users.alert_frequency_seconds`
- `user_coin_subscriptions` with one lowercase symbol row per user and coin
- `user_premium_subscriptions` for current Premium entitlement state
- `payments` with one row per processed Telegram Stars payment

`/subscribe` starts a recurring Telegram Stars Premium subscription. The default price is
configured by `PREMIUM_MONTHLY_STARS=199`, uses Telegram Stars currency `XTR`, and uses a
30-day subscription period (`2592000` seconds). Premium unlocks automatic alerts for enabled
non-BTC watchlist coins. BTC automatic alerts and manual `/price` checks remain free.
Active Premium means paid access is available until `active_until`; it does not prove the user
still has an active recurring Telegram subscription. CCWBot does not reliably track Telegram
recurring subscription active/cancelled status, so users manage recurring payments in Telegram
Stars settings. `/subscribe` can still create a payment link for users with active paid access,
and a new payment extends access from the current paid access date.

After payment, non-BTC coins are not enabled automatically; users choose coins manually in
`/watchlist`. Saved non-BTC choices remain stored when Premium expires and become effective
again after renewal.

Premium access is based primarily on `active_until > now`. Manual admin grants use
`/grantpremium <telegram_user_id> <days>`, and revokes use `/revokepremium <telegram_user_id>`.
Revoking Premium preserves saved coin choices.

Premium payments are received as Telegram Stars on the bot's Stars balance. Withdrawal to TON
wallet is handled separately by the bot owner through Telegram/Fragment. CCWBot does not store
wallets and does not perform payouts. Exact withdrawal availability, limits, exchange rate,
fees, and regional restrictions are controlled by Telegram/Fragment and may change. There is no
`/starsbalance`; check the bot's Stars balance manually through Telegram/BotFather/Telegram UI
when available.

## Docker Compose

Docker Compose defines both the bot and PostgreSQL services. The bot service publishes the
health endpoint and depends on the PostgreSQL health check.

Useful commands:

```bash
cp .env.example .env
docker compose config >/dev/null
docker compose up --build
docker compose down
```

Compose overrides `DATABASE_URL` inside the bot container so it connects to the `postgres`
service. Keep `POSTGRES_PASSWORD` set in `.env`, and do not publish `docker compose config`
output from a real `.env` because Compose can expand secrets.

## Development And Production Environments

Use the same environment variable names in every environment. Local development should use a
dev Telegram bot token in `.env` with `ENVIRONMENT=development`. The production VPS should use
its own production `.env` with `ENVIRONMENT=production` and the production Telegram bot token.
Both files set `TELEGRAM_BOT_TOKEN`; do not add separate dev/prod token variable names.

Do not commit `.env`, `.env.local`, `.env.production`, database dumps, backup folders, or local
state files. `.env.example` contains placeholders only and is safe to copy.

When using Telegram polling, never run the same Telegram bot token in two places at the same
time. Stop the local dev bot before starting another process that uses the same token, and keep
the VPS production token separate from local development.

Full startup smoke test:

```bash
docker compose up --build -d
docker compose ps
docker compose down
```

Both `bot` and `postgres` should show healthy before considering the Compose startup verified.

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
python -m py_compile main.py bot/config.py bot/storage.py bot/health.py bot/alerting/alert_rules.py bot/alerting/alert_severity.py bot/db/database.py bot/domain/premium.py bot/domain/supported_coins.py bot/services/price_service.py bot/services/news_service.py bot/services/ai_agent_groq.py
ruff check .
python -m pytest tests/ -v
docker compose config >/dev/null
```

CI runs Ruff, compile checks, the test suite, and Compose validation on pull requests.

## Manual Telegram Smoke Test

After deploy, verify with a private chat:

1. Send `/start` as the configured `TELEGRAM_ADMIN_USER_ID`; admin-only commands should appear.
2. Send `/settings` and `/status` as admin; both should work. Send the same commands from a normal user; both should be denied.
3. Send `/grantpremium <telegram_user_id> 1` and `/revokepremium <telegram_user_id>` as admin; both should update `/myplan` without deleting saved coin choices.
4. Send `/userid`; it should work manually but stay hidden from command menus.
5. Send `/price btc` and another supported symbol such as `/price eth`; both should return concise price text or a generic temporary-unavailable message. Send `/price usdt`; it should be rejected as unsupported.
6. Send `/watchlist` as a free user; BTC should be available and non-BTC choices should be locked. After an admin grant or paid access, non-BTC choices should unlock but should not auto-enable.
7. Send `/myplan`; it should show Free, Premium, or expired Premium state without exposing internals.
8. Send `/subscribe`; it should return a Telegram Stars invoice link. Repeating it immediately should return a short wait message.
9. Send `/reports`; daily/weekly report buttons should respond without diagnostic labels, and repeated report requests should be briefly rate-limited.
10. Trigger or wait for an automatic alert sanity check; BTC remains free, non-BTC delivery requires active Premium and enabled watchlist choices.
11. In a group chat, send `/start`; automatic alert delivery should not retarget to that group.

Do not paste bot logs, `.env`, Compose config output, or private Telegram text into PRs.

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
