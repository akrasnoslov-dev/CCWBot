# CLAUDE.md

## Project
CCWBot / CryptoCurrencyWatcherBot (`akrasnoslov-dev/CCWBot`).

Stack: Python Telegram Bot API, Groq/OpenAI-compatible LLM, CoinGecko, RSS/news, PostgreSQL, async SQLAlchemy + asyncpg, Alembic, Docker Compose, CI, `/health`.

Core invariant:

```text
1 coin market event = 1 AI analysis = many alert deliveries
```

Never put LLM/Groq calls inside a recipient loop.

## How This Project Is Actually Run
- Andrei is a product/project manager and vibe coder, not a professional developer. He plans,
  reviews, and approves work in Claude Desktop chat; Claude Code performs the actual
  implementation, tests, and PR creation.
- When Claude Code finishes a task, assume Andrei will ask Claude (Desktop) to review the diff/PR
  before merging — keep PR descriptions and diffs reviewable by a non-developer: explain *what*
  changed and *why* in plain terms, not just code.
- Do not assume deep familiarity with framework internals; when a design choice is non-obvious,
  say so briefly in the PR description instead of assuming it's understood.

## Default Claude Code Workflow
- Read required context first: `CLAUDE.md` (this file), `AGENTS.md` (legacy, still authoritative
  for product rules), `docs/codex_instructions.md`, `docs/project_context.md`, and
  `agents/routing.toml`.
- Check for project skills under `.claude/skills/` and any installed plugins before starting
  non-trivial work. If no skill applies, say so explicitly in the final response/PR body.
- Check branch and worktree status before edits.
- Work from `dev` or a focused branch based on `dev`; never work directly on `main`.
- Do not overwrite, revert, reformat, or delete uncommitted user work unless explicitly asked.
- Keep changes focused on the requested task.
- For every non-trivial task: write a short plan before editing, search repo-wide for affected
  concepts (not just the obvious file), add a regression test for every bug fix/behavior change
  unless genuinely not applicable, self-review the full diff, and write a `Self-review / risk
  check` section in the PR body before calling anything "ready".
- Open normal PRs against `dev`.
- Open `dev` -> `main` PRs only when explicitly asked for a production release.
- Use `docs/codex_task_prompt_template.md` as a template for short task prompts.

## Product Rules
- Do not change product behaviour unless explicitly asked.
- Do not change Event Alert business logic unless explicitly asked.
- Do not change Premium, watchlist, subscription, payment, or grant/revoke behaviour unless explicitly asked.
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
- Create and verify backups before destructive database operations.
- Never log secrets or connection strings.

## Telegram UX
- Keep admin-only commands protected.
- Keep messages concise and clear.
- Do not expose raw JSON, stack traces, DB internals, secrets, tokens, Telegram IDs, payment IDs, or debug fields.
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

## Ops-Agent and Reports
- Ops-agent/report PRs are observability-only unless the task explicitly asks for runtime changes.
- Keep ops-agent collectors isolated, read-only where applicable, and sanitized.
- If a collector fails, keep later collectors running and make the partial report list failed collectors in `Collector Status`.
- Treat missing or `unknown` evidence as incomplete, not healthy.
- Do not paste or commit raw bundles, generated reports, logs, Telegram text, IDs, payment IDs, secrets, DB URLs, or raw JSON evidence.
- After ops-agent code changes, production deploy requires explicitly rebuilding the `ops-agent` Docker image.

## Sub-Agents / Review Lenses
These review lenses exist as native Claude Code subagents under `.claude/agents/` (committed to
the repo, so every session gets the same set). Claude Code delegates to them automatically based
on their descriptions, or explicitly via the Agent tool. They are not runtime Telegram bot agents
and are not imported by `main.py` or `bot/`. The original Codex TOML configs in `agents/*.toml`
(routing in `agents/routing.toml`) remain in place for Codex and were the source these subagents
were derived from; for Claude Code, the `.claude/agents/*.md` files are the operative definitions.

- `architecture-guardian`: cross-cutting design and the one-event/one-analysis/many-deliveries invariant.
- `security-review`: authorization, secrets, privacy, logging, payment abuse, and user-controlled data exposure.
- `code-quality`: maintainability, async boundaries, error handling, logging levels, and focused refactors.
- `test-ci`: regression coverage, validation commands, and CI confidence (may run verification via Bash).
- `product-policy`: Telegram command access, alert wording, premium/free UX, and product-rule consistency.
- `market-pipeline`: CoinGecko/news/LLM payloads, event detection, delivery flow, and rate-limit handling.
- `db-migration-guardian`: PostgreSQL, async SQLAlchemy, Alembic, persistence contracts, and data integrity.
- `telegram-stars-payments`: Premium, Telegram Stars, subscription expiry, grants/revokes, and payment idempotency.
- `devops-release`: Docker, CI, config, health monitoring, dependencies, and release safety (may run verification via Bash).

Review lenses are read-only (Read/Grep/Glob) except `test-ci` and `devops-release`, which may
also run verification commands. Note in the PR which lenses ran and what they found.

Mandatory lens examples:
- Security-sensitive changes: `security-review`.
- Database/schema changes: `db-migration-guardian`.
- Alert/report logic changes: `architecture-guardian`, `market-pipeline`, `product-policy`.
- LLM prompt or output format changes: `architecture-guardian`, `market-pipeline`, `product-policy`.
- Production/debugging tasks: `devops-release`, `security-review`.
- Refactors affecting multiple modules: `architecture-guardian`, `code-quality`, `test-ci`.
- Changes that may increase API/token usage or rate-limit pressure: `architecture-guardian`, `market-pipeline`, `test-ci`.
- Premium/payment changes: `telegram-stars-payments`, `security-review`, `product-policy`.

