# AGENTS.md

## Project
CCWBot / CryptoCurrencyWatcherBot (`akrasnoslov-dev/CCWBot`).

Stack: Python Telegram Bot API, Groq/OpenAI-compatible LLM, CoinGecko, RSS/news, PostgreSQL, async SQLAlchemy + asyncpg, Alembic, Docker Compose, CI, `/health`.

Core invariant:

```text
1 coin market event = 1 AI analysis = many alert deliveries
```

Never put LLM/Groq calls inside a recipient loop.

## Default Codex Workflow
- Read required context first: `AGENTS.md`, `docs/codex_instructions.md`,
  `docs/project_context.md`, and `agents/routing.toml`.
- Check installed skills before edits: inspect user skills under
  `C:\Users\Loki\.codex\skills\` and `C:\Users\Loki\.agents\skills\`, plus
  project-copied skills under `.agents/skills/` when present.
- Read each relevant skill instruction file (`SKILL.md`, `README.md`, or equivalent) and apply
  every relevant installed skill for the task.
- If no installed skill applies, state that explicitly in the final response and PR body.
- For documentation work, use `documentation-writer` for general docs and `agents-md` for
  agent-facing instructions such as `AGENTS.md` and Codex workflow docs.
- Check branch and worktree status before edits.
- Work from `dev` or a focused branch based on `dev`; never work directly on `main`.
- Do not overwrite, revert, reformat, or delete uncommitted user work unless explicitly asked.
- Keep changes focused on the requested task.
- For every non-trivial task, follow the mandatory implementation and PR-readiness workflow in
  `docs/codex_instructions.md`: plan before edits, search affected concepts, add regression tests
  when applicable, self-review the full diff, update PR risk notes, and verify review/check status.
- Open normal PRs against `dev`.
- Open `dev` -> `main` PRs only when explicitly asked for a production release.
- Use `docs/codex_task_prompt_template.md` for short future task prompts.

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

## Available Agents
Codex task-review agents live in `agents/*.toml`; routing rules live in
`agents/routing.toml`. These are not runtime Telegram bot agents and are not imported by
`main.py` or `bot/`. The runtime LLM service remains `bot/services/ai_agent_groq.py`.

Claude Code review-lens agents also live in `.claude/agents/*.md`. They are development tooling
only, derived from the Codex TOML agents, and are not imported by runtime code.

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
- Before starting any non-trivial task, check whether `agents/routing.toml` requires one or more agents.
- If agents are relevant, use them through Codex subagent/delegation support when available. If that support is unavailable, apply the relevant TOML instructions manually and state that in the PR description.
- Do not silently skip required agents for high-risk areas. If a required agent is not used, explain why before or in the PR description.
- For production-impacting changes, use `architecture_guardian` plus the required domain agents from `agents/routing.toml`.
- Use `security_review_agent`, `code_quality_agent`, and `test_ci_agent` for broad repository reviews.
- Use `db_migration_guardian` for persistence/schema changes.
- Use `market_pipeline_agent` for price, news, alert, and delivery changes.
- Use `telegram_stars_payments_agent` for Premium, subscriptions, grants/revokes, and billing state.
- Use `product_policy_agent` for command behavior, menus/help, and user-visible copy.
- Use `devops_release_agent` for Docker, CI, config, health, dependencies, and deployment docs.
- If no agent is relevant, state why in the PR description.

## Installed Codex Skills
Codex skills are developer tooling only and are not imported by `main.py` or `bot/`.
They can be installed as user-level skills or project-copied skills:

- Local user skills live under `C:\Users\Loki\.codex\skills\`.
- Additional user skills may live under `C:\Users\Loki\.agents\skills\`.
- Project-copied skills live under `.agents/skills/` when present and may be pinned by
  `skills-lock.json`.

- `documentation-writer`: use for general documentation quality, structure, README/docs guides,
  references, and explanations.
- `agents-md`: use for `AGENTS.md`, Codex-facing instructions, and agent workflow docs.
- `supabase-postgres-best-practices`: use when writing, reviewing, or optimizing PostgreSQL
  queries, schema designs, indexes, connection handling, RLS/security, or database performance.
  This complements `db_migration_guardian`; it does not replace required routing agents.
- `requesting-code-review`: use after completing major features or subagent-driven tasks, and
  before merge/PR finalization when review support is available. For this project, combine it
  with the required agents from `agents/routing.toml`.

See `docs/codex_skills.md` for locations and usage notes.

Mandatory agent examples:

- Security-sensitive changes: `security_review_agent`.
- Database/schema changes: `db_migration_guardian`.
- Alert/report logic changes: `architecture_guardian`, `market_pipeline_agent`, and `product_policy_agent`.
- LLM prompt or output format changes: `architecture_guardian`, `market_pipeline_agent`, and `product_policy_agent`.
- Production/debugging tasks: `devops_release_agent` and `security_review_agent`.
- Refactors affecting multiple modules: `architecture_guardian`, `code_quality_agent`, and `test_ci_agent`.
- Changes that may increase API usage, token usage, or rate-limit pressure: `architecture_guardian`, `market_pipeline_agent`, and `test_ci_agent`.

Optional agent examples:

- Typo-only documentation fixes.
- Comment-only clarifications that do not change behaviour.
- Narrow formatting-only changes after verifying no code or workflow behaviour changed.

## Safe Changes
- Keep changes focused and safe.
- Prefer small helpers, clear names, explicit boundaries, and behaviour tests.
- Avoid unrelated rewrites, risky file moves, unused abstractions, and product changes.
- Do not rename `ai_agent_groq.py` unless explicitly requested.
- `python main.py` and Docker Compose startup must keep working.
- Update docs when setup, config, commands, dependencies, architecture, or behaviour changes.
- Keep project and process documentation under `docs/`. Root `README.md` is the public entry
  point, while root `AGENTS.md` and `CLAUDE.md` stay at the repository root for agent tooling.
  Subtree README.md files are acceptable when they document only that local tool or package
  directory.

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
- Production runs on the Hetzner VPS from `main` only.
- Production project path is `/opt/CCWBot`.
- Local development uses a development Telegram bot token in the local `.env`.
- Production uses a separate production Telegram bot token in the VPS `.env`.
- Local development uses local Docker PostgreSQL.
- Production uses server Docker PostgreSQL.
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
- `dev` is the default branch for local development, Codex tasks, and feature work.
- Start work from `dev` or from a focused feature branch based on `dev`.
- Never commit directly to `main`.
- Codex should continue creating Pull Requests automatically for normal tasks.
- Default PR target/base branch is `dev`, not `main`.
- Open PRs against `dev` by default.
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

Operational deploy checklist:

1. Verify the local release branch and VPS environment are correct.
2. Pull the latest `main` on the VPS.
3. Run `docker compose up -d --build`.
4. Check container health with `docker compose ps`.
5. Check bot logs with `docker compose logs -f`.
6. Verify basic bot functionality in Telegram.

## PR Description
Every PR must include summary, files changed, behaviour confirmation, database/schema confirmation, verification performed, manual verification status, protected files changed and why, and known limitations/follow-ups.

For sensitive changes, also confirm alert scope, recipient delivery behaviour, LLM call placement, payment/subscription impact, and no secrets exposed.

## Protected Files
Treat these carefully: `docker-compose.yml`, `.env.example`, `requirements.txt`, `requirements-dev.txt`, `README.md`.

Modify protected files only when required and explain why. `docker-compose.yml` must keep top-level `services:`. Never place `postgres:` at top level.

## When Unsure
Prefer the smallest safe change. If a task is too large, split it into focused PRs. If requirements conflict, stop and explain. If external service support is unclear, investigate before implementing.
