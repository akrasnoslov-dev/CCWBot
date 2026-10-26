# CCW-43 — Evidence-based Event Analysis prompt redesign
Private analytical record, 2026-10-23. OFFLINE ONLY. Do not publish case IDs, raw contexts, provider replies, C rationales or private hashes of original inputs to a public tracker.

## Scope and decision
**Analysis completed; two new prompt candidates prepared but untested.** No provider inference, bot start, Telegram/DB operation, production change, merge, deploy or paid API request in CCW-43. CCW-29 owns fresh replay and blind holdout. CCW-42 production observations unavailable; not pooled with replay.

Sources: 200 original immutable real-market cases, Reviewer A and B, independent Reviewer C's 200 sealed assessments, the owner's unblinded re-review of 66 A/C disagreements, the final CCW-16 ledger (120 valid paired observations) and the preserved 86-attempt checkpoint. This analysis is **calibration**, not independent validation.

### Verified provenance
- 200 cases canonical dataset digest: `ed126380369014e6522cee49009b880cf0350aa7565269d50641c3f1bbdc3bee`; frozen source file SHA-256 `e983a16e8d6f1ae20cf0b155c982e33baec65d06c0f9be4fbb68c90f6499cce6`.
- Original Reviewer A source SHA-256 `181944fafd138bc2d69ed7ecf4ab32ed234a905eabf5afc8adf177a2f33946eb`; B `fdff0dd9c5fb7150bdb8e8928f8c0f4cae4268d74a2b146deaf3acd391bcc233`.
- Independent C sealed SHA-256 `6478f54188501f1acb2a55a57e6a4ffead989e2eedf900d689846a2c3c9cdd2f`; owner calibration candidate SHA-256 `0efbb5ccc2fac7d00f7a4b136b1654d31e23b12fae6992a276d819d292bbd20a`; original owner 66-vote SHA-256 `aa0f2fb6a1273d9e08f8f63e768fb5e0acac072af233f0cc9bfd62440a64f53f`.
- Finished CCW-16 ledger `pilot-ledger-complete_20261023_120.json`: SHA-256 `2512e4e340f3074fafc1ee07e497be7b71014e6c2c9b38a6cff2f21c32623ab4`; pre-restart checkpoint 86 entries SHA-256 `6bad5025c1d31bd4c2ba69db14ba59084ff3b707531e035ae20852133be0412d`.
- Validation: `analyze_ccw43.py` validates canonical/row hashes, unique IDs, all owner-A/B/C references, 86 preserved entries, exactly 20 unchanged market contexts, all 120 unique provider/candidate/market combinations, exact model-visible prompt hashes, statuses and schema-shaped positive decisions. Local run returned **PASS**. Input set: exactly 50 cases for each BTC, ETH, GRAM, SOL.
- A 41 alert /112 no_alert /47 ambiguous, 153 decisive; B 101 /59 /40; C 31 /167 /2. Owner combined candidate 31 /159 /10, 190 decisive, from 66 manually re-reviewed A/C disagreements and 134 retained A labels; 53 changed A. The owner saw C's assessment, did not supply written reasons. The owner reference is **NOT a new blind ground truth**.

## Complete CCW-16 20-case stratified diagnostic

Every row below represents **20 identical cases for its provider**, 6 combinations per case across prompts/providers: 120 of 120 valid. Original A has 16 decisive cases/4 ambiguous (excluded without silently turning negative); owner reference has 20 decisive/0 ambiguous in this subset.

