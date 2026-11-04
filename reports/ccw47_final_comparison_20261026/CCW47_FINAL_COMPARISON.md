# CCW-47 Final Event Significance Prompt Comparison

## Outcome

**Recommendation: Keep Original Refined v2. Do not adopt Refined v2 Final.**

All 200 authorized new requests were attempted exactly once, with no retries or fallback models. Refined v2 Final returned 186 schema-valid decisions and 14 schema-invalid decisions (7.0% failure rate). It improved recall on the owner-labelled matched subset, but added substantially more false positives, reduced specificity and accuracy, and increased the alert rate. The incomplete decision coverage prevents a valid full-200 quality comparison and is itself a material regression.

Production was not changed or restarted. The temporary API credential was deleted after the run.

## Main comparison

| Metric | Original Refined v2 | Refined v2 Final |
|---|---:|---:|
| Requests attempted | 200 (archived) | 200 (new) |
| Valid results | 200 | 186 |
| Failures | 0 | 14 schema failures |
| Alerts | 42/200 (21.0%) | 59/186 valid (31.7%) |
| No-alerts | 158/200 | 127/186 valid |
| Owner TP/FP/FN/TN | 9/8/15/26 on all 58 | 12/15/11/18 on 56 valid |
| Precision | 52.9% | 44.4% |
| Recall | 37.5% | 52.2% |
| F1 | 43.9% | 48.0% |
| Specificity | 76.5% | 54.5% |
| Accuracy | 60.3% | 53.6% |
| Input tokens | 286,864 | 142,664 |
| Completion tokens (incl. reasoning) | 67,147 | 79,192 |
| Total tokens | 354,011 | 221,856 |
| Usage-based cost | $0.062260 | $0.053862 |
| Mean / median / P95 latency | 5362/4604/10694 ms | 5350/4680/10233 ms |

Owner metrics are conditional on the 58 selected disagreement cases, not production-wide estimates. Two decisive owner-labelled cases failed schema validation under the new prompt, so its metrics cover only 56 cases. For an apples-to-apples 56-case comparison, Original Refined v2 scored 8/8/15/25 with 58.9% accuracy, versus 12/15/11/18 and 53.6% for Final.

## Coverage and per-coin decisions

| Coin | Old alerts / 50 | New valid | New failures | New alerts / valid |
|---|---:|---:|---:|---:|
| BTC | 7 (14.0%) | 45 | 5 | 14 (31.1%) |
| ETH | 9 (18.0%) | 42 | 8 | 9 (21.4%) |
| GRAM | 10 (20.0%) | 49 | 1 | 15 (30.6%) |
| SOL | 16 (32.0%) | 50 | 0 | 21 (42.0%) |

## Owner-labelled classification quality

| Metric | Old, all 58 | Old, paired 56 | New, valid 56 |
|---|---:|---:|---:|
| TP | 9 | 8 | 12 |
| FP | 8 | 8 | 15 |
| FN | 15 | 15 | 11 |
| TN | 26 | 25 | 18 |
| Precision | 52.9% | 50.0% | 44.4% |
| Recall | 37.5% | 34.8% | 52.2% |
| F1 | 43.9% | 41.0% | 48.0% |
| Specificity | 76.5% | 75.8% | 54.5% |
| Accuracy | 60.3% | 58.9% | 53.6% |
| False-positive rate | 23.5% | 24.2% | 45.5% |
| False-negative rate | 62.5% | 65.2% | 47.8% |

## Decision differences

Among 186 cases with valid decisions from both prompts, 160 agreed (86.0%). There were 4 old-only alerts and 22 new-only alerts. Fourteen additional cases have no comparable new decision because of schema failure.

Every flip and schema failure is listed in `CCW47_CASE_DIFFERENCES.csv` with grounded numeric market evidence.

## Distributions

Counts use all 200 old decisions and 186 valid new decisions.

### materiality

| Value | Old | New valid |
|---|---:|---:|
| material | 54 | 63 |
| routine | 146 | 123 |
| unclear | 0 | 0 |

### novelty

| Value | Old | New valid |
|---|---:|---:|
| new | 42 | 59 |
| continuation | 12 | 0 |
| repeated | 0 | 1 |
| unclear | 146 | 126 |

### reason_code

