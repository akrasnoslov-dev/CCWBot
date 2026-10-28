# LLM Usage Reporting

`llm_usage_logs` records one row per LLM call attempt when database storage is enabled. The
`provider` column names which provider handled the request, so per-provider statistics come from
grouping by `provider` — no separate telemetry system. Historical rows retain the provider value
recorded at the time of the call.

## Provider fallback (redundancy)

Groq is the primary LLM provider. The built-in general chain is
`groq,openai,cloudflare`; Daily/Weekly Reports and the legacy `market_report` alias deliberately
use `groq,openai` and then their verified data-only fallback. Per-feature overrides are
`LLM_EVENT_PROVIDERS`, `LLM_EVENT_RENDER_PROVIDERS`, `LLM_NEWS_INTELLIGENCE_PROVIDERS`,
`LLM_HEARTBEAT_PROVIDERS`, and `LLM_REPORT_PROVIDERS`.

Reports do not inherit `LLM_PROVIDER_PRIORITY`: without an explicit non-empty
`LLM_REPORT_PROVIDERS`, Daily, Weekly, and legacy `market_report` always use the
built-in Groq -> optional OpenAI chain, followed by the deterministic data-only
renderer. This prevents a global Cloudflare fallback from silently entering the
report path; a report-specific override remains an intentional operator action.

OpenAI is excluded before client construction unless `OPENAI_ENABLED=true`; an API key alone does
not enable it. Therefore the shipped free-only chains are Groq -> Cloudflare for Event Analysis,
Render, News Intelligence and Heartbeat, and Groq -> data-only for reports. Cloudflare is skipped
when its token/account ID is absent.
No provider is called inside recipient loops, and the result is attributed to the actual
provider/model that answered. This does not change Event Alert significance rules.

For Event Analysis, the pinned Cloudflare Workers AI
`@cf/meta/llama-3.3-70b-instruct-fp8-fast` model now receives a **bare JSON Schema**
in `response_format.json_schema` when JSON mode is enabled, not the
`{name, strict, schema}` envelope used by Groq. This constrains six required
fields, JSON types and enum values before the existing strict semantic validator.
Other Cloudflare model overrides retain `json_object` until schema support is
verified. The Cloudflare endpoint can still reject its own schema-mode output,
and a schema-compliant response can still be logically contradictory; both
remain fallback-eligible invalid output, never an implicit `no_alert`.
Provider order, request count, budget, significance rules and recipient delivery
are unchanged. Offline tests verify the request contract and reject synthetic
invalid outputs; they do **not** establish an improvement in live Cloudflare
success rate, latency, or billable/free-tier inference cost. Check sanitized
post-release provider-attempt telemetry before claiming a quality improvement.

Gemini, Qwen Preview, and Mistral have been retired from active routing. Stale provider-priority
entries are rejected with sanitized warnings; historical usage telemetry is retained. Cloudflare Workers AI has a finite free
daily neuron quota (10,000 neurons/day as of October 2026); it does not guarantee capacity.
See https://developers.cloudflare.com/workers-ai/platform/pricing/ .

`event_alert_render` uses `Groq openai/gpt-oss-20b -> optional OpenAI gpt-6-luna ->
Cloudflare @cf/meta/llama-3.3-70b-instruct-fp8-fast`. Its Groq model is independently
configurable with `GROQ_EVENT_RENDER_MODEL`; it no longer shares the 120B Event Analysis slot.
Cloudflare requires both `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`.
Model environment variables are intentional overrides, not normal required configuration: leave
them unset in ordinary deployments so pinned code defaults stay authoritative.

The project-wide zero-cost/free-tier service policy is owned by `docs/project_context.md`.
For LLM capacity problems, apply that guardrail by checking supported free-tier models, call
efficiency, caching/reuse, and graceful degradation before considering any paid provider tier.

### CCW-20 owner-selected Event Alert provider order

For the next reviewed deployment, the owner chose **Cloudflare -> budget-guarded
OpenAI GPT-6 Luna -> Groq** for both `event_analysis` and `event_alert_render`.
Set both explicit per-call-type overrides in the actual deployment `.env`:

```dotenv
LLM_EVENT_PROVIDERS=cloudflare,openai,groq
LLM_EVENT_RENDER_PROVIDERS=cloudflare,openai,groq
```

The global provider priority and dedicated report chains are unaffected by these
two overrides. The shipped code's default without these variables stays Groq-first.
`.env.example` is only a template; editing it does not alter the server's `.env`.
Restarting/recreating the runtime after a reviewed configuration change is needed
to load updated environment variables. PR #378 merged this provider-order
support into `main` source; verify actual server settings and deployed revision
separately.

