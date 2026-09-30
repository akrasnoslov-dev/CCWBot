# Event Analysis grounding and token budget

## Goal

Reduce Event Analysis factual/schema validation failures without weakening grounding, and reduce real production prompt usage toward the existing <=700 average prompt-token target.

## Production evidence

Post-deploy production evidence from 2026-09-29 16:56 UTC shows:
- Groq Event Analysis: 147 attempts, 137 success, 10 schema errors (6.8%).
- Error classes: 4 analysed-window trajectory unsupported, 2 window value mismatch, 2 window direction mismatch, 2 market percentage mismatch.
- GRAM accounts for 6 of 10 schema errors.
- Successful Groq calls average about 994 prompt tokens.
- Real input messages are commonly about 2.0k-3.3k characters; the previous UTF-8 chars/4 fixture estimate materially understated provider-reported prompt usage.
- A replay of 162 persisted production Event Analysis inputs against the first PR implementation measured about 1,764 mean message characters, p95 about 2,415, and max 2,582, so the original synthetic <=1,500 average guard was not representative enough.
- After the final production-shaped compaction revision, the same 162-input replay measures about 1,389 mean characters, p95 about 1,752, and max 1,762.
- Across the 147 matching production Groq calls, the observed relationship was approximately `prompt_tokens = 0.336 * input_chars + 207`. Applying that empirical relationship to the revised replay projects about 674 average prompt tokens and about 885 total tokens using the observed ~211 average completion tokens. This is a projection only; provider telemetry after deployment remains the acceptance check.

Known false positive:
- A grounded statement such as "declined 0.312% across the 180-minute window" can currently be rejected as an unsupported trajectory because generic wording such as "across" is treated as a trajectory marker.

Known true positives that must remain rejected:
- invented sub-window moves;
- unsupported monotonic/consistent snapshot trajectories;
- wrong time-window attribution;
- wrong sign/direction;
- percentage values that do not match supplied market facts;
- unavailable metrics.

## Clarified requirements

- Event Analysis remains the sole significance decider.
- No deterministic numeric significance threshold.
- No cadence, provider-order, model, recipient, cooldown, dedupe, or delivery changes.
- Preserve factual-grounding validation.
- Preserve exact-context reuse semantics.
- No database/schema migration.
- No paid service or new token-counting dependency.
- Production token verification remains provider telemetry after deploy; deterministic tests must be labelled as message-size/proxy checks only.
- Keep news freshness semantic but compact: model-visible news carries whole hours old rather than two timestamp strings, and Exact Context Reuse fingerprints the same age bucket.
- Strip RSS/HTML markup from Event Analysis news summaries before truncation; omit markup-only remnants rather than spending prompt budget on image tags/URLs.

## Out of scope

- News Intelligence schema failures.
- Market Report schema failures.
- Provider/model changes.
- Production deployment or merge to main.

## Expected areas

- `bot/alerting/event_analysis.py`
- `bot/services/ai_agent_groq.py`
- `bot/alerting/event_identity.py` only if the compact semantic model contract changes
- focused Event Analysis validation/token tests
- canonical docs only if a durable contract changes

## Acceptance criteria

1. A grounded aggregate-window statement using "across the 180-minute window" passes when its value/direction match `chg_window_percent`.
2. Explicit consistent/persistent/throughout trajectory claims still fail when snapshots do not support them.
3. Invented sub-window metrics still fail.
4. Wrong direction, wrong period, unavailable values, and mismatched percentages still fail.
5. Compact prompt retains the facts required for significance, grounding, news attribution, previous-event context, and exact-context reuse.
6. Representative deterministic message-size tests target <=1.45k average message characters, including a production-shaped six-snapshot/three-news case, while clearly not claiming equivalence to provider prompt tokens.
7. The persisted 162-input production replay stays near or below that average budget; actual provider-token targets are verified only after deployment.
8. Focused and repository-required verification is green.
9. PR targets `dev`; do not merge.

## Risks

- Over-relaxing trajectory detection could admit fabricated monotonic paths.
- Over-compacting candidate news or prior-event context could change significance, attribution, or semantic repeat handling.
- Strict JSON Schema may contribute fixed provider prompt overhead; do not remove it without direct evidence and scoped safety proof.

## Test strategy

Test-first:
- add a passing regression for aggregate "across the window" wording;
- retain/add failing regressions for unsupported persistent trajectory, invented sub-window metric, wrong direction, and wrong percentage;
- replace misleading provider-token-style fixture assertions with deterministic message-character budget assertions plus a clearly labelled proxy;
- include a production-shaped six-snapshot/three-news regression and replay persisted production payloads outside the committed test suite before merge;
- preserve all snapshot values while encoding them as compact pairs, remove redundant previous-alert title text, clean/truncate news summaries, retain coarse news age, and bound model-visible percentage precision to six decimals without erasing tiny non-zero values;
- run focused tests, then the repository verification suite.

## Proposed decomposition

1. Correct trajectory-marker semantics and add regressions.
2. Tighten/compact Event Analysis instructions and model payload without removing required semantic facts.
3. Update exact-context schema only if model-visible semantic fields change.
4. Run focused/full verification and self-review.
