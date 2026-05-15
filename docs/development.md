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
python -m py_compile main.py bot/config.py bot/storage.py bot/health.py bot/alerting/alert_rules.py bot/alerting/alert_severity.py bot/db/database.py bot/domain/premium.py bot/domain/supported_coins.py bot/services/price_service.py bot/services/news_service.py bot/services/ai_agent_groq.py
ruff check .
python -m pytest tests/ -v
docker compose config >/dev/null
```

These checks do not require real Telegram, Groq, CoinGecko, or PostgreSQL calls.
Use dummy values from `.env.example` for Compose validation. Do not publish
`docker compose config` output generated from a real `.env`, because Compose can expand secrets.

## Runtime Notes

- `python main.py` remains the local bot entry point.
- Docker Compose starts PostgreSQL and the bot, and the bot runs Alembic migrations on startup.
- Docker Compose overrides `DATABASE_URL` for the bot container to use the `postgres` service.
- PostgreSQL is the primary store when `DATABASE_URL` is configured.
- Migration `0007_unique_telegram_user_id` blocks startup if duplicate Telegram users already
  exist. Merge duplicates before applying it.
- Local `state.json` is a fallback only and must not be committed.
- Automatic alerts use global multi-coin polling. BTC is free; enabled non-BTC watchlist
  alerts require active Premium.
- Manual `/price` checks support `btc`, `eth`, `sol`, `xrp`, `bnb`, `doge`, `ada`,
  `ton`, `link`, and `trx`. `usdt` is not supported.
- `/watchlist` and `/myplan` use PostgreSQL-backed Premium/watchlist state when
  `DATABASE_URL` is configured.
- `/subscribe` creates a Telegram Stars invoice link for a recurring Premium subscription.
  The price is `PREMIUM_MONTHLY_STARS` (default `199`), currency is `XTR`, and the period is
  30 days / `2592000` seconds. Active Premium means paid access exists until `active_until`;
  it does not prove the Telegram recurring subscription is still active. CCWBot does not
  reliably track Telegram recurring subscription active/cancelled status, so users manage
  recurring payments in Telegram Stars settings. `/subscribe` can still create another invoice
  for users with active paid access, and a new payment extends access from the current paid
  access date.
- Premium unlocks automatic alerts for enabled non-BTC watchlist coins. BTC alerts and manual
  `/price` checks remain free. Non-BTC coins are not auto-enabled after payment; users choose
  them in `/watchlist`.
- `/grantpremium <telegram_user_id> <days>` and `/revokepremium <telegram_user_id>` are
  admin-only manual Premium controls for testing and support.
- Automatic alert threshold remains one global admin-controlled value for all coins.
- Saved non-BTC watchlist choices remain stored when Premium expires, but non-BTC deliveries
  are blocked until Premium is active again.
- Telegram Stars payments arrive on the bot's Stars balance. Withdrawal to TON wallet is handled
  outside CCWBot by the bot owner through Telegram/Fragment. CCWBot does not request or store
  wallet addresses, does not connect wallets, and does not automate payouts. Withdrawal
  availability, limits, exchange rate, fees, and regional restrictions are controlled by
  Telegram/Fragment and may change.
- Explicit subscription cancellation/refund events are not automated in this PR. Entitlement
  remains based on `user_premium_subscriptions.active_until > now` and naturally expires when
  renewals stop.