| Value | Old | New valid |
|---|---:|---:|
| unusual_move | 18 | 26 |
| fast_move | 15 | 6 |
| reversal | 9 | 23 |
| trend_acceleration | 0 | 4 |
| market_news_alignment | 0 | 0 |
| routine_move | 151 | 124 |
| news_only | 0 | 0 |
| unclear | 7 | 3 |

### confidence

| Value | Old | New valid |
|---|---:|---:|
| low | 0 | 0 |
| medium | 115 | 127 |
| high | 85 | 59 |

## Tokens, cost and latency

| Metric | Old | New | Difference |
|---|---:|---:|---:|
| Input total | 286,864 | 142,664 | -144,200 |
| Input average | 1,434.320 | 713.320 | -721.000 |
| Input median | 1,434.000 | 713.000 | -721.000 |
| Completion total | 67,147 | 79,192 | 12,045 |
| Completion average | 335.735 | 395.960 | 60.225 |
| Completion median | 247.000 | 336.500 | 89.500 |
| Total tokens | 354,011 | 221,856 | -132,155 |
| Total average | 1,770.055 | 1,109.280 | -660.775 |
| Cost total | $0.062260 | $0.053862 | $-0.008398 (-13.5%) |
| Cost average/case | $0.000311300 | $0.000269312 | $-0.000041988 |
| Latency mean | 5362 ms | 5350 ms | -12 ms |
| Latency median | 4604 ms | 4680 ms | +76 ms |
| Latency P95 | 10694 ms | 10233 ms | -461 ms |

New-prompt cost is 13.5% lower, mainly because its shorter instruction reduced input tokens. This secondary efficiency benefit does not offset reliability and owner-agreement regressions.

## Reliability

| Failure type | Old | New |
|---|---:|---:|
| HTTP failures | 0 | 0 |
| Invalid JSON | 0 | 0 |
| Schema/consistency failures | 0 | 14 |
| Transport failures | 0 | 0 |

The 14 invalid responses were parseable JSON but failed the six-field schema or cross-field consistency validator. The runner intentionally did not retain invalid response bodies, so no unsupported diagnosis of the exact conflicting fields is made.

## Focused error analysis

### Owner alert: old missed, new catches

| Event | Coin | Owner | Old | New | Grounded market evidence |
|---|---|---|---:|---:|---|
| ev_14758c4bcbd58e1b | SOL | alert | false | true | w=180m; cw=3.45425%; c30=0.351886%; c60=0.592319%; c24=0.926112%; cl=0.935963%; pw=98.6; p24=31.2; prev_age=89m; prev_family=price_uptrend; prev_cw=1.1255%; cnt6/24=2/4; snapshot_path=100.60504→100.79797→101.70194→103.11507→103.71523→104.08019 |
| ev_59528ff24933263f | SOL | alert | false | true | w=180m; cw=-1.03159%; c30=0.0906226%; c60=-0.222579%; c24=-2.18712%; cl=-2.42697%; pw=74.6; p24=66.4; prev_age=479m; prev_family=price_downtrend; prev_cw=-1.1929%; cnt6/24=2/5; snapshot_path=105.38148→105.28897→105.07343→104.98881→104.19995→104.29438 |
| ev_686065337837bd2d | GRAM | alert | false | true | w=180m; cw=1.174%; c30=-0.207255%; c60=-0.0598914%; c24=0.534875%; cl=-2.30184%; pw=72.9; p24=14; prev_age=3119m; prev_family=price_uptrend; prev_cw=1.5961%; cnt6/24=0/0; snapshot_path=1.3399474→1.3485069→1.352696→1.3564908→1.3584939→1.3556783 |
| ev_7d71da21a73bd3fa | SOL | alert | false | true | w=180m; cw=1.1617%; c30=0.0562432%; c60=0.406843%; c24=1.83362%; cl=2.39225%; pw=79.1; p24=58; prev_age=599m; prev_family=price_uptrend; prev_cw=0.4748%; cnt6/24=1/7; snapshot_path=105.7321→105.79548→106.36642→106.66174→106.90026→106.96038 |
| ev_a4e1bd93914f6249 | SOL | alert | false | true | w=180m; cw=1.30072%; c30=-0.119241%; c60=0.250132%; c24=1.38106%; cl=1.89032%; pw=82.1; p24=45.5; prev_age=269m; prev_family=price_uptrend; prev_cw=1.1255%; cnt6/24=2/4; snapshot_path=103.71523→104.08019→104.24852→104.55078→105.18971→105.06428 |
| ev_df5a044c6b9374c9 | ETH | alert | false | true | w=180m; cw=-0.863484%; c30=-0.571297%; c60=-0.487973%; c24=-2.64362%; cl=-2.32268%; pw=81.2; p24=82.5; prev_age=1109m; prev_family=price_uptrend; prev_cw=0.9052%; cnt6/24=0/3; snapshot_path=2370.5187→2362.9729→2368.0302→2369.1499→2363.5526→2350.0497 |

