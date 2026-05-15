# AGENTS.md

## Project
CCWBot / CryptoCurrencyWatcherBot (`akrasnoslov-dev/CCWBot`).

Stack: Python Telegram Bot API, Groq/OpenAI-compatible LLM, CoinGecko, RSS/news, PostgreSQL, async SQLAlchemy + asyncpg, Alembic, Docker Compose, CI, `/health`.

Core invariant:

```text
1 coin market event = 1 AI analysis = many alert deliveries
```

Never put LLM/Groq calls inside a recipient loop.

## Product Rules
- Do not change product behaviour unless explicitly asked.
- Automatic alerts are BTC-only unless explicitly expanded.
- Manual `/price` supports configured supported coins and remains free.
- `/reports`, `/dailyreport`, `/weeklyreport` are available to all users.
- `/settings` is admin-only.
- `/status` is admin-only if present.
- `/userid` is hidden: works manually, not shown in menus/help.
- Normal users must not change global settings.
- Global alert threshold is admin-controlled.
- Keep alert language cautious.
- Never write direct financial advice like "buy now" or "sell now".
- Include "Not financial advice." where applicable.
- Related news must use real title/source/link from `bot/services/news_service.py`.

## Alert Flow
1. Create/reuse one market event.
2. Create/reuse one AI analysis.
3. Resolve eligible recipients.
4. Send the same sanitized analysis to recipients.
5. Store one delivery record per recipient.

Never implement "1 user = 1 LLM call" for the same event.

## Coins and Data
- Use lowercase internal symbols and uppercase display symbols.
- Keep CoinGecko ID mapping explicit.
- Prefer batch CoinGecko calls for multiple coins.
- Handle CoinGecko 429/rate limits carefully.
- Do not add coins unless requested.

## Database
- Runtime DB paths must be async.
- Use PostgreSQL, async SQLAlchemy, asyncpg, and Alembic.
- Do not add sync DB calls to async paths.
- Do not casually create extra DB engines.
- Avoid asyncpg cross-event-loop issues.
- Use Alembic for schema changes.
- Do not change schema unless required.
- Every new database table and column must include a clear English DB comment.
- Handle database migrations carefully and test them locally before production.
- Never log secrets or connection strings.

## Telegram UX
- Keep admin-only commands protected.
- Keep messages concise and clear.
- Do not expose raw JSON, stack traces, DB internals, or debug fields.
- Never leak diagnostic labels in Telegram messages, including `Data:`, `News:`, `Debug:`, `move=`, `change24h=`, `change7d=`, `threshold=`, `interval=`, `previous=`, `current=`.

## Logging
- Use Python logging, not `print`.
- Keep useful INFO logs: database configured, bot started, health server started, automatic interval, command handled/denied, alert delivery summary, clean shutdown.
- Move repetitive/internal logs to DEBUG.
- Reduce noisy third-party INFO logs from `httpx` and APScheduler if needed.
- Never log tokens, API keys, `DATABASE_URL`, raw `.env` values, or private Telegram text.

## Health
`/health` is for monitoring only. Return safe JSON with `status`, `uptime_seconds`, and available state such as `last_btc_check_at`. If state lookup fails, return a degraded response without secrets, stack traces, or raw exceptions.

## Premium and Payments
- BTC remains free unless explicitly changed.
- Manual `/price` remains free unless explicitly changed.
- Premium unlocks automatic non-BTC alerts.
- Store subscription/payment state in PostgreSQL.
- Keep price configurable where practical.
- Add admin/manual premium grant/revoke only when useful for testing.
- Do not auto-enable non-BTC coins after purchase unless requested.
- If Premium expires, keep non-BTC choices in DB, block non-BTC deliveries, and restore them after renewal.
- If Telegram Stars recurring support is unclear, investigate and document it before implementing.

## Available Agents
All agents live in `agents/*.toml`.

