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

Current product behavior:

- Manual `/price` supports the active runtime symbols: `btc`, `eth`, `ton`, and `sol`.
  Internal `ton` is user-facing GRAM; `/price gram` and legacy `/price ton` both work.
- BTC automatic alerts remain free.
- Non-BTC automatic alerts require active Premium and enabled watchlist choices.
- `/reports`, `/dailyreport`, and `/weeklyreport` are available to all users.
- `/settings` is admin-only.
- `/userid` works manually but stays hidden from menus/help.
- Alert copy must stay cautious and include `Not financial advice.` where applicable.

Primary context files:

- `AGENTS.md`
- `docs/README.md`
- `docs/codex_instructions.md`
- `docs/release_checklist.md`
- `docs/dev_ops_guide.md`
- `README.md`
- `docs/development.md`
- `docs/codex_agent_workflow.md`
- `docs/observability.md`
- `docs/llm_usage.md`
- `docs/ops_agent_service.md`
