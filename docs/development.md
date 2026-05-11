# Development

This project keeps the runtime install and developer tools separate:

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

Use `requirements.txt` for runtime dependencies and `requirements-dev.txt` for lint,
test, and type-check tooling.

## Local Checks

Run the same lightweight checks before opening a pull request:

```bash
python -m py_compile main.py config.py database.py storage.py alert_rules.py price_service.py news_service.py ai_agent_groq.py health.py
ruff check .
python -m pytest tests/ -v
docker compose config
```

These checks do not require real Telegram, Groq, CoinGecko, or PostgreSQL calls.

## Runtime Notes

- `python main.py` remains the local bot entry point.
- Docker Compose starts PostgreSQL and the bot, and the bot runs Alembic migrations on startup.
- PostgreSQL is the primary store when `DATABASE_URL` is configured.
- Local `state.json` is a fallback only and must not be committed.
- Automatic alerts remain BTC-only.
- Manual `/price` checks support `btc`, `eth`, `sol`, `xrp`, `bnb`, `doge`, `ada`,
  `ton`, `link`, and `trx`. `usdt` is not supported.
- `/watchlist` and `/myplan` use PostgreSQL-backed Premium/watchlist state when
  `DATABASE_URL` is configured.
- `/subscribe` is a placeholder only. Real Telegram Stars purchase handling is not implemented
  yet.
- `/grantpremium <telegram_user_id> <days>` and `/revokepremium <telegram_user_id>` are
  admin-only manual Premium controls.
- Automatic alerts remain BTC-only; saved non-BTC watchlist choices are for future delivery
  work.
