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

Current product behavior:

- Manual `/price` supports the active runtime symbols: `btc`, `eth`, `ton`, and `sol`.
  Internal `ton` is user-facing GRAM; `/price gram` and legacy `/price ton` both work.
- BTC automatic alerts remain free.
- Non-BTC automatic alerts require active Premium and enabled watchlist choices.
- Event Alerts are market-event-first: analysed-window market context is the primary basis,
  and news is supporting context only. Standalone news-only Event Alerts are disabled.
- Event Alert `Possible action` stays in alert copy and is observed for quality; generic wording
  is not a suppression gate.
- `/reports`, `/dailyreport`, and `/weeklyreport` are available to all users.
- `/settings` is admin-only.
- `/userid` works manually but stays hidden from menus/help.
- Alert copy must stay cautious and include `Not financial advice.` where applicable.

Primary context files:

- `AGENTS.md`
- `docs/README.md`
- `docs/codex_instructions.md`
- `docs/codex_skills.md`
- `docs/release_checklist.md`
- `docs/dev_ops_guide.md`
- `README.md`
- `docs/development.md`
- `docs/codex_agent_workflow.md`
- `docs/observability.md`
- `docs/llm_usage.md`
- `docs/ops_agent_service.md`
- `docs/codex_task_prompt_template.md`
