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
For example, raw keys such as `btc_price_drop`, `btc_selloff_prediction`, and
`market_drop_btc` normalize to `btc_price_downtrend`. The raw key and semantic family are emitted
in event-analysis logs and persisted in alert numeric context where available.

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

Suppressed semantic duplicates are logged as `event_alert_suppressed` with
`suppression_reason=semantic_cooldown`. Cooldown is evaluated by symbol plus the canonical
semantic family key, so minor raw-key wording drift does not bypass the cooldown.

## Event Alert Suppression Reasons

Event Alert suppression diagnostics are operational-log only and must not be copied into
Telegram messages. Suppression logs use:

```text
ops_event=event_alert_suppression symbol=BTC raw_event_key=... canonical_event_key=...
semantic_family=price_downtrend event_instance_key=... delivery_count=0 suppression_count=1
suppression_reason=semantic_cooldown analysed_window_minutes=180
```

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
