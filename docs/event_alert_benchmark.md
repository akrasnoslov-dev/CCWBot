# Event Alert benchmark and historical diagnostics (PR 1)

This is a **diagnostic** companion to [alert_logic.md](alert_logic.md), not a new
significance rule. The runnable entry point remains
`scripts/replay_event_significance.py`. The existing synthetic cases are
**test hypotheses** and must never be combined with real-market quality results.

## Frozen evidence contract

- Manifest: `tests/fixtures/event_alert_benchmark/v1.json`
- Version: `v1-2026-10-16`; SHA-256 of canonical `cases`:
  `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`
- Actual fully replayable **real-market examples: 0**. No approved full
  historical LLM inputs or privacy-approved independent human labels were
  available to populate the repository at PR 1 creation.
- Target: **150–200** real BTC/ETH/GRAM/SOL cases. This is **not met**.
  Existing synthetic cases remain in `tests/event_significance_replay_cases.json`,
  outside the frozen real-market benchmark.
- No test assumes the 0.16% BTC event is unimportant solely from its percentage,
  or the 4.03% SOL event is always important solely from its percentage.

An operator may construct a **new** frozen `v2` manifest only from permitted,
privacy-safe market evidence, collected via the investigator SELECT-only access
path described in [observability.md](observability.md), or independently verified
public market archives. Never dump entire production tables or transmit private
user data, prompts, raw model payloads, secrets, payment data or chat identifiers.

### Case schema

Every real case must have an opaque `id`, `symbol`, a single primary
`scenario_type`, `source_type` (`approved_read_only` or
`public_market_archive`), and the **canonical original significance-stage
`input`**. Include full precision market price, analysed-window change, window
length, at least two original snapshots, 24h/short-window context, previous
alert context, relevant selected news (or an empty list), and recent-event counts
*where these facts were genuinely available*. Preserve missing fields as missing,
rather than inventing them.

Include the case's `input_sha256`, computed using
`scripts.event_alert_benchmark.digest(input)`. Set the manifest's
`dataset_sha256` to `digest(cases)` and never edit an already published
manifest in place. To add evidence, create a new version and record the
provenance, extraction window, original production revision, effective
provider/model/reasoning configuration, and sampling/eligibility limitations.
Do **not** derive real cases from synthetic fixtures or abbreviated ops-agent
aggregates.

A case's `observed` object may contain evidence-backed `should_alert`,
`delivered_count`, `eligible_recipients`, `delivery_failures`,
`llm_calls`, `provider_attempts`, `total_tokens`,
`rate_limit_attempts`, `operating_cost_usd`, `same_event_duplicates`,
`same_family_duplicates`, and an independently privacy-approved sanitized
`final_message`. Omit unavailable values; do not default unknown metrics to
zero. Store only facts actually evidenced for that event. If accurate eligible
recipient counts are missing for **no-alert** cycles, recipient-eligible
weighted recall remains unmeasured.

Sample both sent and no-alert cycles, plus distinct significant, routine,
borderline, repeat, continuation, reversal, news-present and news-absent cases.
Sampling only sent messages produces **selection bias** and cannot measure
recall. Keep balanced coverage by symbol, not only BTC delivery volume.
One case is one distinct market analysis context; never repeat it hundreds of
times to represent the users who received it.

### Independent blinded evaluation

Two **different human evaluators** independently label each event after viewing
a **significance packet** without the bot's decision, delivery counts,
rendered text or provider output. Then they may assess a separate **message
packet** with the final delivered/sanitized message. Assess:
- `warrant`: `alert`, `no_alert` or `ambiguous`.
- `useful`: `true`, `false` or `null`; does the final text add a verified
  market relationship or useful next observation?
- `factual`: `true`, `false` or `null`; do all claims follow from context?
  Record unsupported directions, periods, numbers or catalysts for adjudication.

