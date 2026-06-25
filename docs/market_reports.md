# Market Reports

Daily and weekly reports are cached market-wide LLM reports across the active
symbols: BTC, ETH, GRAM, and SOL. A report is generated once per cache window
and reused for manual report requests.

## Market Data

Report generation uses a report-specific CoinGecko `/coins/markets` request.
This is separate from the automatic alert price fetcher so reports can include
richer context without changing alert behavior.

The report payload includes:

- current USD price;
- 1h, 24h, and 7d percentage changes when CoinGecko provides them;
- 24h volume, market cap, and market-cap rank;
- 7d sparkline context;
- weekly start, weekly end, weekly high, weekly low, and range position calculated
  from the 7d sparkline.

If a provider omits 7d data for a coin, weekly report rows say
`7d unavailable from provider`. The report should not describe missing 7d data
as normal market context.

## Guardrails

Reports remain available to all users. The cache model stays global: one report
generation creates one LLM report, then many users can read the cached result.
Report changes must not add LLM calls inside user or recipient loops.

The report LLM returns structured JSON only. The bot does not trust an
LLM-composed `telegram_message` for reports. Telegram text is assembled in code
from validated fields and selected source-backed news items.

Automatic Event Alerts continue to use their existing market data path and are
not affected by report-specific data enrichment.

## Telegram Templates

Daily reports use this deterministic section model:

```text
Daily Market Report
Market pulse
Dashboard
Tracked assets
What moved today
Coin-specific news
What to watch next
Not financial advice.
```

Weekly reports use a different section model:

```text
Weekly Market Report
Week in one line
Weekly scoreboard
Market breadth
Themes of the week
Week timeline
Coin-specific recap
Top catalysts of the week
Next week in focus
Not financial advice.
```

The LLM supplies concise structured fields such as `market_pulse`,
`dashboard`, `coin_cards`, `themes`, and `next_week_focus`. Price rows, market
breadth, weekly path notes, and news citations are still rendered from
backend-selected market/news data.

Weekly report input also includes `weekly_context`:

- `scoreboard`: one row per supported symbol with 7d change, weekly start/end,
  range context, and relative 7d performance versus BTC when BTC data exists;
- `breadth`: a backend summary of how many tracked assets were positive over
  seven days, plus leaders and laggards;
- `timeline`: backend evidence from 7d sparkline path notes and selected
  source-backed news dates.

If the provider omits the required weekly sparkline values, the weekly timeline
states that the 7d path is unavailable for that symbol instead of inventing a
weekly story.

## News Selection

Report news uses the existing RSS/news-intelligence boundary. It does not add a
separate news provider abstraction.

The report input is split into:

- `market_news`: a small market-wide list for broad crypto catalysts;
- `coin_news`: direct news buckets for BTC, ETH, GRAM, and SOL.

Only items with a real title, source, and link are eligible. Direct coin matches
rank above market-wide items for coin buckets, and fresher/higher-scored items
rank first. BTC-only news must not be shown as ETH, SOL, or GRAM news unless it
is clearly market-wide.

The LLM payload stays bounded to at most two market-wide items and two direct
items per tracked coin. If no clearly relevant fresh news is found, reports use
the explicit fallback:

```text
No clearly relevant fresh news found for tracked coins
```
