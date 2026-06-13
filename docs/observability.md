# Observability Snippets

Use these read-only queries for production analysis. Adjust interval windows as needed.

## Event Alerts With Market Events

```sql
SELECT
  a.id AS alert_id,
  a.created_at,
  a.user_id,
  a.symbol,
  a.alert_type,
  a.status,
  a.trigger_source,
  me.id AS market_event_id,
  me.event_key,
  me.event_instance_key,
  me.detected_at
FROM alerts a
LEFT JOIN market_events me ON me.id = a.market_event_id
WHERE a.alert_type = 'event_alert'
ORDER BY a.created_at DESC
LIMIT 100;
```

## Delivery Outcome Tracking

`alert_delivery_outcomes` is the queryable decision ledger for Event Alerts. `alerts` remains the
Telegram delivery table; outcome rows explain recipient filtering, cooldown suppression, delivery
success/failure, LLM rate-limit skips, and event-level no-recipient cases.

Outcome statuses:

- `delivered`
- `suppressed`
- `filtered`
- `failed`
- `rate_limited`
- `cooldown`
- `not_scheduled`
- `no_eligible_recipients`

Common reason codes:

- `delivered`
- `duplicate_event`
- `similar_event_suppressed`
- `user_not_eligible`
- `premium_required`
- `watchlist_disabled`
- `cooldown_active`
- `telegram_send_failed`
- `llm_rate_limited`
- `llm_invalid_response`
- `no_recipients`
- `delivery_not_scheduled`
- `already_delivered`
- `severity_below_threshold`

For a market event, trace analysis, recipient decisions, and delivery outcomes:

```sql
SELECT
  me.id AS market_event_id,
  me.symbol,
  me.event_key,
  me.event_instance_key,
  eaa.id AS event_ai_analysis_id,
  eaa.status AS analysis_status,
  eaa.should_alert,
  ado.user_id,
  ado.recipient_considered,
  ado.recipient_eligible,
  ado.status AS outcome_status,
  ado.reason_code,
  a.status AS delivery_status,
  ado.created_at AS outcome_at
FROM market_events me
LEFT JOIN event_ai_analyses eaa ON eaa.market_event_id = me.id
LEFT JOIN alert_delivery_outcomes ado ON ado.market_event_id = me.id
LEFT JOIN alerts a ON a.id = ado.alert_id
WHERE me.id = :market_event_id
ORDER BY ado.created_at, ado.id;
```

Find future `should_alert=true` cases with no successful delivery and their explicit reason:

```sql
SELECT
  me.id AS market_event_id,
  me.symbol,
  me.event_key,
  eaa.id AS event_ai_analysis_id,
  eaa.created_at AS analysis_at,
  coalesce(ado.status, 'missing_outcome') AS outcome_status,
  coalesce(ado.reason_code, 'missing_outcome') AS reason_code,
  count(a.id) FILTER (WHERE a.status = 'sent') AS sent_deliveries
FROM event_ai_analyses eaa
JOIN market_events me ON me.id = eaa.market_event_id
LEFT JOIN alert_delivery_outcomes ado ON ado.event_ai_analysis_id = eaa.id
LEFT JOIN alerts a ON a.event_ai_analysis_id = eaa.id
WHERE eaa.should_alert = true
GROUP BY me.id, me.symbol, me.event_key, eaa.id, eaa.created_at, ado.status, ado.reason_code
HAVING count(a.id) FILTER (WHERE a.status = 'sent') = 0
ORDER BY eaa.created_at DESC;
```

## Event Key Frequency

```sql
SELECT
  symbol,
  event_key AS canonical_event_key,
  COUNT(*) AS market_events,
  MIN(detected_at) AS first_seen_at,
  MAX(detected_at) AS last_seen_at
FROM market_events
WHERE event_type = 'event_alert'
GROUP BY symbol, event_key
ORDER BY market_events DESC, last_seen_at DESC;
```

`market_events.event_key` is the backend canonical semantic key, not necessarily the raw LLM key.
Semantic family normalization, stable event identity, and similarity cooldown checks existed
before `alert_delivery_outcomes`; outcome rows now make those decisions queryable in the database.
For example, raw keys such as `btc_price_drop`, `btc_selloff_prediction`, and
`market_drop_btc` normalize to `btc_price_downtrend`. Generic keys such as `news_catalyst`,
`price_movement`, and `volatility` are not trusted as final identity when the title/body or
selected real related-news title/source/link supports a more specific family, such as
`btc_protocol_security_risk` or `btc_price_level_range`. The raw key and semantic family are
emitted in event-analysis logs and persisted in alert numeric context where available.

## Duplicate/Suppressed Analysis

```sql
SELECT
  a.user_id,
  a.symbol,
  me.event_key,
  COUNT(*) AS sent_count,
  MIN(a.created_at) AS first_sent_at,
  MAX(a.created_at) AS last_sent_at
FROM alerts a
JOIN market_events me ON me.id = a.market_event_id
WHERE a.alert_type = 'event_alert'
  AND a.status = 'sent'
GROUP BY a.user_id, a.symbol, me.event_key
HAVING COUNT(*) > 1
ORDER BY last_sent_at DESC;
```

Suppressed semantic duplicates are persisted as `alert_delivery_outcomes.reason_code =
'similar_event_suppressed'` and logged as `event_alert_suppressed` with
`suppression_reason=semantic_cooldown`. Cooldown is evaluated by symbol plus the canonical
semantic family key, and also checks delivered outcome semantic family where available, so minor
raw-key wording drift does not bypass the cooldown. Same-family events can still deliver inside the
semantic cooldown when urgency increased, the absolute analysed-window movement grew by at least
2.5 percentage points, or stable related-news identity shows a new news driver.

