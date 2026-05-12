# CCWBot subagents

Runtime subagent definitions live here in TOML format. Keep each agent focused on a review area with actionable blocking criteria and concise deliverables.

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
