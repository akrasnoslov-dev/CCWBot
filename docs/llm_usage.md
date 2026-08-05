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

## Models, token budgets, and reasoning effort

Model identifiers are provider-controlled and do change; a decommissioned model answers
`404 model_not_found`. Every call type is therefore configurable from the environment, so
adopting a replacement model is an `.env` edit and a restart, not a code deploy.

| Call type | Model | Completion budget | Reasoning effort |
| --- | --- | --- | --- |
| `event_analysis` | `GROQ_EVENT_ANALYSIS_MODEL` | `LLM_EVENT_ANALYSIS_MAX_TOKENS` (300) | `LLM_EVENT_ANALYSIS_REASONING_EFFORT` |
| `market_heartbeat` | `GROQ_MARKET_HEARTBEAT_MODEL` | `LLM_MARKET_HEARTBEAT_MAX_TOKENS` (350) | `LLM_MARKET_HEARTBEAT_REASONING_EFFORT` |
| `daily_report` / `weekly_report` / `market_report` | `GROQ_REPORT_MODEL` | `LLM_REPORT_MAX_TOKENS` (800) | `LLM_REPORT_REASONING_EFFORT` |
| `news_intelligence` | `GROQ_NEWS_INTELLIGENCE_MODEL` | `LLM_NEWS_INTELLIGENCE_MAX_TOKENS` (350) | `LLM_NEWS_INTELLIGENCE_REASONING_EFFORT` |

Defaults in brackets are the values these budgets previously had hardcoded, so an unconfigured
deployment is unchanged. `GROQ_EVENT_ANALYSIS_MAX_TOKENS` still works as the legacy name for the
event-analysis budget and is used when `LLM_EVENT_ANALYSIS_MAX_TOKENS` is unset.

One budget covers every provider in that call type's chain, so a chain whose fallback runs a
reasoning or thinking model needs a budget large enough for that model too. A per-provider budget
override is a known gap, not a supported configuration.

This matters for the shipped fallback defaults: `CEREBRAS_MODEL=gpt-oss-120b` reasons before it
answers, and `GEMINI_MODEL=gemini-2.5-flash` thinks by default; both draw those tokens from the
completion budget. At the llama-sized defaults (300 for `event_analysis`) those fallback attempts
have no room to produce JSON. Startup therefore logs
`ops_event=llm_config_budget_risk call_type=... provider=... model=... max_tokens=...` whenever a
chain member is a thinking model and the call type's budget is below 1024. Raise the budget for
that call type before relying on such a fallback.

`reasoning_effort` (`low` / `medium` / `high`) is omitted from the request payload entirely when
unset, so non-reasoning models are unaffected. `LLM_REASONING_EFFORT` sets a global default that a
per-call-type variable overrides.

The gate for sending the parameter is the resolved **model identifier**, not the provider: a
provider serves reasoning and non-reasoning models side by side, and sending `reasoning_effort` to
a non-reasoning model is a 400 that the router treats as deterministic and does not fall back on.
A model counts as reasoning-capable when its identifier contains one of
`LLM_REASONING_MODEL_MARKERS` (default `gpt-oss`). So with a `groq:llama-3.3-70b-versatile →
cerebras:gpt-oss-120b` chain, a global `LLM_REASONING_EFFORT=low` reaches only the Cerebras
attempt.

Only extend `LLM_REASONING_MODEL_MARKERS` for models whose provider actually accepts the
`reasoning_effort` request field. Gemini 2.5 and Mistral's reasoning models think internally but
their OpenAI-compatible endpoints reject the parameter, so adding a marker that matches them
converts a working fallback into a 400. The budget warning above covers those models instead.

`openai/gpt-oss-120b` and `openai/gpt-oss-20b` are reasoning models: reasoning tokens are drawn
from the same completion budget as the answer. At the llama-era budgets the model emits no JSON at
all and the call fails with `400 json_validate_failed` and an empty `failed_generation`. Raise the
call type's `*_MAX_TOKENS` substantially before pointing it at a gpt-oss model.

The completion budget is sent as `max_tokens`. All four providers accept it, and Groq documents it
as an alias of `max_completion_tokens`, so reasoning models receive the correct budget without a
per-provider payload difference. The `json_validate_failed` failures seen during the gpt-oss
migration attempt were caused by the budget being too small, not by the field name — sending
`max_completion_tokens` would not have changed the outcome.

An unparseable value for any of these variables — or one below 1 or above 32768 — is rejected with
a WARNING naming the variable and the rejected value (`ops_event=llm_config_invalid`), and the
default is used; a typo is never applied silently. The same applies to an unrecognised provider
name in `LLM_PROVIDER_PRIORITY` or a per-call-type chain override, which would otherwise shorten
the fallback chain invisibly. Values of credential-like variables are redacted before logging.

### Startup configuration log

On startup the runtime logs the fully resolved configuration, one INFO line per call type:

```text
ops_event=llm_config call_type=event_analysis max_tokens=300
  chain=groq:llama-3.3-70b-versatile,cerebras:gpt-oss-120b/effort=low(no_api_key)
```

This answers "is the running deploy actually using what I configured?" without reading `.env` on
the server — the case that made the 2026-07 event-analysis outage hard to diagnose, since the code
default and the deployed `.env` disagreed. `(no_api_key)` marks a provider that the router will
exclude from the chain. The line carries provider names, model identifiers, budgets, and effort
only — never credentials. An API key appears only as the `(no_api_key)` presence marker; the key
value itself is never read into a log line.

Changing a model identifier also invalidates the news-intelligence analysis cache, which is keyed
on `(news item, llm_model)`. Expect one bounded re-analysis burst after a model swap, capped by
`NEWS_INTELLIGENCE_MAX_LLM_CALLS_PER_RUN` and `NEWS_INTELLIGENCE_MAX_LLM_CALLS_PER_HOUR`.

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
