# Event Alert cadence evaluation — CCW-50 (2026-11-06)

## Decision

**Keep the existing 30-minute per-symbol automatic check interval.** Do not change the
production/default cadence in CCW-50. The observed notification delay was primarily
associated with consecutive Stage-2 Render validation failures, which shorter polling
does not repair. Reassess a separate 15-minute experiment only after observing the
combined reliability/news fixes, provider admission capacity and budget headroom.

## Reproducible baseline

Source: read-only sanitized production ops-agent bundle
`20261105T165552Z_94d31396`, covering **2026-11-04 16:55:52 UTC to
2026-11-05 16:55:52 UTC**. The aggregate `llm_usage_summary` in
`evidence/db/aggregate_metrics.json` reports:

| OpenAI call type | Provider attempts | Prompt tokens | Completion tokens |
| --- | ---: | ---: | ---: |
| Event Analysis (Stage-1) | 192, including 2 timeouts with no recorded tokens | 299,870 | 62,883 |
| Event Alert Render (Stage-2) | 43, including 33 schema errors | 41,410 | 8,845 |
| **Total** | **235** | **341,280** | **71,728** |

These are usage aggregates, not per-user data. One shared analysis/render serves an
event's recipients. Provider calls do not scale with recipient count. Within the
same bundle, 33 of 43 Stage-2 Render operations failed; six consecutive SOL
Stage-1-positive operations failed to render. The historical rejected Stage-2
text was not persisted.

## Hypothetical comparison — not a historical replay

Assume constant four tracked symbols, the same per-call token mix and roughly the
same Stage-1-positive rate. More frequent polling changes market inputs and LLM
decisions, so Render counts are **illustrative**, not a prediction.

| Metric | 30 min (observed) | 15 min (scenario) | 10 min (scenario) |
| --- | ---: | ---: | ---: |
| Symbol checks / Stage-1 calls per day | 192 | 384 | 576 |
| Stage-2 calls per day if positive rate stays constant | 43 | ~86 | ~129 |
| Total LLM calls/day | 235 | ~470 | ~705 |
| Expected detection wait under a uniformly timed move, excluding processing | 15 min | 7.5 min | 5 min |
| Maximum wait until the next scheduled check, excluding processing | up to 30 min | up to 15 min | up to 10 min |
| Token-based nominal OpenAI standard cost/day* | ~$0.070 | ~$0.140 | ~$0.210 |
| 30-day unconstrained nominal cost* | ~$2.10 | ~$4.20 | ~$6.30 |

*Pure arithmetic using the pinned October 2026 project price assumptions:
$0.10 per million input tokens and $0.50 per million output tokens.
It excludes unrecorded timeout usage, overhead, model pricing changes and
long-context/cache/billing differences. The project's budget admission
reserves conservatively ($0.25/million input, $0.75/million output and
per-request ceiling), and the **global $2.50/month cap** can block calls before
these hypothetical unconstrained totals are reached. Therefore the scenarios
are **not** an invoice prediction nor evidence that all projected alerts could
be generated within budget.

The 30-minute baseline cost in this example is approximately $0.070/day
before conservative admission. The same observed tokens would use
approximately $0.139/day when priced at conservative token rates alone;
actual reservation policy may be stricter. A 15-minute schedule may double
calls and cost pressure; a 10-minute schedule may triple them.

## What this can and cannot establish

- **Polling vs window:** The 180-minute analysed market window is independent of
  the check interval. Keeping 180 minutes at 15 or 10 minutes gives more overlapping
  context windows, not faster validity or guaranteed greater recall.
- **Historical SOL delay:** the observed 39-minute lag versus Walt's notification
  coincided with six rejected Render attempts. A 10-minute timer would not have
  made those rejected texts valid. Precise earlier-alert recall is not recoverable
  from 30-minute observations alone.
- **Market-data pressure:** CoinGecko cache, request batching, concurrency,
  429/backoff and scheduler alignment may change the actual HTTP call count.
  Do not equate symbol checks with CoinGecko HTTP requests without request logs.
- **Novelty/cooldown:** the four-hour semantic cooldown and Stage-1 significance
  remain unchanged. Additional overlapping windows may yield more no-alert decisions,
  repeated-signal suppression and potential noise, not simply more useful alerts.
- **Measurement gaps:** the existing 30-minute snapshot history cannot reconstruct
  exact 10/15-minute inputs, intermediate market swings, model text, LLM responses,
  provider latency or hypothetical alert decisions. Interpolation would not prove
  recall or cost. The stated wait improvements are theoretical scheduling bounds,
  not measured historical improvements.

## Follow-up decision gates

1. Release the verified CCW-48/49/50 batch once, after separate owner approval.
2. Observe at least seven days of Render terminal outcomes, three-failure streaks,
   confirmed missed checks, actual budget admission/cost and genuine related-news
   attachments. Label unavailable or sparse data **unknown**, not healthy.
3. If material, avoidable polling-only lag remains, propose a separate bounded
   15-minute experiment with explicit cost/admission ceiling, provider quota review,
   CoinGecko checks, noise/recall acceptance and rollback plan. Compare against
   the 30-minute control using actual observations.
4. Keep 10 minutes out of scope until 15-minute evidence demonstrates benefit
   without increasing monetary cost or pushing the paid provider through its cap.

No production configuration, Stage-1 decision threshold, cooldown, recipient
eligibility or additional provider request is changed by this evaluation.
