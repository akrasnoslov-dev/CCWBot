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
advances to the next provider on a rate limit, timeout, 5xx, auth, or network error, and on a
provider-side model failure. It surfaces a genuine request defect to the caller unchanged. When
every provider is exhausted it raises the exception each existing caller already handles, so the
deterministic fallback / `skipped_due_to_rate_limit` paths are unchanged — they now trigger only
after the whole chain is exhausted, not on the first Groq rate limit.

### Which 4xx responses fall back

A 4xx is not one thing, and treating it as one is what kept the fallback chain from engaging for
18 days when Groq decommissioned the `event_analysis` model. `error_reason` now distinguishes:

| `error_reason` | Meaning | Falls back? |
| --- | --- | --- |
| `provider_model_error` | `404 model_not_found`, `model_decommissioned`, and the equivalents from Cerebras/Gemini/Mistral | yes |
| `provider_json_validate_failed` | the provider's own JSON-mode validation rejected the model's output | yes |
| `provider_bad_request` | malformed parameters, oversized payload, context length exceeded | no |
| `provider_4xx` | any other 4xx (unchanged meaning) | no |

All four keep the `provider_` prefix, so consumers that match `provider_%` — including the
ops-agent `llm_failure_category_summary` query — continue to bucket them without modification.

`provider_json_validate_failed` is fallback-eligible on purpose. It means the model produced no
usable content, which is the same condition as a client-side `AIInvalidJsonError` — and that has
always advanced the chain here. Making the server-detected variant behave like the client-detected
one removes an inconsistency rather than adding retry cost: the prompt is fixed per call type and
not user-controlled, so a genuinely bad prompt already fans out across the chain today via the
client-side path, bounded to one pass. A malformed *request*, by contrast, would fail identically
everywhere and stays terminal.

### Circuit breaker

A `(call_type, provider, model)` triple that fails `LLM_BREAKER_FAILURE_THRESHOLD` times in a row
(default 5) is opened and skipped, then retried on the widening `LLM_BREAKER_BACKOFF_SECONDS`
schedule (default `60,300,900,3600`). When an interval elapses the triple goes half-open and the
next cycle probes it once; a success closes it immediately and clears all state, so a fixed
provider is used again on the very next cycle.

Three properties matter operationally:

- **Skipping is not failing.** An open primary is skipped *within* the same cycle, so the fallback
  answers that cycle. The breaker never costs a delivery opportunity.
- **Only failures that are a property of the triple count.** The counted set is exactly
  `provider_model_error`, `auth_error`, and `config_missing`. Everything else is excluded for a
  specific reason:
  - rate limits have their own `(provider, model)` backoff registry, and timeouts/5xx are
    transient — neither should latch a breaker open;
  - `provider_bad_request` and residual `provider_4xx` are terminal, so opening a breaker on them
    would skip the primary next cycle and hand the same defective request to the fallback,
    walking a purely client-side bug down the entire chain;
  - `provider_json_validate_failed` depends on the prompt, which carries fresh market data every
    cycle, and its client-side twin `AIInvalidJsonError` does not open a breaker either.
- **A skip is still recorded.** Each skipped attempt writes an `llm_usage_logs` row with
  `status = 'skipped_due_to_circuit_breaker'` and `error_reason = 'provider_circuit_broken'`,
  mirroring `skipped_due_to_rate_limit`. Without it a broken provider would simply stop appearing
  in the table once its breaker opened, and the evidence of an ongoing outage would fade out a few
  cycles after it began.

If every provider in a chain is circuit-broken, the router raises `AllProvidersFailedError` with
`circuit_broken=True`, which classifies as `provider_circuit_broken` rather than a generic
`other_error`, so "known-bad, waiting to probe" stays distinguishable from a fresh failure in
`event_ai_analyses.error_reason`.

Transitions log `ops_event=llm_breaker_opened` (WARNING), `ops_event=llm_breaker_half_open` and
`ops_event=llm_breaker_closed` (INFO), alongside the existing `llm_provider_switch` and
`llm_rate_limit_started` events. State is in-memory and per process; a restart clears it, costing
at most one extra probe per triple.

