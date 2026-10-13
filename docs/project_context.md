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

## Manual command UX and price lookups

- Manual commands in private Telegram chats produce dismissible, transient bot replies.
  **Close** dismisses every bot message belonging to that command result, including
  associated text and document exports. Starting another manual command cleans up the
  previous result on a best-effort basis; automatic Event Alerts, scheduled reports,
  payments and proactive messages are never included in that cleanup.
- Navigating a manual inline menu should edit the current message and preserve
  **Back** to its actual parent. Direct admin-only `/settings` has a standalone
  **Close** root, while settings reached from `/admin` return to Admin.
- Manual `/price` uses the configured 300-second per-symbol CoinGecko cache and
  must not impose a separate UI cooldown. Concurrent uncached requests for the
  same coin share one in-flight refresh. The result offers **Change coin** and
  **Close**. Expired prices must never be shown as current if refresh fails.
- The supported manual symbols remain BTC, ETH, GRAM and SOL (legacy `ton` maps
  to GRAM). Price cache and screen behavior never change automatic market-alert
  precision or eligibility.

## Market Heartbeat

- A heartbeat is a fallback after **24 consecutive hours of silence**, independently for each
  user and enabled coin (BTC, ETH, GRAM, SOL). Delivery on the next scheduled check is acceptable;
  delivery before 24 hours is forbidden.
- Any successfully delivered automatic alert for that user and coin, including an Event Alert
  or heartbeat, restarts the clock. Failed, pending, suppressed and generated-only alerts do not.
  `alerts.sent_at` records completion after retries; `created_at` remains reservation time.
- With no successful delivery history, the baseline is the latest of persisted user creation,
  watchlist activation/update and the earliest currently active entitlement update/start time.
  Entitlement updates can conservatively delay a first non-BTC heartbeat on renewal. Missing
  activation evidence fails closed. Repeating an unchanged watchlist choice does not reset its
  activation timestamp. Eligibility and watchlist selection remain required at send time.
- BTC remains free; non-BTC still requires active Premium/trial and an enabled watchlist choice.
  Event Alert significance and semantic cooldown are independent of heartbeat timing.
- No heartbeat frequency setting exists. The deprecated `users.alert_frequency_seconds` column
  remains for compatibility/data preservation and has no effect on delivery.
- Hourly generation uses one shared analysis/cache per due coin and skips provider work when no
  recipient needs a heartbeat. Recipients receive only fresh completed cached heartbeats.
- Automatic sends are serialized per user and coin across workers with PostgreSQL transaction
  advisory locks. Heartbeat eligibility is checked again under the lock, which spans retries and
  successful-delivery persistence. Existing delivery identities still prevent repeat sends.
  Telegram acceptance followed by a process crash before persistence retains the existing
  transport limitation: Telegram does not supply an idempotency key for `sendMessage`.

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