### Owner alert: new misses

| Event | Coin | Owner | Old | New | Grounded market evidence |
|---|---|---|---:|---:|---|
| ev_05f1c3c4230e884a | ETH | alert | false | false | w=180m; cw=-0.0421753%; c30=0.0122546%; c60=-0.104309%; c24=-1.4564%; cl=-1.19952%; pw=8.4; p24=67.3; prev_age=479m; prev_family=price_uptrend; prev_cw=0.7295%; cnt6/24=0/1; snapshot_path=2384.5238→2382.2881→2382.7245→2383.8826→2383.2261→2383.5181 |
| ev_14a7e14b3235b74f | GRAM | alert | false | false | w=180m; cw=0.374214%; c30=0.428671%; c60=0.521425%; c24=-2.33349%; cl=-2.57666%; pw=32.7; p24=52.1; prev_age=2519m; prev_family=price_uptrend; prev_cw=1.5961%; cnt6/24=0/0; snapshot_path=1.3468249→1.3456564→1.3472098→1.3413892→1.3460946→1.3518649 |
| ev_542fbc621e28df65 | ETH | alert | false | false | w=180m; cw=-0.817557%; c30=-0.0714729%; c60=0.214025%; c24=-1.53378%; cl=-1.57533%; pw=79.8; p24=68.3; prev_age=989m; prev_family=price_uptrend; prev_cw=0.9052%; cnt6/24=0/3; snapshot_path=2387.5498→2369.9752→2375.6529→2370.5187→2369.7239→2368.0302 |
| ev_56ce5a3b11bfb1dc | ETH | alert | true | false | w=180m; cw=-0.860464%; c30=0.285702%; c60=-0.0335292%; c24=-1.28021%; cl=-1.50494%; pw=81.1; p24=62.4; prev_age=959m; prev_family=price_uptrend; prev_cw=0.9052%; cnt6/24=0/4; snapshot_path=2390.2915→2387.5498→2380.2664→2375.6529→2362.9729→2369.7239 |
| ev_5c1fe678cd551519 | GRAM | alert | false | false | w=180m; cw=-0.650369%; c30=-0.183266%; c60=-0.30809%; c24=-1.21829%; cl=-3.92696%; pw=50.9; p24=32.9; prev_age=4109m; prev_family=price_uptrend; prev_cw=1.5961%; cnt6/24=0/0; snapshot_path=1.3418549→1.3394445→1.3436132→1.3401168→1.3355755→1.3331279 |
| ev_64352f403a4118af | SOL | alert | false | false | w=180m; cw=0.367903%; c30=0.0502512%; c60=0.24606%; c24=2.08359%; cl=2.55676%; pw=35.6; p24=62.7; prev_age=509m; prev_family=price_uptrend; prev_cw=1.1255%; cnt6/24=0/4; snapshot_path=105.36383→105.18433→105.57667→105.37433→105.69835→105.75147 |
| ev_939765504bd1e470 | SOL | alert | false | false | w=180m; cw=0.856258%; c30=-0.0410459%; c60=-0.21134%; c24=0.947856%; cl=1.96488%; pw=66.8; p24=31.6; prev_age=359m; prev_family=price_uptrend; prev_cw=1.1255%; cnt6/24=2/4; snapshot_path=104.24852→104.55078→105.18971→105.06428→105.18433→105.14116 |
| ev_9b87a21dfc191ec6 | ETH | alert | false | false | w=180m; cw=-0.0385294%; c30=-0.0166696%; c60=0.083567%; c24=0.403103%; cl=1.30257%; pw=7.9; p24=24.1; prev_age=419m; prev_family=price_uptrend; prev_cw=1.246%; cnt6/24=3/5; snapshot_path=2423.0774→2423.7311→2422.263→2424.9175→2422.5476→2422.1438 |
| ev_b1950efeba816ba3 | SOL | alert | false | false | w=180m; cw=-0.0937084%; c30=-0.362829%; c60=-0.171718%; c24=1.61067%; cl=2.20915%; pw=9.8; p24=51.8; prev_age=659m; prev_family=price_uptrend; prev_cw=1.1255%; cnt6/24=0/4; snapshot_path=105.4919→105.69835→105.71465→105.75263→105.77683→105.39304 |
| ev_dc246bd4160b239e | GRAM | alert | false | false | w=180m; cw=-0.291556%; c30=0.256387%; c60=0.114641%; c24=-2.11593%; cl=-3.81682%; pw=25.5; p24=50.2; prev_age=4169m; prev_family=price_uptrend; prev_cw=1.5961%; cnt6/24=0/0; snapshot_path=1.3385588→1.3436132→1.3372478→1.3355755→1.331243→1.3346562 |
| ev_ed2b9dc1c9a9a2af | SOL | alert | true | false | w=180m; cw=1.05025%; c30=-0.170364%; c60=0.114268%; c24=0.915649%; cl=2.00675%; pw=74.8; p24=30.9; prev_age=329m; prev_family=price_uptrend; prev_cw=1.1255%; cnt6/24=2/4; snapshot_path=104.09111→104.24852→104.80213→105.18971→105.36383→105.18433 |

