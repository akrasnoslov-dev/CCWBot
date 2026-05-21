# Codex Agent Workflow

CCWBot has two separate agent concepts:

- Runtime LLM service: `bot/services/ai_agent_groq.py`, used by the Telegram bot for market
  analysis, reports, and alert text.
- Codex task-review subagents: `agents/*.toml`, used during repository work for specialised
  review, planning, and risk checks.

The Telegram bot does not load `agents/*.toml` at runtime. Those files are a durable Codex
workflow contract.

## Current Agents

- `architecture_guardian`: cross-cutting design and the one-event/one-analysis/many-deliveries invariant.
- `security_review_agent`: authorization, secrets, privacy, logging, payment abuse, and user-controlled data exposure.
- `code_quality_agent`: maintainability, async boundaries, error handling, logging levels, and focused refactors.
- `test_ci_agent`: regression coverage, validation commands, and CI confidence.
- `product_policy_agent`: Telegram command access, alert wording, premium/free UX, and product-rule consistency.
- `market_pipeline_agent`: CoinGecko/news/LLM payloads, event detection, delivery flow, and rate-limit handling.
- `db_migration_guardian`: PostgreSQL, async SQLAlchemy, Alembic, persistence contracts, and data integrity.
- `telegram_stars_payments_agent`: Premium, Telegram Stars, subscription expiry, grants/revokes, and payment idempotency.
- `devops_release_agent`: Docker, CI, config, health monitoring, dependencies, and release safety.

## Routing Rules

Detailed routing lives in `agents/routing.toml`. Before starting any non-trivial task, Codex
must check that file and decide which agents apply.

Agents are mandatory for:

- Security-sensitive changes.
- Database or schema changes.
- Alert or report logic changes.
- LLM prompt, model setting, or output format changes.
- Production debugging, deployment, CI, health, or log analysis.
- Refactors affecting multiple modules or shared boundaries.
- Changes that may increase API calls, LLM calls, token usage, or rate-limit pressure.
- Premium, Telegram Stars, subscription, grant/revoke, or payment-idempotency changes.

If Codex subagent/delegation support is available, use it for the required agents. If not,
Codex must read and apply the relevant `agents/*.toml` instructions manually and state that in
the PR description. High-risk areas must not skip required agents silently.

## Mandatory Examples

- Changing Event Alert recipient selection requires `architecture_guardian`,
  `market_pipeline_agent`, and `product_policy_agent`.
- Editing `bot/services/ai_agent_groq.py` prompts requires `architecture_guardian`,
  `market_pipeline_agent`, and `product_policy_agent`; add `test_ci_agent` for prompt/output
  tests and `security_review_agent` when user-visible text or diagnostics change.
- Adding an Alembic migration requires `db_migration_guardian` and `test_ci_agent`.
- Changing `/settings`, `/status`, `/grantpremium`, or `/revokepremium` requires
  `security_review_agent` and `product_policy_agent`.
- Changing Docker, CI, health, `.env.example`, or release docs requires
  `devops_release_agent`; add `security_review_agent` when secrets or diagnostics are involved.
- Changing CoinGecko polling, RSS fetches, or LLM call frequency requires
  `architecture_guardian`, `market_pipeline_agent`, and `test_ci_agent`.

## Optional Examples

Agents are optional after an explicit relevance check for:

- Typo-only documentation changes.
- Comment-only clarifications.
- Narrow formatting-only edits.
- Updating test names without changing tested behaviour.

## PR Notes

Every PR description should include one of:

- Agents used: list the relevant agents and their findings.
- Agents not used: explain why the task was trivial or why subagent support was unavailable.

For sensitive changes, also confirm alert scope, recipient delivery behaviour, LLM call
placement, payment/subscription impact, and no secrets exposed.