OpenAI does **not** become usable just because its key is present or second in
the chain: it requires `OPENAI_ENABLED=true`, a nonempty API key, the exact
`OPENAI_MODEL=gpt-6-luna` (other models fail closed), a positive remaining
UTC-month budget, and working budget DB. GPT-6 Luna's verified pricing and
input ceiling are pinned in code; no separate pricing environment variables are required.
When budget-blocked, it is skipped without an HTTP call and Groq is attempted
last if available. Do not bypass the local USD $2.50/month limit.

For Render, changing provider order must retain
`CLOUDFLARE_EVENT_RENDER_MODEL` (and `GROQ_EVENT_RENDER_MODEL`)
rather than silently selecting generic models. The focused source release #378 contract-tests these model overrides.

For a future quality evaluation, use **one bounded 20-case / maximum 40-call Cloudflare-only
paired final-copy test** (20 same sanitized positive events with old vs new
Stage-2 Render+fallback); record raw model text, schema checks, compaction/
replacement and final assembled Telegram message, not just generated draft.
Do not invoke the full production provider cascade for this *quality* comparison:
letting one candidate silently fall back to Luna would compare different models
and make the verdict invalid. Do not make paid Luna or Groq requests for this test.
Stop on Cloudflare quota exhaustion; no automatic retry or expanded cohort.
A separate provider-order contract test uses mocked providers with no tokens.

This section records an **approved direction**, not a measured improvement or
confirmation that the Cloudflare service is currently reachable. Official
Cloudflare Workers AI Free allocation is 10,000 neurons/day, shared across
the account. Finite free quota and output-format compatibility must be verified
from actual response/attempt telemetry. The test does not send Telegram messages.

### Optional OpenAI activation and spend cap

OpenAI ships disabled. **Exactly four OpenAI environment settings** are used for the
only approved paid model, `gpt-6-luna`:

```dotenv
OPENAI_ENABLED=true
OPENAI_API_KEY=<secret>
OPENAI_MODEL=gpt-6-luna
OPENAI_MONTHLY_BUDGET_USD=2.50
```

