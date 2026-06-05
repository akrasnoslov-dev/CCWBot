# CCWBot

CCWBot is a Python Telegram crypto watcher bot. It provides manual crypto price checks,
cached market-wide reports, and automatic Event Alerts decided by Groq-backed LLM market
analysis.

## Features

- Manual `/price` checks for the active runtime symbols: `btc`, `eth`, `ton`, and `sol`.
- Automatic Event Alerts use global polling: BTC is free, while enabled non-BTC watchlist
  alerts require active Premium.
- Market Heartbeat generates cached hourly per-coin monitoring updates and sends them only
  when the user's last sent heartbeat for that coin is older than their heartbeat frequency.
- Daily and weekly reports are cached market-wide LLM reports across all active symbols.
  Daily cache refresh runs every 4 hours; weekly cache refresh runs every 24 hours.
- One coin market event creates or reuses one AI analysis, then sends it to many recipients.
- If Groq is unavailable or returns invalid JSON, no fallback threshold alert is sent.
- If report generation fails, the bot stores the failed attempt when DB storage is enabled and
  shows a temporary unavailable message instead of a fake deterministic report.
- Premium-aware `/plan`, `/watchlist`, `/myplan`, and Telegram Stars `/subscribe` commands.
- `/reports`, `/dailyreport`, and `/weeklyreport` report flows.
- User `/settings` for watchlist and heartbeat frequency, plus admin-only `/admin`,
  `/chatid`, `/grantpremium`, and `/revokepremium` commands. System status is available
  from `/admin`.
- Hidden `/userid` utility command.
- Related news links from `bot/services/news_service.py` data.
- Health endpoint for runtime checks.

Alert and report text is informational and keeps `Not financial advice.` guidance.

## Current Limitations

- Automatic Event Alerts are single-coin LLM calls. Batch all-coin analysis is not exposed yet.
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
- `GROQ_EVENT_ANALYSIS_MODEL`
- `GROQ_EVENT_ANALYSIS_MAX_TOKENS`
- `GROQ_MARKET_HEARTBEAT_MODEL`
- `GROQ_RATE_LIMIT_FALLBACK_BACKOFF_SECONDS`
- `GROQ_REPORT_MODEL`
- `GROQ_NEWS_INTELLIGENCE_MODEL`
- `GROQ_JSON_MODE`
- `GROQ_JSON_MODE_RETRY_PLAIN`
- `AUTOMATIC_CHECK_INTERVAL_SECONDS`
- `ALERT_COOLDOWN_MINUTES`
- `EVENT_ALERT_SEMANTIC_COOLDOWN_SECONDS`
- `PRICE_CACHE_TTL_SECONDS`
- `HEALTH_PORT`
- `ERROR_LOG_FILE`
- `PREMIUM_MONTHLY_STARS`
- `ENABLE_NEWS_INTELLIGENCE`
- `ENABLE_NEWS_DRIVEN_ALERTS`
- `NEWS_INTELLIGENCE_MAX_ITEMS_PER_RUN`
- `NEWS_INTELLIGENCE_MAX_LLM_CALLS_PER_RUN`
- `NEWS_INTELLIGENCE_MAX_LLM_CALLS_PER_HOUR`
- `NEWS_LLM_TIMEOUT_SECONDS`

News Intelligence stores structured RSS metadata in `news_items` and checks that persistent cache
before calling Groq. Per-run and hourly budgets keep the feature from materially increasing LLM
usage; when budget is exhausted, RSS news still flows through the existing alert/report contracts.

Legacy `PRICE_MOVE_ALERT_PERCENT`, `GROQ_STRONG_SIGNAL_MODEL`, `ENABLE_WEEKLY_REPORT`, `WEEKLY_REPORT_DAY`,
`WEEKLY_REPORT_HOUR`, `ENABLE_STRONG_SIGNAL_ALERTS`, `STRONG_SIGNAL_CHECK_INTERVAL_SECONDS`,
and `STRONG_SIGNAL_COOLDOWN_HOURS` are no longer used by active production flow.

`AUTOMATIC_CHECK_INTERVAL_SECONDS` controls Event Alert LLM analysis cadence per symbol.
The supported cadence is `1800` seconds (30 minutes); stale custom values from local state
or app settings are normalized back to 1800 seconds. It does not control Market Heartbeat
delivery frequency. Event Alert jobs are staggered by symbol in the default 30-minute cycle:
BTC at minute 00/30, ETH at 05/35, TON at 10/40, and SOL at 15/45. On startup, the schedule
log should show `symbol_first_delays=BTC:0s,ETH:300s,TON:600s,SOL:900s` at the cycle boundary.
The first-delay calculation is anchored to the wall-clock cycle, so restarts preserve the same
symbol spacing instead of pairing symbols together.

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
- `market_heartbeats` with one cached hourly heartbeat generation row per supported coin

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

