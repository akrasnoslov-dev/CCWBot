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

### Reuse all paid pilot responses before any new test (PR 2)

The earlier 63-call pilot and disjoint 16-call holdout were saved in **different
private ledgers**. The two runs must be merged before spending more tokens;
otherwise full-dataset scoring misses valid existing decisions and needlessly
repeats provider requests. This local/offline command does **not** contact Groq:

```bash
python scripts/merge_event_significance_runs.py --benchmark reports/event-alert-review-20261016/v2_private_sanitized.json --states reports/event-alert-review-20261016/live_groq_ab_20261016/replay_state.json reports/event-alert-review-20261016/trajectory_holdout_private/replay_state.json --out reports/event-alert-review-20261016/merged_pilots_private
```

The merger refuses changed input hashes, different models/prompt fingerprints,
duplicate variant+case provider attempts, unknown result fields and requests
exceeding the previously authorised 600-call ceiling. It records all requests
(including ambiguous outcomes), preserves unknown provider failures without
turning them into negative decisions, and writes only gitignored local data.
The new output directory must not exist; source ledgers are not modified.

After merging, a resumed, explicitly approved replay can use
`--out reports/event-alert-review-20261016/merged_pilots_private` and
`--variants production trajectory_evidence --skip-ambiguous`. Its
`attempted_requests` count already includes both earlier runs. The complete
153-case paired score must be produced from that same merged state, never from
a handpicked pilot cohort. Do not promote any prompt until all required
quality/cost gates pass. This merge is **not yet executed** if the owner's
local workstation is offline.

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

### Additional calibration and previous-delivery fix (2026-10-17)

A resumed private replay merged the 63-call pilot and 16-call disjoint holdout,
then used **64 further Groq calls**, with no provider/schema failures. Cumulative
owner-approved usage is **143/600 Groq calls** and **257,427 provider-reported
tokens** across the two dates. The new replay remains gitignored and contains
only opaque case hashes, validated decisions and usage.

The latest prompt-only candidates were **not deployed**. The following use
**different deliberately error-stratified scored subsets** of the same real
frozen corpus; percentages are *not* unbiased production-quality estimates:

| Prompt | Decisive scored | TP | FP | FN | TN | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `relative_displacement` | 19 | 5 | 2 | 3 | 9 | 71.4% | 62.5% |
| `rebalanced_core` | 25 | 8 | 0 | 5 | 12 | 100% | 61.5% |
| `global_prior_safe` | 20 | 6 | 1 | 2 | 11 | 85.7% | 75.0% |

On the **same 20 cases** that have all three historical/core/global decisions,
the original bot had TP=4, FP=8, FN=4, TN=4; `rebalanced_core` had
TP=5, FP=0, FN=3, TN=12; and `global_prior_safe` had
TP=6, FP=1, FN=2, TN=11. No candidate meets the 90% recall requirement;
the complete 153-case evidence gate is **not satisfied**.

**Confirmed implementation fault found:** `get_latest_sent_event_alert_context_for_symbol`
previously sorted by reservation `created_at`, even when successful delivery
occurred much later. The prompt's previous-alert age also used reservation
time. It now orders by `coalesce(sent_at, created_at)` and derives age from
successful `sent_at`, falling back only for legacy sent rows. An isolated
SQLite DB regression and direct context unit tests pass. The revised real
PostgreSQL regression was **not locally verifiable at that point** because the
Docker daemon/DB was unavailable; it later passed on CI's PostgreSQL service,
as recorded below.

**Confirmed context contract:** the prior-alert hint is the last *globally*
delivered alert for a symbol, not the previous delivery for every recipient.
Matching global `prev.f` does not prove that the current subscriber was
notified; actual four-hour cooldown uses that user's own successful delivery
records. `global_prior_safe` explicitly calibrates that distinction without
changing the recipient cooldown or adding a deterministic price gate.

The full historical baseline can now be scored **without re-calling Groq**:
all 153 owner-reviewer-A-decisive cases are present in the frozen observed
bot outcomes: TP=21, FP=53, FN=20, TN=59; precision=28.4%,
recall=51.2%. Score live candidate decisions against that real baseline:

```bash
python scripts/score_event_significance_ab.py --benchmark reports/event-alert-review-20261016/v2_private_sanitized.json --reviewer-a reports/event-alert-review-20261016/reviewer_A_significance_for_pr1.json --run-state reports/event-alert-review-20261016/merged_pilots_private/replay_state.json --historical-baseline --variants historical global_prior_safe
```

