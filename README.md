# CCWBot

CCWBot is a Telegram crypto watcher bot focused on automatic **BTC movement alerts** with optional AI-assisted context.

## What the bot does
- Monitors BTC on a schedule.
- Sends automatic alerts to a configured Telegram chat when movement crosses a threshold.
- Provides manual price checks for supported coins.
- Adds optional AI summaries and optional weekly/strong-signal reporting.

## Current features
- Manual `/price` checks and inline coin buttons.
- Automatic BTC checks with configurable interval and movement threshold.
- AI-assisted alert/report text generation (Groq provider) with safe fallback messages.
- RSS news context filtering for crypto/BTC relevance.
- Admin-only settings, status, and reports.
- Local `state.json` persistence for runtime state/settings overrides.

## Supported coins
- `btc`
- `eth`
- `ton`
- `usdt`

## Commands and menus
### Main commands
- `/start`
- `/price` (or `/price <symbol>`)
- `/settings` (admin only)
- `/status` (admin only)
- `/reports` (admin only, if present in your menu)

### Hidden utility commands
- `/userid` - returns your Telegram user ID.
- `/chatid` - admin utility to show current chat ID.
- `/dailyreport` and `/weeklyreport` - admin report shortcuts.

### Menus
- Price menu: BTC / ETH / TON / USDT.
- Settings menu: current settings, threshold presets, interval presets.
- Reports menu: daily report, weekly report.

## Admin policy
- `TELEGRAM_ADMIN_USER_ID` controls admin permissions.
- `TELEGRAM_CHAT_ID` controls destination for automatic alerts and scheduled bot messages.
- Non-admin users can use non-admin commands only.

## Environment variables
Required core values:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `TELEGRAM_ADMIN_USER_ID`
- `GROQ_API_KEY`

Common runtime values:
- `GROQ_MODEL`
- `PRICE_MOVE_ALERT_PERCENT`
- `AUTOMATIC_CHECK_INTERVAL_SECONDS`
- `PRICE_CACHE_TTL_SECONDS`
- `ALERT_COOLDOWN_MINUTES` (legacy; currently not used in alert decision)

Optional report/signal values:
- `ENABLE_WEEKLY_REPORT`
- `WEEKLY_REPORT_DAY`
- `WEEKLY_REPORT_HOUR`
- `ENABLE_STRONG_SIGNAL_ALERTS`
- `STRONG_SIGNAL_CHECK_INTERVAL_SECONDS`
- `STRONG_SIGNAL_COOLDOWN_HOURS`

## Local setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Then fill `.env` and run:
```bash
python main.py
```

## How to find your Telegram user ID
Use `/userid` in a private chat with the bot.

## Notes
- CoinGecko can return HTTP 429 rate-limit errors.
- The bot uses in-memory price caching (`PRICE_CACHE_TTL_SECONDS`) to reduce API calls.
- AI text generation uses Groq via an OpenAI-compatible client.
- Bot output is informational only and includes **Not financial advice** guidance.

## Current limitations
- Automatic monitoring targets BTC only.
- `state.json` is local-file persistence (single-instance oriented).
- No database/backend queue in this version.
- Depends on third-party APIs/services.

## Planned improvements
- Multi-coin automatic monitoring.
- More granular admin settings.
- Stronger resilience/observability.
- Optional shared/distributed state storage.
