# CCW-12 matched Luna significance comparison

Frozen dataset: `ad06de5fac921c8d0db46f9ab086bed470733df62670bcda5c96d0479c837f7d`. New prompt SHA-256: `b2217c3608ec763d1b0072e75d3f34948dcedfb0ba25c3984560171aad05202c`. Old prompt SHA-256: `e30183660bffd977bc81a5a8f19093a07e9267a3da12aa12e9bbac913ed3f07c`.
Old Refined v2 = archived paid Luna responses; Refined v2 final = new paid Luna responses on identical cases. No production LLM routing, database records, Telegram sends or recipient cooldown were changed.

## Matched comparison

| Metric | Refined v2 (old) | Refined v2 final (new) |
|---|---:|---:|
| Valid / all 200 | 200 | 186 |
| Matched decisions | 186 | 186 |
| Proposed alerts / matched | 41 | 59 |
| BTC alerts / matched | 7 | 14 |
| ETH alerts / matched | 8 | 9 |
| GRAM alerts / matched | 10 | 15 |
| SOL alerts / matched | 16 | 21 |
| Owner-labelled decisive matches (selection-biased) | 56 | 56 |
| Owner-review TP | 8 | 12 |
| Owner-review FP | 8 | 15 |
| Owner-review FN | 15 | 11 |
| Owner-review TN | 25 | 18 |
| Conditional precision (58 selected disagreements) | 50.0% | 44.4% |
| Conditional recall (58 selected disagreements) | 34.8% | 52.2% |
| Owner ambiguous (excluded) | 8 | 8 |
| Alerts among owner-ambiguous cases | 1 | 3 |
| BTC owner TP/FP/FN/TN | 0/3/0/8 | 0/7/0/4 |
| ETH owner TP/FP/FN/TN | 2/1/4/8 | 2/3/4/6 |
| GRAM owner TP/FP/FN/TN | 3/4/4/5 | 4/4/3/5 |
| SOL owner TP/FP/FN/TN | 3/0/7/4 | 6/1/4/3 |
| materiality: material | 45 | 63 |
| materiality: routine | 141 | 123 |
| novelty: continuation | 4 | 0 |
| novelty: new | 41 | 59 |
| novelty: repeated | 0 | 1 |
| novelty: unclear | 141 | 126 |
| reason_code: fast_move | 15 | 6 |
| reason_code: reversal | 9 | 23 |
| reason_code: routine_move | 143 | 124 |
| reason_code: trend_acceleration | 0 | 4 |
| reason_code: unclear | 2 | 3 |
| reason_code: unusual_move | 17 | 26 |
| confidence: high | 84 | 59 |
| confidence: medium | 102 | 127 |
| Input tokens (matched) | 266715 | 0 |
| Input tokens / case avg | 1433.951613 | N/A |
| Completion tokens incl. reasoning (matched) | 60435 | 72235 |
| Completion tokens incl. reasoning / case avg | 324.919355 | 388.360215 |
| USD uncached-price upper estimate (matched) | 0.056889 | 0.049378 |
| USD uncached-price upper estimate / case avg | 0.000306 | 0.000265 |
| Median latency ms | 4416.500000 | 4587.500000 |
| Median input tokens | 1432.500000 | 711.500000 |
| Median completion tokens | 235.500000 | 328.000000 |
| P95 response latency ms | 10928 | 10206 |
| New paid calls | 0 | 200 |
| New paid spending (estimate) | 0 | 0.053862 |
| Total old experiment cost USD / 200 | 0.062260 | N/A — see new paid spending |
| New non-valid responses | 0 | 14 |
| Identical binary decisions | 186 | 160 |

## Changed binary decisions

| Direction | Count | Case IDs |
|---|---:|---|
| no_alert → alert | 22 | ev_747d289d8339476d, ev_686065337837bd2d, ev_df5a044c6b9374c9, ev_c4f80ddef5b3fe97, ev_8fc0a71d48f52691, ev_e07c676303ecd260, ev_9294785f8cecc14b, ev_f2228512fba9b5c6, ev_112d988b15ae224d, ev_59528ff24933263f, ev_3e3ce48a85ad2810, ev_7d0b437fc7918a36, ev_892ea2a1ddc8d54b, ev_5c6f2ef3ed19099c, ev_7d71da21a73bd3fa, ev_8f7f1e3fc7f9abb5, ev_c8704629f5224c76, ev_a4e1bd93914f6249, ev_673845ec86094a1d, ev_14758c4bcbd58e1b, ev_8300d36139fb118b, ev_48aac7876a7da763 |
| alert → no_alert | 4 | ev_eccdf281c0b85c80, ev_56ce5a3b11bfb1dc, ev_251c5b08bdea3dc3, ev_ed2b9dc1c9a9a2af |

## Limits

- Precision/recall are **conditional on 58 selected disagreement cases**, not representative of 200 or unseen live traffic.
- This is a replay of archived real-production market contexts; not a live collection or Telegram-delivery test.
- Same coin/family recipient cooldown, final Situation/Possible Action, and production Groq/Cloudflare behavior are **not evaluated**.
- OpenAI usage is per-request metering; price rates are inherited from archived Luna experiment and should be checked against current billing.
- Only the owner can choose a winner; do not change production or merge new significance instructions automatically.
- Incomplete coverage or errors prevent a final head-to-head decision; no re-run without explicit authorization.
