# CCW-20 final Cloudflare Render A/B — 2026-10-26

## Decision

**REJECT the candidate's text changes.** Candidate materially improves structured acceptance, fallback frequency, specificity and exact repetition, but fails the hard acceptance criterion of zero detected factual errors. Two final Possible Action lines invert convergence/divergence: extending a latest decline cannot further diverge from an already downward 24-hour direction.

## Frozen design

- 20 previously delivered events, exactly 5 each BTC/ETH/GRAM/SOL, frozen before the first request.
- Selection: Per symbol, stable case-id order: first delivered case covering latest countermove, window/24h divergence, sustained path, and pace change when available; fill remaining slot by highest exact historical final-pair repetition then case id.
- Same verified market inputs and same frozen positive significance projection in both arms; Stage-1 was not rerun.
- Model: `@cf/meta/llama-3.3-70b-instruct-fp8-fast` through Cloudflare Workers AI only; 40/40 one-shot attempts; no retries or provider fallback.
- Limitation: Sanitized historical dataset preserves accepted/delivered outcome but not the original six-field Stage-1 raw decision; the same schema-valid positive projection is frozen for both Render arms and Stage-1 is not rerun.

## Results

| Metric | Baseline A | Candidate B |
| --- | ---: | ---: |
| Successful Cloudflare responses | 20/20 | 20/20 |
| JSON/schema valid | 20/20 | 20/20 |
| Accepted by factual validator | 11/20 | 20/20 |
| Deterministic fallback used | 9/20 | 0/20 |
| Any Situation/Action final replacement | 17/20 | 17/20 |
| Specific, useful, grounded pair (single-evaluator) | 13/20 | 18/20 |
| Detected factual errors | 1 | 2 |
| Normalized duplicate Situation excess | 12 | 7 |
| Normalized duplicate Action excess | 13 | 7 |
| Normalized duplicate pair excess | 11 | 4 |

Candidate passes the 16/20 usefulness target (18/20), reduces repetition and replacement/fallback rates, and preserves 20/20 JSON reliability. It nevertheless fails criterion 1 (zero factual errors), so the final decision is reject rather than accept.

## Factual findings

1. `ev_0ab71234c9080ecc` (ETH): latest decline counters the net window rise while the 24h direction is down. Candidate says extending the decline would “further diverge” from the 24h decline; it would converge/align.
2. `ev_4bba21dd01bc8372` (SOL): the same directional inversion appears in another final action.

The programmatic backend validator accepted both; this exposes a missing cross-relation guard, not a JSON failure. Baseline contains one analogous ill-posed action on the ETH case, but candidate acceptance independently requires zero errors.

## Evaluation method

Programmatic checks measured HTTP/JSON success, application validator acceptance, final compactor/replacement, deterministic fallback, usage and exact normalized repetition. A single Codex evaluator then compared every final pair with the frozen numeric path and backend evidence labels. “Specific/useful” requires a distinctive verified relationship plus a connected next observation that separates continuation from weakening/reversal. This is not represented as independent human review.

## Safety and operations

PR CI is green on exact head `362467cbb8a94d50e5a31f6bb39f1c7b872368f1` ([run 40357899098](https://github.com/akrasnoslov-dev/CCWBot/actions/runs/40357899098)); focused offline routing/render tests passed (207). The intended Cloudflare → budget-guarded Luna → Groq order was verified offline only. No production `.env`, containers, DB, services, schedules or routing were changed; no Telegram messages, OpenAI/Luna calls or Groq calls occurred.

