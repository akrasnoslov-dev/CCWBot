# CCW-41 owner-reviewed significance reference v1

Status: PRIVATE PROMPT CALIBRATION CANDIDATE. Not officially promoted as ground truth.
Frozen 200-case dataset SHA: ed126380369014e6522cee49009b880cf0350aa7565269d50641c3f1bbdc3bee
Owner 66-response original SHA: aa0f2fb6a1273d9e08f8f63e768fb5e0acac072af233f0cc9bfd62440a64f53f
66 re-reviewed A/C disagreements + 134 original A labels on A/C agreements.

## Warrant distributions
| Source | Alert | No alert | Ambiguous |
|---|---:|---:|---:|
| Original A (200) | 41 | 112 | 47 |
| Owner new decisions (66) | 7 | 50 | 9 |
| Combined candidate (200) | 31 | 159 | 10 |

Owner retained A on 13 disputed cases, agreed with C on 53, chose neither on 0.
Changed original A in 53 cases.

## How disputed labels changed
| A | C | Owner | Cases |
|---|---|---|---:|
| alert | no_alert | alert | 4 |
| alert | no_alert | no_alert | 13 |
| ambiguous | alert | alert | 2 |
| ambiguous | alert | ambiguous | 3 |
| ambiguous | no_alert | ambiguous | 5 |
| ambiguous | no_alert | no_alert | 36 |
| no_alert | alert | alert | 1 |
| no_alert | alert | no_alert | 1 |
| no_alert | ambiguous | ambiguous | 1 |

## Historical bot against reference (selected benchmark only)
| Reference | Scored | Ambiguous | TP | FP | FN | TN | Precision | Recall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Original A | 153 | 47 | 21 | 53 | 20 | 59 | 28.4% | 51.2% |
| Owner candidate | 190 | 10 | 20 | 75 | 11 | 84 | 21.1% | 64.5% |

## Asset-specific labels
- BTC: alert 5, no_alert 44, ambiguous 1
- ETH: alert 5, no_alert 42, ambiguous 3
- GRAM: alert 13, no_alert 34, ambiguous 3
- SOL: alert 8, no_alert 39, ambiguous 3

## Using this reference for future model prompts
1. Compare pinned model decisions against the scorer JSON on the original frozen inputs.
2. Use the 66 changed decisions and historical FP/FN to diagnose materiality and novelty separately.
3. Ambiguous is excluded from binary scoring. Never silently turn ambiguous into no_alert.
4. Do not invent owner's reasoning: their uploaded responses only contain labels.
5. Avoid fixed percentage cutoffs; assess movement in asset-specific context, prior alerts and news-support only.
6. Repeated tuning on these 200 cases is calibration, not independent validation. Collect a separate blind holdout before claiming improvement.
7. Neither the original A/B/C files, official CCW-16 baseline, production prompts nor the bot runtime were modified.

Private output files: owner_reference_candidate_v1_20261022.json, owner_reference_candidate_v1_20261022.scorer.json, owner_reference_candidate_v1_20261022.changes_66.csv, owner_reference_candidate_v1_20261022.summary.md
