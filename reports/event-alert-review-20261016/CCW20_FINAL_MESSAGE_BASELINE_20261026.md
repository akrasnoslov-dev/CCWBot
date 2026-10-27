# CCW-20: historical final Event Alert copy baseline (2026-10-26)

Source: `reports/event-alert-review-20261016/v2_private_sanitized.json`,
dataset SHA `ed126380369014e6522cee49009b880cf0350aa7565269d50641c3f1bbdc3bee`.
It includes 200 real-market cases, intentionally stratified as 18 delivered,
7 positive-but-undelivered, and 25 no-alert cases per BTC/ETH/GRAM/SOL.
The time window is October 6–16, 2026 (to 11:00 UTC).
Exactly **72** cases have a final assembled Telegram message
(18 delivered Event Alerts per coin). All 72 have a positive recorded
delivery count, sometimes hundreds of recipient deliveries; the counts below
are **per event, not weighted per recipient**.

For each delivered message, extract `Situation:` and `Possible action:`,
collapse whitespace, lowercase, and normalize BTC/ETH/SOL/GRAM (and full names)
to COIN. Compare exact normalized strings, not subjective similarity.

| Historical final-message diagnostic | Event count |
| --- | ---: |
| Delivered event messages assessed | 72 |
| Missing Situation | 0 |
| Missing Possible Action | 0 |
| Distinct Situation sentences | **9** |
| Distinct Possible Action sentences | **13** |
| Most common Situation (latest snapshot countermove) | **29/72** |
| Next Situation (short-term vs 24h divergence) | **17/72** |
| Third Situation (latest observed interval picks up pace) | **11/72** |
| Most common Action (reversal vs renewed movement) | **25/72** |
| Next Action (24h convergence/divergence) | **16/72** |
| Third Action (pace sustained vs easing) | **11/72** |
| Percent or dollar-price repeated in extracted Situation | 0/72 |

Representative historical final pair, quoted only from the approved
sanitized research cohort:

> Situation: The most recent supplied snapshot reverses part of the earlier
> path, so the current move may be fading rather than extending.
>
> Possible action: Watch the next short-term snapshots for further reversal
> versus renewed movement in the current direction.

The repeated pair is evidence-grounded but not distinctive across many
market events. Other examples use 24h divergence and interval pace, but
recur nearly verbatim. Repetition is **observed**; human-judged usefulness
and factual error rates are **not established** by exact-string counts.

**Critical limitation:** the archived cohort contains the final message
but lacks the matched raw Render response, validator rejection/replacement
trace and candidate-after message. These counts cannot determine whether
the LLM itself or the backend fallback caused the repetition and cannot
establish a before/after benefit of the new prompt.

CCW-20 proposal: [draft PR #376](https://github.com/akrasnoslov-dev/CCWBot/pull/376)
asks Stage-2 Render to select the strongest supplied verified relationship
and one matched *next observation*. This is **prompt-only**, not a proven
quality win. Green CI and paired actual Groq/Cloudflare generated
Render → validator/fallback → final Telegram text are still necessary
before accepting the content change. No extra paid or quota-consuming
provider calls are authorised by this baseline audit. Neither significance
nor production is changed.