Each evaluator file has `dataset_sha256`, a distinct human `evaluator_id`,
and `labels` with `id`, `warrant`, `useful`, `factual`. A reconciliation
file uses the same structure with an adjudicator ID and explicit values for
disagreements. **Never resolve disagreements by majority-by-AI or running the
same model twice.** The evaluator files are not included in the repository
until privacy-approved and reviewed. Disagreements remain unscored until
explicitly resolved; ambiguous labels remain out of precision/recall.

### Owner-designated reviewer A reference for private v2 (2026-10-16)

For the private `v2-2026-10-16-private-human-review` frozen set (200 real
BTC/ETH/GRAM/SOL cases; dataset SHA-256
`ed126380369014e6522cee49009b880cf0350aa7565269d50641c3f1bbdc3bee`),
the owner explicitly chose **reviewer A as the reference on all 99
significance disagreements**. Keep both independent original reviews and the
unchanged frozen inputs. This is an **owner-designated reference**, not
agreement by both evaluators or independently established market truth.

The operator keeps the explicit conflict resolution in the private, ignored
`reports/event-alert-review-20261016/owner_reviewer_A_resolution_private.json`,
generated from original reviewer A labels. Supply it using `--reconciled`;
do not commit it or the private cases. All 47 reviewer-A `ambiguous` labels
remain excluded. The resulting **153 unambiguous** cases are the reference
scoring set for PR 2 candidates; preserve the former 94-case two-human
consensus metrics separately for transparency.

| Asset | TP | FP | FN | TN | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BTC | 2 | 21 | 4 | 20 | 8.7% | 33.3% |
| ETH | 3 | 13 | 3 | 17 | 18.8% | 50.0% |
| GRAM | 8 | 11 | 8 | 10 | 42.1% | 50.0% |
| SOL | 8 | 8 | 5 | 12 | 50.0% | 61.5% |
| **Total** | **21** | **53** | **20** | **59** | **28.4%** | **51.2%** |

For positive-decision delivery exposure, reviewer A's non-ambiguous labels
cover 504 deserved versus 6,286 low-value deliveries (**7.4% deserved**);
513 other deliveries are reviewer-A ambiguous. This is *not* population
precision or recipient-eligible-weighted recall. Those latter metrics remain
unmeasured where no-alert recipient eligibility is absent. The owner-supplied
message-quality summary (1 useful of 72 reviewed final messages) is a
single-reviewer assessment; independently confirmed factuality and a complete
two-evaluator final-text audit remain unverified.

No significance candidate replay, provider/token cost comparison or quality
acceptance gate is made valid merely by choosing the owner-designated labels.

### Commands (offline by default)

```bash
python scripts/replay_event_significance.py --benchmark
python scripts/replay_event_significance.py --benchmark path/to/v2.json --blind-export /tmp/significance.json
python scripts/replay_event_significance.py --benchmark path/to/v2.json --review-phase message --blind-export /tmp/message.json
python scripts/replay_event_significance.py --benchmark path/to/v2.json --evaluator-one /tmp/human-a.json --evaluator-two /tmp/human-b.json --reconciled /tmp/adjudication.json
python scripts/replay_event_significance.py --benchmark path/to/v2.json --evaluator-one /tmp/human-a.json --evaluator-two /tmp/human-b.json --reconciled /tmp/adjudication.json --recorded-run /tmp/candidate.json
```

For an explicitly owner-approved Groq replay (never during normal test runs),
use the bounded, resumable runner and compare only completed paired cases:

```bash
python scripts/live_event_significance_benchmark.py --benchmark reports/event-alert-review-20261016/v2_private_sanitized.json --reviewer-a reports/event-alert-review-20261016/reviewer_A_significance_for_pr1.json --out reports/event-alert-review-20261016/live_groq_ab_20261016 --approve-provider-requests --max-requests 12 --delay-seconds 18
python scripts/score_event_significance_ab.py --benchmark reports/event-alert-review-20261016/v2_private_sanitized.json --reviewer-a reports/event-alert-review-20261016/reviewer_A_significance_for_pr1.json --run-state reports/event-alert-review-20261016/live_groq_ab_20261016/replay_state.json
```

