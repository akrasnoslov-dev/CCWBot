# LLM Usage Reporting

`llm_usage_logs` records one row per LLM call attempt when database storage is enabled. The
`provider` column names which provider handled the request (`groq`, `cerebras`, `gemini`, or
`mistral`), so per-provider statistics come from grouping by `provider` — no separate telemetry
system.

## Provider fallback (redundancy)

Groq is the primary LLM provider. Cerebras, Gemini, and Mistral form an ordered fallback chain,
configured via `LLM_PROVIDER_PRIORITY` (default `groq,cerebras,gemini,mistral`) with optional
per-task-type overrides `LLM_EVENT_PROVIDERS`, `LLM_REPORT_PROVIDERS`, `LLM_HEARTBEAT_PROVIDERS`.
All four providers are reached through the OpenAI-compatible chat-completions API (Gemini via its
OpenAI-compatible endpoint), so no extra client dependency is required.

The router (`bot/services/llm/router.py`) tries each configured provider in priority order. It
advances to the next provider on a rate limit, timeout, 5xx, auth, or network error, and surfaces
deterministic errors (e.g. a 4xx bad request or JSON-mode validation failure) to the caller
unchanged. When every provider is exhausted it raises the exception each existing caller already
handles, so the deterministic fallback / `skipped_due_to_rate_limit` paths are unchanged — they
now trigger only after the whole chain is exhausted, not on the first Groq rate limit.

A provider with no API key is excluded from the chain (logged once), so leaving the fallback keys
blank keeps Groq-only behaviour. Rate-limit backoff is tracked per `(provider, model)`. The
runtime LLM entry point remains `bot/services/ai_agent_groq.py`, now a thin facade over the router
that keeps all public names/signatures (`AIGroqRateLimitError` is an alias of the provider-agnostic
`AIProviderRateLimitError`).

The persisted analysis/report provider and model reflect the provider that actually answered:
`event_ai_analyses.provider/model` and `market_reports.provider/model` follow the fallback, not a
hardcoded `groq`. Admin diagnostics (`bot/observability/system_status.py`) and the ops-agent
`llm_usage_summary` collector are provider-agnostic.

Per-provider usage counts (24h) — group by `provider`:

```sql
SELECT
  provider,
  status,
  count(*) AS calls,
  sum(total_tokens) AS total_tokens,
  count(*) FILTER (WHERE status = 'rate_limit') AS rate_limit_errors,
  count(*) FILTER (WHERE status = 'timeout') AS timeout_errors,
  max(created_at) AS latest_at
FROM llm_usage_logs
WHERE created_at >= now() - interval '24 hours'
GROUP BY provider, status
ORDER BY provider, status;
```

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
- Event Analysis is market-event-first. The prompt treats `market.chg_window` and short-term
  snapshots as the primary basis, `market.chg24h` as broader context, and news as supporting
  context only. News alone must return no alert, and a backend guard rejects clear news-only
  `should_alert=true` decisions before market event creation or delivery.
- Before Event Analysis calls Groq, the runtime checks a sanitized similar-context fingerprint
  against recent durable outcomes. Clear repeats of no-alert, news-only rejection, semantic
  cooldown suppression, similar-context reuse, or delivered decisions are recorded as
  `decision_stage = 'pre_llm'` and `decision_reason = 'similar_context_reused'` without creating a
  market event or calling the LLM.
- The Event Analysis input can include a compact sanitized `previous_event_alert` object with
  prior title, canonical key, semantic family, analysed-window move, related-news hash, possible
  action, and timestamp. It excludes Telegram IDs, raw messages, raw prompts, secrets, and private
  identity data.
- If a repeated check creates a fresh successful LLM attempt for an already-known market event, the
  fresh attempt must remain unattached and delivery must reuse the existing attached analysis id and
  sanitized text.
- Event analysis is skipped when no eligible recipients exist for the symbol.
- Active Groq backoff skips are persisted as `event_ai_analyses.status =
  'skipped_due_to_rate_limit'` and `alert_delivery_outcomes.reason_code =
  'llm_rate_limited'`.
- LLM allow/no-alert decisions are also persisted in `alert_delivery_outcomes` with sanitized
  `decision_stage`, `decision_reason`, `previous_alert_id`, and `context_fingerprint` fields.
- `context_fingerprint` for Event Alert outcomes is a stable similarity hash for operator reuse
  and reporting. Exact raw input hashes remain on `event_ai_analyses.input_hash`.
- Market Heartbeat generation remains separate from Event Alerts; heartbeat cadence should not
  suppress Event Alerts.

## Ops-Agent LLM Usage Evidence

The ops-agent `llm_usage_summary` collector groups sanitized usage by provider, call type, model,
status, and symbol. It reports call counts, prompt/completion/total token sums, latest call time,
rate-limit count, timeout count, and invalid-JSON/schema-error count.

The collector reads `llm_usage_logs` only. It does not call Groq, retry failed requests, inspect
raw prompts, or export provider response bodies.
