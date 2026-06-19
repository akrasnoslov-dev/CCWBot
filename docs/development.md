# Development

This project keeps the runtime install and developer tools separate:

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

Use `requirements.txt` for runtime dependencies and `requirements-dev.txt` for lint,
test, and type-check tooling.

## Local Checks

Run the same lightweight checks before opening a pull request:

```bash
python -m py_compile main.py bot/config.py bot/storage.py bot/health.py bot/alerting/alert_rules.py bot/alerting/alert_severity.py bot/db/database.py bot/domain/premium.py bot/domain/supported_coins.py bot/services/price_service.py bot/services/news_service.py bot/services/ai_agent_groq.py
ruff check .
python -m pytest tests/ -v -ra --durations=20
docker compose config >/dev/null
```

These checks do not require real Telegram, Groq, CoinGecko, or PostgreSQL calls.
Use dummy values from `.env.example` for Compose validation. Do not publish
`docker compose config` output generated from a real `.env`, because Compose can expand secrets.
`docker compose config` validates Compose syntax only; it does not prove that Alembic migrations
apply successfully.

For database migrations, also run the migration guard and a real PostgreSQL-backed upgrade before
merge:

```bash
python -m pytest tests/test_alembic_migrations.py -v
docker compose up -d postgres
docker compose run --rm bot alembic upgrade head
```

Alembic revision ids must be 32 characters or shorter because the default
`alembic_version.version_num` column is `VARCHAR(32)`. Prefer compact numeric/descriptive ids such
as `0022_unique_event_analysis`; long revision ids can break startup migrations before the bot
starts.

## Codex Agent Workflow

Codex task-review agents live in `agents/*.toml`, with mandatory routing rules in
`agents/routing.toml`. They are development workflow prompts, not Telegram bot runtime code.
Before starting any non-trivial task, Codex must check whether one or more agents apply, use
them when required, or explain why they were not needed. See
`docs/codex_agent_workflow.md`.

