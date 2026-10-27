# Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26)

## Dataset and evaluation scope

- Frozen real-market cohort: **200** source cases (50 each BTC/ETH/GRAM/SOL), dataset SHA-256 `ad06de5fac921c8d0db46f9ab086bed470733df62670bcda5c96d0479c837f7d`.
- Six saved GPT-6 Luna significance prompt variants: **1,200** case-prompt decisions, all saved source input hashes matched (no new LLM inference).
- Owner independently rated all **66 prompt-disagreement cases**: 24 alert, 34 no_alert, 8 ambiguous. Only **58 decisive disagreements** are included in the confusion table.
- **Selection warning:** the remaining 134 cases in the new200 cohort did not receive a new owner label here. These metrics are conditional on selected disagreements, **not** general population precision/recall, and do not validate production provider parity.

## Owner-label confusion on 58 decisive disagreement cases

| Prompt | TP | FP | FN | TN | Agreement |
|---|---:|---:|---:|---:|---:|
| Production | 2 | 5 | 22 | 29 | 53.4% |
| Balanced | 8 | 12 | 16 | 22 | 51.7% |
| **Refined v2** | **9** | **8** | **15** | **26** | **60.3%** |
| Refined v3 | 0 | 1 | 24 | 33 | 56.9% |
| Quality-first | 20 | 32 | 4 | 2 | 37.9% |
| Economical | 13 | 17 | 11 | 17 | 51.7% |

Overall positive decisions per all 200 cases: Production 26; Balanced 44; Refined v2 42; Refined v3 24; Quality-first 83; Economical 56. These counts are model behavior, **not** owner-confirmed market relevance across 200 cases.

## Findings

- **Refined v2** aligns with the owner most often on the selected disagreement cases, but still misses 15/24 owner-positive cases.
- Production misses 22/24 owner-positive cases in this sample.
- Refined v3 finds none of the 24 owner-positive cases despite a superficially reasonable overall agreement.
- Quality-first catches 20/24 owner-positive cases while incorrectly alerting on 32/34 owner-negative cases — too noisy for the expressed preference.
- The owner repeatedly identifies tiny movements as unimportant; important cases include sustained declines, growth after a decline, and meaningful incremental movement relative to the preceding alert. Premature reversals often merit waiting for confirmation.
- No fixed percent cutoff, backend numeric gate or new timed delay is justified by the owner comments alone.

## Restrictions and next steps

1. This file deliberately contains **only aggregate evaluations**, no raw archived user/Telegram data, closed market input payloads, owner comments, secrets or private model ledgers. The public GitHub repo is not approved storage for the raw research archive.
2. Exact underlying six-ledger results are available only from the owner-provided experiment archive. This summary is sufficient to recover the high-level conclusions, **not** to reconstruct each historical model prediction.
3. CCW-12: compare prompt-level counterexamples and historical Groq/Cloudflare results before proposing a limited instruction-only improvement; do not automatically deploy Refined v2.
4. CCW-46: once the owner authorizes the private repo migration and Hetzner authenticated fetch/CI/integrations are verified, privacy-audit and migrate the full experiment evidence into the **same** CCWBot repository. Never commit raw credentials or personal-user records even in a private repo.
