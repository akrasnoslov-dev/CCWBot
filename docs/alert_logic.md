# Event Alert logic

## 1. Purpose of Event Alerts

Event Alerts tell users about meaningful, explainable changes in a coin's market situation. They
are not triggered by every small price change. Several alerts may arrive close together when each
represents a genuinely different event or a material escalation. Alerts use cautious language and
end with `Not financial advice.`

## 2. When each coin is checked

BTC, ETH, GRAM, and SOL use one effective 30-minute Event Analysis cadence. Checks are staggered so
all coins do not call external services at once. A legacy stored interval such as 600 seconds is
normalized to 1,800 seconds for scheduling, freshness, status, operational estimates, and the
analysed window.

A coin is analysed only when at least one user could receive its automatic alerts. BTC is free.
ETH, GRAM, and SOL require active Premium and an enabled watchlist choice.

## 3. Input data

Each analysis can use:

- Current price, 24-hour change, and stored snapshots.
- Net analysed-window movement, cumulative trajectory, persistence, and acceleration.
- The price and time of the previous relevant sent Event Alert.
- Movement since that same previous sent record.
- Previous semantic event context, urgency, movement, action, and stable related-context identity.
- Selected real news with title, source, and link.
- Recipient eligibility, including active status, blocked status, Premium, and watchlist choice.

News supports market interpretation. It is not an independent Event Alert trigger.

## 4. Pre-LLM checks

Before an LLM provider is called, CCWBot resolves eligible recipients, collects market data,
selects non-noise context, checks for an existing attached analysis, and checks recent durable
decisions for a matching sanitized context fingerprint.

No LLM call is made when no eligible recipient exists, an existing event analysis can be reused,
or a recent no-alert, rejected, suppressed, or delivered decision already covers the same stable
context. Raw prompts, user IDs, timestamps, and arbitrary wording do not form the reuse key.

## 5. What the LLM receives

In business terms, the LLM receives one coin's current price, compact recent trajectory, analysed
window, 24-hour context, movement since the previous sent alert, previous event context, and
selected news. Market behavior is primary; news is supporting context.

## 6. What the LLM decides

The structured Event Analysis contains `should_alert`, stable event identity/family, urgency,
confidence, `Situation`, `Possible action`, selected related-news identifiers, and a reason for a
no-alert result. The response is schema-validated. A provider failure may fall through to another
provider; a successful fallback is a successful final feature outcome.

`Situation` should explain why the event matters. `Possible action` remains trading-oriented but
conditional and cautious.

## 7. Backend checks after the LLM

`should_alert=true` does not guarantee delivery. Before creating a market event, the backend applies
a deterministic significance policy using several signals together:

- Analysed-window net movement.
- Persistent cumulative movement across snapshots.
- Acceleration in the recent trajectory.
- Aligned 24-hour continuation.
- Material movement since the previous sent alert.
- Relevant context accompanied by a meaningful market reaction.

Tiny isolated moves, small flip-flops, generic news with a weak reaction, and unsupported LLM
urgency are rejected. A sequence of smaller aligned moves may alert once it accumulates into a
meaningful trend. News alone never makes an otherwise weak move significant.

The backend normalizes wording variants into semantic families such as price uptrend/downtrend,
price level/range, volatility, ETF flows, liquidations, regulatory change, derivatives,
network/mining, news catalyst, and protocol/security risk. Cross-family price wording is compared
by direction, analysed window, and market-structure traits for every supported coin.

Inside semantic cooldown, the same user meaning is suppressed unless quantitative evidence supports
an escalation. A materially stronger movement or supported urgency increase may pass, with an
explicit durable allow reason. New news alone does not bypass cooldown. A different significant
event is not blocked by a broad per-symbol quota.

## 8. Event creation and analysis reuse

CCWBot follows one invariant:

```text
1 coin market event = 1 AI analysis = many alert deliveries
```

One event is created or reused, one validated analysis is attached, and the same sanitized message
is delivered to every eligible recipient. Provider calls never run inside a recipient loop.

## 9. Recipient selection

- BTC automatic alerts are available to active free and Premium users who enabled BTC.
- ETH, GRAM, and SOL require active Premium and an enabled watchlist choice.
- Expired Premium keeps saved non-BTC choices but blocks delivery until renewal.
- Inactive users, blocked users, missing chats, disabled choices, and ineligible plans are filtered
  with durable reasons.
- Manual `/price` remains free for supported coins.

## 10. Message construction

A delivered Event Alert can contain current price; `Since last alert/message (1h 25m ago)` using
the timestamp and price from the same prior record; analysed-window movement; a useful `Situation`;
real related context; a conditional `Possible action`; and `Not financial advice.`

Hard commands such as “Buy now” or “Sell now” are softened. Unsupported numeric claims,
contradictory directions, placeholders, and dramatic wording for weak moves are corrected or
replaced before delivery.

## 11. Delivery

The shared analysis is sent to many users. Each delivery is reserved idempotently. Transient
Telegram failures are retried; permanent blocked-chat failures disable future delivery. One user's
failure neither causes another LLM call nor prevents delivery to other recipients.

## 12. What is stored

CCWBot stores snapshots/state, the market event, the LLM analysis and structured decision, the
shared rendered analysis, recipient delivery rows, and decision outcomes. Outcome stages include
pre-LLM reuse, LLM no-alert, significance rejection, semantic cooldown, escalation allow, and
Telegram delivery. Raw analysis input/output may be retained internally for auditability, but
Telegram diagnostics and log exports render only sanitized aggregate facts and never expose
prompts, responses, credentials, identifiers, or private user data.

## 13. Examples

- **Tiny isolated move:** 0.01% or 0.05% with no material context is rejected even if the LLM says
  alert.
- **Accumulating trend:** aligned smaller moves that become a persistent multi-percent trend may
  alert.
- **Repeated situation:** minor key or wording changes do not bypass suppression.
- **Meaningful escalation:** materially stronger movement or evidence-supported urgency may alert.
- **News with weak reaction:** relevant news plus a tiny reaction does not guarantee an alert.
- **GRAM no-alert:** GRAM reaching Event Analysis and returning `should_alert=false` is healthy.

## 14. Operator troubleshooting map

```text
No alert?
-> Was price collected?
-> Was Event Analysis called/reused/skipped?
-> Did LLM say no-alert?
-> Did significance reject it?
-> Was it suppressed as repeat?
-> Were recipients eligible?
-> Did Telegram delivery succeed?
```

Use Admin -> System status for compact feature health and Admin -> LLM diagnostics for provider and
call-type attempts. See [Observability](observability.md), [LLM usage](llm_usage.md), and
[Development](development.md) for operational details.