### Owner no-alert: new fixes old false positive

| Event | Coin | Owner | Old | New | Grounded market evidence |
|---|---|---|---:|---:|---|
| ev_eccdf281c0b85c80 | GRAM | no_alert | true | false | w=180m; cw=-0.903431%; c30=-0.0196514%; c60=0.324197%; c24=-0.486084%; cl=-1.39548%; pw=66.9; p24=17.4; prev_age=719m; prev_family=price_uptrend; prev_cw=1.7746%; cnt6/24=0/2; snapshot_path=1.3552909→1.3494187→1.3401036→1.3417091→1.3433108→1.3430468 |

### Owner no-alert: new introduces false positive

| Event | Coin | Owner | Old | New | Grounded market evidence |
|---|---|---|---:|---:|---|
| ev_48aac7876a7da763 | BTC | no_alert | false | true | w=180m; cw=0.495069%; c30=0.490435%; c60=0.771831%; c24=0.410106%; cl=0.490435%; pw=71.1; p24=30.1; prev_age=28m; prev_family=price_uptrend; prev_cw=0.09%; cnt6/24=1/6; snapshot_path=81140.806→81001.039→80903.345→80882.178→81144.548→81542.509 |
| ev_673845ec86094a1d | SOL | no_alert | false | true | w=180m; cw=1.22887%; c30=0.524596%; c60=0.722075%; c24=-0.309841%; cl=0.11102%; pw=80.6; p24=9.6; prev_age=419m; prev_family=price_downtrend; prev_cw=-0.1903%; cnt6/24=1/2; snapshot_path=102.72296→102.91393→103.12923→103.23164→103.44264→103.98529 |
| ev_747d289d8339476d | BTC | no_alert | false | true | w=180m; cw=-0.63658%; c30=-0.206718%; c60=-0.0984103%; c24=-0.219773%; cl=-1.09147%; pw=79.6; p24=15.5; prev_age=448m; prev_family=price_uptrend; prev_cw=0.2959%; cnt6/24=0/5; snapshot_path=81502.666→81461.394→81005.785→81095.868→81151.591→80983.837 |
| ev_7d0b437fc7918a36 | BTC | no_alert | false | true | w=180m; cw=0.899229%; c30=-0.0614917%; c60=0.122058%; c24=2.38935%; cl=0.641459%; pw=88.6; p24=90.8; prev_age=147m; prev_family=price_uptrend; prev_cw=0.1916%; cnt6/24=3/5; snapshot_path=82614.781→82717.312→83041.345→83134.044→83408.966→83357.677 |
| ev_8f7f1e3fc7f9abb5 | ETH | no_alert | false | true | w=180m; cw=-0.251271%; c30=0.222629%; c60=0.498062%; c24=0.0841145%; cl=0.657247%; pw=39.2; p24=5; prev_age=89m; prev_family=None; prev_cw=-0.9443%; cnt6/24=1/5; snapshot_path=2422.8429→2414.7983→2405.1755→2400.9747→2411.3866→2416.755 |
| ev_8fc0a71d48f52691 | GRAM | no_alert | false | true | w=180m; cw=-0.344717%; c30=-0.555956%; c60=-0.78422%; c24=-0.300756%; cl=-0.909769%; pw=30.5; p24=8.8; prev_age=509m; prev_family=price_uptrend; prev_cw=0.0611%; cnt6/24=0/1; snapshot_path=1.3407762→1.3402279→1.3421479→1.3441646→1.3436242→1.3361543 |
| ev_9294785f8cecc14b | ETH | no_alert | false | true | w=180m; cw=-0.451744%; c30=-0.681132%; c60=-0.869961%; c24=-0.193965%; cl=-0.658014%; pw=58.9; p24=11.9; prev_age=179m; prev_family=price_uptrend; prev_cw=0.5894%; cnt6/24=3/8; snapshot_path=2429.3415→2434.3857→2432.0265→2431.0675→2434.9523→2418.3671 |
| ev_f2228512fba9b5c6 | BTC | no_alert | false | true | w=180m; cw=0.605877%; c30=0.0618361%; c60=0.30899%; c24=0.732445%; cl=0.30899%; pw=78.4; p24=49.6; prev_age=58m; prev_family=price_uptrend; prev_cw=0.2959%; cnt6/24=2/4; snapshot_path=81635.888→81580.768→81609.585→81659.566→82079.746→82130.501 |

