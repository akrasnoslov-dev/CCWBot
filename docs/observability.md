# Observability Snippets

Use these read-only queries for production analysis. Adjust interval windows as needed.

## Event Analysis Health

Event Alerts were dead for 18 days in 2026-07 while every monitoring surface reported healthy.
`/health` only proved that price polling ran, and the sole trace was one identical WARNING
repeated 3396 times at unchanged severity. These four surfaces exist so an outage of that shape
becomes visible in hours instead of weeks.

**`/health` — Event Analysis block.** The endpoint now carries a nested block:

```json
{
  "status": "ok",
  "uptime_seconds": 1234,
  "last_btc_check_at": "2026-08-05T12:00:00+00:00",
  "event_analysis": {
    "state": "degraded",
    "last_success_at": "2026-07-17T23:00:01+00:00",
    "last_success_age_seconds": 1555199,
    "consecutive_failures": 3396
  }
}
```

The top-level `status` deliberately stays `"ok"`. The Compose healthcheck fails the container
whenever `status != "ok"`, and nothing restarts it on that basis — `restart: always` reacts to
process exit, not to health, and there is no autoheal or orchestrator in this deployment. Flipping
`status` would therefore buy no remediation and would instead mark the container permanently
`unhealthy` in `docker compose ps` and to any external monitor, on a bot that is still serving
prices, heartbeats and reports. Degradation is reported *inside* the payload instead. `state` is
`unknown` when there is no evidence to judge on, which per project rule is incomplete, not healthy. Tune with
`EVENT_ANALYSIS_FAILURE_ESCALATION_THRESHOLD` (default 5) and
`EVENT_ANALYSIS_HEALTH_MAX_AGE_SECONDS` (default 10800). The payload carries counters and
timestamps only — no model identifiers, provider names, or environment values.

**Log severity reflects duration.** The repeating per-symbol failure line escalates from WARNING
to ERROR once consecutive failures reach the threshold, and carries the streak length:

```text
ops_event=event_analysis_failed symbol=BTC reason=provider_model_error consecutive_failures=5
```

**Candidate crossings are recorded independently of the LLM.** Market events are only created
after a successful analysis, so a dead LLM produces zero events rather than events without
analyses — the outage was silent by construction. Every symbol that reaches the analysis stage now
emits, before the LLM is called:

```text
ops_event=event_alert_candidate_crossing symbol=BTC analysed_window_change_percent=-4.2
  change_24h_percent=-6.1 threshold_percent=3.0 crossed_threshold=true analysed_window_minutes=30
```

This is evidence only: it creates no market event, triggers no alert, and feeds no decision.
Comparing its count against created `market_events` turns "detections happening but zero events
created" into a measurable gap.

**Log-evidence baseline shifts once.** Traceback continuation lines now carry a leading
`<timestamp> | ` prefix so every line of a record stays attributable. The ops-agent's log
collector only counts lines with a parseable in-period timestamp, so traceback bodies — previously
invisible to that filter — now count toward `period_matched_lines` and the error pattern counters.
Expect a one-off step up in those numbers after deploy; it is higher fidelity, not a regression,
and bundles from before and after this change are not directly comparable on those counters.

**Ops-agent detectors.** `event_analysis_success_rate_zero` (critical) triggers when zero
`event_analysis` calls succeeded, and counts consecutive collection cycles with the same result
via a two-counter signal carried in ops-agent state. `event_analysis_model_drift` compares only
Groq primary-provider evidence in `llm_usage_logs` against the shipped default (or an explicit
operator override); Gemini and Mistral fallback models are reported separately and do
not count as drift. Missing Groq evidence is inconclusive, never healthy. A withdrawn primary
model is high severity. Both read existing tables only.

Last successful Event Analysis, and the size of the current failure streak:

```sql
SELECT
  max(created_at) FILTER (WHERE status IN ('success', 'no_alert')) AS last_success_at,
  count(*) FILTER (WHERE status NOT IN ('success', 'no_alert')) AS failures_24h,
  count(*) AS attempts_24h
FROM event_ai_analyses
WHERE coalesce(analysis_type, 'event_analysis') = 'event_analysis'
  AND created_at >= now() - interval '24 hours';
```

Detections versus created market events, the gap the candidate-crossing line measures:

```sql
SELECT
  date_trunc('hour', created_at) AS hour,
  count(*) AS market_events_created
FROM market_events
WHERE created_at >= now() - interval '48 hours'
GROUP BY 1
ORDER BY 1;
```

## Admin System Status

Admin -> System status is a compact Telegram-safe dashboard for live operators. It uses persisted
final-feature telemetry. Admin -> LLM diagnostics also reads in-memory provider backoff state.
Opening either screen must not call CoinGecko, an LLM provider, RSS feeds, or Telegram delivery
APIs.

