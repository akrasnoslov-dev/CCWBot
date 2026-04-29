# CCWBot - CryptoCurrencyWatcherBot

CCWBot is a Telegram bot that monitors **BTC** and sends automatic AI-enhanced alerts for significant BTC moves.

## Features

- `/price` supports direct lookup (`/price btc`) and a button menu when no symbol is provided
- Supported `/price` symbols: `btc`, `eth`, `ton`, `usdt`
- `/settings` opens an inline settings menu (current settings, threshold presets, cooldown presets)
- Text fallback commands: `/setthreshold` and `/setcooldown`
- `/status` command for last saved BTC state
- Automatic BTC background checks + threshold/cooldown-based alerts
- AI-generated BTC alert messages via Groq
- Local JSON state storage

## Supported `/price` symbols

The bot maps symbols to CoinGecko IDs internally:

- `btc` → `bitcoin`
- `eth` → `ethereum`
- `ton` → `toncoin`
- `usdt` → `tether`

Examples:

- `/price` → opens inline button menu (BTC, ETH, TON, USDT)
- `/price eth`
- `/price USDT`

If a symbol is unsupported (example: `/price abc`), the bot replies with a friendly message listing supported symbols.

## Settings menu

`/settings` opens a button menu with:

- **Current settings**
- **Set threshold** → preset buttons: `0.5%`, `1.0%`, `2.0%`
- **Set cooldown** → preset buttons: `10 min`, `30 min`, `60 min`

You can still configure settings via text commands:

- `/setthreshold 1.0`
- `/setcooldown 30`

## Automatic alerts behavior

Automatic alert behavior remains **BTC-only**:

- Background scheduler checks BTC only
- Threshold/cooldown rules are applied to BTC only
- Saved status fields (`last_price`, `last_24h_change`, etc.) remain BTC-focused

## Project structure

- `main.py` - Telegram commands, inline button handlers, scheduler, alert flow
- `price_service.py` - CoinGecko symbol mapping + price fetching
- `alert_rules.py` - Threshold and cooldown logic
- `news_service.py` - News fetching used in AI alert context
- `ai_agent_groq.py` - Groq AI message generation
- `storage.py` - Local state loading/saving
- `config.py` - Environment configuration

## Environment

Create a `.env` file from `.env.example`:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here

GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-20b

PRICE_MOVE_ALERT_PERCENT=0.01
ALERT_COOLDOWN_MINUTES=2
```

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```