### Owner-labelled schema failures

| Event | Coin | Owner | Old decision | Grounded market evidence |
|---|---|---|---:|---|
| ev_df21210a26fe1d35 | ETH | alert | true | w=180m; cw=1.34161%; c30=0.395458%; c60=0.667816%; c24=0.741101%; cl=1.34161%; pw=90.7; p24=43.7; prev_age=209m; prev_family=price_uptrend; prev_cw=1.246%; cnt6/24=4/6; snapshot_path=2390.9994→2383.0134→2404.4087→2408.0222→2413.5329→2423.0774 |
| ev_f2e3ab01706221e2 | ETH | no_alert | false | w=180m; cw=-1.49214%; c30=-0.226195%; c60=-0.455024%; c24=-2.51838%; cl=-0.455024%; pw=92.2; p24=81.5; prev_age=59m; prev_family=price_downtrend; prev_cw=-1.3989%; cnt6/24=3/7; snapshot_path=2436.4449→2431.0344→2425.5906→2420.9281→2405.5309→2400.0898 |

### Eight owner-ambiguous cases (excluded from scoring)

| Event | Coin | Old | New/status | Grounded market evidence |
|---|---|---:|---|---|
| ev_3e3ce48a85ad2810 | SOL | false | true | w=180m; cw=0.398393%; c30=0.0336249%; c60=0.00643253%; c24=0.0485373%; cl=1.32515%; pw=38.4; p24=1.2; prev_age=179m; prev_family=None; prev_cw=-0.8228%; cnt6/24=2/3; snapshot_path=104.77289→103.8146→104.53369→104.73327→105.15494→105.1903 |
| ev_3f11561b791a53f8 | SOL | true | true | w=180m; cw=1.28911%; c30=-0.0355717%; c60=-0.00195879%; c24=-0.545762%; cl=1.28911%; pw=82.5; p24=18.1; prev_age=209m; prev_family=None; prev_cw=-0.8228%; cnt6/24=2/3; snapshot_path=103.8146→104.51934→104.73327→105.18353→105.1903→105.15288 |
| ev_4cef8d0733a56185 | BTC | false | false | w=180m; cw=-0.197102%; c30=-0.150797%; c60=-0.171753%; c24=1.181%; cl=-1.3553%; pw=40.4; p24=68.7; prev_age=628m; prev_family=price_uptrend; prev_cw=0.2636%; cnt6/24=0/6; snapshot_path=81939.462→81944.282→81852.683→81753.659→81901.463→81777.958 |
| ev_6b6ede4514df7393 | SOL | false | false | w=180m; cw=-0.0786738%; c30=0.198695%; c60=0.258761%; c24=1.52208%; cl=1.47833%; pw=8.2; p24=49.2; prev_age=449m; prev_family=price_uptrend; prev_cw=0.4748%; cnt6/24=3/7; snapshot_path=106.08915→106.42204→106.36019→105.83552→105.79548→106.00569 |
| ev_76d059ad58cd9c02 | ETH | false | false | w=180m; cw=-0.211361%; c30=-0.40194%; c60=-0.465925%; c24=-0.477387%; cl=-1.61847%; pw=33.8; p24=28.4; prev_age=1019m; prev_family=price_uptrend; prev_cw=0.5894%; cnt6/24=0/4; snapshot_path=2400.0586→2402.4679→2406.9003→2405.1809→2404.6511→2394.9859 |
| ev_ae7bb0bcf5848ba5 | ETH | false | false | w=180m; cw=-0.140914%; c30=-0.254649%; c60=0.158527%; c24=-4.39994%; cl=-1.01342%; pw=23.1; p24=94.3; prev_age=299m; prev_family=price_uptrend; prev_cw=0.2933%; cnt6/24=1/7; snapshot_path=2387.5715→2376.7708→2375.9633→2376.3214→2390.2939→2384.2071 |
| ev_c4f80ddef5b3fe97 | BTC | false | true | w=180m; cw=-0.663296%; c30=?%; c60=?%; c24=1.06375%; cl=-1.16048%; pw=80.9; p24=65.3; prev_age=418m; prev_family=price_uptrend; prev_cw=0.2636%; cnt6/24=0/6; snapshot_path=82486.593→82482.07→82131.614→81939.462 |
| ev_e55d7b380c4f6c11 | SOL | false | false | w=180m; cw=0.246793%; c30=0.0599472%; c60=-0.0378342%; c24=1.50073%; cl=1.2771%; pw=24.9; p24=48.9; prev_age=419m; prev_family=price_uptrend; prev_cw=0.4748%; cnt6/24=3/7; snapshot_path=105.53503→106.08915→106.55063→106.36019→105.7321→105.79548 |