## Event Alert Suppression Reasons

Event Alert suppression diagnostics are persisted in `alert_delivery_outcomes` and also emitted to
operational logs. These diagnostics must not be copied into Telegram messages. Suppression logs use:

```text
ops_event=event_alert_suppression symbol=BTC raw_event_key=... canonical_event_key=...
semantic_family=price_downtrend event_instance_key=... delivery_count=0 suppression_count=1
suppression_reason=semantic_cooldown analysed_window_minutes=180
```

Debug cooldown checks include sanitized escalation fields such as `urgency_increased`,
`material_movement_increased`, `new_news_driver`, previous/current movement percentages, and
previous/current selected-news counts. These fields explain whether same-family delivery was
allowed through cooldown or denied; they are for logs/outcomes only and must not be copied into
Telegram messages.

Market-only event instance keys are built from symbol, canonical semantic key, rounded UTC time
bucket, urgency, and a coarse movement bucket. News-linked event instance keys use stable selected
news identities instead of temporary `n1`/`n2` labels. Small payload or input-hash changes should
not create new event identities; severity increases, materially larger movement buckets, and
distinct news drivers may create new identities.

Stable `suppression_reason` values include:

- `exact_cooldown`
- `semantic_cooldown`
- `user_frequency_cooldown`
- `no_eligible_recipient`
- `premium_required`
- `product_gated`
- `delivery_failed`
- `llm_rate_limited`
- `stale_heartbeat`
- `unknown`

The ops-agent log collector aggregates these in
`evidence/logs/pattern_counts.json` under `suppression_reason_counts`,
`period_matched_suppression_reason_counts`, and
`tail_context_suppression_reason_counts`.

## Multiple AI Analyses Per Market Event

The expected invariant is:

```text
1 coin market event = 1 AI analysis = many alert deliveries
```

Use this read-only diagnostic to quantify possible duplicate analyses:

```sql
WITH analysis_counts AS (
  SELECT
    me.id AS market_event_id,
    me.symbol,
    me.event_key,
    me.event_instance_key,
    count(eaa.id) AS analysis_count,
    count(eaa.id) FILTER (WHERE eaa.status IN ('success', 'completed')) AS successful_analyses,
    sum(coalesce(eaa.total_tokens, 0)) AS event_analysis_tokens
  FROM market_events me
  JOIN event_ai_analyses eaa ON eaa.market_event_id = me.id
  GROUP BY me.id, me.symbol, me.event_key, me.event_instance_key
)
SELECT *
FROM analysis_counts
WHERE analysis_count > 1
ORDER BY analysis_count DESC, event_analysis_tokens DESC, market_event_id DESC;
```

Estimate duplicated LLM usage impact:

```sql
WITH duplicate_events AS (
  SELECT market_event_id
  FROM event_ai_analyses
  WHERE market_event_id IS NOT NULL
  GROUP BY market_event_id
  HAVING count(*) > 1
)
SELECT
  count(DISTINCT eaa.market_event_id) AS market_events_with_multiple_analyses,
  count(eaa.id) AS total_analysis_rows,
  greatest(count(eaa.id) - count(DISTINCT eaa.market_event_id), 0) AS extra_analysis_rows,
  sum(coalesce(eaa.total_tokens, 0)) AS total_tokens_on_affected_events
FROM event_ai_analyses eaa
JOIN duplicate_events de ON de.market_event_id = eaa.market_event_id;
```

## LLM Outcomes By Symbol

```sql
SELECT
  symbol,
  status,
  should_alert,
  COUNT(*) AS attempts,
  MAX(created_at) AS latest_attempt_at
FROM event_ai_analyses
WHERE analysis_type = 'event_analysis'
GROUP BY symbol, status, should_alert
ORDER BY latest_attempt_at DESC;
```

## Event Alert LLM Cadence Estimate

```sql
WITH settings AS (
  SELECT greatest(coalesce(automatic_check_interval_seconds, 1800), 1)
    AS event_analysis_interval_seconds
  FROM app_settings
  ORDER BY id DESC
  LIMIT 1
),
eligible_symbols AS (
  SELECT count(DISTINCT lower(ucs.symbol)) AS symbols
  FROM user_coin_subscriptions ucs
  JOIN users u ON u.id = ucs.user_id
  LEFT JOIN user_premium_subscriptions ups ON ups.user_id = u.id
  WHERE u.telegram_chat_id IS NOT NULL
    AND u.is_active = true
    AND u.bot_blocked = false
    AND ucs.is_enabled = true
    AND (lower(ucs.symbol) = 'btc' OR ups.active_until >= now())
)
SELECT
  s.event_analysis_interval_seconds,
  6 AS payload_points,
  ceil((s.event_analysis_interval_seconds * 6) / 60.0)::integer
    AS analysed_window_minutes,
  coalesce(e.symbols, 0) AS eligible_symbols,
  round((coalesce(e.symbols, 0) * 3600.0 / s.event_analysis_interval_seconds)::numeric, 2)
    AS estimated_event_alert_llm_calls_per_hour,
  round((coalesce(e.symbols, 0) * 86400.0 / s.event_analysis_interval_seconds)::numeric, 2)
    AS estimated_event_alert_llm_calls_per_day
FROM settings s
CROSS JOIN eligible_symbols e;
```

## Heartbeat Delivery By User

```sql
SELECT
  user_id,
  symbol,
  status,
  COUNT(*) AS deliveries,
  MAX(created_at) AS latest_delivery_at
FROM alerts
WHERE alert_type = 'market_heartbeat'
GROUP BY user_id, symbol, status
ORDER BY latest_delivery_at DESC;
```