This saves an entire baseline-provider replay. At that stage the
`global_prior_safe` candidate had **20/153** decisive cases; the
expanded replay below raises coverage to **42/153**. The remaining cases
still require real provider inference across quota windows. The historical
baseline is not a same-configuration live-model control. Release gates for
final delivered text and measured monetary/provider costs also remain
open. Do not merge or deploy PR 2 on exploratory scores.

### Expanded Groq significance replay and CI database validation (2026-10-17)

A further **23 Groq API requests** resumed the `global_prior_safe`
candidate from the merged private ledger: 22 valid strict-schema responses
and **one HTTP 429 (rate limit)**, at which point the runner stopped.
Cumulative replay: **166 authorised attempts**, including this one
rate-limited attempt, and **295,849 provider-reported tokens** for successful
responses only. A 429 is not an automatic negative market decision.

On the **42 completed reviewer-A-unambiguous cases** for
`global_prior_safe`: TP=18, FP=3, FN=4, TN=17,
**precision=85.7% and recall=81.8%**. These deliberately
error-stratified cases do **not** pass the 90% recall gate, nor do
they cover all **153** scored cases (111 remain). The
historical baseline on the *same 42* cases was TP=10, FP=12, FN=12,
TN=8. The full frozen historical baseline remains TP=21, FP=53,
FN=20, TN=59. Do not extrapolate the selected-cohort scores.

After the daily/account rate limit resets, a human explicitly
restarting the runner can include `--retry-rate-limited` with
`--approve-provider-requests`, `--variants global_prior_safe`
and the same `--out` merged run. Only the recorded HTTP 429 entry
is eligible for a new attempt; a successful existing decision is never
re-requested. The runner updates that single scored row in-place,
increments its persistent overall request counter *before* HTTP, and
retains the prior failed attempt through conservative missing-attempt
token accounting. A renewed 429 stops immediately again. Choose an
adequate new cumulative `--max-total-tokens` based on actual account
budget rather than interpreting 600 approved calls as unlimited quota.
No unattended Groq process was left running.

**PostgreSQL integration gate:** The project's GitHub Actions CI
provides a PostgreSQL 16 service. The added `test_event_alert_pr2_postgres.py`
now accepts the existing CI-only `OPS_AGENT_POSTGRES_TEST_DATABASE_URL`
and flushes rows without committing them. The CI run for commit
`83b2a3a` **explicitly PASSED** both the new PostgreSQL alert-context
test and the two PostgreSQL advisory-lock tests. Local Docker is not
required for this CI gate.

### Rate-limit retry and coarse prior-family hypothesis (2026-10-17)

A short explicitly authorised retry attempt recovered the recorded 429 case
without re-querying successful decisions. The next distinct market case
received another HTTP 429, with a **293-second `Retry-After`**. The runner
stopped immediately. Cumulative **168 attempted calls** (166 successful
strict-schema decisions and 2 HTTP 429 attempts) and **297,533 measured
provider tokens**; both failures are counted in the persistent attempt ledger.
With 43 valid scored `global_prior_safe` cases: TP=19, FP=3,
FN=4, TN=17, precision **86.4%**, recall **82.6%**;
**110 reviewer-A-decisive cases remain**. This is still a deliberately
selected subset and fails the release gates.

A new OFFLINE-only hypothesis `global_prior_no_family` withholds
`prev.f`, the globally sampled previous alert's coarse directional
semantic family. The remaining `prev.min` and `prev.cw` facts
remain unchanged. A shared prior family is **not evidence** that a
subscriber has seen the same event, and it may cause the model to mistake
fresh movement in the same direction for a duplicate; however removing
the field could also increase false-positive repeats. No production
prompt or backend decision gate changes. The hypothesis has zero measured
provider results until a new, rate-limit-respecting replay is completed.
A candidate-specific input-view fingerprint prevents accidentally mixing
its outputs with older full-payload prompts.

Recorded 429s are retryable **only** with the explicit
`--retry-rate-limited` opt-in, after the provider-supplied
`Retry-After` interval. Replacing a failed scored row does not lose
the failed request: `attempted_requests` still includes all calls and
the unmetered call is conservatively charged against the local
safety-token estimate. Provider 429 is not evidence of the exact
rate-limit type; the organization account's limits govern.
All regression tests and the PostgreSQL CI gate are separate from
these market-quality results.