Provider and call-type attempt details are shown separately under Admin -> LLM diagnostics. A
recovered primary-provider failure remains visible there but does not make headline feature health
unhealthy when the final feature outcome succeeded. Market-data freshness uses the normalized
1,800-second cadence plus 120 seconds of scheduler grace.

Default output is designed for mobile scanning:

- `✅`: the component has fresh successful telemetry.
- `⚠️`: telemetry is stale, partial, degraded, or not enough to claim healthy.
- `❌`: the latest required operation failed or a core dependency is unavailable.

The default Telegram message shows one main line per component. It adds indented details only for
degraded or failing components. Long OK details, repeated timestamps, price values, CoinGecko ids, raw
table names, provider payloads, traces, and secrets are not shown in the default dashboard.

Signals currently summarized:

- Runtime: admin command response.
- Database: explicit lightweight PostgreSQL query.
- Market data: freshness for each active symbol from persisted price telemetry. Automatic market
  check health is folded into this component.
- AI: latest event-analysis attempt, latest successful attempt, and latest failure from
  `event_ai_analyses`; failure details are sanitized and redacted if they look like provider
  payloads, traces, headers, connection strings, or secrets. Old failures resolved by newer
  success/no-alert rows do not clutter the default dashboard.
- News: cache freshness and usable non-noise/non-duplicate rows in the last 24h. Fresh usable
  news remains OK even when enrichment telemetry has not run yet.
- Telegram delivery: last-24h counts from `alerts` by `sent`, `pending`, `retry_pending`,
  `failed`, final-failed rows, and blocked-user count from `users.bot_blocked`. Expected
  Telegram permanent failures such as blocked users, unavailable chats, deactivated users, and
  forbidden sends are shown separately from real delivery failures. Blocked-user/chat-unavailable
  failures do not mark the whole system as broken unless non-blocked delivery failures are also
  present. Blocked users are shown only when non-zero.

Example degraded output:

```text
System status — 2026-06-15 16:55 UTC
Overall: ⚠️ Needs attention

✅ Bot — running
✅ Database — connected
⚠️ Market data — stale/missing symbols
   BTC stale: last check 32h ago
   Missing: ETH, GRAM, SOL
✅ AI — latest success 32h ago
✅ News — 5 usable items in 24h
⚠️ Telegram — no delivery rows in 24h
```

Provider attempts, rate limits, backoffs, circuit skips, schema failures, and active limits are
shown separately under Admin -> LLM diagnostics. Mutually exclusive aggregate categories reconcile
to total attempts and do not degrade System Status after a successful final feature outcome.

Current limitations:

- CoinGecko provider health is inferred from stored market-data freshness, not a live provider
  request.
- RSS fetch health is inferred from `news_items` cache freshness and news-intelligence telemetry;
  there is no separate provider fetch-run table yet.
- Delivery health is based on stored delivery rows and user blocked-state telemetry, not a live
  Telegram send probe.

## Ops-Agent Diagnostics

The repo-managed ops-agent source lives under `ops-agent/`. Production wrappers should point to
that source and keep using the safe collection command:

```bash
sudo /usr/local/bin/ccwbot-ops-agent-collect --since <UTC> --until now
```

DB collectors are isolated per read-only query. If one collector fails, the bundle records that
collector as failed with a sanitized error class/category and continues later collectors. The
bundle status becomes `partial` when any collector fails, but unrelated evidence should still be
present.

Generated report context includes a collector status table. Interpret statuses as:

- `OK`: collector succeeded.
- `Warning`: collector produced degraded but usable evidence.
- `Critical`: detector evidence shows a high-impact issue.
- `Unknown`: collection succeeded, but evidence is insufficient.
- `Collector failed`: evidence is missing because the named collector failed.

Failed collector errors must not include SQL parameters, connection strings, `.env` values, raw
stack traces, or private Telegram text.

## GRAM Rebrand Price-State Check

GRAM is stored internally as symbol `gram`; legacy `ton` input normalizes to `gram`.
CoinGecko identity for this internal symbol must resolve to `the-open-network`; old `toncoin` or ambiguous `symbols=ton` data can create
false price moves.

Do not run cleanup blindly. First inspect the affected rows:

```sql
select *
from price_state
where symbol = 'TON';

select *
from price_snapshots
where symbol = 'TON'
order by checked_at desc
limit 100;

select id, symbol, alert_type, created_at, numeric_context, message
from alerts
where symbol = 'TON'
order by created_at desc
limit 50;
```

If bad `$0.38` TON/GRAM snapshots, `price_state.last_price`, or alert `numeric_context` values were
persisted, remove or correct them before or immediately after deploy. Otherwise the next correct
GRAM price around the current market level may look like a false rebound and trigger another bad
alert. Take and verify a current database backup before any destructive production cleanup.

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
Event Alerts are market-event-first: news may support the analysis, but standalone news-only
Event Alerts are not part of current product behavior. If an LLM returns `should_alert=true`
for a clear news-only situation, the backend records a `news_only_rejected` LLM-stage outcome
before market event creation or Telegram delivery.

