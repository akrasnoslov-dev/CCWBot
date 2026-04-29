# CCWBot - CryptoCurrencyWatcherBot

CCWBot is a Telegram bot that monitors **BTC** and sends automatic AI-enhanced alerts for significant BTC moves.

## Key behavior

- `TELEGRAM_CHAT_ID` is used only for automatic alert delivery target chat.
- `TELEGRAM_ADMIN_USER_ID` is used for admin permission checks.
- Admin-only: `/settings`, `/status`, `/chatid`, `/setthreshold`, `/setcooldown`, and all settings inline actions.
- Normal users: `/start`, `/price`.
- Hidden utility: `/userid` (available to help discover your Telegram user ID).
- Hidden admin utility: `/chatid`.

## Supported `/price` symbols

- `btc` → `bitcoin`
- `eth` → `ethereum`
- `ton` → `toncoin`
- `usdt` → `tether`

`/price` with no arguments opens a coin button menu. Automatic checks remain BTC-only.

## Rate-limit handling

- CoinGecko price responses are cached in memory per symbol for 60 seconds.
- Repeated `/price` calls within TTL reuse cache to reduce API calls.
- If CoinGecko returns 429:
  - Manual `/price`: user sees `CoinGecko rate limit reached. Please wait a bit and try again.`
  - Automatic BTC check: bot logs and skips cycle without sending alert spam.

## Environment

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
TELEGRAM_ADMIN_USER_ID=your_admin_telegram_user_id_here

GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-20b

PRICE_MOVE_ALERT_PERCENT=0.01
ALERT_COOLDOWN_MINUTES=2
```
