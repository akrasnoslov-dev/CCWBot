# CCWBot — blind owner disagreement-only replay

Frozen dataset SHA-256: `ad06de5fac921c8d0db46f9ab086bed470733df62670bcda5c96d0479c837f7d`.

Review: 66 of 66 model-disagreement cases marked by owner (24 `alert`, 34 `no_alert`, 8 `ambiguous`); 58 decisive used for scoring. Six exact saved Luna ledgers were joined using case ID and original input SHA-256; all 1200 valid rows matched original 200-case source. No new inference.

## Owner comparison, disagreement subset only

| Prompt | TP | FP | FN | TN | Owner agreement | Precision* | Recall* | Positives / 200 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| production | 2 | 5 | 22 | 29 | 53.4% | 28.6% | 8.3% | 26 |
| balanced | 8 | 12 | 16 | 22 | 51.7% | 40.0% | 33.3% | 44 |
| refined_v2 | 9 | 8 | 15 | 26 | 60.3% | 52.9% | 37.5% | 42 |
| refined_v3 | 0 | 1 | 24 | 33 | 56.9% | 0.0% | 0.0% | 24 |
| quality_first | 20 | 32 | 4 | 2 | 37.9% | 38.5% | 83.3% | 83 |
| economical | 13 | 17 | 11 | 17 | 51.7% | 43.3% | 54.2% | 56 |

*Precision/recall are conditional on the 58 **selected disagreements**, not representative total population metrics. Eight ambiguous evaluations excluded from accuracy. The 134 unanimous events in the new200 cohort were not included in this review. This evaluation cannot establish 85%/90% release acceptance or provider parity.*

## Operational recommendation

- **Refined v2** leads disagreement-only owner agreement (35/58, 60.3%). Versus production: +7 true alerts (9 vs 2), +3 false alerts (8 vs 5), 15 owner-requested alerts still missed. This is a candidate for deeper evaluation, **not an authorized production replacement**.
- **Production** is too restrictive on this sample (2/24 owner-positive cases detected).
- **Refined v3** missed all 24 owner-positive events and should not be selected based on an overall agreement that rewards the majority negative class.
- **Quality-first** detects 20/24 owner-positive but produces 32/34 owner-negative alerts; this is not aligned with low-noise preferences.
- Do not apply hard movement percentage cutoffs; focus prompt adjustments on sustained/reversing trajectory and material incremental change relative to previous alert, while preventing weak BTC/GRAM noise.
- Model/provider mismatch: tests used GPT-6 Luna, deployed routing uses Groq/Cloudflare. No new paid inference or release without owner approval.

## Per coin (TP/FP/FN/TN)

| Coin | Production | Balanced | Refined v2 | Refined v3 | Quality-first | Economical |
|---|---|---|---|---|---|---|
| BTC | 0/2/0/9 | 0/5/0/6 | 0/3/0/8 | 0/0/0/11 | 0/9/0/2 | 0/7/0/4 |
| ETH | 0/0/7/10 | 4/2/3/8 | 3/1/4/9 | 0/0/7/10 | 7/10/0/0 | 4/5/3/5 |
| GRAM | 2/2/5/7 | 1/5/6/4 | 3/4/4/5 | 0/0/7/9 | 3/9/4/0 | 6/5/1/4 |
| SOL | 0/1/10/3 | 3/0/7/4 | 3/0/7/4 | 0/1/10/3 | 10/4/0/0 | 3/0/7/4 |

## Limitations and next actions

1. Case source is sensitive, and the original archive is private user-provided; do not publish source or raw per-case model texts while GitHub is public.
2. Raw experimental 'reports' folder was not completely transferred. The `CCWBot-reports-full.zip` upload is truncated and lacks ZIP central directory. Previous `CCWBot-experiments.zip` is valid and sufficient for the scores here.
3. Transfer full reviewed research artifacts into same repository only after permissions and GitHub privacy are ready (CCW-46); never include secrets, full DB dumps or user-identifying data.
4. Carry quantitative interpretation into CCW-12 and keep CCW-20 final text improvements separate.