- `architecture_guardian`: cross-cutting design and the one-event/one-analysis/many-deliveries invariant.
- `security_review_agent`: authorization, secrets, privacy, logging, payment abuse, and user-controlled data exposure.
- `code_quality_agent`: maintainability, async boundaries, error handling, logging levels, and focused refactors.
- `test_ci_agent`: regression coverage, validation commands, and CI confidence.
- `product_policy_agent`: Telegram command access, alert wording, premium/free UX, and product-rule consistency.
- `market_pipeline_agent`: CoinGecko/news/LLM payloads, event detection, delivery flow, and rate-limit handling.
- `db_migration_guardian`: PostgreSQL, async SQLAlchemy, Alembic, persistence contracts, and data integrity.
- `telegram_stars_payments_agent`: Premium, Telegram Stars, subscription expiry, grants/revokes, and payment idempotency.
- `devops_release_agent`: Docker, CI, config, health monitoring, dependencies, and release safety.

## Agent Workflow
- Use relevant agents proactively for every task.
- For production-impacting changes, use `architecture_guardian` plus at least one domain agent.
- Use `security_review_agent`, `code_quality_agent`, and `test_ci_agent` for broad repository reviews.
- Use `db_migration_guardian` for persistence/schema changes.
- Use `market_pipeline_agent` for price, news, alert, and delivery changes.
- Use `telegram_stars_payments_agent` for Premium, subscriptions, grants/revokes, and billing state.
- Use `product_policy_agent` for command behavior, menus/help, and user-visible copy.
- Use `devops_release_agent` for Docker, CI, config, health, dependencies, and deployment docs.
- If no agent is relevant, state why in the PR description.

## Safe Changes
- Keep changes focused and safe.
- Prefer small helpers, clear names, explicit boundaries, and behaviour tests.
- Avoid unrelated rewrites, risky file moves, unused abstractions, and product changes.
- Do not rename `ai_agent_groq.py` unless explicitly requested.
- `python main.py` and Docker Compose startup must keep working.
- Update docs when setup, config, commands, dependencies, architecture, or behaviour changes.

## Verification
Default checks:

```bash
python -m py_compile main.py bot/config.py bot/storage.py bot/health.py bot/alerting/alert_rules.py bot/alerting/alert_severity.py bot/db/database.py bot/domain/premium.py bot/domain/supported_coins.py bot/services/price_service.py bot/services/news_service.py bot/services/ai_agent_groq.py
ruff check .
python -m pytest tests/ -v
docker compose config >/dev/null
```

If Docker Compose changes, run `docker compose config >/dev/null`. Do not publish Compose config output from a real `.env`, and do not claim manual Telegram/runtime verification unless it was actually performed.

## Branching and Deployment Workflow
- `dev` is the default branch for local development, Codex tasks, and feature work.
- Start work from `dev` or from a focused feature branch based on `dev`.
- Codex should continue creating Pull Requests automatically for normal tasks.
- Default PR target/base branch is `dev`, not `main`.
- Open PRs against `dev` by default. Only open PRs against `main` when explicitly asked for a production release or `dev` -> `main` merge.
- `main` is production/stable and must stay deployable.
- The production VPS runs only `main` from `/opt/CCWBot`.
- After `dev` is validated, merge `dev` into `main`, then update the VPS.

Production server update flow:

```bash
cd /opt/CCWBot
git checkout main
git pull
docker compose up -d --build
docker compose logs -f
```

Never commit `.env` files or real secrets.

## Git and PR Workflow
Never commit directly to `main`.

For every task:
1. Create a focused branch from `dev`.
2. Make only relevant changes.
3. Run verification.
4. Commit.
5. Push.
6. Create a GitHub PR against `dev` unless explicitly asked to release production or merge `dev` into `main`.

Do not auto-merge PRs, delete user work, or include generated/cache files.

Never commit `.env`, `state.json`, `.venv`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.ruff_cache/`, `pytest-cache-files-*/`, `*.db`, `*.sqlite`, or database volumes.

## PR Description
Every PR must include summary, files changed, behaviour confirmation, database/schema confirmation, verification performed, manual verification status, protected files changed and why, and known limitations/follow-ups.

For sensitive changes, also confirm alert scope, recipient delivery behaviour, LLM call placement, payment/subscription impact, and no secrets exposed.

## Protected Files
Treat these carefully: `docker-compose.yml`, `.env.example`, `requirements.txt`, `requirements-dev.txt`, `README.md`.

Modify protected files only when required and explain why. `docker-compose.yml` must keep top-level `services:`. Never place `postgres:` at top level.

## When Unsure
Prefer the smallest safe change. If a task is too large, split it into focused PRs. If requirements conflict, stop and explain. If external service support is unclear, investigate before implementing.
