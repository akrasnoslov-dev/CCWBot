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
6. Representative deterministic message-size tests target roughly <=1.45k-1.50k average message characters, while clearly not claiming equivalence to provider prompt tokens.
7. Focused and repository-required verification is green.
8. PR targets `dev`; do not merge.

## Risks

- Over-relaxing trajectory detection could admit fabricated monotonic paths.
- Over-compacting candidate news or prior-event context could change significance, attribution, or semantic repeat handling.
- Strict JSON Schema may contribute fixed provider prompt overhead; do not remove it without direct evidence and scoped safety proof.

## Test strategy

Test-first:
- add a passing regression for aggregate "across the window" wording;
- retain/add failing regressions for unsupported persistent trajectory, invented sub-window metric, wrong direction, and wrong percentage;
- replace misleading provider-token-style fixture assertions with deterministic message-character budget assertions plus a clearly labelled proxy;
- run focused tests, then the repository verification suite.

## Proposed decomposition

1. Correct trajectory-marker semantics and add regressions.
2. Tighten/compact Event Analysis instructions and model payload without removing required semantic facts.
3. Update exact-context schema only if model-visible semantic fields change.
4. Run focused/full verification and self-review.
