# CCW-41 exploratory Reviewer-C agreement/disagreement

Reviewer A remains the authoritative reference for CCW-16/29. Reviewer C is an independent AI audit, not an adjudicator or majority vote.

Dataset: 200 frozen cases. Original A/B conflicts: 99.

## Overall distributions

| Reviewer | alert | no_alert | ambiguous |
|---|---:|---:|---:|
| A | 41 | 112 | 47 |
| B | 101 | 59 | 40 |
| C | 31 | 167 | 2 |

## Pairwise agreement (all 200 cases)

| Pair | Agreed | Disagreed | Rate |
|---|---:|---:|---:|
| A-C | 134/200 | 66 | 67.0% |
| B-C | 87/200 | 113 | 43.5% |
| A-B | 101/200 | 99 | 50.5% |

## Original A/B disagreement subset

Of 99 original disagreements: C agrees with A in 53, with B in 7, with neither in 37, and selected ambiguous in 2.
These are descriptive categories, not votes or corrections to human labels.

## Reviewer A decisive vs ambiguous

- A decisive: A/C agreement 133/153; disagreement 20/153
- A ambiguous: A/C agreement 1/47; disagreement 46/47

## Differences by symbol (A vs C)

| Symbol | Disagreements | Denominator |
|---|---:|---:|
| BTC | 8 | 50 |
| ETH | 15 | 50 |
| GRAM | 20 | 50 |
| SOL | 23 | 50 |

## Observed scenario and tag splits (A vs C)

- scenario_type:delivered: 22/72 disagreements
- scenario_type:news_absent: 0/1 disagreements
- scenario_type:news_present: 1/3 disagreements
- scenario_type:no_alert: 32/100 disagreements
- scenario_type:repeat: 11/24 disagreements
- tag:borderline: 25/72 disagreements
- tag:continuation: 43/112 disagreements
- tag:news_absent: 31/90 disagreements
- tag:news_present: 35/110 disagreements
- tag:repeat: 43/121 disagreements
- tag:reversal: 23/88 disagreements

## High-impact disagreement counts

- A=alert, C=no_alert: 17
- A=no_alert, C=alert: 2
- A=ambiguous, C=decisive: 46

## Confirmed observations

- Reviewer C selected no_alert more often and ambiguous less often than either human reviewer.
- Reviewer C agreed with Reviewer A more often on A-decisive cases than on A-ambiguous cases.
- Reviewer A/C disagreement increased from BTC through ETH and GRAM to SOL in this frozen sample.

## Hypotheses requiring owner judgment

- The frozen rubric may have induced a conservative materiality/novelty interpretation in Reviewer C; this is a hypothesis, not a demonstrated human-label defect.
- Reviewer C's low ambiguous rate may indicate over-resolution of incomplete evidence rather than stronger certainty.
- Higher GRAM/SOL disagreement may reflect asset-specific context gaps or reviewer calibration and requires case-level owner review.

## Limitations and decisions

- Reviewer C is exploratory and is not adjudicated truth.
- Agreement with either human reviewer does not establish correctness.
- Small subgroup denominators are descriptive and must not be generalized.
- No majority-vote relabeling or production policy change is authorized.
- Review the restricted private shortlist against original market evidence and the independent rationales before deciding whether labels need a new protocol.
- Any benchmark relabeling, evaluation-policy change, or CCW-16/29 acceptance change requires separate owner approval and versioning.
- Cohen's kappa and all subgroup rates in the aggregate JSON are descriptive only; small groups and three-class ambiguity limit inference.