### Further provider-limit evidence and safe candidate refresh (2026-10-17)

After obeying the 293-second `Retry-After`, Groq completed one
`global_prior_no_family` call, then returned another HTTP 429
with `Retry-After: 340 seconds`. The experiment immediately stopped.
Across the full private merged ledger the counter is now
**170 provider attempts**, with **167 valid recorded decisions**,
**two currently recorded 429 rows** and **one previously retried 429**
preserved in the cumulative request count; provider-reported measured
tokens are **299,324**. `global_prior_safe` retains 43 valid
decisive results (86.4% precision, 82.6% recall on this selected cohort).
The new no-family candidate has **one valid result only** and cannot yet
be assessed; no change to production prompt or eligibility is justified.

The replay accepts `--refresh-unused-candidate-config` to explicitly
revise the fingerprint for a candidate with **zero recorded responses**
in an existing ledger, while strictly refusing any changed fingerprint
for a candidate with actual observations. This avoids mixing a
hypothesis that was revised before its first provider call with any
older measured answers. A separate opt-in `--retry-rate-limited`
is still required for recorded HTTP 429 cases. The latest 340-second
backoff must be respected; do not continuously retry until accepted.

### Significance evidence and adaptive stopping (2026-10-18)

The new `global_prior_no_family` experimental prompt strips the globally
sampled previous alert's coarse semantic family, preserving its age/move.
It was replayed on **45 reviewer-A-decisive events**: TP=19, FP=2,
FN=4, TN=20 (**90.5% precision, 82.6% recall**) on the deliberately
error-stratified cohort. The best possible complete-recall outcome now is
**37/41 = 90.24%**, and this would require correctly identifying every
one of the 18 as-yet-untested positives. It is NOT accepted. **108**
decisive cases remain for this candidate. The replay stopped at the next
HTTP 429 with provider `Retry-After: 190 seconds`; the request was counted.
Across all historical experiments, the cumulative approved ledger now
records **215/600 requests** and **375,799 provider-reported successful
tokens**. Do not treat the allowed call ceiling as account quota.

The benchmark tools now compute a mathematical **best-possible**
precision/recall bound against all 41 positive and 112 negative reviewer-A
labels. With `--stop-on-impossible-gates`, the live replay stops as soon
as existing false negatives/positives make **85% precision + 90% recall
mathematically unattainable** even if all remaining labels are perfect.
Invalid/provider-error rows do not count as negative decisions. This
protects the Groq quota and is only an evaluation tool, not a runtime
numeric alert cutoff.

Offline diagnosis of the **200 real frozen sampled paths** supports the
next hypothesis: reviewer-A-positive cases had median observed path
efficiency **0.756** versus **0.345** for negatives, and median largest
sampled-step magnitude about **1.039%** versus **0.373%**. This is
descriptive evidence only, not an alert threshold, trained classifier
or an unbiased out-of-sample quality score. All 200 have computable
path facts. The new `path_facts` and `market_signal_path` candidates
include transparent, backend-computed path efficiency, adjacent-step
movements and current distance from sampled extrema. In particular,
`market_signal_path` removes the global previous-alert and recent-count
hints from significance entirely, making the model evaluate the current
noteworthy market window; user-specific semantic cooldown still decides
whether a subscriber receives a repeat. This is an **unverified offline
hypothesis** and requires a real Groq replay before any product-rule change.

### Global novelty follow-up and quota-respecting continuation (2026-10-18)

The `global_prior_no_family` prompt now has **45 valid scored cases**:
TP=19, FP=2, FN=4, TN=20, **precision 90.5%, recall 82.6%**
on the deliberately error-stratified cohort. In the complete 153-case
reference it can at best reach **37/41 = 90.24% recall**, and
only if no further alert-worthy event is missed. No promotion is justified.
The next call returned Groq HTTP 429 with `Retry-After: 190 seconds`,
so that batch stopped automatically.

Offline path diagnostics computed for all 200 real frozen trajectories
show that the model can miss substantial intra-window movement when the
net change is modest. A new, **unproven** `market_signal_path`
candidate removes the global previous-alert and recent-count hints,
supplements the sampled price path with verified efficiency, maximum
adjacent sampled-interval steps and distance from extrema, and evaluates
the current noteworthy market displacement. The backend's separate
per-recipient semantic cooldown is unchanged. The first candidate
call was valid; the second received another HTTP 429 with
`Retry-After: 524 seconds` and the runner stopped.

