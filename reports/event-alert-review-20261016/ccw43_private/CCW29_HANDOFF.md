# CCW-29 Handoff — New CCW-43 Event Analysis Prompts
Prepared 2026-10-23. **DESIGN ONLY. No provider replay authorized by CCW-43.**

## Artifacts and cryptographic identity

Canonical frozen 200-case market dataset: SHA-256 `ed126380369014e6522cee49009b880cf0350aa7565269d50641c3f1bbdc3bee`.

Unchanged baseline:
- Current exact production instruction (without terminating LF) SHA-256: `e6496d98812ca7380a899c33c8e8e9294eddcee00d157515a179a91892aeb308`.
- Frozen control source `benchmarks/ccw15-v1/production.txt` remains unchanged; full file SHA-256: `0635c03e68b8fe519ae64bdc433c5a057e101581c9dfdf34929ec4d67d860ac4`. The offline generator asserts parity with the actual `_EVENT_SIGNIFICANCE_INSTRUCTIONS`.
- This is a controlled baseline, **NOT** one of the two new candidates.

**NEW candidate E1:** `ccw43_incremental_market_leg_v1.txt`
- Full UTF-8 LF file SHA-256: `1a74766e81d775d4d93159dd4cae15b7ef8867164f94783ee0aee6ad760120de`.
- Exact instruction text excluding final LF SHA-256: `af47056653aa7257ffe0ab5e339f216b45f889cc6c18890472492a5622a77247`.
- Concatenated SHA-256 list of exact 200 rendered model-visible user prompts: `eab472c80e40588455b5d0eb0b27f53fed3fd5b2ba74fc8562c1474e38c36eee`.
- Hypothesis: reduce misses of genuine new legs within old same-direction episodes; reject large overlapping old-window moves with near-flat incremental observations.
- Regression risks: duplicate episode from ordinary continued fluctuations; conflicting or missing prior-alert fields.
- Regressions to retain in **private** case tests: SOL deepens another -1.92% after one-hour-old alert; ETH declines another -1.04% in a new half hour; BTC has changed only +0.018% after previous hour-old alert. No cutoff permitted as an implementation rule.

**NEW candidate E2:** `ccw43_two_sided_counterfactual_v1.txt`
- Full UTF-8 LF file SHA-256: `4efe2d8b1ae7ff9d429ec9237a885802e1c67afaf9a5160c5a0802f891d55e0a`.
- Instruction SHA-256: `aab1596ee2cf8432a9bb7a427323d3a23a76e82e16f02b0b640a8cfd790f8228`.
- Rendered 200 model-visible user prompt hash aggregation: `02290d7bec8086dccab692d2a1dd43ef89e90424867e7ffb7937e093114fcab1`.
- Hypothesis: first isolate current market evidence from news/24h/previous events; then check novelty, finally challenge a negative result against any new substantial extension.
- Regression risks: unnecessary extra reasoning/tokens, too-conservative materiality, short-lived but real reversal lost.
- Private regressions: SOL short 30m bounce +0.76% with ordinary full window +0.43% and price still below older alert is not a material reversal; ETH +0.39% without short-window values is ordinary; GRAM current +1.69% with quiet latest hour can still have a distinct new path.

Both candidates are fully written new instruction strings built from the exact unchanged baseline plus new independent revisions; both rendered on all 200 original market payloads for fingerprints without provider calls. Max user message UTF-8 length observed in original 200 cases was **4523 bytes** for each. Revalidate request envelope byte count against any isolated Cloudflare 6000-byte cap before execution.

## Exact prompt construction
System message is the unchanged `You are a careful crypto monitoring assistant.`.
For EACH original frozen input, build:
`<full candidate instruction minus its final newline> + "\\nInput JSON:\\n" + _json_dumps(_event_significance_prompt_payload(original_input))`.
Keep case ID, `input_sha256`, prompt/message SHA-256, exact provider request body SHA-256, model, schema, reasoning, response envelope, timeout, token quota and per-attempt response provenance. Do not use explanations or A/B/C/owner labels in the inference prompt. Check 200 unique IDs and 50 per asset. Reject any changed input or duplicate attempt; never silently retry.