Set `LLM_BREAKER_ENABLED=false` to disable it entirely.

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

Defaults in brackets are the base budgets retained from the prior configuration.
`GROQ_EVENT_ANALYSIS_MAX_TOKENS` still works as the legacy name for the
event-analysis budget and is used when `LLM_EVENT_ANALYSIS_MAX_TOKENS` is unset.

The router resolves an effective budget per provider/model attempt. Plain models keep the base
answer ceiling; known thinking models add 1024, 8192, or 24576 completion tokens of reasoning
headroom for low, medium, or high effort so the configured JSON-answer capacity remains available.
This avoids raising a plain primary's ceiling merely because a thinking model exists later in the
fallback chain. Startup chain entries include `/max=N` for the effective attempt budget. The
sanity ceiling remains 32768; startup emits `llm_config_budget_risk` if answer budget plus reasoning
headroom would exceed it.

`reasoning_effort` (`low` / `medium` / `high`) defaults to `low` for reasoning-capable models and
is omitted for non-reasoning models. `LLM_REASONING_EFFORT` sets a global override that a
per-call-type variable overrides.

The gate for sending the parameter is the resolved **model identifier**, not the provider: a
provider serves reasoning and non-reasoning models side by side, and sending `reasoning_effort` to
a non-reasoning model is a 400 that the router treats as deterministic and does not fall back on.
A model counts as reasoning-capable when its identifier contains one of
`LLM_REASONING_MODEL_MARKERS` (default `gpt-oss,gemini-2.5`). In a chain that mixes plain and
reasoning models, a global `LLM_REASONING_EFFORT=low` reaches only the compatible attempts.

Only extend `LLM_REASONING_MODEL_MARKERS` for models whose provider actually accepts the
`reasoning_effort` request field. Gemini 2.5's OpenAI-compatible endpoint supports it and maps
`low` to a 1024-token thinking budget. Other thinking models stay outside the effort gate until
their endpoint contract is verified; known names still receive token headroom.

Groq GPT-OSS supports JSON Object Mode and `reasoning_effort`, but Groq explicitly documents that
GPT-OSS does **not** accept `reasoning_format`. Do not add that parameter to these requests; it is
for other Groq reasoning-model families.

The Groq defaults are `openai/gpt-oss-120b` for Event Analysis and `openai/gpt-oss-20b` for the
other structured call types. They replace the Llama 3 defaults scheduled to shut down on
2026-08-16. Their attempts use low reasoning effort and the additional headroom above.

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
  chain=groq:openai/gpt-oss-120b/effort=low/max=1324,cerebras:gpt-oss-120b/effort=low/max=1324(no_api_key)
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
blank keeps Groq-only behaviour. Rate-limit backoff is tracked per `(provider, model)` and is
consulted by every active call type; the triggering call type is logged for attribution. The
runtime LLM entry point remains `bot/services/ai_agent_groq.py`, now a thin facade over the router
that keeps all public names/signatures (`AIGroqRateLimitError` is an alias of the provider-agnostic
`AIProviderRateLimitError`).

The persisted analysis/report provider and model reflect the provider that actually answered.
Reports produced after provider-chain exhaustion use the explicit
`deterministic:deterministic-market-report-v1` attribution:
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
- `provider_model_error`
- `provider_json_validate_failed`
- `provider_bad_request`
- `provider_circuit_broken`
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

Latest known LLM rate-limit headers by provider, model, and call type:

```sql
SELECT DISTINCT ON (provider, model, call_type)
  provider,
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
ORDER BY provider, model, call_type, created_at DESC, id DESC;
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

- Admin System status summarizes final feature outcomes. Admin LLM diagnostics separately shows
  mutually exclusive provider-attempt categories whose displayed counts reconcile to the total.

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
- Before Event Analysis calls the LLM provider chain, the runtime checks a sanitized
  similar-context fingerprint
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