Outcome statuses:

- `delivered`
- `suppressed`
- `filtered`
- `failed`
- `rate_limited`
- `cooldown`
- `not_scheduled`
- `no_eligible_recipients`
- `allowed`

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
- `llm_should_alert`
- `llm_no_alert`
- `news_only_rejected`

Decision fields:

- `decision_stage`: operator-facing stage such as `pre_llm`, `llm`, `semantic_cooldown`, or
  `delivery`.
- `decision_reason`: operator-facing reason such as `news_only_rejected`, `llm_no_alert`,
  `llm_should_alert`, `semantic_cooldown_suppressed`, `similar_context_reused`,
  `allowed_market_context_changed`, `delivered`, `delivery_failed`, `no_eligible_recipient`, or
  `unknown`.
- `previous_alert_id`: nullable link to a previous alert considered for repeat/cooldown context.
- `context_fingerprint`: safe hash of sanitized decision context; it is not a raw prompt or
  Telegram message export.

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
  ado.decision_stage,
  ado.decision_reason,
  ado.previous_alert_id,
  ado.context_fingerprint,
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
  coalesce(ado.decision_reason, 'missing_outcome') AS decision_reason,
  count(a.id) FILTER (WHERE a.status = 'sent') AS sent_deliveries
FROM event_ai_analyses eaa
JOIN market_events me ON me.id = eaa.market_event_id
LEFT JOIN alert_delivery_outcomes ado ON ado.event_ai_analysis_id = eaa.id
LEFT JOIN alerts a ON a.event_ai_analysis_id = eaa.id
WHERE eaa.should_alert = true
GROUP BY me.id, me.symbol, me.event_key, eaa.id, eaa.created_at, ado.status, ado.reason_code,
  ado.decision_reason
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
semantic cooldown when urgency increased or the absolute analysed-window movement grew by the
configured material movement delta. Stable related-news identity remains diagnostics/supporting
context only; new news alone does not bypass cooldown.
Generic `possible_action` wording is reported as a quality signal only; it does not suppress
runtime delivery.

## Event Alert Similar-Context Reuse

Before calling the Event Analysis LLM, the runtime can reuse a recent durable decision with the
same sanitized `context_fingerprint`. The fingerprint is built from stable normalized fields such
as symbol, analysed-window length, coarse market movement identity, compact candidate-news
identity, and previous Event Alert semantic context. It excludes raw timestamps, prompts, LLM
outputs, Telegram ids, user ids, and secrets.

Pre-LLM reuse writes an event-less `alert_delivery_outcomes` row:

```sql
SELECT
  symbol,
  semantic_family,
  decision_stage,
  decision_reason,
  status,
  reason_code,
  previous_alert_id,
  context_fingerprint,
  created_at
FROM alert_delivery_outcomes
WHERE alert_type = 'event_alert'
  AND decision_stage = 'pre_llm'
  AND decision_reason = 'similar_context_reused'
ORDER BY created_at DESC
LIMIT 50;
```

These rows are expected to have no `market_event_id` and no `event_ai_analysis_id`, because no new
market event or LLM attempt was created.

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
previous/current selected-news counts. `new_news_driver` is diagnostics only and is not sufficient
to allow a same-family repeat inside cooldown; allowed repeat reasons must be market-context based.
These fields are for logs/outcomes only and must not be copied into Telegram messages.

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

## Event Alert User-Facing Copy Checks

Event Alert percentage labels distinguish two different movements:

- `Since last alert/message`: movement since the last user-visible alert/message context.
- `<window> market move`: analysed-window movement, using the actual payload window such as
  `30m market move`, `1h market move`, or `3h market move`.

If an Event Alert numeric field is missing, the line is omitted. User-facing Event Alert bodies
must not render placeholder text such as `n/a`, `unknown`, `unavailable`, or `null`. Event Alert
bodies should also avoid old/confusing labels such as `Since last BTC alert`,
`Analysed-window change`, or generic `Price change`.

When the analysed-window move is below the semantic material-movement threshold, backend formatting
applies a narrow deterministic wording guard for dramatic terms such as crash, surge, collapse,
panic, bloodbath, explosion, moon, and meltdown. This guard only affects Event Alert text; it does
not change market-event identity, recipient eligibility, cooldown decisions, or LLM call placement.

The ops-agent decision context now includes `## Event Alert Regression Checks`. Interpret it as:

- `OK`: no collected duplicate attached analyses, unexplained `should_alert=true` gaps,
  same-family repeat noise, bad placeholders, or old labels.
- `Warning`: likely same-family repeat noise was found, while allowed escalation groups are
  counted separately.
- `Critical`: duplicate attached successful analyses, unexplained `should_alert=true` gaps,
  user-facing placeholders, or old confusing labels were found.

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
  SELECT 1800 AS event_analysis_interval_seconds
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