Expected **six fields exactly**: `symbol` (coin), `materiality` = material|routine|unclear, `novelty` = new|continuation|repeated|unclear, `should_alert` boolean, `reason_code`, `confidence` = low|medium|high.
Positive only if materiality=material, novelty=new, and reason_code is unusual_move|fast_move|reversal|trend_acceleration|market_news_alignment; negative reason code only routine_move|news_only|unclear. News-only must remain false. No numeric hard gates. Strict validation and normalized six-field JSON are required; invalid responses stay invalid in coverage, not no-alert.

## Provider-specific comparison settings to freeze

**Groq:** API/provider Groq, model `openai/gpt-oss-120b`, `reasoning_effort=medium`, `max_tokens=6300`, JSON strict six-field validation. This is the known CCW-16 declared protocol and runner requirement, not proof of the deployed bot's future production routing.

**Cloudflare Workers AI:** `@cf/meta/llama-3.3-70b-instruct-fp8-fast`, `max_tokens=300`, Cloudflare-supported structured response envelope, exact same case text and six-field logical schema; independently score all results. Last isolated runner conservatively reserved up to 250 Neurons per request and used an experimental 1000 estimated Neurons/day cap after restoring the runner; quota/account-wide spend are not independently verified. **Do not reuse a rate/cost cap blindly for a new run.**

For **both**: temperature, sampling, exact schema envelope, HTTP timeout, full model revision/endpoint and any provider-specific parsing must be captured from authoritative CCW-16 pinned request evidence or new approved CCW-29 contract **before activation**; these are not fully certified by the current local read-only ledger. If exact request-config parity is not verified, stop rather than claim controlled prompt-only equivalence. Version full per-provider config fingerprints (without secrets) and capture measured tokens, latency and failure modes. No provider fallback or mixed-provider quality statistic.

## Proposed bounded CCW-29 execution (requires separate owner approval)
1. Preflight unchanged private frozen market inputs, protected labels, both candidate texts and production baseline, actual provider request schema, secret isolation, free-tier headroom, per-provider exact cost/TPM/RPM limits, no paid plan. Read-only inspect runner; **do not auto-reactivate CCW-16's canceled/stopped scheduler**.
2. Suggest a finite exploratory **20 cases × 2 new candidates × 2 providers = 80 new attempts**, paired on the same fixed stratified 20 cases. Any additional unchanged baseline **new** executions, larger calibration replay, unseen holdout calls or retries must be counted in a separately authorized budget. The existing CCW-16 completed production baseline is historical; if configuration/version drift exists, it cannot serve as new matched baseline.
3. Independently hold out **new market events not among the original 200**. Obtain independent, blind labels before unblinding candidate/model results. Ensure both positives and negatives, BTC/ETH/GRAM/SOL, and clear ambiguous handling. Same 200 historical cases and owner v1 are **tuning**, not a fresh holdout.
4. Compare by provider and prompt separately against **original A** and **owner v1** with exact TP/FP/FN/TN, precision/recall, ambiguous/unscored counts, per-asset and high-risk case breakdown, significance-vs-novelty classifications, cost, retries, quota, errors and latency. Do not generalize 20-case precision to real traffic.
5. Stress mandatory counterexamples: new material continuation after a recent prior alert, stale overlapping big window but flat current price, partial rebounds, missing 30m/1h, news-only, recent-event count alone, asset-specific materiality and A/C contested GRAM. Add final message factuality and PostgreSQL concurrency/cooldown tests in later engineering/release gates.
6. Require explicit owner acceptance and measured quality/cost results before considering any code or production change. **No merge, deployment or new provider spend automatically follows this handoff.**

References: `CCW43_REPORT.md`, `candidate_manifest.json`, `evidence_summary.json`, `pilot_case_audit_PRIVATE.json`, `owner_200_case_audit_PRIVATE.json`. Do not move private case-level material into repository commits, public PRs or Linear.

## Current status
- Artifact integrity and new candidate construction: PASS (offline).
- Provider performance on either NEW candidate: **INSUFFICIENT EVIDENCE** (0 calls).
- Independent holdout: **NOT STARTED**.
- Account-wide cost and deploy safety: **UNMEASURED / NOT AUTHORIZED**.
