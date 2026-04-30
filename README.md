# CCWBot

CCWBot is a Telegram bot for tracking crypto prices and sending automatic **BTC movement alerts**. It supports quick manual price checks for multiple coins, plus admin controls for alert settings.

## Project overview

- Runs as a polling Telegram bot (`python-telegram-bot`).
- Checks BTC price every 60 seconds.
- Sends automatic alerts when BTC moves beyond a configurable threshold.
- Optionally enriches automatic alerts with AI-generated summaries and recent crypto news.

## Current features

- Manual `/price` lookup with button menu.
- Automatic BTC monitoring with cooldown logic.
- Admin-only alert configuration (`threshold`, `cooldown`) via commands and inline buttons.
- In-memory CoinGecko response caching for manual price checks.
- Persistent runtime state in local storage (`last price`, `last alert time`, settings overrides).

## Supported coins

- `btc`
- `eth`
- `ton`
- `usdt`

## Telegram commands and button menus

### User-visible commands

- `/start` — intro and available commands.
- `/price` — open coin button menu.
- `/price <symbol>` — fetch current USD price + 24h change.

### Admin-only commands

- `/settings` — open settings menu.
- `/status` — bot health + last saved BTC state.
- `/chatid` — show current chat ID (admin utility).
- `/setthreshold <percent>` — set alert trigger threshold.
- `/setcooldown <minutes>` — set alert cooldown.

### Hidden utility command

- `/userid` — returns your Telegram user ID (useful when configuring admin).

### Inline button menus

- **Price menu** (`/price`): `BTC`, `ETH`, `TON`, `USDT`
- **Settings menu** (`/settings`, admin only):
  - `Current settings`
  - `Set threshold` → `0.5%`, `1.0%`, `2.0%`
  - `Set cooldown` → `10 min`, `30 min`, `60 min`

## Admin policy

- `TELEGRAM_ADMIN_USER_ID` controls admin permissions.
  - Only this user can access admin commands and settings buttons.
- `TELEGRAM_CHAT_ID` controls where automatic alerts are delivered.
  - Automatic BTC alerts are sent to this chat ID.
- `/userid` is intentionally hidden from command menus and helps you discover your Telegram user ID.

## Environment variables

Create a `.env` file in the project root:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_target_chat_id_here
TELEGRAM_ADMIN_USER_ID=your_admin_user_id_here

GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-20b

PRICE_MOVE_ALERT_PERCENT=0.01
ALERT_COOLDOWN_MINUTES=2
```

### Notes

- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and `TELEGRAM_ADMIN_USER_ID` are required at startup.
- `TELEGRAM_ADMIN_USER_ID` should be your numeric Telegram user ID.
- `PRICE_MOVE_ALERT_PERCENT` is interpreted as a percent value in current behavior (default `0.01`).

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Then add your `.env` file.

## Run the bot

```bash
python main.py
```

If startup succeeds, the bot begins polling Telegram and schedules automatic BTC checks.

## CoinGecko rate limits and caching

- Manual price lookups use an in-memory cache per symbol (TTL: 60 seconds).
- Repeated `/price` requests inside the TTL reuse cached data to reduce API calls.
- If CoinGecko returns HTTP `429`:
  - Manual commands return a user-facing rate-limit message.
  - Automatic BTC checks skip that cycle and log the event (no alert spam).

## Current limitations

- Automatic monitoring is BTC-only (manual checks support multiple coins).
- Cache is in-process only (clears on restart; not shared across instances).
- State persistence is local-file based (single-instance oriented).
- No built-in retry/backoff queue beyond current handling paths.
- Depends on third-party APIs (Telegram, CoinGecko, Groq/news sources).

## Planned improvements

- Multi-coin automatic monitoring rules.
- More configurable thresholds/cooldowns from Telegram UI.
- Stronger resilience (retries/backoff/circuit-breaking).
- Better observability (structured logs, metrics, health endpoints).
- Optional datastore-backed state and distributed cache.