Codex skills are developer tooling, not runtime bot code. Local user skills live under
`C:\Users\Loki\.codex\skills\` and `C:\Users\Loki\.agents\skills\`; project-copied skills live
under `.agents/skills/` when present and may be pinned by `skills-lock.json`. Use
`documentation-writer` for general docs, `agents-md` for `AGENTS.md` and Codex-facing docs,
`supabase-postgres-best-practices` for PostgreSQL/schema/performance work, and
`requesting-code-review` for review checkpoints when available. See `docs/codex_skills.md`.

## Runtime Notes

- `python main.py` remains the local bot entry point.
- Docker Compose starts PostgreSQL and the bot, and the bot runs Alembic migrations on startup.
- Docker Compose overrides `DATABASE_URL` for the bot container to use the `postgres` service.
- Docker Compose binds the bot health port and PostgreSQL host port to `127.0.0.1` only.
  This keeps internal services off the public internet while preserving host-local checks and
  SSH-tunnel database access.
- PostgreSQL is the primary store when `DATABASE_URL` is configured.
- SQLAlchemy models, metadata, DB initialization, and compatibility re-exports live in
  `bot/db/database.py`. Runtime persistence operations are split by domain in `bot/db/`
  modules such as users, premium, prices, news, alerts, reports, and LLM usage.
- Telegram handlers live in the `bot/handlers/` package. Command and callback
  implementations are split by UX domain, while `bot/handlers/registration.py` keeps startup
  registration centralized for `bot/runtime/telegram_app.py`.
- Migration `0007_unique_telegram_user_id` blocks startup if duplicate Telegram users already
  exist. Merge duplicates before applying it.
- Local `state.json` is a fallback only and must not be committed.
- Automatic Event Alerts use per-symbol LLM analysis every 30 minutes. Custom persisted
  interval values are normalized back to 1800 seconds. Active symbols are staggered across
  the cycle to avoid burst LLM calls; for the current symbols the first-delay pattern is
  BTC 0s, ETH 300s, GRAM 600s, SOL 900s. Staggering is anchored to the wall-clock cycle, so
  restarts preserve symbol spacing and do not pair symbols together. BTC is free; enabled
  non-BTC watchlist alerts require active Premium.
- Event Alert messages show the analysed-window price change. The window is derived from
  `AUTOMATIC_CHECK_INTERVAL_SECONDS` and the compact payload point count: 30 minutes * 6
  points = 3 hours by default. The analysed-window baseline ignores stale snapshots outside
  one automatic check interval before the window start; if no fresh baseline exists, the
  message leaves the analysed-window change unknown instead of reusing old market data.
- Manual `/price` checks support the active runtime symbols: `btc`, `eth`, `ton`, and `sol`.
  The internal `ton` key is displayed as GRAM / Gram (prev. Toncoin), `/price gram` is accepted
  as an alias, and CoinGecko requests use `ids=the-open-network`. `usdt` is not supported.
- `/watchlist` and `/myplan` use PostgreSQL-backed Premium/watchlist state when
  `DATABASE_URL` is configured.
- `/subscribe` creates a Telegram Stars invoice link for a recurring Premium subscription.
  The price is `PREMIUM_MONTHLY_STARS` (default `199`), currency is `XTR`, and the period is
  30 days / `2592000` seconds. Active Premium means paid access exists until `active_until`;
  it does not prove the Telegram recurring subscription is still active. CCWBot does not
  reliably track Telegram recurring subscription active/cancelled status, so users manage
  recurring payments in Telegram Stars settings. `/subscribe` can still create another invoice
  for users with active paid access, and a new payment extends access from the current paid
  access date.
- Premium unlocks automatic alerts for enabled non-BTC watchlist coins. BTC alerts and manual
  `/price` checks remain free. Non-BTC coins are not auto-enabled after payment; users choose
  them in `/watchlist`.
- User heartbeat frequency controls regular Market Heartbeat delivery only. Event Alerts can
  arrive separately when market events are detected, subject to backend cooldowns and LLM
  decisioning.
- `/grantpremium <telegram_user_id> <days>` and `/revokepremium <telegram_user_id>` are
  admin-only manual Premium controls for testing and support.
- Automatic alert threshold remains one global admin-controlled value for all coins.
- Saved non-BTC watchlist choices remain stored when Premium expires, but non-BTC deliveries
  are blocked until Premium is active again.
- Alert orchestration remains in `bot/alerts.py`. Deterministic event identity, analysed-window,
  and news relevance helpers live under `bot/alerting/`; they must not perform Telegram delivery,
  recipient lookup, LLM calls, or database writes.
- Event Alert generation must preserve `1 market event = 1 AI analysis = many deliveries`.
  The LLM event-analysis attempt is created outside recipient loops, a resolved market event reuses
  any existing successful attached `event_analysis`, and `_deliver_market_event_alert` only reserves,
  sends, and stores per-recipient delivery rows. Delivery code must not call Groq or create
  `event_ai_analyses` rows.
- Admin System status is read-only observability. It must use persisted telemetry such as
  `price_state`, `event_ai_analyses`, `llm_usage_logs`, `news_items`, and `alerts`, plus existing
  in-memory Groq backoff state. It must not perform live CoinGecko, Groq, RSS, or Telegram probes.
  Use `OK`, `WARN`, `FAIL`, and `UNKNOWN` only when the underlying telemetry supports that state.
- Event Alert identity is backend-owned after LLM validation. Broad LLM keys such as
  `news_catalyst`, `price_movement`, and `volatility` are normalized with deterministic rules using
  the raw key, alert title/body, and selected real related-news title/source/link context. Repeated
  same-family alerts stay inside the semantic cooldown unless urgency increases, analysed-window
  movement grows by the configured material delta, or selected stable news identity shows a new
  driver.
- Migration `0022_unique_event_analysis` enforces one attached `event_analysis` row per
  `market_event_id`. During upgrade it preserves evidence by setting `market_event_id=NULL` on
  failed/no-alert attached attempts and on non-canonical duplicate successful attempts, preferring
  delivery-referenced and then oldest analyses as canonical. Confirm a current production backup
  exists before deploying this migration.

## Ops-Agent Development

`ops-agent/` is the repo-managed diagnostics collector used by the production wrapper
`/usr/local/bin/ccwbot-ops-agent-collect`. Keep wrapper compatibility for:

```bash
sudo /usr/local/bin/ccwbot-ops-agent-collect --since <UTC> --until now
```

Ops-agent DB collectors must be read-only, isolated from each other, and sanitized. A failed DB
collector should record a failed collector status and allow later collectors to run. Add focused
tests under `tests/ops_agent/` for collector isolation, report status wording, query contracts, and
redaction whenever diagnostics change.

Run the focused ops-agent suite for ops-agent code or reporting changes:

```bash
python -m pytest tests/ops_agent/ -v -ra
```

For PostgreSQL query-contract verification, run the ops-agent integration test against a local
throwaway PostgreSQL database. The test upgrades the database to Alembic head, runs `EXPLAIN` for
every ops-agent DB query, and executes the same-family/same-news repeat collectors against
malformed `alerts.numeric_context` rows inside a rolled-back transaction:

```bash
OPS_AGENT_POSTGRES_TEST_DATABASE_URL=postgresql+asyncpg://<user>:<password>@localhost:<port>/<test_db> \
  python -m pytest tests/ops_agent/test_db_queries_and_detectors.py::test_all_ops_agent_queries_explain_against_migrated_postgres_schema -v
```

## Local Migration Recovery

If a local development database failed during an Alembic migration, inspect the current version
before changing state:

```bash
docker compose exec postgres psql -U <user> -d <db> -c "select * from alembic_version;"
```

If the failed migration did not update `alembic_version`, apply the code fix and rerun:

```bash
docker compose up -d --build
```

or:

```bash
docker compose exec bot alembic upgrade head
```

If a developer manually widened the local `alembic_version.version_num` column and stamped the old
long revision locally, treat that as local-dev-only repair work: inspect `alembic_version`, confirm
the matching migration effects are present, then update the local stamp to the short revision id or
rerun the migration from a clean local backup. Do not mutate production Alembic state manually.
- Telegram Stars payments arrive on the bot's Stars balance. Withdrawal to TON wallet is handled
  outside CCWBot by the bot owner through Telegram/Fragment. CCWBot does not request or store
  wallet addresses, does not connect wallets, and does not automate payouts. Withdrawal
  availability, limits, exchange rate, fees, and regional restrictions are controlled by
  Telegram/Fragment and may change.
- Explicit subscription cancellation/refund events are not automated. Entitlement
  remains based on `user_premium_subscriptions.active_until > now` and naturally expires when
  renewals stop.