Cumulative authorised live benchmark activity is **217/600 requests**
with **377,645 provider-reported measured tokens** from successful
responses. Rate-limited requests count against the call ceiling and
conservative token budget even without provider usage receipts.
`market_signal_path` has only **1 valid case**, nowhere near the
153-case completeness gate. No production LLM instructions or
delivery logic were changed in this calibration step. CI and local
tests remain separate from proof of product-quality improvement.

The user approved continuing the remaining evaluation over subsequent
quota windows. Work must not blindly consume all 600 requests: the
mathematical bound in the replay/score tools retires an unachievable
candidate early. The offline scorer's feasibility bound uses **all valid
reviewer-A-decisive responses for each candidate**, even when other variants
have not completed those cases. Paired confusion matrices remain restricted
to the common cases for fair A/B comparisons. Otherwise a multi-variant
report with a tiny overlap could incorrectly report a 100% best-case recall
while ignoring known false negatives from the rest of a candidate's ledger.
The private frozen benchmark and reply records must remain gitignored;
PR 2 stays Draft and unmerged until all quality and release checks pass.

### 18 October evening: rate-limit replay and early recall screening

After the 505-second recorded backoff, Groq accepted one more bounded
`market_signal_path` case, then returned HTTP 429 with a fresh
`Retry-After: 598 seconds`. The merged private ledger contains **223/600
approved requests** and **four valid** `market_signal_path` decisions,
all correctly negative on four original-bot false positives. **This says
nothing about recall yet:** the candidate has not seen an owner-labelled
positive in its replay; **149 decisive cases remain**, and the full gates
cannot be passed on this tiny selected prefix.

The optional `--screen-positives-first` replay flag now stably orders
the existing **41 owner-labelled positive** cases before negatives,
preserving the ordinary ordering *within* each label. Its sole purpose
is to stop spending the shared free-tier provider quota on an
ultimately hopeless prompt once more than four false negatives have
been observed: at least 37/41 owner-labelled positives are needed for
90% recall. It never changes the frozen cases, reference labels, input
hashes, alert policy or model, and all 112 negatives still require
completion before precision can be accepted. **Positive-screen
precision is not a population or paired quality estimate.**

The replay enforces the saved HTTP 429 `Retry-After` across manual
restarts; it does not force a new request while the provider's time
window remains active. No replay is run by this documentation.
PR2 remains Draft, with no merge/deploy.

### Rate-limit diagnostic improvement (2026-10-18 late)

A fresh explicitly approved replay of `market_signal_path` after the
previous 598-second backoff returned **HTTP 429 immediately**:
**224/600** cumulative attempts, **no additional validated decision**.
The new backoff was **257 seconds**. The corresponding strict-schema
candidate still has **4/153** decisive results. No quality claim is made.

Groq's official rate-limit documentation specifies distinct request
counts per day and token counts per minute. The benchmark now records
ONLY allowlisted numeric quota headers, when the provider supplies them:
`rate_limit_daily_requests`, `rate_limit_remaining_requests`,
`rate_limit_minute_tokens`, and `rate_limit_remaining_tokens`.
This can distinguish exhausted daily-request capacity from per-minute
token pressure in **future** failures without saving arbitrary
headers, response bodies, tokens or account identifiers. Previous
HTTP 429 records do not have these headers; their exact limiting
dimension remains unknown. Continue to respect `Retry-After` and
never force rapid retries into the production-shared free-tier quota.

### Follow-up rate-limit evidence and safe classification (2026-10-18)

The next explicitly approved replay after the provider-specified wait
produced one schema-valid `market_signal_path` positive (BTC,
correctly identified against reviewer A), then HTTP 429 again.
The merged ledger reached **226/600** requests, with five valid
`market_signal_path` responses (TP=1, FP=0, FN=0, TN=4) on the
deliberately selected prefix; **148 decisive cases remain**, so
the significance quality gate is still open.