Optional: typo-only doc fixes, comment-only clarifications, narrow formatting-only changes after
confirming no behaviour changed.

## Safe Changes
- Keep changes focused and safe.
- Prefer small helpers, clear names, explicit boundaries, and behaviour tests.
- Avoid unrelated rewrites, risky file moves, unused abstractions, and product changes.
- Do not rename `ai_agent_groq.py` unless explicitly requested.
- `python main.py` and Docker Compose startup must keep working.
- Update docs when setup, config, commands, dependencies, architecture, or behaviour changes.
- Keep project and process documentation under `docs/`. Root `README.md` is the public entry
  point; root `AGENTS.md` and `CLAUDE.md` stay at the repository root for agent tooling. Subtree
  README.md files are acceptable when they document only that local tool or package directory.

## Verification
Default checks:

```bash
python -m py_compile main.py bot/config.py bot/storage.py bot/health.py bot/alerting/alert_rules.py bot/alerting/alert_severity.py bot/db/database.py bot/domain/premium.py bot/domain/supported_coins.py bot/services/price_service.py bot/services/news_service.py bot/services/ai_agent_groq.py
ruff check .
python -m pytest tests/ -v -ra --durations=20
docker compose config >/dev/null
```

If Docker Compose changes, run `docker compose config >/dev/null`. Do not publish Compose config output from a real `.env`, and do not claim manual Telegram/runtime verification unless it was actually performed.

For ops-agent code or reporting changes, add focused checks under `tests/ops_agent/` when
behaviour changes and run the relevant subset, for example:

```bash
python -m pytest tests/ops_agent/ -v -ra
```

When PostgreSQL is available and ops-agent DB queries changed, run the PostgreSQL query-contract
test documented in `docs/development.md`.

## Environments
- Local development runs on the developer PC from `dev` or a feature branch based on `dev`.
- Production runs on the Hetzner VPS from `main` only, at `/opt/CCWBot`.
- Local development uses a development Telegram bot token in the local `.env`.
- Production uses a separate production Telegram bot token in the VPS `.env`.
- Local development uses local Docker PostgreSQL; production uses server Docker PostgreSQL.
- `.env` files are environment-local and must never be committed.
- Never use the production bot token locally.
- Never overwrite the production `.env`.
- Never edit tracked production files manually on the VPS. Production tracked-file changes must come through Git.
- Test migrations locally before production.
- Create and verify backups before destructive database operations.

## Production Safety Rules
- Never work directly in `main` locally. Use `dev` or a focused branch based on `dev`.
- Production runs `main` only; `dev` and feature branches are not deployed to the VPS.
- Keep production deploys reproducible through Git and Docker Compose only.
- Never commit `.env` files, real secrets, database dumps, or local state files.
- Never use the production Telegram bot token locally.
- Never manually edit tracked production files on the VPS; commit changes and deploy from Git.
- Never overwrite the production `.env`.
- Test database migrations locally before production.
- Verify a current backup before destructive database operations.
- After every deploy, check `docker compose ps`, bot logs, and basic Telegram functionality.

## Branching and PR Workflow
- `dev` is the default branch for local development and feature work.
- Start work from `dev` or from a focused feature branch based on `dev`.
- Never commit directly to `main`.
- Claude Code should create Pull Requests automatically for normal tasks.
- Default PR target/base branch is `dev`, not `main`.
- Only open PRs against `main` when explicitly asked for a production release or a `dev` -> `main` merge.
- `main` is production/stable and must stay deployable.
- Do not auto-merge PRs, delete user work, or include generated/cache files.

## Git and PR Workflow
For every task:
1. Create a focused branch from `dev`.
2. Make only relevant changes.
3. Run verification.
4. Commit.
5. Push.
6. Create a GitHub PR against `dev` unless explicitly asked to release production or merge `dev` into `main`.

Never commit `.env`, `.ops-agent.env`, logs, generated reports, DB dumps, `state.json`, `.venv`,
`__pycache__/`, `*.pyc`, `.pytest_cache/`, `.ruff_cache/`, `pytest-cache-files-*/`, `*.db`,
`*.sqlite`, database volumes, local state, or secrets.

## Production Deployment Workflow
- Production updates happen through Git only.
- After `dev` is validated, merge `dev` into `main`, then update the VPS from `main`.
- Do not edit tracked files directly under `/opt/CCWBot` on the VPS.
- Do not overwrite the production `.env`; update it manually only when the deployment explicitly requires an environment variable change.
- For migrations, test locally first and confirm a current backup exists before running against production.

Production server update flow:

```bash
cd /opt/CCWBot
git checkout main
git pull
docker compose up -d --build
docker compose ps
docker compose logs -f
```

## PR Description
Every PR must include summary, files changed, behaviour confirmation, database/schema confirmation, verification performed, manual verification status, protected files changed and why, and known limitations/follow-ups.

For sensitive changes, also confirm alert scope, recipient delivery behaviour, LLM call placement, payment/subscription impact, and no secrets exposed.

## Protected Files
Treat these carefully: `docker-compose.yml`, `.env.example`, `requirements.txt`, `requirements-dev.txt`, `README.md`.

Modify protected files only when required and explain why. `docker-compose.yml` must keep top-level `services:`. Never place `postgres:` at top level.

## When Unsure
Prefer the smallest safe change. If a task is too large, split it into focused PRs. If requirements conflict, stop and explain. If external service support is unclear, investigate before implementing.