This replay sends frozen sanitized market context to Groq, but performs no Telegram
delivery, no production DB writes, no alert persistence, and no live market
fetch. The ledger counts an HTTP attempt **before** sending and refuses more
than 600 attempts in the selected run directory; it retains only validated
decisions, status, provider token usage, opaque IDs, and input/config hashes.
It stops on provider auth, cost or rate-limit rejection, rather than bypassing
account controls. A separate cumulative 125K-token safety ceiling (including
estimated unknown-usage attempts) limits this local replay's consumption of
the shared provider quota; it is not proof of remaining account-wide capacity. Do not publish anything beneath `reports/`.
Each candidate inherits production model, system prompt, JSON Schema, reasoning
effort and token ceiling; the only variable is the added prompt guidance.
**Partial pilot precision/recall is a paired-subset diagnostic, not a product
acceptance result**, even if it is numerically high. Unknown provider spending
must remain unknown. Never change the model-serving prompt on pilot evidence
without complete coverage and a validated trade-off.

### Live Groq pilot decision record (2026-10-16, PR 2)

The owner approved up to 600 requests, but this run stopped at **63 attempts** to
protect the free-tier account's shared operating budget. All **63 returned
schema-valid decisions**, with **115,148 provider-reported tokens** and no
observed provider failures. The run saved 24 responses for the unchanged
production prompt, 23 for `materiality_first`, and 16 for
`balanced_novelty`. Private case-level records and token receipts remain in
the ignored `reports/event-alert-review-20261016/live_groq_ab_20261016/`.

The completed, **deliberately error-stratified 23-case paired cohort**, excluding
reviewer-A ambiguous cases, yields:

| Prompt | TP | FP | FN | TN | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Unchanged current prompt | 1 | 0 | 10 | 12 | 100% | 9.1% |
| `materiality_first` | 3 | 1 | 8 | 11 | 75% | 27.3% |

These **are not unbiased production quality estimates** and **do not meet**
the 85%/90% release gates. The former 153-case scored historical reference
remains 28.4% precision and 51.2% recall; its stored decisions are not a
matched live-provider comparison. The materiality-first variant recovered
some missed alerts but also generated an unnecessary positive, so it was
**not promoted**. The discontinued balanced-novelty variant failed all
eight positive cases in the first paired pilot and was not tested further.
The experiment isolates the market-significance prompt; it does not validate
actual Telegram-copy usefulness or the dollar cost of provider calls.

Separate database checks: a real local PostgreSQL test (in an ephemeral
database removed afterward) verified that the cooldown honours confirmed
`sent_at` rather than late/early reservation `created_at`, with a legacy
fallback when `sent_at` is absent; existing advisory-lock concurrency and
cancellation tests also passed. This is not production-scale load validation.

**Next release gate:** design and measure a genuinely improved materiality
prompt on substantially broader unseen scored market inputs, including both
false-positive and false-negative exposure; do not merge/deploy PR 2 merely
because the small pilot improved relative recall. Source choices remain
LLM-owned without numeric backend alert thresholds.

### Unseen holdout replay after materiality recalibration (2026-10-16)

A new **experimental, non-production** `trajectory_evidence` prompt explicitly
asks the LLM to distinguish genuinely substantial current trajectories from
news-driven, minor counter-moves and routine noise, without numeric gates.
Its input JSON, pinned Groq model, strict response schema and token budget are
unchanged. A frozen **8-case unseen holdout**, excluding every previously
replayed event and reviewer-A ambiguities, was tested with matched live model
responses:

| Prompt | TP | FP | FN | TN | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| Current production instructions | 0 | 0 | 5 | 3 | Undefined | 0% |
| `trajectory_evidence` | 3 | 2 | 2 | 1 | 60% | 60% |

All 16 new provider calls returned schema-valid responses; 28,758 tokens were
measured. Cumulative owner-approved replay activity (this and the previous
experiment) was **79 requests and 143,906 measured tokens**. The local
36K-token experiment ceiling prevented further requests; none remains running.
Results and original reviewer labels are gitignored. The new candidate is
**not safe to promote**: it increases recall but admits new false positives
and fails the ≥85% precision and ≥90% recall release gates. Do not interpret
these deliberately selected subsets as a representative precision estimate.

