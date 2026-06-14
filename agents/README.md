# CCWBot Codex subagents

Codex task-review subagent definitions live here in TOML format. These files are not loaded by
the Telegram bot at runtime; they guide Codex planning, implementation review, and PR checks.
Keep each agent focused on a review area with actionable blocking criteria and concise
deliverables.

Routing rules live in `agents/routing.toml`. Before starting any non-trivial task, Codex must
check those rules, use the required agents when relevant, or explicitly explain why a relevant
agent was not used. High-risk areas must not skip agents silently.

Local Codex skills are separate from these project agents and live under
`C:\Users\Loki\.codex\skills\`. Use `supabase-postgres-best-practices` for PostgreSQL best
practices and `requesting-code-review` for review checkpoints when relevant, but still follow
the mandatory routing rules below. See `docs/codex_skills.md`.

Current agents:

- `architecture_guardian`: cross-cutting design and the one-event/one-analysis/many-deliveries invariant.
- `security_review_agent`: authorization, secrets, privacy, logging, payment abuse, and user-controlled data exposure.
- `code_quality_agent`: maintainability, async boundaries, error handling, logging levels, and focused refactors.
- `test_ci_agent`: regression coverage, validation commands, and CI confidence.
- `product_policy_agent`: Telegram command access, alert wording, premium/free UX, and product-rule consistency.
- `market_pipeline_agent`: CoinGecko/news/LLM payloads, event detection, delivery flow, and rate-limit handling.
- `db_migration_guardian`: PostgreSQL, async SQLAlchemy, Alembic, persistence contracts, and data integrity.
- `telegram_stars_payments_agent`: Premium, Telegram Stars, subscription expiry, grants/revokes, and payment idempotency.
- `devops_release_agent`: Docker, CI, config, health monitoring, dependencies, and release safety.

Mandatory routing summary:

- Security-sensitive changes: `security_review_agent`.
- Database/schema changes: `db_migration_guardian`.
- Alert/report logic changes: `architecture_guardian`, `market_pipeline_agent`, and `product_policy_agent`.
- LLM prompt/output changes: `architecture_guardian`, `market_pipeline_agent`, and `product_policy_agent`.
- Production/debugging tasks: `devops_release_agent` and `security_review_agent`.
- Multi-module refactors: `architecture_guardian`, `code_quality_agent`, and `test_ci_agent`.
- API, token, or rate-limit pressure changes: `architecture_guardian`, `market_pipeline_agent`, and `test_ci_agent`.
- Premium/payment changes: `telegram_stars_payments_agent`, `security_review_agent`, and `product_policy_agent`.

Simple typo fixes, comment-only changes, and narrowly scoped docs edits may skip subagents after
an explicit agent relevance check.