The 429 included `Retry-After: 541 seconds`. Groq's numeric
rate-limit headers reported 999/1000 daily requests remaining and
8000/8000 minute tokens remaining. Therefore those two reported
counters were not exhausted; they do **not** reveal which *other*
provider limit caused the 429. The offline runner now also safely
classifies the provider's structured error message into one of the
allowlisted rate-limit dimensions (TPD, TPM, RPD, RPM, ITPM, OTPM),
when explicitly present. Raw error messages, organization IDs and
provider headers are never persisted. The new classification
will only apply to subsequent attempts; existing stored errors
cannot be retroactively diagnosed. Do not force another request
before the recorded retry interval or assume this account is
eligible for paid service tiers.

### Autonomous local PR2 replay (2026-10-19)

The approved benchmark may run unattended on the **authorised Windows
workstation only**. The worker `scripts/auto_event_significance_replay.py`
uses the existing ignored `reports/event-alert-review-20261016/` dataset
and merged replay ledger; it cannot run from GitHub Actions or leak those
private files. It makes at most **one Groq request per invocation**, with
a strictly enforced minimum hour between requests, and reserves a
conservative **8,300 tokens per attempt**. Limits are **8 requests and
60,000 reserved tokens in any rolling 24 hours**, capped by the original
**600 approved calls** overall and a separate cumulative token safety
ceiling. This reserves the majority of the published 200K free-tier TPD
for the live bot. These limits are intentionally stricter than Groq's
public model quotas and are not a guarantee of free capacity.

The worker respects provider `Retry-After` across restarts, applies
additional exponential backoff on repeated 429s, pauses for a full day
when TPD/RPD is positively identified, and **stops for manual review
after three consecutive rate-limit failures**. It also stops automatically
when either full-cohort significance gate becomes unattainable or all
153 decisive events have been scored. A completed 153-case score still
requires technical, delivery-quality and cost gate review before release.
It never changes the production prompt, bot delivery logic or Telegram.

Installation is explicitly operator-initiated on the local Windows machine:

```powershell
powershell -NoProfile -File .\scripts\install_event_significance_replay_task.ps1 -Install
Get-ScheduledTaskInfo -TaskName 'CCWBot-PR349-EventSignificanceReplay'
Get-Content .\reports\event-alert-review-20261016\merged_pilots_private\hourly_replay_status.json
```

Remove the scheduler, preserving all benchmark data, with:

```powershell
powershell -NoProfile -File .\scripts\install_event_significance_replay_task.ps1 -Uninstall
```

On 19 October the owner-approved task was installed and a real manual
trigger via Windows Task Scheduler succeeded with `LastTaskResult=0`:
**request 227/600** returned schema-valid, raising
`market_signal_path` coverage to **6/153** (TP=2, FP=0,
FN=0, TN=4 on the selected pilot). The full quality gate remains open.
The scheduler works only with the machine powered on and the authorized
user signed in; it cannot run during sleep or shutdown. ChatGPT/Desktop
Commander connectivity is not required for the local Windows task.

### One-shot Groq Batch acceptance replay (2026-10-19)

The previous one-request-per-hour Windows scheduler was unsuitable for
finishing a frozen 153-case reference promptly and requires a powered-on
computer. It is now **DISABLED** on the canonical development machine
until the one-shot alternative has been evaluated. Do not re-enable it
while a batch is prepared or submitted: concurrent writes would
invalidate the frozen request manifest and potentially double-bill.

The official Groq Batch API allows the same `openai/gpt-oss-120b`
model to process an entire set of individual chat completions as one
asynchronous job, **without consuming ordinary synchronous model rate
limits**. It can continue after the client machine switches off. The
provider offers a **24-hour to 7-day completion window**, so this is
*one submission*, **not guaranteed instant completion**. A separate
Developer plan grants Batch access; upgrading changes provider billing.
The Batch API uses a 50% discount on published per-token pricing.
Source: https://console.groq.com/docs/batch and
https://console.groq.com/docs/billing-faqs.

An authenticated **read-only access test** on the currently configured
account returned `403 not_available_for_plan`. This is a **confirmed
account-plan blocker**, not an unstable 429 provider retry. We must
not submit a paid batch or upgrade the plan without explicit owner
approval.