| Reference | Provider | Old prompt | TP | FP | FN | TN | Precision | Recall |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Original A | Groq | production | 1 | 0 | 7 | 8 | 100% | 12.5% |
| Original A | Groq | materiality_v1 | 0 | 0 | 8 | 8 | undefined (no positives) | 0% |
| Original A | Groq | novelty_v1 | 3 | 0 | 5 | 8 | 100% | 37.5% |
| Original A | Cloudflare | production | 3 | 0 | 5 | 8 | 100% | 37.5% |
| Original A | Cloudflare | materiality_v1 | 3 | 0 | 5 | 8 | 100% | 37.5% |
| Original A | Cloudflare | novelty_v1 | 4 | 2 | 4 | 6 | 66.7% | 50% |
| Owner v1 | Groq | production | 0 | 2 | 6 | 12 | 0% | 0% |
| Owner v1 | Groq | materiality_v1 | 0 | 0 | 6 | 14 | undefined | 0% |
| Owner v1 | Groq | novelty_v1 | 3 | 0 | 3 | 14 | 100% | 50% |
| Owner v1 | Cloudflare | production | 3 | 1 | 3 | 13 | 75% | 50% |
| Owner v1 | Cloudflare | materiality_v1 | 2 | 2 | 4 | 12 | 50% | 33.3% |
| Owner v1 | Cloudflare | novelty_v1 | 3 | 4 | 3 | 10 | 42.9% | 50% |

Historical recorded bot decisions over all **200 frozen cases** (different observation source, not the matched 120-provider test): original A decisive subset 21 TP /53 FP /20 FN /59 TN (28.4% precision, 51.2% recall); owner reference 20 TP /75 FP /11 FN /84 TN (21.1% precision, 64.5% recall). These historical scores **MUST NOT** be compared as a controlled provider/prompt lift against the 20-case experiment.

### Priority 1: missed new meaningful extensions — false negatives
- On owner pilot positive cases, Groq production missed all 6: 5 materiality rejected, 1 novelty rejected; Groq old materiality missed all 6 by materiality, whereas Groq old novelty missed 3 (1 materiality, 2 novelty). Cloudflare production missed 3 by materiality; old novelty still missed the same 3.
- `ev_fc6cf60f2f603650` ETH: current 3h -2.29%, fresh -1.04% after prior alert 29m ago and new low; A/C/owner all positive. Groq production and old materiality rejected, old novelty recovered.
- `ev_7bc9f5986fce346f` SOL: -5.29% over 3h, another -1.92% after prior alert 59m ago; A/C/owner positive. **All** six Groq/Cloudflare old variants rejected, often as continuation or routine. This is a key regression case for any new prompt.
- `ev_8b508b14b2220e57` SOL: -2.58% 3h, another -1.38% after prior alert 89m; A/C/owner positive. Cloudflare recognised the fresh extension; Groq prod and novelty classified as not new.
- `ev_b0444ced2d1e8577` BTC: sharp new trough-to-rebound 1h +2.17%, 30m +0.80%, previous alert 418m ago; A/C/owner positive. Groq prod dismissed novelty while old novelty recovered.
- `ev_a9913f63628cf57d` GRAM: current +1.69%, +1.72% since previous near-flat negative-window alert 329m earlier; A/C/owner positive. Quiet most recent 1h (+0.02%) does not erase substantial new window change. Only Groq old novelty positive.
- `ev_895e0dfdd31bff53` GRAM: A/owner positive, C negative with ordinary current window (-0.52%) and long elapsed since previous alert. All prompts rejected. **Contested label / uncertain calibration:** do not overfit to owner without independent adjudication.

### Priority 2: near-duplicate/noise alerts — false positives
- `ev_86a8ba257afb7ea2` BTC: large overlapping old 3h movement (+1.62%) but only +0.018% since prior alert 59m earlier, latest short intervals flat. Original A positive, but owner and C negative. Groq production positive (FP against owner); Cloudflare old materiality/novelty also positive. Thus original A scoring alone misses an important owner-identified duplicate.
- `ev_73ee7f7d464106e6` ETH: large daily drop -5.44% but routine current 3h -0.31%, previous alert 89m; original A ambiguous, owner/C negative. Groq production FP against owner; older candidates correctly reject.
- `ev_fc35d58391836075` SOL: ordinary net 3h +0.43%, 30m +0.76% bounce, still -1.96% below previous alert; original A ambiguous, owner/C negative. Cloudflare production/materiality/novelty all FP.
- `ev_f10d1068c89b3e34` ETH: ordinary +0.39% net, missing 30m/1h and price nearly unchanged since older same-direction alert. Cloudflare novelty FP.
- `ev_6cb59fb839fa1a11` SOL: routine +0.36% net/0.16% daily, minor latest retrace with market-wide headline. Cloudflare novelty FP. News must remain support, not evidence of materiality.

