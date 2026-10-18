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
- `change_1h_percent`, `change_24h_percent`, and `change_7d_percent` when CoinGecko provides
  them; these are already percentage values, not decimal fractions (`0.042` means `0.042%`);
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

A failed scheduled generation is recorded as a terminal report attempt, but does not
replace a still-valid completed cache entry (PostgreSQL or in-memory fallback).
After a scheduled failure, the existing one-hour report backoff remains in force.
A single one-shot recovery job runs after that backoff; it does not recursively
reschedule on failure. The usual daily four-hour and weekly 24-hour schedules stay
unchanged. An expired cache can leave manual requests temporarily unavailable
until an eligible generation succeeds; a later provider success alone does not
prove that requests during that gap succeeded.

When every configured LLM report provider is exhausted by rate limits, backoff,
timeouts, transport failures, or other router-recognized provider failures after
usable source market data has been acquired, the same existing deterministic
data-only report fallback used for invalid JSON is returned and cached. It is
clearly attributed to the deterministic provider; no additional provider call
or per-user work is made. Market-data collection failures, persistence failures,
and unexpected program errors must still remain terminal failures rather than
pretending success. A fallback is factual and intentionally less analytical than
a normal validated LLM report.

The report LLM returns structured JSON only. The bot does not trust an
LLM-composed `telegram_message` for reports. Telegram text is assembled in code
from validated fields and selected source-backed news items.


When the resolved Groq report model is in the verified strict-schema allowlist, the provider request
uses strict JSON Schema requiring every report top-level field and the `symbol`, `summary`, and
`watch` fields on every coin card. Gemini, Cloudflare, and unsupported/custom Groq report models keep
JSON Object Mode. Provider-side shape enforcement does not replace application validation:
report type, active-symbol completeness, non-empty content, safety wording, and other semantic
checks still run in the backend.

Automatic Event Alerts continue to use their existing market data path and are
not affected by report-specific data enrichment.

## Telegram Templates

Daily reports present **one** price/24h-change scoreboard with no repeated
Dashboard or What moved today metrics:

```text
Daily Market Report
Market pulse
Tracked assets
What to monitor
Coin-specific news
What to watch next
Not financial advice.
```

Weekly reports present **one** 7d scoreboard; 24h data and textual sparkline
blocks do not appear repeatedly in other sections:

```text
Weekly Market Report
Week in one line
Weekly scoreboard
Market breadth
Coin watchpoints
Top catalysts of the week
Next week in focus
Not financial advice.
```

Removed weekly Theme/Timeline/Coin-specific recap prose repeated the same
returns, ranges and unverified model narratives. The original validated model
fields remain available for compatibility; they do not create duplicate
user-facing sections. Already cached legacy report rows remain immutable, but
manual Rich/HTML rendering compacts their historical text without LLM calls.

Native Telegram Rich presentation of either report is built **only** from the
cached, already-sanitized report text and `raw_input_json`. It uses Rich section headings and restores the owner's CCWBotIcons by
using Telegram-verified sticker Unicode alternate text for each `tg-emoji`
entity. The ordinary HTML/plain fallback uses neutral symbols if Custom Emoji
are unavailable. Source-linked articles and a single inline PNG are preserved.
Daily shows per-coin **24h percentage change**; Weekly combines 7d change
bars with miniature normalized 7d source paths from the existing 12-step
sparkline evidence. These are truthful schematic trends, not invented prices,
high-resolution time series or interpolated missing history. Missing data stays omitted;
if no changes are available, a short chart-unavailable explanation replaces
the image. No new provider/LLM/news calls are made on report requests.

Native `sendRichMessage` returns one message receipt. Manual command and
callback replies must remain registered in the existing transient-session
Close/next-command cleanup; normal PTB HTML (then plain text) is the fallback
only after a **definite Rich rejection**. Uncertain Rich acceptance must not
trigger a duplicate message. Cache data, scheduled generation, freshness,
premium access, legacy plaintext and report JSON semantics are unchanged.
Telegram Desktop/iOS/Android appearance requires a private smoke test; CI
verifies only the transport formatting contract.

The LLM supplies concise structured fields such as `market_pulse`,
`dashboard`, `coin_cards`, `market_catalysts`, `week_timeline`, `themes`, and
`next_week_focus`. `week_timeline` and `themes` are short string lists. Price
rows, market breadth, weekly path notes, and news citations are still rendered
from backend-selected market/news data.

Weekly report input also includes `weekly_context`:

- `scoreboard`: one row per supported symbol with `change_7d_percent`, weekly start/end,
  range context, and `vs_btc_7d_percent` when BTC data exists;
- `breadth`: a backend summary of how many tracked assets were positive over
  seven days, plus leaders and laggards;
- `timeline`: backend evidence from 7d sparkline path notes only.

If the provider omits the required weekly sparkline values, the weekly timeline
states that the 7d path is unavailable for that symbol instead of inventing a
weekly story.

## News Selection

Report news uses the existing RSS/news-intelligence boundary. It does not add a
separate news provider abstraction.

Report news uses **distinct periods**: 24 hours for Daily and 168 hours
for Weekly, based on real publication timestamps (undated and expired
articles are excluded). The existing RSS fetch runs once per report generation,
then joins read-only with previously analysed and **successful, non-noise,
non-duplicate** News Intelligence records already stored in PostgreSQL.
Weekly reports must not infer that an entire week was news-free from a short
rolling RSS feed page. No additional provider/LLM calls are made.
Links require real titles, source and HTTP(S) URL. Explicit per-coin matches
rank within coin buckets; a BTC-only headline must not appear as an ETH story.
The data sent to the LLM remains capped at two broad-market and two direct
items per tracked coin. The final user-facing news list contains up to **four
unique source URLs**, including article titles and publishers, without repeats
across coin buckets. News is not a presumed cause of price movement unless
its source supports that claim; generic AI catalyst claims are no longer
rendered as unverified explanations.

If none qualifies, the report says **No verified relevant news selected for
the last 24 hours** or **last seven days**. That statement describes the
selection result, not a claim that no relevant news occurred.

Log only selection counts/periods, never titles or raw article payloads.

## Restored analysis and cache content revision

Daily includes up to three distinct coin-specific scenario/watchpoints and
Weekly includes up to four, from the already validated coin-card fields.
These are additive observations rather than duplicate 24h/7d percentage
rows, and model-only generic causal claims are not presented as real news.

When existing persisted report input predates this content revision, the
next manual request attempts **one globally shared** content refresh while
holding the per-report generation lock. If the refresh fails, the prior
still-valid completed cache is retained and one-hour retry suppression
prevents repeated manual views from exhausting provider quotas. A successful
report includes current source-selected news and one content version marker.
No new per-recipient LLM/RSS calls are introduced; schedules and report
eligibility remain unchanged.
