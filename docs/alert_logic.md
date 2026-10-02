# Event Alert logic

## Product contract

Event Alerts are market-event-first. BTC, ETH, GRAM, and SOL are checked on the configured
automatic cadence; market data and selected news are supplied to one schema-validated Event
Analysis per coin. News supports interpretation and standalone news-only alerts are disabled.

No deterministic numeric market threshold may create, reject, suppress, or bypass an Event Alert.
Prices, snapshots, analysed-window change, 24-hour change, and 30-day same-symbol relative-move
percentiles are evidence for the LLM, not backend product-decision gates. Percentiles are context
only; no percentile cutoff decides significance. If sufficient history is unavailable, relative
context is null. The LLM's `should_alert` decides significance. The backend keeps deterministic
evidence preparation, schema validation, canonical event identity, the market-event-first
news-only guard, cooldown, recipient eligibility, and idempotent delivery safeguards.

Event Analysis market change fields are explicitly percentage values: `chg_window_percent`,
`chg24h_percent`, and `chg_since_msg_percent`. They are not decimal fractions; for example,
`0.042` means `0.042%`, not `4.2%`. The LLM must not multiply them by 100 or invent a market
significance threshold when reasoning about the supplied evidence.

## Exact Context Reuse

Before a provider call, CCWBot may reuse a durable result only when the canonical semantic Event
Analysis input is exactly unchanged. The fingerprint includes normalized coin identity, full-price
market facts, snapshot sequence, analysed-window fields, previous Event Alert context, selected
news identity/content, and the versioned static prompt policy. It excludes operation IDs, tracing
IDs, recipients, database IDs, redundant display metadata, and observation timestamps. Decimal
representation is normalized (`1.3500` equals `1.35`), but a real value change (`-0.183` to
`-0.184`) is different. There are no movement buckets, tolerances, or similarity comparisons.

## Flow

```text
market data -> relative-move evidence -> Exact Context Reuse -> compact significance LLM
-> should_alert=false stop
-> should_alert=true -> alert-render LLM -> factual/news-only validation -> market event
-> strict four-hour Semantic Cooldown -> recipient eligibility -> idempotent delivery
```

The significance call runs every analysis cycle and returns only the decision, confidence, and a
constrained reason code. The render call runs only after `should_alert=true`; it renders the existing
grounded Event Alert contract and must not re-decide significance. One coin market event has one
durable Event Analysis and can have many deliveries. Provider calls never run in a recipient loop.
Detection and market-event creation are global; BTC is free and non-BTC delivery requires the
existing Premium/watchlist entitlement.

## Cooldown and precision

The Semantic Cooldown is strict: the same canonical event key or semantic family for a recipient
is suppressed for four hours. There is no urgency, larger-movement, direction, structural, or
new-news bypass. A different semantic event is not suppressed by that rule.

CoinGecko automatic-price requests use `precision=full`. Decimal values are retained in the cache
and in `Numeric(38,18)` price state, snapshots, and market events. User-facing rendering rounds
only for readability after calculations and Event Analysis input are complete.

## Operations

`ops_event=event_alert_analysis_candidate` is evidence that a symbol reached analysis; it does
not decide significance. Durable outcomes distinguish LLM no-alert, news-only rejection, exact
context reuse, semantic cooldown, recipient filtering, and delivery. Historical threshold and
similar-context rows remain readable as historical data only.
