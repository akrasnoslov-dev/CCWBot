# CCW-15 — Reviewer A Event Analysis prompt pack (2026-10-21)

**Scope:** reproducible OFFLINE preparation only. No production edit, no new model call, no paid request, no Telegram sends or production DB access. Do not restart canceled CCW-28 timers. Replay execution, quota approval, and independent holdout belong to CCW-16/CCW-29.

## Versioned artifacts

This directory contains three **complete instruction texts**. The Event Analysis *system* message is unchanged: `You are a careful crypto monitoring assistant.` For each frozen input, the *user* message is the file's exact instruction content (without its final LF), followed by `\nInput JSON:\n` and the production compact JSON from `_event_significance_prompt_payload` serialized by `_json_dumps`. The strict `event_significance` six-field output schema remains unchanged. The accompanying offline Python tool builds this exact message; it also prints SHA-256 instruction and aggregate per-case prompt fingerprints.

| Candidate ID | File | Precise evidenced failure | Intended change | Principal regression risk |
| --- | --- | --- | --- | --- |
| `production` | `production.txt` | Current observed baseline | Control: **unchanged** dev/production Event Analysis instruction | Model/config drift; ensure strict parity |
| `ccw15_materiality_evidence_v1` | `materiality-evidence.txt` | Routine positive decisions, especially marginal BTC moves; minor counter-moves named as reversals; headline-assisted FP | Demand meaningful current-window and actually observed path evidence, while retaining substantial net moves after small bounces | More missed material events if insufficient path observations |
| `ccw15_novelty_independent_v1` | `novelty-independent.txt` | Material movements skipped around prior alerts / counts or short counter-moves; weak novelty distinctions | Treat global previous alerts and event counts as *limited evidence*, not proof of duplication; recognize independent fresh material price evidence | Duplicate-looking event-level positives; backend recipient cooldown must still suppress repeats |

These are **untested hypotheses**, not better-scoring models. Both are additive complete prompt revisions grounded in the materiality/novelty diagnostic, not a decision gate. They keep no deterministic percentage/percentile threshold, no news-only alert, strict materiality → novelty → should_alert ordering, and valid positive/negative reason codes. They do not change candidate payloads, back-end schema, model/provider selection, shared single analysis per event or recipient delivery. The frozen PR #349 `materiality_first`/`balanced_novelty` options are historical unscored experiments, **not** the present candidate IDs.

### Ground-truth evidence and limitations

Owner-designated Reviewer A is the **sole reference** for these 200 real-market cases. Preserve Reviewer B's 99 original disagreements untouched. The decisive split is 153, with 41 `alert`, 112 `no_alert`; 47 `ambiguous` remain unscored. The saved baseline has 21 TP, 53 FP, 20 FN, 59 TN (precision 28.4%, recall 51.2%). Per symbol: BTC 2/21/4/20, ETH 3/13/3/17, GRAM 8/11/8/10, SOL 8/8/5/12 (TP/FP/FN/TN). Across A's labelled cases the historical BTC low-magnitude FP and ETH/SOL/GRAM larger missed moves are descriptive *evidence*, not universal significance thresholds.

Known illustrative errors from the saved PR #349 report: independently low-value BTC +0.0192%, +0.0909%, −0.2684%; historically missed ETH −3.6373%, BTC +2.7958%, SOL −2.5798%, GRAM −2.2014%. Classify these only against their **complete original contexts**. Additional regression probes: repeated GRAM movements, little bounces against large window trends, sign changes against 24h without current significance, strong full-window displacement with missing 30m/1h data, relevant-but-news-only stories, previous-alert global identity vs recipient cooldown, ambiguous cases excluded.