## Reproducibility

- Canonical dataset SHA-256: `ad06de5fac921c8d0db46f9ab086bed470733df62670bcda5c96d0479c837f7d`; raw source-file SHA-256: `377fc476beb3c189120bc74998f691a13f895b914eb68e141a7cc4e6c91ade34`.
- Old prompt raw/instruction SHA-256: `91da15c45f09fcf1752038a092e8485d3989eda4d69d9886c61ad6d94e4f29f3` / `e30183660bffd977bc81a5a8f19093a07e9267a3da12aa12e9bbac913ed3f07c`.
- New prompt raw/instruction SHA-256: `4fb6a80dfca0740eae48094156647e57f5438a77fb35cd07e46882d223196f12` / `b2217c3608ec763d1b0072e75d3f34948dcedfb0ba25c3984560171aad05202c`; reference commit `62dad35f93a193ba083bb42436b505864f116ca7`.
- Old/new ledger SHA-256: `167d1685b36a54f42bd8883f2257321cb3bafe44a50cdc0fcdcbafebb335b640` / `7b5ecdf8f38c2fc475136e5189ac0e41d31fe97601373aba3b84bf04e149f66a`.
- Provider/model: OpenAI / `gpt-6-luna`; Chat Completions; system message `You are a careful crypto monitoring assistant.`; JSON object mode; max completion tokens 4096.
- Execution environment: Linux on Hetzner under the unprivileged `ccwbot_ops` account in `/home/ccwbot_ops/ccw12_refined_compare`; the runner's privilege check is Linux-specific.
- All 200 baseline rows were revalidated against case ID, input hash, reconstructed prompt hash, reconstructed request hash, symbol, HTTP 200, and schema-valid status.
- New rows were revalidated against all 200 case IDs, input hashes, prompt hashes, symbols, and unique single-attempt coverage.

## Limitations

- The 58 decisive owner labels were selected because earlier prompts disagreed; these precision/recall values are not representative holdout or production-wide performance.
- Fourteen missing new decisions prevent a complete 200-case quality comparison. They must not be treated as no-alerts or silently retried.
- The remaining 134 cases lack owner labels from this review. Model-model agreement is not human correctness.
- This test evaluates OpenAI Luna significance output only. It does not prove Groq/Cloudflare parity, Telegram delivery behavior, cooldown behavior, or final Situation/Possible Action quality.
- Cost uses actual returned token counts at verified Standard prices; provider billing adjustments such as caching or regional processing are not independently invoiced here.

## Final recommendation

Keep **Original Refined v2**. Refined v2 Final caught four additional owner-positive cases on the paired subset and raised recall, especially for SOL and GRAM, but it introduced seven additional false positives, lowered paired specificity from 75.8% to 54.5%, lowered paired accuracy from 58.9% to 53.6%, increased known alerts from 41 to 59 on comparable valid cases, and failed schema validation in 14/200 requests. Its lower token cost is useful but secondary. Do not change production; any future prompt revision or retest requires a new owner decision.