The 200-case dataset and reviewer A decisions are unchanged. A full,
representative, paired evaluation on the 153 decisive cases remains
**uncompleted**: it requires substantially more provider tokens across
account-budget windows; the repo deliberately does not queue unattended jobs,
alter production credentials, or consume the operating bot's remaining
free-tier capacity. Tests only verify input and schema invariants, not model
quality. No prompt, model, Telegram or production delivery change is released.

The pinned candidate JSON must include `dataset_sha256`, `model`,
`config_fingerprint` (hash of provider, model, prompt revision, reasoning,
sampling and other effective settings, excluding secrets), and `results`.
Each result includes `id`, `input_sha256`, `status`
(`valid`/`schema_error`/`invalid_json`/`provider_error`), and a
**validated** `should_alert` boolean only on valid responses. Record observed
`llm_calls`, `provider_attempts`, `total_tokens`, `operating_cost_usd`
and rate-limit attempts only where measured. Candidate results must come from
a replay of the **unchanged** frozen input. This tool scores pre-recorded
results and makes **zero external calls**; the older synthetic `--live`
path requires its existing explicit provider opt-in.

Reports return four per-symbol breakdowns, event-level confusion,
recipient-eligible-weighted confusion (only where eligible cohort size is
known), final-text usefulness/factual rates with actual delivery weighting,
and measured coverage for each reliability/cost signal. A missing denominator
returns `null`, not 0% or 100%. Raw delivered counts are an exposure measure,
**not independent relevance labels**. Unambiguous labelled positives and
negatives only enter precision/recall. For additional quality measurement,
use the exact final message, not unvalidated render output.

## Historical investigation: evidence status

