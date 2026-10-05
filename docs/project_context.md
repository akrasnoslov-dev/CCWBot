# Project Context

CCWBot is a Python Telegram bot for crypto price checks, reports, Premium watchlists, onboarding,
growth attribution, and automatic Event Alerts.

Runtime stack:
- Python Telegram Bot API
- Groq/OpenAI-compatible LLM calls
- CoinGecko prices
- RSS/news services
- PostgreSQL with async SQLAlchemy, asyncpg, and Alembic
- Docker Compose
- `/health` monitoring endpoint

Core invariant:

```text
1 coin market event = 1 AI analysis = many alert deliveries
```

Never place provider/LLM calls inside recipient loops.

## Permanent guardrails

- Do not change Event Alert business logic unless explicitly requested.
- Keep runtime integrations free-tier / zero-cost where practical. Do not make a paid external
  service a requirement without owner approval.
- Do not change Premium, watchlist, subscription, payment, trial, or grant/revoke behavior unless
  explicitly requested.
- Never expose raw JSON, stack traces, DB internals, secrets, tokens, Telegram IDs, payment IDs, or
  diagnostic internals in user-facing Telegram messages.
- Never commit secrets, local env files, logs, generated reports, DB dumps, caches, or local state.
- Production forensic SQL uses the read-only `ccwbot_investigator` role through the approved SSH
  tunnel.

## Current product behavior

- Supported runtime symbols: BTC, ETH, GRAM, SOL. Legacy `/price ton` maps to GRAM.
- BTC automatic alerts are free. Non-BTC automatic alerts require an enabled watchlist choice plus
  active Premium/trial entitlement.
- New-user onboarding provides an instant cached brief and a coin-customisation path.
- Selecting Premium coin intent can activate the one-time 7-day Premium trial.
- Growth analytics and first-touch acquisition attribution are persisted with allowlisted events.
- Telegram Stars Premium remains 199 Stars/month.
- Payment handling is idempotent and enriches the user's Premium/watchlist state after successful
  payment.
- `/reports`, `/dailyreport`, and `/weeklyreport` are available to all users.
- `/settings` is admin-only. `/userid` works manually but stays hidden from menus/help.

## Event Alerts

- Detection is global for BTC, ETH, GRAM, and SOL. Recipient eligibility is checked only after a
  significant market event exists.
- Market context is primary. News is supporting context. Standalone news-only Event Alerts are
  disabled by the product contract.
- No deterministic numeric threshold may create, reject, suppress, or bypass an Event Alert.
- Exact Context Reuse is allowed only when the canonical semantic analysis input is unchanged.
- Significance is decided by schema-validated LLM output.
- The same canonical event key or semantic family is suppressed for four hours per recipient.
- CoinGecko automatic market data keeps full source precision through analysis; user-facing
  formatting is separate.
- Alert text must remain cautious and include `Not financial advice.` where applicable.

Detailed Event Alert flow: `docs/alert_logic.md`.
Growth/attribution contract: `docs/product_analytics.md`.
Report contract: `docs/market_reports.md`.

Repository authority is defined in `docs/source_of_truth.md`.