Frozen 200-case canonical digest (from PR #349): `ed126380369014e6522cee49009b880cf0350aa7565269d50641c3f1bbdc3bee`. The full manifest and human label JSONs are **private**, not Git-tracked. Git-only review cannot freshly inspect the 200 original IDs or independently rerun their hashes. Do not label this private-data gate verified until the script below succeeds in the authorized isolated workspace. Never commit/upload the private dataset or reviewer records.

## Read-only local check

From the matching repository branch:

```bash
python -m scripts.ccw15_prompt_pack
python -m scripts.ccw15_prompt_pack --benchmark /private/approved/frozen-v2.json --reviewer-a /private/approved/reviewer-a.json
```

The first command verifies the exact live code constant against `production.txt` and prints content SHA-256 hashes; no private input needed. The second checks manifest/input hashes (via `load_frozen`), **exact 200 unique case ID-to-A label coverage**, 50 cases per symbol, expected A warrants and per-symbol FP/FN from the **actual scoring function**, plus aggregate SHA-256 for all 200 rendered prompts per candidate. Missing source files, changed inputs, incorrect Reviewer A mapping, or production prompt drift fail closed. It prints counts/hashes only, never raw input/labels/IDs. No live requests.

`_read_evaluations(reviewer_a)` and `report(dataset, labels)` use A **directly**; they do not average votes or silently resolve conflicts. The legacy `scripts/replay_event_significance.py` accepts two evaluators plus a reconciliation file; before using it to score recorded CCW-16 results, confirm the existing private owner-selected reconciliation exactly reproduces A for all 200 IDs. Any difference is a blocker: never use a consensus scorer as if it were A.

## CCW-16 matched-input replay contract (NOT authorized by this task)

1. Pin this branch commit, production baseline module SHA and **three prompt instruction SHA-256 values** from the offline check. Pre-register candidate IDs, model, system prompt, compact JSON serialization, strict six-field schema, `dataset_sha256`, 200 `input_sha256`, pricing, and actual effective router options. Keep `production` as current deployed prompt, not the historical PR #349 variant.
2. **Primary chain:** Groq `openai/gpt-oss-120b`, `reasoning_effort=medium`, Groq-specific 6300 effective completion-token cap; same temperature/response_format/timeouts and identical case order for all variants. Pinned current provider env must be audited read-only; changing only the instruction text defines the experiment. `OPENAI_ENABLED=false` and no OpenAI calls.
3. **Fallback:** evaluate Cloudflare `@cf/meta/llama-3.3-70b-instruct-fp8-fast` separately, with its supported structured response envelope and explicitly recorded effective model parameters. Never pool Groq and Cloudflare decisions to claim a prompt improvement. Do not include retired Gemini/Qwen candidates.
4. Run on the **existing isolated Hetzner runner environment only after separately verifying** least-privilege account, no bot/DB/Telegram credentials, no scheduler from canceled CCW-28, no production queries/writes, and **explicit owner approval of free-tier Groq quota isolation**. Never compete with bot's production Groq allowance. No automatic job activation; no paid API. Use the pack's `build_prompt(original_input, candidate_id)` and original `input_sha256` unchanged; use a checkpoint/attempt ledger with bounded retries, per-attempt latency and verified usage tokens.
5. Predeclare a finite stratified diagnostic screen (e.g. 40 frozen, balanced by symbol and Reviewer A truth, without modifying/replacing the full 200), then only run qualifying variants to completion. Stop any candidate early when even perfect remaining classifications cannot reach either precision ≥85% or recall ≥90% on 153 decisive cases. In particular target at least 37/41 TP; for any partial run upper bounds are `TP_max = TP_so_far + remaining_A_alert_cases`, `recall_max = TP_max/41`, `precision_max = TP_max/(TP_max + FP_so_far)`. Do not treat failed/invalid responses as no-alert or quietly drop their coverage. Set a fixed maximum request/time budget, cap transient retries, stop on real rate/TPM quota danger, and require owner approval before any extension.
6. For each candidate record all **200** statuses and all 153 decisive A labels (or explicit missing coverage), 47 ambiguous separate, complete TP/FP/FN/TN and precision/recall, per-symbol counts, decision deltas, duplicate exposure, token usage, provider attempts, 429/timeout/invalid-schema counts, latency p50/p95, USD cost and nominal free-tier usage with denominators. Delivery-weighted exposure is contextual, not an independent relevance score. Use original, not fabricated, actual baseline measurements; keep unmeasured values as unknown.
7. Pass a **new independent held-out market sample** with fresh labels before product acceptance (CCW-29), plus final Telegram text usefulness/factual review, actual four-hour recipient cooldown and technical/CI checks. Do not relabel the 200 or select a fourth candidate based on outcome. All eight release gates in `docs/alert_logic.md` still apply.

**Status at artifact creation:** prompt pack prepared. Private dataset/A-scoring verification is blocked until an authorized copy is accessible. No model replay, quota test, actual precision delta, held-out confirmation or release gate is claimed.