## Market Heartbeat And Coin Icons

Market Heartbeat is separate from Event Alert analysis. Event Alert LLM analysis runs every
30 minutes per active symbol by default and returns only `should_alert=true` or
`should_alert=false`; heartbeat generation runs hourly, stores the latest cached result in
PostgreSQL, and does not deliver it immediately.

The Event Alert analysed market window is derived from the analysis interval and the number
of compact price points sent to the LLM. With the default 30-minute interval and 6 payload
points, alerts analyse a 3-hour window. Event Alert messages show that analysed-window
change, for example `Analysed window: 3h` and `Price change: -2.40%`, instead of exposing
CoinGecko's rolling 24h change as the main alert move.

During automatic processing, the bot checks each eligible user and coin. If a sent
`market_heartbeat` for that user and coin happened within the user's configured heartbeat
frequency, heartbeat is skipped. Event Alerts do not reset or delay the heartbeat cadence. If
no recent heartbeat exists, the bot sends the latest completed heartbeat only when it is fresh
enough, normally up to 2 hours old. Missing or stale heartbeat rows are logged and not sent.

Candidate news is filtered before it reaches the LLM. The bot selects coin-specific news by
symbol/name, adds limited high-impact general crypto market news, prefers fresh/unseen items,
and allows the LLM to reference only selected `related_news_ids`.

Coin icon mapping lives in `bot/coin_icons.py`:

- `COIN_CUSTOM_EMOJI_IDS` is where custom Telegram `custom_emoji_id` values go.
- `COIN_FALLBACK_EMOJI` is used automatically when a custom emoji ID is missing.

To extract custom emoji IDs from the CCWBotIcons pack:

1. Deploy the bot with this version.
2. As the configured admin, send all custom coin emojis from `https://t.me/addemoji/CCWBotIcons`
   to the bot in a private chat.
3. Check logs for `custom_emoji_entity ... custom_emoji_id=...`.
4. Copy the IDs into `COIN_CUSTOM_EMOJI_IDS` in `bot/coin_icons.py`.

Missing custom emoji IDs are safe; alerts and heartbeats use fallback emoji instead.

Premium payments are received as Telegram Stars on the bot's Stars balance. Withdrawal to TON
wallet is handled separately by the bot owner through Telegram/Fragment. CCWBot does not store
wallets and does not perform payouts. Exact withdrawal availability, limits, exchange rate,
fees, and regional restrictions are controlled by Telegram/Fragment and may change. There is no
`/starsbalance`; check the bot's Stars balance manually through Telegram/BotFather/Telegram UI
when available.

## Docker Compose

Docker Compose defines both the bot and PostgreSQL services. The bot service publishes the
health endpoint on localhost only and depends on the PostgreSQL health check.

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

### Production Network Exposure

Production uses Telegram polling, so no public webhook or bot HTTP endpoint is required.
Compose binds the bot health endpoint to `127.0.0.1:${HEALTH_PORT:-8080}` only. It is available
from the VPS itself for local checks and container health checks, but it should not be reachable
directly from the public internet.

PostgreSQL is intentionally not publicly exposed. Compose binds it to `127.0.0.1:5433` on the
VPS and keeps in-container traffic on Docker service networking. The bot container must connect
to PostgreSQL with the `postgres:5432` service address, not `localhost` or host networking.

Remote database access should happen only through an SSH tunnel. Expected DBeaver setup:

- SSH tunnel host: the VPS hostname or IP
- SSH tunnel user/key: your VPS SSH credentials
- Database host: `localhost`
- Database port: `5433`
- Database name/user: `ccwbot`
- Password: the environment-local `POSTGRES_PASSWORD`

After production updates, `docker ps` should show loopback bindings such as
`127.0.0.1:8080->8080/tcp` and `127.0.0.1:5433->5432/tcp`, not `0.0.0.0` bindings.

## Warning/Error File Logs

Console logging stays enabled by default. Admins can additionally persist `WARNING`, `ERROR`,
and `CRITICAL` logs to a rotating file without restarting the bot:

```text
/error_logging_on
/error_logging_off
/error_logging_status
```

The toggle is stored in `app_settings`, so it survives bot/container restarts. The log path is
configured by `ERROR_LOG_FILE`; the default is `logs/ccwbot-warnings-errors.log`, and Docker
uses `/app/logs/ccwbot-warnings-errors.log` with `./logs:/app/logs` mounted so files survive
container recreation. Rotation keeps 10 MB plus 5 backups.

On the VPS:

```bash
cd /opt/CCWBot
tail -n 100 logs/ccwbot-warnings-errors.log
```

Do not share logs publicly. Review them for secrets, private Telegram text, and operational
details before sending them to anyone.

## Development And Production Environments

Local development runs from `dev` or a feature branch based on `dev`. Production runs from
`main` on the Hetzner VPS at `/opt/CCWBot`.

Use the same environment variable names in every environment. Local development uses a
development Telegram bot token and local Docker PostgreSQL. Production uses a separate
production Telegram bot token and server Docker PostgreSQL. Both files set
`TELEGRAM_BOT_TOKEN`; do not add separate dev/prod token variable names.

Do not commit `.env`, `.env.local`, `.env.production`, database dumps, backup folders, or local
state files. `.env.example` contains placeholders only and is safe to copy.

When using Telegram polling, never run the same Telegram bot token in two places at the same
time. Stop the local dev bot before starting another process that uses the same token, and keep
the VPS production token separate from local development. Never use the production bot token
locally.

Normal work should be opened as pull requests against `dev`. Only open pull requests against
`main` for an explicit production release or `dev` -> `main` merge.

## Production Safety Rules

- Never work directly in `main` locally; use `dev` or a focused branch based on `dev`.
- Production runs `main` only.
- Keep deploys reproducible through Git and Docker Compose only.
- Never commit `.env` files, secrets, database dumps, or local state files.
- Never use the production Telegram bot token locally.
- Never manually edit tracked production files on the VPS.
- Test database migrations locally before production.
- Verify a current backup before destructive database operations.
- After deploy, always check containers, bot logs, and basic Telegram functionality.

## Operational Deploy Checklist

1. Verify the release branch and VPS environment.
2. Pull the latest `main` on the VPS.
3. Run `docker compose up -d --build`.
4. Check container health with `docker compose ps`.
5. Check bot logs with `docker compose logs -f`.
6. Verify bot functionality in Telegram.

Production tracked files should not be edited manually on the VPS. Deploy production changes
through Git only:

```bash
cd /opt/CCWBot
git checkout main
git pull
docker compose up -d --build
docker compose ps
docker compose logs -f
```

Never overwrite the production `.env`. Test migrations locally before production, and create
and verify backups before destructive database operations.

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
- Docker Compose publishes it only on `127.0.0.1` for local VPS monitoring; Telegram uses
  polling, not webhooks.

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
2. Send `/settings` as admin; it should work. Send it from a normal user; it should be denied.
3. Send `/grantpremium <telegram_user_id> 1` and `/revokepremium <telegram_user_id>` as admin; both should update `/myplan` without deleting saved coin choices.
4. Send `/userid`; it should work manually but stay hidden from command menus.
5. Send `/price btc` and another supported symbol such as `/price eth`; both should return concise price text or a generic temporary-unavailable message. Send `/price usdt`; it should be rejected as unsupported.
6. Send `/watchlist` as a free user; BTC should be available and non-BTC choices should be locked. After an admin grant or paid access, non-BTC choices should unlock but should not auto-enable.
7. Send `/plan`; My plan should show Free, Premium, or expired Premium state without exposing internals.
8. In `/plan`, Subscribe should return a Telegram Stars invoice link. Repeating it immediately should return a short wait message.
9. Send `/reports`; daily/weekly report buttons should respond without diagnostic labels, and repeated report requests should be briefly rate-limited.
10. Open Admin -> System status; Groq AI status should show OK after a successful/no-alert LLM analysis and NOT OK after an LLM failure.
11. Trigger or wait for an automatic alert sanity check; BTC remains free, non-BTC delivery requires active Premium and enabled watchlist choices. No Important Alert, Critical Alert, Market Update, or Strong Signal labels should be sent.
12. In a group chat, send `/start`; automatic alert delivery should not retarget to that group.

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
Read-only operational SQL snippets are in [docs/observability.md](docs/observability.md).
Codex agent routing and review rules are in
[docs/codex_agent_workflow.md](docs/codex_agent_workflow.md).
