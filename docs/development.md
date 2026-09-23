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

These checks do not require real Telegram, LLM provider, CoinGecko, or PostgreSQL calls.
Use dummy values from `.env.example` for Compose validation. Do not publish
`docker compose config` output generated from a real `.env`, because Compose can expand secrets.
`docker compose config` validates Compose syntax only; it does not prove that Alembic migrations
apply successfully.

For database migrations, also run the migration guard and a real PostgreSQL-backed upgrade before
merge:

```bash
python -m pytest tests/test_alembic_migrations.py -v
docker compose up -d postgres
docker compose run --rm migrate
```

Alembic revision ids must be 32 characters or shorter because the default
`alembic_version.version_num` column is `VARCHAR(32)`. Prefer compact numeric/descriptive ids such
as `0022_unique_event_analysis`; long revision ids can break migration execution.

## Scope boundaries

This document owns local development, repository layout, and verification. For durable product
behavior, use `project_context.md`, `alert_logic.md`, `market_reports.md`, and
`product_analytics.md`. For implementation workflow and review policy, use
`source_of_truth.md`, `codex_instructions.md`, and `agents/routing.toml`.

## Runtime Notes

- `python main.py` remains the local bot entry point.
- Docker Compose starts PostgreSQL and the bot. Alembic migrations are explicit and do not run
  during normal bot startup.
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
- Alert orchestration remains in `bot/alerts.py`. Deterministic event identity, analysed-window,
  and news relevance helpers live under `bot/alerting/`; they must not perform Telegram delivery,
  recipient lookup, LLM calls, or database writes.
- Admin System status is compact, feature-level, read-only observability. Detailed provider and
  call-type attempts live in the separate admin LLM diagnostics screen. Both use telemetry such as
  `price_state`, `event_ai_analyses`, `llm_usage_logs`, `news_items`, and `alerts`, plus existing
  in-memory Groq backoff state. It must not perform live CoinGecko, Groq, RSS, or Telegram probes.
  Use `OK`, `WARN`, `FAIL`, and `UNKNOWN` only when the underlying telemetry supports that state.
- Migration `0022_unique_event_analysis` enforces one attached `event_analysis` row per
  `market_event_id`. During upgrade it preserves evidence by setting `market_event_id=NULL` on
  failed/no-alert attached attempts and on non-canonical duplicate successful attempts, preferring
  delivery-referenced and then oldest analyses as canonical. Confirm a current production backup
  exists before deploying this migration.
- Migration `0023_alert_outcome_decisions` adds nullable operator-facing decision observability
  fields to `alert_delivery_outcomes`: `decision_stage`, `decision_reason`, `previous_alert_id`,
  and `context_fingerprint`.

## Ops-Agent Development

`ops-agent/` is the repo-managed diagnostics collector. Its operational contract is in
`ops_agent_service.md`; the production wrapper is:

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
docker compose run --rm migrate
```

or:

```bash
alembic upgrade head
```

If a developer manually widened the local `alembic_version.version_num` column and stamped the old
long revision locally, treat that as local-dev-only repair work: inspect `alembic_version`, confirm
the matching migration effects are present, then update the local stamp to the short revision id or
rerun the migration from a clean local backup. Do not mutate production Alembic state manually.
