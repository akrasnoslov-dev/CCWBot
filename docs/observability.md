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
  event_key,
  COUNT(*) AS market_events,
  MIN(detected_at) AS first_seen_at,
  MAX(detected_at) AS last_seen_at
FROM market_events
WHERE event_type = 'event_alert'
GROUP BY symbol, event_key
ORDER BY market_events DESC, last_seen_at DESC;
```

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
`reason=semantic_cooldown`.

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
