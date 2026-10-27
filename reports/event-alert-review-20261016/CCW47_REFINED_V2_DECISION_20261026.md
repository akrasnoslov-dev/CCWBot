# CCW-47 — Owner decision: retain original Refined v2 (2026-10-26)

**Status:** owner decision final for this prompt comparison; **not a production release or a formal market-alert quality acceptance**. Evidence originated from the completed, isolated, paid GPT-6 Luna case replay reported in [Linear CCW-47](https://linear.app/ccwbot/issue/CCW-47/ccw-12-run-final-refined-v2-vs-revised-prompt-luna-replay-and-owner) and its attached sanitized files and [full comparison document](https://linear.app/ccwbot/document/ccw-47-final-refined-v2-vs-refined-v2-final-luna-comparison-7d8a4ee5dfd6). The private case ledger stays out of the public repository.

## Frozen comparison and important limitations

- Same frozen cohort: **200** real market contexts (**50 each BTC / ETH / GRAM / SOL**), dataset SHA-256 `ad06de5fac921c8d0db46f9ab086bed470733df62670bcda5c96d0479c837f7d`.
- API model: `gpt-6-luna`; original Refined v2 previously run on all 200; the revised shorter candidate run separately **once per case**, without retries or fallback.
- Owner adjudication: **66** originally selected disagreement cases (24 alert, 34 no_alert, eight ambiguous). This is a **selection-biased disagreement set**. New candidate was schema-valid for only **56 of the 58** decisive owner-labelled cases; confusion denominators differ.
- Counts of model alerts over all cases are not owner-confirmed relevance. No full-cohort ground-truth precision/recall; no Groq or Cloudflare parity verification; no assessment of actual recipient delivery/cooldown.
- Monetary amounts use the paid-run reported per-token pricing `$0.10/M` input and `$0.50/M` output, including reasoning tokens. New-candidate additional metered spend: `$0.053862`.

| Measure | Original Refined v2 (selected) | Short Refined v2 Final (rejected) |
| --- | ---: | ---: |
| Calls attempted | 200 | 200 |
| Valid schema replies | **200** | 186 |
| Invalid schema replies | **0** | **14 (7%)** |
| Model alert decisions | 42 / 200 | 59 / 186 valid |
| Owner-labelled TP | 9 | 12 |
| Owner-labelled FP | **8** | **15** |
| Owner-labelled FN | 15 | 11 |
| Owner-labelled TN | **26** | 18 |
| Owner decisively scored | 58 | 56 |
| Conditional precision | **52.9%** | 44.4% |
| Conditional recall | 37.5% | 52.2% |
| Conditional F1 | 43.9% | 48.0% |
| Conditional specificity | **76.5%** | 54.5% |
| Conditional accuracy | **60.3%** | 53.6% |
| Input tokens | 286,864 | 142,664 |
| Completion tokens, reasoning included | 67,147 | 79,192 |
| Total tokens | 354,011 | 221,856 |
| Measured USD | $0.062260 | $0.053862 |
| Median latency | 4,604 ms | 4,680 ms |
| P95 latency | 10,694 ms | 10,233 ms |

The shorter candidate catches more owner-positive events **among its valid replies** but creates seven more false positives in the scored comparison, with weaker specificity and 14 invalid decisions. The owner prefers the original for more reliable, less noisy alerts. Note that the scored subsets are not identical: exact paired changes and per-symbol confusion require the attached private/sanitized case-level results, not the aggregate table alone.

## Owner decision and precise dev implementation

1. **Keep the exact original Refined v2** that produced 200/200 valid Luna replies. Reject the shorter `Refined v2 Final`. No further paid significance tests requested.
2. The selected significance instructions are the frozen file `reports/event-alert-review-20261016/ccw29_private/fresh200_unseen/candidate_refined.txt`, **normalised final-newline SHA-256** `e30183660bffd977bc81a5a8f19093a07e9267a3da12aa12e9bbac913ed3f07c`. Do not accidentally substitute the tested short file `benchmarks/event-alert-owner-20261026/prompt_refined_v2_final.txt`; it is retained for negative experiment provenance only.
3. On `dev`, change only the Stage-1 `_EVENT_SIGNIFICANCE_INSTRUCTIONS` in `bot/services/ai_agent_groq.py` and lock its equality/hash in `tests/test_event_significance_prompt.py`. Input payload, six-field schema, model routing, cooldown, recipients, billing, thresholds and Stage-2 Render remain unchanged by the significance selection.
4. **Do not deploy to `main` or production** without separate release review and permission. Groq/Cloudflare live quality and required acceptance gates remain open; the Luna choice is a pragmatic owner preference, not proof of release acceptance.
5. Start a distinct [CCW-20](https://linear.app/ccwbot/issue/CCW-20/improve-verified-situation-and-possible-action-without-changing) / CCW-13 Render-quality phase: review raw Render vs validator/fallback vs final Telegram copy, then improve Situation/Possible Action without touching significance or adding recipient-loop provider calls.

## Audit scope

Only owner-shared aggregate results are replicated here. The CSV case flips, 66 owner reviews, run manifest, model responses, total failure categories and detailed comparison live in CCW-47's sanitized Linear evidence and protected local archives. **Do not claim all private evidence has been migrated to GitHub** or reproduce it in this public repo. No production services, DB, env files or Telegram notifications were altered by the paid replay.
