Great. Paste this into `README.md`:

````markdown
# CCWBot - CryptoCurrencyWatcherBot

CCWBot is a Telegram-based BTC monitoring bot with AI-generated alerts.

The bot checks the BTC price at regular intervals, compares the current price with the previous saved value, applies threshold and cooldown rules, and sends a Telegram alert when the movement is significant enough. The alert message is generated with Groq AI.

## Current features

- Telegram bot interface
- `/start` command
- `/price` command to get current BTC price
- `/status` command to show last saved BTC data
- Automatic BTC price checks
- Price movement threshold
- Alert cooldown to avoid spam
- AI-generated alert messages via Groq
- Local state storage using `state.json`
- Environment-based configuration

## Project structure

```text
CCWBot/
│
├── main.py              # Telegram bot, commands, scheduler
├── config.py            # Environment variables and bot settings
├── ai_agent_groq.py     # Groq AI alert generation
├── price_service.py     # CoinGecko BTC price fetching
├── storage.py           # Local state loading/saving
├── alert_rules.py       # Threshold and cooldown logic
├── requirements.txt     # Python dependencies
├── .env.example         # Example environment variables
└── .gitignore           # Files excluded from Git
````

## How it works

```text
Scheduled BTC check
→ Fetch BTC price from CoinGecko
→ Compare with previous saved price
→ Check movement threshold
→ Check alert cooldown
→ Generate AI alert with Groq
→ Send alert to Telegram
→ Save new state
```

## Environment variables

Create a `.env` file based on `.env.example`:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here

GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-20b

PRICE_MOVE_ALERT_PERCENT=0.01
ALERT_COOLDOWN_MINUTES=2
```

For real usage, increase the threshold and cooldown, for example:

```env
PRICE_MOVE_ALERT_PERCENT=1.0
ALERT_COOLDOWN_MINUTES=30
```

## Local setup

Create and activate a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Run the bot:

```powershell
python main.py
```

## Telegram commands

```text
/start   - show available commands
/price   - get current BTC price
/status  - show last saved BTC data
/chatid  - show your Telegram chat ID
```

## Current status

This is an early learning project created to practise building AI agents, Telegram bots, external API integrations, background jobs, and basic project structure in Python.

## Planned improvements

* Add support for more cryptocurrencies
* Add configurable alert settings from Telegram
* Add news monitoring
* Add stronger AI reasoning with structured outputs
* Add deployment for 24/7 operation
* Add persistent database instead of local JSON