Evidence sources are the merged GitHub PRs
[#269](https://github.com/akrasnoslov-dev/CCWBot/pull/269),
[#293](https://github.com/akrasnoslov-dev/CCWBot/pull/293),
[#298](https://github.com/akrasnoslov-dev/CCWBot/pull/298),
[#327](https://github.com/akrasnoslov-dev/CCWBot/pull/327),
[#330](https://github.com/akrasnoslov-dev/CCWBot/pull/330),
[#334](https://github.com/akrasnoslov-dev/CCWBot/pull/334),
[#337](https://github.com/akrasnoslov-dev/CCWBot/pull/337) and
[#340](https://github.com/akrasnoslov-dev/CCWBot/pull/340), current `dev`
code and the privacy-sanitized operator report for the UTC period
2026-10-15 10:06:12–2026-10-16 11:05:28 (bundle
`20261016T110530Z_cd90a56d`). The raw private event rows were
**not exported or inserted into Git**.

| Finding | Classification | Evidence and remaining uncertainty |
| --- | --- | --- |
| BTC +0.1602% / 180m / percentile 32.9 generated 485 successful deliveries on Oct 16, with a positive medium-confidence significance decision. | **CONFIRMED** outcome, **LIKELY** limited marginal value | Sanitized decision timeline and delivery aggregates. Full snapshots, relevant news strength and exact final text unavailable; **UNKNOWN** whether the original judgement was a false positive. |
| Three subsequent +0.1185–0.1712% BTC positive decisions in a similar range were recipient-suppressed. | **CONFIRMED** | Same sanitized report. Suppression is distinct from LLM decision and from user-visible spam. |
| Earlier compact prompt yielded 178/178 negative significance decisions, including reported SOL +4.03% / 3h. | **CONFIRMED** historical observed outcome | PR #269 documents this production window. Prompt calibration as sole cause is **LIKELY**, not proven by a frozen counterfactual replay. |
| Splitting significance and render, then materiality/novelty ordering changes, improved controlled examples. | **CONFIRMED** code/history; **UNKNOWN** live impact | PRs #269/#293/#298. Synthetic/pinned-model replay results cannot establish population precision/recall. A risk of renewed over-suppression remains. |
| Stable numeric directional keys were previously missing semantic families, causing four-hour recipient cooldown bypasses. | **CONFIRMED** historical defect | PR #327 reports ~480-person BTC consecutive alerts 30 minutes apart. PR #330 reports seven ETH/GRAM/SOL repeat deliveries after the first fix; missing **current** family was the second gap. Both sides are now inferred from numeric price keys in `dev`. |
| The Oct 16 sample had no collected same-recipient same-family cooldown violation and no repeated full-message group. | **CONFIRMED** for that window; **UNKNOWN** universally | Sanitized outcome/identity detectors. A large BTC fan-out is not duplicate sends to the same recipient. |
| Final Situation text differs from stored Render in 10/10 distinct delivered events; Possible Action differs in 4/10. | **CONFIRMED** differences; **UNKNOWN** harm | Final assembly applies deterministic normalization and factual guards. Differences alone cannot prove loss of good text. |
| Situation repetition signals were 7/10, Action repetition 2/10 and generic Action 1/10. | **CONFIRMED** heuristic observations; **LIKELY** low differentiation | Signals use final sent text; no blinded human ratings. PRs #334/#337/#340 addressed several overly strict/incorrect guards. |
| Contradictory cross-period/persistence statements could bypass earlier validators. | **CONFIRMED** code defects in history; **UNKNOWN** actual bad deliveries | PR #340 added regression guards; the PR explicitly had no evidence these exact sentences were sent. |
| Exact context reuse is keyed to canonical market/snapshot/news/prior-alert input without numerical buckets. | **CONFIRMED** current implementation contract | `bot/alerting/event_identity.py` and existing exact-context tests; actual production reuse error rate is **UNKNOWN** without matched diagnostic outcomes. |

### Technical baseline, not product-quality scores

| Signal | Observed baseline (Oct 15–16 UTC) |
| --- | --- |
| Event Analysis terminal operations | 200/200 successful (positive and no-alert included); 17 positive decisions |
| Distinct market events / delivered events | 16 / 10 |
| Successful / failed Event Alert deliveries | 1,458 / 2; two classified blocked-user failures |
| Delivered messages by symbol | BTC 1,449; ETH 4; GRAM 4; SOL 1 |
| Delivered BTC events | Three events, with 481 / 483 / 485 recipients |
| Event-alert message placeholders / obsolete labels | 0 / 0 in aggregate checks |
| LLM provider churn | 25 failure incidents; 213 active-backoff skips; 263 logical operations reconciled with 0 gaps |
| Measured alert precision / recall | **UNKNOWN** / **UNKNOWN** (0 independently adjudicated full contexts) |
| Independently judged final-message usefulness / factual errors | **UNKNOWN** / **UNKNOWN** |
| Exact event-level LLM token totals / marginal provider cost | **UNKNOWN** in the supplied report |

The historic record is **not** a frozen 200-event replay benchmark: it lacks
the full decision inputs and independent labels. Do not treat all 183
non-positive analyses as correct negatives, or label delivered cases as true
positives by definition. Historic provider incidents are attempts, not
terminal analysis failures. No-cost claims require separate provider/usage
accounting for equivalent workloads; successful calls alone do not prove
zero marginal spend.

## Next-stage dependency and acceptance

PR 2 must use a genuinely populated and frozen real-market manifest (new
version, same schema), paired blinded human labels, and exactly matched
`dataset_sha256` and `input_sha256` values for all recorded candidate
responses. Preserve original code's significance authority and current
no-numeric-gate/no-extra-paid-cost architecture. Compare both event
precision/recall and delivery-weighted exposure/quality; report per symbol,
ambiguous/unscored counts and technical/cost coverage. A relevance gate must
not be won by suppressing all alerts.

PR 1 only supplies the harness, historical defect tests, observations and
guardrails. It **does not meet** any unmeasured October 16 acceptance gate,
does not prove the baseline useful and **changes no runtime behavior**.
