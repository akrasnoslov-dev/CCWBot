# CCWBot

CCWBot is a Telegram bot for tracking crypto prices and sending automatic **BTC movement alerts**. It supports quick manual price checks for multiple coins, plus admin controls for alert settings.

## Project overview

- Runs as a polling Telegram bot (`python-telegram-bot`).
- Checks BTC price on a configurable interval (default: every 300 seconds).
- Sends automatic alerts when BTC moves beyond a configurable threshold.
- Enriches automatic alerts with Groq AI structured reasoning (severity, risk level, cautious possible actions, news relevance) and recent crypto news context.
- Includes BTC weekly trend context (7d change when available) in automatic alerts.
- Adds admin-only BTC `/reports` menu with Daily/Weekly report buttons and cautious AI summaries.
- Supports optional scheduled weekly report delivery and optional strong-signal alert checks.

## Current features

- Manual `/price` lookup with button menu.
- Automatic BTC monitoring with simple interval + threshold logic.
- AI alert pipeline that validates structured JSON output before sending the final Telegram alert text, including weekly trend context and risk-level interpretation.
- Admin-only alert configuration (`threshold`, `check interval`) via commands and inline buttons.
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
- `/reports` — open admin BTC reports menu with `Daily report` and `Weekly report` buttons.
- `/chatid` — show current chat ID (admin utility).
- `/setthreshold <percent>` — set alert trigger threshold.
- `/setinterval <seconds>` — set automatic BTC check interval.
- `/setcooldown <seconds>` — legacy alias for `/setinterval` (hidden).

### Hidden utility command

- `/userid` — returns your Telegram user ID (useful when configuring admin).
- Hidden fallback commands: `/dailyreport` and `/weeklyreport` still work for admin but are not shown in command menus.

### Inline button menus

- **Price menu** (`/price`): `BTC`, `ETH`, `TON`, `USDT`
- **Settings menu** (`/settings`, admin only):
  - `Current settings`
  - `Set threshold` → `0.5%`, `1.0%`, `2.0%`
  - `Set check interval` → `60 sec`, `300 sec`, `600 sec`
- **Reports menu** (`/reports`, admin only):
  - `Daily report`
  - `Weekly report`

## Admin policy

- `TELEGRAM_ADMIN_USER_ID` controls admin permissions.
  - Only this user can access admin commands, settings buttons, and report buttons.
- `TELEGRAM_CHAT_ID` controls where automatic alerts are delivered.
  - Automatic BTC alerts are sent to this chat ID.
- `/userid` is intentionally hidden from command menus and helps you discover your Telegram user ID.
- `/chatid` is admin-only and hidden from command menus.

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
PRICE_CACHE_TTL_SECONDS=300
AUTOMATIC_CHECK_INTERVAL_SECONDS=300
ENABLE_WEEKLY_REPORT=false
WEEKLY_REPORT_DAY=sunday
WEEKLY_REPORT_HOUR=9
ENABLE_STRONG_SIGNAL_ALERTS=false
STRONG_SIGNAL_CHECK_INTERVAL_SECONDS=1800
STRONG_SIGNAL_COOLDOWN_HOURS=6
```

### Notes

- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and `TELEGRAM_ADMIN_USER_ID` are required at startup.
- `TELEGRAM_ADMIN_USER_ID` should be your numeric Telegram user ID.
- `PRICE_MOVE_ALERT_PERCENT` is interpreted as a percent value in current behavior (default `0.01`).
- `AUTOMATIC_CHECK_INTERVAL_SECONDS` controls how often BTC is checked (default `300`).
- `PRICE_MOVE_ALERT_PERCENT` controls when an alert is sent based on BTC movement since the previous check.
- MVP alert timing model: no separate alert cooldown is used for sending decisions.
- `ALERT_COOLDOWN_MINUTES` is legacy and ignored by current alert logic.
- `PRICE_CACHE_TTL_SECONDS` controls in-memory CoinGecko cache TTL for `btc`, `eth`, `ton`, and `usdt` (default `300`).
- `ENABLE_WEEKLY_REPORT` enables/disables scheduled weekly report delivery to `TELEGRAM_CHAT_ID`.
- `WEEKLY_REPORT_DAY` and `WEEKLY_REPORT_HOUR` set weekly schedule in UTC.
- `ENABLE_STRONG_SIGNAL_ALERTS` enables/disables periodic AI strong-signal classification.
- `STRONG_SIGNAL_CHECK_INTERVAL_SECONDS` controls periodic strong-signal check frequency.
- `STRONG_SIGNAL_COOLDOWN_HOURS` reduces spam by enforcing cooldown between strong-signal alerts.

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

- Manual price lookups use an in-memory cache per symbol (TTL from `PRICE_CACHE_TTL_SECONDS`, default `300`).
- Repeated `/price` requests inside the TTL reuse cached data to reduce API calls.
- Inline `/price` button clicks also reuse the same symbol cache.
- If CoinGecko returns HTTP `429`:
  - Manual commands return `CoinGecko rate limit reached. Please wait a bit and try again.` (cooldown: max one Telegram warning per chat per 120 seconds).
  - Automatic BTC checks log `CoinGecko returned 429 during automatic BTC check. Skipping this cycle.` and skip alerting for that cycle.

## Graceful shutdown

- Pressing `Ctrl+C` stops the bot cleanly and logs: `Bot stopped by user.`
- Normal `Ctrl+C` shutdown avoids noisy traceback output while preserving real runtime errors during operation.

## Current limitations

- Automatic monitoring is BTC-only (manual checks support multiple coins).
- Cache is in-process only (clears on restart; not shared across instances).
- State persistence is local-file based (single-instance oriented).
- No built-in retry/backoff queue beyond current handling paths.
- Depends on third-party APIs (Telegram, CoinGecko, Groq/news sources).
- Alerts are informational and do not provide financial advice.
- Reports and strong-signal alerts are decision-support only, use cautious language, and include “Not financial advice.”

## Planned improvements

- Multi-coin automatic monitoring rules.
- More configurable thresholds from Telegram UI.
- Stronger resilience (retries/backoff/circuit-breaking).
- Better observability (structured logs, metrics, health endpoints).
- Optional datastore-backed state and distributed cache.
