# Project Context

CCWBot is a Python Telegram bot for crypto price checks, reports, Premium watchlists, and
automatic Event Alerts.

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

Do not place LLM/Groq calls inside recipient loops.

Permanent guardrails:

- Do not change Event Alert business logic unless explicitly requested.
- Do not change Premium, watchlist, subscription, payment, or grant/revoke behavior unless
  explicitly requested.
- Do not expose raw JSON, stack traces, DB internals, secrets, tokens, Telegram IDs, payment IDs,
  or diagnostic internals in user-facing Telegram messages.
- Do not commit `.env`, `.ops-agent.env`, logs, generated reports, DB dumps, caches, local state,
  or secrets.
- Production forensic SQL investigations use the dedicated read-only `ccwbot_investigator`
  role through an SSH tunnel. Lack of table `SELECT` permission is an access-provisioning gap,
  not a reason to switch to the application/admin DB role.

Current product behavior:

- Manual `/price` supports the active runtime symbols: `btc`, `eth`, `gram`, and `sol`.
  GRAM is the primary backend/product symbol; legacy `/price ton` still works as an alias.
- BTC automatic alerts remain free.
- Non-BTC automatic alerts require active Premium and enabled watchlist choices.
- Event Alerts are market-event-first: analysed-window market context is the primary basis,
  and news is supporting context only. Standalone news-only Event Alerts are disabled.
- Event Alerts use conservative pre-LLM similar-context reuse inside the semantic cooldown window.
  The reuse key is built from sanitized stable market/news context, not raw prompts, raw outputs,
  timestamps, user ids, or arbitrary hard movement-threshold gates.
- New news alone cannot allow a same-family repeat inside semantic cooldown; a repeat must have
  market-context escalation such as higher urgency or materially changed analysed-window movement.
- Event Alert `Possible action` stays in alert copy and is observed for quality; generic wording
  is not a suppression gate.
- `/reports`, `/dailyreport`, and `/weeklyreport` are available to all users.
- `/settings` is admin-only.
- `/userid` works manually but stays hidden from menus/help.
- Alert copy must stay cautious and include `Not financial advice.` where applicable.

Repository authority and ownership are defined in `docs/source_of_truth.md`.

This file is the canonical owner for product behavior, product boundaries, and architecture
invariants. Workflow, release, operational, and agent-routing rules belong to their canonical
owners and should be linked rather than repeated here.
