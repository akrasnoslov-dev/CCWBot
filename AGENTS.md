# AGENTS.md

## Project
You are working on CCWBot / CryptoCurrencyWatcherBot (`akrasnoslov-dev/CCWBot`).

Stack: Python Telegram Bot API, Groq/OpenAI-compatible LLM, CoinGecko, RSS/news, PostgreSQL, async SQLAlchemy + asyncpg, Alembic, Docker Compose, CI, `/health`.

Core rule:

```text
1 coin market event = 1 AI analysis = many alert deliveries
```

Preserve this rule.

## Product rules
Do not change product behaviour unless explicitly asked.

Current rules:
- Automatic alerts are BTC-only unless explicitly expanded.
- Manual `/price` supports configured supported coins.
- `/reports`, `/dailyreport`, `/weeklyreport` are available to all users.
- `/settings` is admin-only.
- `/status` is admin-only if present.
- `/userid` is hidden: works manually, not shown in menus/help.
- Normal users must not change global settings.
- Global alert threshold is admin-controlled.
- Keep alert language cautious.
- Never write direct financial advice like “buy now” or “sell now”.
- Include “Not financial advice.” where applicable.
- Related news must use real title/source/link from `news_service.py`.

## Alert architecture
Never put LLM/Groq calls inside a recipient loop.

Alert flow:
1. Create/reuse one market event.
2. Create/reuse one AI analysis.
3. Resolve eligible recipients.
4. Send the same sanitized analysis to recipients.
5. Store one delivery record per recipient.

Never implement “1 user = 1 LLM call” for the same event.

## Coins and price data
- Use consistent lowercase internal symbols and uppercase display symbols.
- Keep CoinGecko ID mapping explicit.
- Prefer batch CoinGecko calls for multiple coins.
- Handle CoinGecko 429/rate limits carefully.
- Do not add coins unless requested.

## Database
Use PostgreSQL, async SQLAlchemy, asyncpg, and Alembic.

Rules:
- Runtime DB paths must be async.
- Do not add sync DB calls to async paths.
- Do not casually create extra DB engines.
- Avoid asyncpg cross-event-loop issues.
- Use Alembic for schema changes.
- Do not change schema unless required.
- Never log secrets or connection strings.

## Telegram UX
- Keep admin-only commands protected.
- Keep messages concise and clear.
- Do not expose raw JSON, stack traces, DB internals, or debug fields.

Never leak diagnostic text in Telegram messages, including `Data:`, `News:`, `Debug:`, `move=`, `change24h=`, `change7d=`, `threshold=`, `interval=`, `previous=`, `current=`.

## Logging
Use Python logging, not `print`.

Keep useful INFO logs: database configured, bot started, health server started, automatic interval, command handled/denied, alert delivery summary, clean shutdown.

Move repetitive/internal logs to DEBUG. Reduce noisy third-party INFO logs from `httpx` and APScheduler if needed. Never log tokens, API keys, `DATABASE_URL`, raw `.env` values, or private Telegram text.

## Health check
`/health` is for monitoring only.

It should return JSON with `status`, `uptime_seconds`, and available state such as `last_btc_check_at`. If state lookup fails, return a safe degraded response. Never expose secrets, stack traces, or raw exceptions.

## Premium and payments
If working on Premium/Telegram Stars:
- BTC remains free unless explicitly changed.
- Manual `/price` remains free unless explicitly changed.
- Premium unlocks automatic non-BTC alerts.
- Store subscription/payment state in PostgreSQL.
- Keep price configurable where practical.
- Add admin/manual premium grant/revoke if useful for testing.
- Do not auto-enable non-BTC coins after purchase unless requested.
- If Premium expires, keep non-BTC choices in DB, block non-BTC deliveries, and restore them after renewal.
- If Telegram Stars recurring support is unclear, investigate and document it before implementing.

## Code style
Keep changes focused and safe. Prefer small helpers, clear names, explicit boundaries, and behaviour tests.

Avoid unrelated rewrites, risky file moves, and unused abstractions. Do not rename `ai_agent_groq.py` unless explicitly requested. `python main.py` and Docker Compose startup must keep working.

## Documentation
Update docs when setup, config, commands, dependencies, architecture, or behaviour changes.

Relevant files: `README.md`, `docs/development.md`, `.env.example`, PR description.

## Verification
Default checks:

```bash
python -m py_compile main.py config.py database.py storage.py alert_rules.py price_service.py news_service.py ai_agent_groq.py health.py
ruff check .
python -m pytest tests/ -v
docker compose config
```

If Docker Compose changes, run `docker compose config`. Do not claim manual Telegram/runtime verification unless it was actually performed.

## Git and PR workflow
Never commit directly to `main`.

For every task:
1. Create a focused branch from `main`.
2. Make only relevant changes.
3. Run verification.
4. Commit.
5. Push.
6. Create a GitHub PR against `main`.

A task is not complete until a GitHub PR exists, or you clearly explain why it could not be created.

Do not auto-merge PRs, delete user work, or include generated/cache files.

Never commit `.env`, `state.json`, `.venv`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.ruff_cache/`, `pytest-cache-files-*/`, `*.db`, `*.sqlite`, or database volumes.

## PR follow-through
After creating a PR, monitor CI when possible.

If CI fails:
1. Inspect failing logs.
2. Identify the minimal fix.
3. Fix the same branch.
4. Run relevant checks.
5. Push the fix.
6. Wait for CI again.

Repeat until CI is green or user input is required. Do not merge PRs. Do not change unrelated behaviour while fixing CI.

## PR description
Every PR must include summary, files changed, behaviour confirmation, database/schema confirmation, verification performed, manual verification status, protected files changed and why, and known limitations/follow-ups.

For sensitive changes, also confirm alert scope, recipient delivery behaviour, LLM call placement, payment/subscription impact, and no secrets exposed.

## Protected files
Treat these carefully: `docker-compose.yml`, `.env.example`, `requirements.txt`, `requirements-dev.txt`, `README.md`.

Modify only when required and explain why. `docker-compose.yml` must keep top-level `services:`. Never place `postgres:` at top level.

## When unsure
Prefer the smallest safe change. If a task is too large, split it into focused PRs. If requirements conflict, stop and explain. If external service support is unclear, investigate before implementing.
