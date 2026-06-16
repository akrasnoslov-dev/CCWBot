# LLM Usage Reporting

`llm_usage_logs` records one row per Groq call when database storage is enabled.

Failure reasons stored in `llm_usage_logs.error_reason` and shown in admin diagnostics use
snake_case safe categories:

- `rate_limit`
- `rate_limit_backoff_active`
- `invalid_json`
- `schema_validation_failed`
- `timeout`
- `auth_error`
- `provider_4xx`
- `provider_5xx`
- `network_error`
- `empty_response`
- `config_missing`
- `other_error`

These values are intentionally short and sanitized. Provider response bodies, raw JSON, stack
traces, API keys, and connection strings must not be copied into Telegram status output.

Last 24h/48h usage by call type, model, and status:

```sql
SELECT
  CASE WHEN created_at >= now() - interval '24 hours' THEN '24h' ELSE '48h' END AS window,
  call_type,
  model,
  status,
  count(*) AS calls,
  sum(prompt_tokens) AS prompt_tokens,
  sum(completion_tokens) AS completion_tokens,
  sum(total_tokens) AS total_tokens,
  avg(total_tokens) AS avg_total_tokens_per_call,
  count(*) FILTER (WHERE status = 'rate_limit') AS rate_limit_errors
FROM llm_usage_logs
WHERE created_at >= now() - interval '48 hours'
GROUP BY 1, call_type, model, status
ORDER BY window, call_type, model, status;
```

Calls by symbol:

```sql
SELECT
  symbol,
  count(*) AS calls,
  sum(total_tokens) AS total_tokens
FROM llm_usage_logs
WHERE created_at >= now() - interval '48 hours'
GROUP BY symbol
ORDER BY calls DESC, symbol;
```

Latest known Groq rate-limit headers by model and call type:

```sql
SELECT DISTINCT ON (model, call_type)
  model,
  call_type,
  created_at,
  rate_limit_remaining_requests,
  rate_limit_remaining_tokens,
  rate_limit_reset_requests,
  rate_limit_reset_tokens,
  retry_after
FROM llm_usage_logs
WHERE created_at >= now() - interval '48 hours'
ORDER BY model, call_type, created_at DESC;
```

Recent event-analysis token averages after deployment:

```sql
SELECT
  call_type,
  model,
  status,
  count(*) AS calls,
  sum(prompt_tokens) AS prompt_tokens,
  sum(completion_tokens) AS completion_tokens,
  sum(total_tokens) AS total_tokens,
  avg(total_tokens) AS avg_total_tokens
FROM llm_usage_logs
WHERE created_at >= now() - interval '2 hours'
GROUP BY call_type, model, status
ORDER BY call_type, model, status;
```

Recent event-analysis usage by symbol:

```sql
SELECT
  symbol,
  status,
  count(*) AS calls,
  avg(total_tokens) AS avg_tokens
FROM llm_usage_logs
WHERE call_type = 'event_analysis'
  AND created_at >= now() - interval '2 hours'
GROUP BY symbol, status
ORDER BY symbol, status;
```

Latest rate-limit rows:

```sql
SELECT
  created_at,
  model,
  call_type,
  symbol,
  status,
  rate_limit_remaining_requests,
  rate_limit_remaining_tokens,
  rate_limit_reset_requests,
  rate_limit_reset_tokens,
  retry_after,
  error_reason,
  error_message
FROM llm_usage_logs
WHERE status = 'rate_limit'
ORDER BY created_at DESC
LIMIT 20;
```

Event-analysis rate-limit delivery outcomes:

```sql
SELECT
  ado.created_at,
  ado.symbol,
  ado.status,
  ado.reason_code,
  eaa.status AS analysis_status,
  eaa.error_reason,
  eaa.model
FROM alert_delivery_outcomes ado
LEFT JOIN event_ai_analyses eaa ON eaa.id = ado.event_ai_analysis_id
WHERE ado.reason_code = 'llm_rate_limited'
ORDER BY ado.created_at DESC
LIMIT 50;
```

LLM stages affected by rate limits:

```sql
SELECT
  call_type,
  model,
  status,
  error_reason,
  count(*) AS calls,
  max(created_at) AS latest_at,
  max(retry_after) AS latest_retry_after
FROM llm_usage_logs
WHERE created_at >= now() - interval '48 hours'
  AND (status = 'rate_limit' OR error_reason ILIKE '%rate%')
GROUP BY call_type, model, status, error_reason
ORDER BY calls DESC, latest_at DESC;
```

Avoidable LLM-call checks:

- `event_analysis` should only run once per symbol check, before recipient delivery and outside
  recipient loops.
- A resolved market event may have at most one attached `event_ai_analyses` row with
  `analysis_type = 'event_analysis'`; many alert delivery rows should reference that same analysis
  id.
- Backend semantic canonicalization runs after validation and before delivery. It may replace broad
  LLM keys such as `news_catalyst`, `price_movement`, or `volatility` with deterministic semantic
  families using the raw key, alert copy, and selected real related-news context; this does not add
  another LLM call.
- If a repeated check creates a fresh successful LLM attempt for an already-known market event, the
  fresh attempt must remain unattached and delivery must reuse the existing attached analysis id and
  sanitized text.
- Event analysis is skipped when no eligible recipients exist for the symbol.
- Active Groq backoff skips are persisted as `event_ai_analyses.status =
  'skipped_due_to_rate_limit'` and `alert_delivery_outcomes.reason_code =
  'llm_rate_limited'`.
- Market Heartbeat generation remains separate from Event Alerts; heartbeat cadence should not
  suppress Event Alerts.

## Ops-Agent LLM Usage Evidence

The ops-agent `llm_usage_summary` collector groups sanitized usage by provider, call type, model,
status, and symbol. It reports call counts, prompt/completion/total token sums, latest call time,
rate-limit count, timeout count, and invalid-JSON/schema-error count.

The collector reads `llm_usage_logs` only. It does not call Groq, retry failed requests, inspect
raw prompts, or export provider response bodies.