The model's pricing and model-wide input ceiling are pinned in
`bot/services/llm/openai_budget.py` and are **not configurable from `.env`**.
As verified against OpenAI's [GPT-6 Luna model page](https://developers.openai.com/api/docs/models/gpt-6-luna)
and [API pricing](https://developers.openai.com/api/docs/pricing) on 2026-10-26,
the context window is 1,050,000 tokens; Standard short-context prices are
$0.10 / 1M input and $0.50 / 1M output. Long contexts (>272K input) cost 2x
input and 1.5x output; cache writes can cost 1.25x uncached input. The guard
conservatively reserves **$0.25 / 1M input** and **$0.75 / 1M output** for
*all* requests, including short prompts, to avoid undercounting these tiers.
This deliberately overstates local spending versus ordinary short prompts.
Only Standard API requests via the default OpenAI endpoint (no Fast, regional
processing or tool-related paid charges) are in scope. Before enabling a new
billing mode or if OpenAI changes pricing/context, review and update the code.

The single global UTC-calendar-month local cap is at most **$2.50**. Missing
database state, malformed/exhausted budget, or a model other than the verified
`gpt-6-luna` skips OpenAI **before HTTP** and proceeds to the next provider.

Before each request, `openai_budget_reservations` atomically reserves the verified full model input
ceiling plus maximum completion/reasoning cost. This deliberately covers Unicode, provider chat
framing, and response schemas without relying on a token estimate. PostgreSQL advisory locking serializes authorization across
workers; the ledger survives restarts. Known token usage reconciles the reservation, while timeout,
5xx, missing usage, or failed reconciliation retains the conservative amount. This is a CCWBot-side
guard, not an OpenAI organization-wide invoice guarantee; other clients on the same
API account and future rate changes are not controlled here. Live API compatibility
and price review are still part of production activation.

The router (`bot/services/llm/router.py`) tries each configured provider/model entry in order. It
advances on a rate limit, timeout, 5xx, auth, network error, provider-side model failure, or invalid
validated output. It surfaces a genuine request defect to the caller unchanged. Generic call types
retain their existing terminal handling after chain exhaustion. Event Alert Render fails closed
when any exhausted attempt has a transport, rate-limit, backoff, unavailable-model, or
circuit-breaker failure. Only exhaustion consisting exclusively of invalid model output
(client-side JSON/schema rejects or provider-side `provider_json_validate_failed`) permits
backend-derived deterministic presentation, subject to full factual validation below.
Providers excluded for missing credentials are not attempted; if none is configured, Render is
terminal. No further LLM calls are made during deterministic recovery.

### Event Analysis timeout and operation budget

Event Analysis uses **one HTTP request per configured provider/model**, ordered by
`LLM_EVENT_PROVIDERS` or the generic provider priority (default Groq -> optional OpenAI -> Cloudflare).
The OpenAI-compatible SDK has `max_retries=0`; neither HTTP 5xx nor timeout causes a
same-provider retry. Such failures advance to the next available provider, unless the operation
budget is exhausted. HTTP 429 activates the existing provider/model backoff; an explicit
billing/quota code instead falls back without treating quota exhaustion as transient 429.
Malformed requests remain terminal and never fan out.

Each provider attempt defaults to a 15-second timeout. The Event Analysis chain has a **90s**
monotonic-clock budget covering HTTP requests, provider telemetry writes, rate-limit/breaker
skips and response validation. Nominal HTTP ceilings total 45s, leaving 45s for processing.
Before any new HTTP attempt the router checks remaining time, shortens its timeout
when necessary, and makes no new request when fewer than 1s remain. A timeout at the
remaining deadline, including on the final provider or during logging/validation, gets
the sanitized terminal `operation_budget_exhausted` reason, not a false provider 429
or a successful operation. A forced cancellation can leave an individual provider-attempt
telemetry row missing, but the terminal feature outcome still carries the reason and
the logical `llm_operation_id`.

`LLM_EVENT_ANALYSIS_OPERATION_BUDGET_SECONDS` adjusts the total budget (default 90, allowed 15-120).
Explicit caller timeouts still override the per-provider default but remain bounded by
the remaining operation budget. All other call types retain their shared 15s timeout,
including Event Alert Render. No extra LLM requests are added. These settings do not
change event significance or delivery logic.

A production check should use sanitized startup configuration and correlated `llm_usage_logs`
attempt/final-outcome timestamps to compare timeout counts, fallback recovery, and active-backoff
skips.

### Which 4xx responses fall back

A 4xx is not one thing, and treating it as one is what kept the fallback chain from engaging for
18 days when Groq decommissioned the `event_analysis` model. `error_reason` now distinguishes:

| `error_reason` | Meaning | Falls back? |
| --- | --- | --- |
| `provider_model_error` | `404 model_not_found`, `model_decommissioned`, and provider equivalents | yes |
| `provider_quota_exhausted` | `402`, `payment_required`, or an explicit provider billing/quota code | yes |
| `provider_json_validate_failed` | the provider's own JSON-mode validation rejected the model's output | yes |
| `provider_bad_request` | malformed parameters, oversized payload, context length exceeded | no |
| `provider_4xx` | any other 4xx (unchanged meaning) | no |

These categories keep the `provider_` prefix, so consumers that match `provider_%` — including the
ops-agent `llm_failure_category_summary` query preserves these two categories separately. It also
keeps actual provider rate limits distinct from active-backoff and circuit-breaker skips, and
groups sanitized provider/model attempt pressure without exporting provider error messages.

`llm_usage_logs` is provider-attempt telemetry. Each new logical LLM operation receives one
opaque backend UUID in `llm_operation_id`; every provider attempt, fallback, pre-call backoff
skip, and circuit-breaker skip for that operation keeps the same value. The final
`event_ai_analyses`, `market_heartbeats`, and `market_reports` row stores the same nullable value,
so ops can join attempts to the terminal feature outcome without timing inference. News
Intelligence stores one sanitized terminal row in `llm_operation_outcomes`; its cached
`news_items.llm_provider/llm_model` fields identify the provider and model that actually answered.
Historical rows remain `NULL`; a telemetry write can still fail open, which is an evidence gap
rather than proof of no attempt. The identifier contains no user identity, Telegram ID, prompt,
output, or secret.

News Intelligence uses a strict JSON Schema for supported Groq models when JSON mode is enabled and
for the optional OpenAI attempt, including an allowlisted nullable `primary_symbol` and all eleven
required fields. Other active models keep their provider-compatible response format. The prompt explicitly uses
`primary_symbol=null` for no clear single coin, including multi-coin and irrelevant news.
Backend schema validation remains mandatory for every provider: an unsupported symbol is an
invalid output, not a silently reassigned primary or a successful intelligence result. Invalid
output still follows the configured provider fallback; if the chain is unavailable, the news
operation is recorded as failed. This changes neither provider priority nor request count.
Offline request-shape tests do not establish live provider compliance or success rates.

The News Intelligence cache hash includes the compact input and configured requested model, while
served-provider attribution stays in the cached row. This preserves exact cache invalidation on a
configured model change and permits fallback results to be reused without pretending Groq served
them. Pre-migration input hashes remain reusable when their configured model matches.

Hourly RSS ingestion also revisits persisted `failed` and `skipped_budget` news
items from the last 24 hours, after a one-hour per-item cooldown, even if they
are no longer returned by RSS. At most one recovery item reserves a new-work
slot when the configured per-run cap is greater than one; all other fresh work
keeps priority. Recovery uses the existing per-run and hourly logical LLM
budgets and writes a new, correlated terminal operation only when an LLM is
actually attempted. Successful cache entries are reused, not reanalyzed.
Items older than the 24-hour recovery window are not automatically retried.

The News Intelligence hourly call budget counts logical `llm_operation_outcomes` across all providers. Migration 0029 creates a
non-overlapping legacy budget snapshot for prior successful/failed News rows, so new retries and
reanalyzes remain additive without a permanent time scan over `news_items`.

Only explicit response-header allowlist fields are persisted. `provider_request_id` is retained
when `x-request-id` or `request-id` is available; raw headers and bodies are never stored. Groq
request/token counters, resets, retry metadata, and request IDs still cannot distinguish quota,
burst, concurrency, or account-policy enforcement unless Groq supplies an explicit safe signal.

`provider_json_validate_failed` is fallback-eligible on purpose. It means the model produced no
usable content, which is the same condition as a client-side `AIInvalidJsonError` — and that has
always advanced the chain here. Making the server-detected variant behave like the client-detected
one removes an inconsistency rather than adding retry cost: the prompt is fixed per call type and
not user-controlled, so a genuinely bad prompt already fans out across the chain today via the
client-side path, bounded to one pass. A malformed *request*, by contrast, would fail identically
everywhere and stays terminal.

### Historical Gemini 429 quota classification and backoff

This retained telemetry behavior applies only to historical Gemini records and direct compatibility
tests; Gemini is not in the runnable provider registry. Google's structured
`google.rpc.QuotaFailure` `quotaId` distinguishes a daily
quota from a per-minute 429. When Gemini explicitly reports a per-day
quota violation, the router records `provider_quota_exhausted` and advances to the
existing fallback provider. A concrete provider `Retry-After`/`RetryInfo`
sets the next eligible probe time without overriding it with a timezone estimate.
When the provider supplies no usable hint, the model is skipped until the next
midnight in `America/Los_Angeles` (Google's documented RPD reset).
The skip makes no HTTP call. The fallback midnight is a safety assumption,
not evidence that capacity will be available. Production hints can differ
from the documented reset, so prefer the direct provider signal.
Other quota/billing identifiers retain their existing treatment. No configured
provider order changes.

For ordinary transient 429s, the backoff parser follows response-header hints,
then Google's structured `google.rpc.RetryInfo.retryDelay`, then a text hint or
the existing safe default. Fractional seconds are rounded **up** rather than
retrying earlier than the provider's requested delay. HTTP 5xx and timeouts
do not arm this rate-limit backoff. There are no same-provider retries.
Actual per-project/model limits still require inspection of the production
account's AI Studio limits/usage; a 429 alone does not establish them.

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
  `provider_model_error`, `provider_quota_exhausted`, `auth_error`, and `config_missing`.
  Everything else is excluded for a
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

## Groq free-tier admission control (Event Analysis)

The Groq pre-call budget guard uses the provider's published free-plan GPT-OSS ceilings
(8K TPM, 200K TPD, 1K RPD, 30 RPM) as conservative **planning** values. Defaults are
7,200 tokens/minute, 180,000 tokens/rolling 24 hours, 900 requests/rolling 24 hours,
and 27 requests/minute **per model**; operators may lower them using
`GROQ_FREE_TOKEN_BUDGET_MINUTE`, `GROQ_FREE_TOKEN_BUDGET_DAY`,
`GROQ_FREE_REQUEST_BUDGET_DAY`, and `GROQ_FREE_REQUEST_BUDGET_MINUTE`.
These estimates are not authoritative for a particular Groq account; organization-level
traffic outside the bot and provider-side policy remain unknown. The existing `max_tokens`
ceiling and `reasoning_effort` are **unchanged**.

The guard reserves a conservative estimated token cost under one async lock *before* the
actual HTTP request, then reconciles with provider-reported `total_tokens`. Groq response
headers constrain remaining RPD (request headers) and TPM (token headers) until their
respective advertised resets. The 24h RPD/TPD approximation is rebuilt from existing
`llm_usage_logs` actual provider-attempt rows when the process starts; skip rows count as
neither requests nor consumed tokens. If telemetry storage is unavailable, only in-process
usage plus observed provider headers are available. This gap is logged, not silently treated
as confirmed quota state.

The four scheduled coin jobs are already staggered; an additional 20% rolling-day token
allocation for each of BTC, ETH, GRAM, SOL prevents one symbol using all the shared Groq
Event Analysis budget. The remaining 20% stays available to render/report/other operations.
No numeric budget gate affects the *market-significance decision*: the guard only decides
which provider may be asked to make that decision.

A budget refusal makes **zero** HTTP calls, writes an attempted-provider skip with
`error_reason=rate_limit_budget_exhausted`, and advances the existing provider fallback
chain. If every configured provider is unavailable, Event Analysis still writes a terminal
`event_ai_analyses` and `alert_delivery_outcomes` row (`rate_limited`), using the same
logical `llm_operation_id` as its attempted-provider rows. It never records `no_alert`
or manufactures significance. A deferred, stale market context is **not** replayed hours
later; the next scheduled check instead analyzes current data. Available fallback API keys
must be configured separately; with Groq only, the free TPD budget necessarily limits
coverage. No provider entry is retried inside the logical operation.

Groq's standard request headers expose RPD, and its token headers expose TPM, **not TPD**.
A 429 alone cannot distinguish TPD exhaustion, hidden organization policy, input/output
split quotas, or short bursts. Use the correlated operation IDs, attempt statuses, the
bounded saved headers, and provider `retry-after` to evaluate actual production causes;
label uncertain causes as hypotheses. Compare actual HTTP attempts (excluding skips) to
terminal logical outcomes (`event_ai_analyses`) rather than treating every attempt as an
independent Event Analysis.

Only the Groq model actually configured for Event Analysis reserves symbol capacity
(when Groq is in that task's provider chain): BTC, ETH, GRAM and SOL each have a
protected 20% daily token share. Render/reports/other tasks sharing **that model**
use its remaining 20%. Other Groq models (including the default 20B report model)
retain their normal full-model planning budgets; they have no idle event reservations.
The guard is conservative planning, not proof of live account capacity. Historical
usage before rollout can exceed the new shares until it ages out. HTTP failures
with ambiguous token consumption retain a reservation, reconstructed after restart
from the stored input length and request ceiling when actual usage is unavailable.
Only confirmed pre-generation rejections release their reserved tokens.

## Models, token budgets, and reasoning effort

Model identifiers are provider-controlled and do change; a decommissioned model answers
`404 model_not_found`. Every call type is therefore configurable from the environment, so
adopting a replacement model is an `.env` edit and a restart, not a code deploy.

| Call type | Model | Completion budget | Reasoning effort |
| --- | --- | --- | --- |
| `event_analysis` | `GROQ_EVENT_ANALYSIS_MODEL` | `LLM_EVENT_ANALYSIS_MAX_TOKENS` (300) | `LLM_EVENT_ANALYSIS_REASONING_EFFORT` (default `medium`) |
| `event_alert_render` | Groq GPT-OSS 20B -> optional OpenAI Luna -> Cloudflare Llama 3.3 70B | `LLM_EVENT_ANALYSIS_MAX_TOKENS` (300) | model-dependent |
| `market_heartbeat` | `GROQ_MARKET_HEARTBEAT_MODEL` | `LLM_MARKET_HEARTBEAT_MAX_TOKENS` (350) | `LLM_MARKET_HEARTBEAT_REASONING_EFFORT` |
| `daily_report` / `weekly_report` / `market_report` | `GROQ_REPORT_MODEL` | `LLM_REPORT_MAX_TOKENS` (800) | `LLM_REPORT_REASONING_EFFORT` |
| `news_intelligence` | `GROQ_NEWS_INTELLIGENCE_MODEL` | `LLM_NEWS_INTELLIGENCE_MAX_TOKENS` (350) | `LLM_NEWS_INTELLIGENCE_REASONING_EFFORT` |

`event_analysis` is the compact always-on significance decision. `event_alert_render` runs only
after a positive significance decision and returns three presentation fields:
`message_body`, `related_news_ids`, and `possible_action`. The backend controls `urgency`
(`normal`), event identity, the deterministic market-fact title, `symbol`,
`should_alert=true`, significance `confidence`, and `reason_for_no_alert=null`
before running the full factual/news validation. Unknown or duplicate
render-selected news IDs are discarded.

When every configured render attempt fails exclusively with invalid JSON or invalid schema,
and no attempt fails on transport/rate-limit/backoff or is skipped by a circuit breaker,
the backend may generate a neutral deterministic message from verified market context.
Recovery is still subject to the factual validator, and flat, news-led contexts
cannot bypass the news-only safeguard by dropping related_news_ids.
The logical Render outcome records success with the sanitized reason
`deterministic_fallback_from_*` while invalid provider attempts remain recorded
in `llm_usage_logs`. Mixed failure chains, unavailable providers, or an invalid
deterministic fallback remain terminal. No extra LLM call is made for recovery.

The Render prompt additionally receives compact verified non-numeric market
relationship labels. This gives it trajectory evidence without raw market
prices or snapshots, and does not alter the upstream significance decision.
Successful provider output and the final Telegram text are tracked separately:
post-render guard replacement does not count as a provider fallback and is
not expressed by alerts.fallback_mode. See docs/observability.md.

The render operation has its own logical operation id and sanitized terminal outcome. Significance
and rendering therefore remain separately attributable: Event Analysis uses its normal
significance chain, while rendering uses the dedicated model-level chain above.

Defaults in brackets are the base budgets retained from the prior configuration.
`GROQ_EVENT_ANALYSIS_MAX_TOKENS` still works as the legacy name for the
event-analysis budget and is used when `LLM_EVENT_ANALYSIS_MAX_TOKENS` is unset.

The router resolves an effective budget per provider/model attempt. Plain models keep the base
answer ceiling; known thinking models add 1024, 8192, or 24576 completion tokens of reasoning
headroom for low, medium, or high effort so the configured JSON-answer capacity remains available.
Groq Event Analysis is the provider-specific exception: its shipped medium-effort attempt is capped
at `max_tokens=6300` so the compact prompt plus requested completion remains below Groq's 8K
free-tier token-per-minute capacity. This capacity guard does not affect alert significance.
This avoids raising a plain primary's ceiling merely because a thinking model exists later in the
fallback chain. Startup chain entries include `/max=N` for the effective attempt budget. The
sanity ceiling remains 32768; startup emits `llm_config_budget_risk` if answer budget plus reasoning
headroom would exceed it.

`reasoning_effort` (`low` / `medium` / `high`) defaults to `medium` for `event_analysis` and `low`
for the other reasoning-capable call types; it is omitted for non-reasoning models.
`LLM_REASONING_EFFORT` sets a global override that a per-call-type variable overrides.

The gate for sending the parameter is the resolved **model identifier**, not the provider: a
provider serves reasoning and non-reasoning models side by side, and sending `reasoning_effort` to
a non-reasoning model is a 400 that the router treats as deterministic and does not fall back on.
A model counts as reasoning-capable when its identifier contains one of
`LLM_REASONING_MODEL_MARKERS` (default `gpt-oss,gpt-6,gemini-2.5,gemini-3.`; Gemini markers are
retained for historical compatibility). In a chain that mixes
plain and reasoning models, a global `LLM_REASONING_EFFORT=low` reaches only the compatible
attempts.

Only extend `LLM_REASONING_MODEL_MARKERS` for models whose provider actually accepts the
`reasoning_effort` request field. The retained historical Gemini compatibility notes are that
Gemini 2.5 and Gemini 3 support it through Google's
OpenAI-compatible endpoint. Gemini 2.5 maps effort to fixed thinking budgets; Gemini 3 maps effort
to thinking levels and uses dynamic thought-token allocation. The existing headroom remains a
bounded client-side safety allowance rather than a provider-guaranteed Gemini 3 thinking budget. Other
thinking models stay outside the effort gate until their endpoint contract is verified.

Gemini 3.x requests intentionally omit explicit sampling parameters such as `temperature`.
Google's Gemini 3.8 migration guidance deprecates `temperature`, `top_p`, and `top_k` for this
model family. The shared OpenAI-compatible provider keeps the existing `temperature=0.0` behavior
for Groq, Cloudflare, and pre-Gemini-3 models; the Gemini adapter removes it only for resolved
`gemini-3.*` model identifiers.

Groq GPT-OSS and optional OpenAI support strict JSON Schema Structured Outputs. Verified Groq
models use `response_format.type=json_schema` with
`strict=true`; existing application validators still run afterwards for semantic, grounding,
active-symbol, safety, and non-empty checks. Cloudflare uses its supported bare JSON Schema for
Event Analysis; an operator-supplied Groq model outside the verified strict-schema allowlist keeps JSON Object Mode so one provider's
strict-schema contract cannot make another provider's request incompatible. For reports, the
strict provider schema requires every top-level field and every `coin_cards` object field,
preventing the missing-field payload that caused the 2026-09-29 Daily Report fallback incident.
`GROQ_JSON_MODE=false` disables Groq/default response-format modes while preserving the OpenAI and
supported Cloudflare provider-specific schemas and application parsing
and fallback behavior.

Groq GPT-OSS does **not** accept `reasoning_format`. Do not add that parameter to these requests;
it is for other Groq reasoning-model families.

The Groq defaults are `openai/gpt-oss-120b` for Event Analysis and `openai/gpt-oss-20b` for the
other structured call types. They replace the Llama 3 defaults scheduled to shut down on
2026-08-16. Event Analysis uses medium reasoning effort by default; its Groq attempt is capped at
6300 effective completion tokens for free-tier TPM safety. The other shipped reasoning call types
use low effort, with the matching additional headroom above.

The completion budget is sent to Groq and Cloudflare as `max_tokens`; Groq documents it as an
alias of `max_completion_tokens`. The native OpenAI adapter sends the same resolved budget as
`max_completion_tokens`, matching that API's reasoning-model contract. The historical
`json_validate_failed` failures seen during the gpt-oss migration attempt were caused by the
budget being too small, not by the Groq field name.

An unparseable value for any of these variables — or one below 1 or above 32768 — is rejected with
a WARNING naming the variable and the rejected value (`ops_event=llm_config_invalid`), and the
default is used; a typo is never applied silently. The same applies to an unrecognised provider
name in `LLM_PROVIDER_PRIORITY` or a per-call-type chain override, which would otherwise shorten
the fallback chain invisibly. Values of credential-like variables are redacted before logging.

### Startup configuration log

On startup the runtime logs the fully resolved configuration, one INFO line per call type:

```text
ops_event=llm_config call_type=event_analysis max_tokens=300
  chain=groq:openai/gpt-oss-120b/effort=medium/max=6300,
  openai:gpt-6-luna/effort=medium/max=8492(disabled),
  cloudflare:@cf/meta/llama-3.3-70b-instruct-fp8-fast/max=300(no_api_key)
  operation_budget_seconds=90
```

The example is line-wrapped for readability; runtime emits one line. For `event_analysis`, the
same startup line also includes `operation_budget_seconds=90` with the actual sanitized value.
This answers "is the running deploy actually using what I configured?" without reading `.env` on
the server — the case that made the 2026-07 event-analysis outage hard to diagnose, since the code
default and the deployed `.env` disagreed. `(no_api_key)` marks a provider that the router will
exclude from the chain, while `(disabled)` marks OpenAI's explicit kill switch. The line carries
provider names, model identifiers, budgets, and effort only — never credentials. An API key appears
only as the `(no_api_key)` presence marker; the key value itself is never read into a log line.

Changing the configured model identifier also invalidates the model-aware News Intelligence input
hash. Expect one bounded re-analysis burst after a model swap, capped by
`NEWS_INTELLIGENCE_MAX_LLM_CALLS_PER_RUN` and `NEWS_INTELLIGENCE_MAX_LLM_CALLS_PER_HOUR`.

A provider with no API key is excluded from the chain (logged once), so leaving the fallback keys
blank keeps Groq-only behaviour. Rate-limit backoff is tracked per `(provider, model)` and is
consulted by every active call type; the triggering call type is logged for attribution. The
runtime LLM entry point remains `bot/services/ai_agent_groq.py`, now a thin facade over the router
that keeps all public names/signatures (`AIGroqRateLimitError` is an alias of the provider-agnostic
`AIProviderRateLimitError`).

Persisted provider/model attribution follows the logical feature row that owns it. For two-stage
Event Alerts, `event_ai_analyses.provider/model/llm_operation_id` and its raw/parsed response belong
to the `event_analysis` significance stage; the separate `event_alert_render` provider/model/status
are recorded in `llm_operation_outcomes`, and the allowed delivery outcome links the render
operation id for forensic correlation. Reports produced after provider-chain exhaustion use the
explicit `deterministic:deterministic-market-report-v1` attribution. `market_reports.provider/model`
and `news_items.llm_provider/llm_model` follow the fallback, not a hardcoded `groq`. Admin
diagnostics (`bot/observability/system_status.py`) and the ops-agent `llm_usage_summary` collector
are provider-agnostic.

When a logical provider chain exhausts, the router emits one
`ops_event=llm_chain_exhausted` WARNING containing only `provider:error_reason` categories and
circuit-breaker skip names. It never includes provider bodies, prompts, model output, credentials,
or user data. Detailed sanitized provider messages and allowlisted rate-limit headers remain in
`llm_usage_logs` for read-only investigation.

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
- `operation_budget_exhausted` (Event Analysis chain deadline; no new provider request)
- `auth_error`
- `provider_model_error`
- `provider_quota_exhausted`
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

Event Alert call placement, reuse, and delivery invariants are owned by `alert_logic.md`.
Use `observability.md` for read-only diagnostics of those invariants.

## Ops-Agent LLM Usage Evidence

The ops-agent `llm_usage_summary` collector groups sanitized usage by provider, call type, model,
status, and symbol. It reports call counts, prompt/completion/total token sums, latest call time,
rate-limit count, timeout count, and invalid-JSON/schema-error count.

The collector reads `llm_usage_logs` only. It does not call Groq, retry failed requests, inspect
raw prompts, or export provider response bodies.

### Admin OpenAI Platform Costs monitoring (optional, read-only)

The `/admin` → **OpenAI Costs** screen compares the existing conservative
`openai_budget_reservations` ledger with
[OpenAI Platform Costs](https://developers.openai.com/api/reference/resources/admin/subresources/organization/subresources/usage/methods/costs),
`GET /v1/organization/costs`. This **does not change** the pinned model,
prices, reserve/settle behavior, or the $2.50 UTC-month admission limit.
The hard admission guard continues to use only the local database; provider
Costs data is delayed and is never an admission source of truth.

The monitor requests daily UTC buckets from the first of the current month
through **00:00 UTC today (exclusive)**. It deliberately excludes today's
partial bucket. It requests one explicit project ID and `group_by=project_id`,
verifies each result belongs to the configured project, follows pagination,
validates USD, and sums decimal amounts without binary-floating rounding.
Missing days, invalid data, other/unknown project attribution, auth/network
errors and incomplete pages all report **UNAVAILABLE**, never fake $0. A
successful response is cached in memory for one hour and is fetched only on
opening the screen. Cache resets on process restart. The private admin screen
uses the existing Telegram allowlist/DB-role check and Back navigation.

The internal section counts each reservation **once**, exactly as admission:
`actual_usd` when known, otherwise `reserved_usd`. Its breakdown is
`settled`/cap-breach actual estimates, still-`reserved` pending charges,
and `conservative` unreconciled charges. The local used/remaining values
cover the entire current UTC month, including today. The difference compares
the provider result with the current state of local ledger rows **created
before the provider coverage end**; older rows may have been reconciled since
that day. These are conservative internal estimates, not invoice charges.
Provider totals may include non-inference costs and may be backfilled.

Three independent opt-in variables (in addition to the four inference settings)
are available. All remain unset/false by default:

```dotenv
OPENAI_COSTS_ADMIN_KEY=
OPENAI_COSTS_PROJECT_ID=
OPENAI_COSTS_SCOPE_CONFIRMED=false
```

**Credential creation and minimum privileges (owner-only, manual):**

1. Sign in to the **OpenAI API Platform**, not ChatGPT Admin Console. Select
   the correct API organization. Only an API Platform organization owner can
   create its Admin keys.
2. Under API Platform **Organization settings → Admin keys**, create a
   dedicated, expiring key for this monitor. Select only the **Usage: Read**
   permission (`api.usage.read`); deny organization administration, projects
   management, writes, inference and other scopes. Verify the actual key scope
   selection exposed to this organization before using it. Do not mistake
   the ChatGPT workspace Costs permission for this API permission.
3. **If the Platform cannot issue an Admin key limited to Usage Read, STOP.**
   Do not place an unrestricted or broadly privileged Admin key in the bot
   runtime. Leave the feature `NOT CONFIGURED` and instead use a separate
   trusted, access-controlled cost-export/broker that stores the Admin key
   outside the bot and releases only CCWBot-project aggregates. Such a broker
   requires a separately reviewed implementation; this PR does not add one.
4. In API Platform **Projects**, verify the dedicated CCWBot project ID
   (format `proj_...`). Confirm the bot's **inference key actually belongs
   to that project** and that no other clients or cost-bearing features use
   it. The local ledger has no project-ID column. Only after this audit,
   set `OPENAI_COSTS_SCOPE_CONFIRMED=true` to enable the numeric difference.
   Otherwise the difference remains `NOT COMPARABLE`.
5. Store the restricted key solely in an operator-controlled secret store or
   protected deployment environment as `OPENAI_COSTS_ADMIN_KEY`. Store the
   verified project ID as `OPENAI_COSTS_PROJECT_ID`. Never commit a populated
   env file, expose values in a Telegram chat, reuse `OPENAI_API_KEY`, or
   create keys automatically. The bot only reads this key on admin screen opens.
6. On a separately approved production release, inject these settings and
   recreate/restart the bot so the new environment is loaded. Confirm private
   admin screen, denied non-admin/group access, project attribution, prior-day
   coverage and refresh timestamp. Check that failure states show no $0,
   local budget remains unchanged, and no sensitive data entered logs.

**Rotation/recovery:** create a *new* minimally scoped, expiring key manually;
update the protected secret store, recreate the bot, verify a private admin
refresh, then revoke the old key. For HTTP 401/403 verify API Platform (not
ChatGPT) key scopes and expiration; for 429/5xx/network failures wait for
provider recovery. The screen is allowed to say `UNAVAILABLE`; do not
elevate key permissions or bypass the local hard cap to make it work.
An Admin key with `api.usage.read` can still expose **organization-wide
usage** if compromised; the request's project filter is not a credential
security boundary. If that residual read exposure is unacceptable, prefer
the external broker and leave the bot credential unset.