### Priority 3: reference and provider calibration drift
- A/C agree 134/200 (67%); on original A-ambiguous cases only 1/47 agree; 46/47 disagreements. Owner's 190-decisive v1 scores differ markedly from original A on pilot and historical baseline. Do not promote owner reference to independent truth or overwrite A.
- Groq old novelty improved positive capture on fixed owner pilot (0 ->3 TP) without any new pilot FP, whereas Cloudflare old novelty increased owner FP (1 ->4) without improving TP (3 ->3). Therefore no provider-pooled claim, and neither old prompt wins robustly.
- Missing/sparse short windows and asset-specific relative historical context can confuse materiality; recent alert age and high event counts can be misused as hard novelty disqualifiers. Root-cause labels are patterns/hypotheses, not proof of internal LLM mechanisms.
- Original 200-case observational outcomes show owner per-asset historical TP/FP/FN/TN: BTC 2/23/3/21, ETH 3/20/2/22, GRAM 8/16/5/18, SOL 7/16/1/23. Retain these as *historical* evidence, not an estimate of new prompt performance.
- No independent CCW-42 production sample, no account-level measured USD charge, no fresh holdout. **INSUFFICIENT EVIDENCE** for production precision/recall improvement, cost equality, repeat suppression end-to-end or live final-text quality.

## New complete prompt proposals (not evaluated)
See `candidate_manifest.json` for exact instruction and full 200-case rendered fingerprints; text files are complete, not diffs or relabelled CCW-15 text. Each appends a new behavioral block to byte-verified unchanged production instruction, retaining the system message, canonical six-field response and original fixed-input serializer:
1. `ccw43_incremental_market_leg_v1.txt` (E1): force independent market-leg analysis and explicit change since prior alert. Expected qualitative tradeoff: lower FN on material ETH/SOL/GRAM extensions; lower FP when old large window overlaps flattened present. Risk: recasting noisy incremental fluctuations as fresh events.
2. `ccw43_two_sided_counterfactual_v1.txt` (E2): explicitly challenge both positive and negative decisions using current-market-only evidence first and novelty evidence second. Expected qualitative tradeoff: reduce headline/reversal/overlap FP while recovering genuine newly deepened legs. Risk: extra instruction complexity, over-conservatism and missed material changes.
These expectations are **hypotheses only**. Neither text has a quality claim and neither changes numeric decision backend or per-user 4h cooldown.

## Reproducibility and handling
- Recompute: `python reports/event-alert-review-20261016/ccw43_private/analyze_ccw43.py` then `python reports/event-alert-review-20261016/ccw43_private/design_ccw43.py` from project checkout.
- Private only: `pilot_case_audit_PRIVATE.json` contains all 20 contexts, model decisions and independent C rationales; `owner_200_case_audit_PRIVATE.json` preserves all 200 case contexts + owner/A/B/C relationships; `evidence_summary.json` stores aggregate scores and SHA references.
- Existing source files were read-only and hash-checked. Baseline production prompt byte-equivalence was asserted. No tracked repository files changed.
- C independently reviewed original 200 before seeing A/B, but owner v1 was created after reviewing C; source bias remains.
- No fresh provider/model test has been performed. See `CCW29_HANDOFF.md` for finite experimental design and explicitly required owner approval.

## Result
**CCW-43 design deliverables PASS.** Production-quality release gate: **INSUFFICIENT EVIDENCE**, pending CCW-29 new paired tests, independent blind holdout, cost/provider isolation and owner acceptance.