An offline dry run of
`scripts/groq_batch_event_significance.py --prepare` has already
prepared exactly **147 still-unscored reviewer-A-decisive events**,
preserving all **6 validated** `market_signal_path` decisions. The
ledger remains at **227/600 allowed synchronous attempts**.
Each request uses the **same model, pinned prompt, temperature,
reasoning effort, max tokens, strict schema and frozen input** as
the original single-event runner. Inputs, opaque ID mapping, and
replay state stay under the existing ignored private directory.
The script refuses duplicate successful cases, unknown outputs, changed
prompt fingerprints, missing 600-call approval capacity, a stale
prepared ledger, and a second submission after one was attempted.
It durably reserves all submitted cases against the 600-call budget
*before the provider's create request*, conservatively accounting for
uncertain network outcomes.

To keep provider billing separate from production, optionally configure
a **dedicated Developer-organization API key** under the ignored
`GROQ_BENCHMARK_BATCH_API_KEY` local environment variable. Otherwise
the script uses the existing `GROQ_API_KEY`; upgrading the shared
organization may affect all production Groq usage charges. This is
**not** approval to create a paid account or install any new secrets.

```powershell
# Preparation only: NO network, NO bill
.\.venv\Scripts\python.exe scripts/groq_batch_event_significance.py --prepare

# Read-only access check (currently 403 on Free plan)
.\.venv\Scripts\python.exe scripts/groq_batch_event_significance.py --check-access

# Only after the owner expressly approves billable batch execution
.\.venv\Scripts\python.exe scripts/groq_batch_event_significance.py --submit --approve-billed-batch

# After returning to the computer, perhaps a day later
.\.venv\Scripts\python.exe scripts/groq_batch_event_significance.py --status
.\.venv\Scripts\python.exe scripts/groq_batch_event_significance.py --collect
```

The collector maps out-of-order provider output using hashed opaque
`custom_id`, rejects unexpected/duplicated IDs, validates **each**
response against the original Event Alert schema, and stores only
sanitized decisions and token usage in the existing private ledger.
It reports final precision and recall **only after every decisive case
is valid and the frozen historical reference is fully paired**.
Provider failures, missing outputs or expired requests do not count as
no-alert and cannot silently pass the gate. A second PR/product
review is still required to assess render/delivery quality, model
cost and any runtime change. The batch does NOT deploy or send
Telegram alerts. The provider may retain batch inputs/results for up
to 30 days under its retention policy.

Cost planning, not an invoice: the first six successful candidate
calls averaged about **1,025 input + 940 output tokens**. At the
published **$0.15/M input** and **$0.60/M output** and **50% Batch
discount**, the corresponding rough estimate is **$0.053 for 147
cases**. Actual tokens can differ, and the request output cap of
6,300 tokens means the output-only worst-case arithmetic would be
about **$0.278**, plus input tokens. These are *not account spend
limits* and do not include production usage if the organization is
upgraded. Groq Developer supports optional organization spend limits.

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


## PR #349: opt-in multi-provider significance discovery (October 2026)

The PR2 quality screen can replay the **same frozen, sanitized** market inputs
against configured Gemini and Cloudflare fallback models, as independent
provider/model/prompt candidates. Provider input contains **no reviewer labels**;
the reviewer A decisions remain local. Do not pool predictions from different
providers or models into one candidate's precision or recall.

Use `scripts/multi_provider_event_significance_benchmark.py` with
`--provider gemini|cloudflare --variant <candidate> --max-requests N
--approve-provider-requests`. On Gemini, `--model-override
gemini-3.5-flash-lite` allows a separate, fingerprinted candidate if the
configured model is unavailable. Free-tier quotas, provider Retry-After, and
provider-side billing arrangements must be respected; this tooling cannot
guarantee that any account is on a free billing tier.

`scripts/auto_event_alert_quality_replay.py --once` is a **local, opt-in**
worker. It uses an OS file lock and private, gitignored result ledgers, skips
candidates once their best possible full-cohort precision/recall is below the
acceptance floor, and screens the next prompt separately. A Windows Task
Scheduler job may run it periodically **only while the authorized machine is
running**. When a temporary production pause is in effect, the private
`quality_worker_policy.json` defines a UTC cutoff to reserve Groq capacity
for the scheduled production restart. Neither replay script sends Telegram
messages, modifies production, merges a PR, or proves final rendered message
usefulness.

These repeated development screens are **candidate discovery**, not an
independent held-out quality certification. PR2 acceptance still requires
full 153/153 decisive frozen-case coverage for one unchanged candidate,
correct per-symbol/delivery-weighted metrics, independent final-message
review, semantic cooldown and delivery checks, provider reliability and
account-level cost evidence. Missing or failed cases are not true negatives.
