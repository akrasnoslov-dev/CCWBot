# Event Analysis factual grounding

## Goal

Prevent Event Analysis provider output from asserting unavailable or misattributed market-time-window facts, including the live SOL incident where a 24-hour/since-alert change was described as a three-hour move.

## Scope and acceptance

- State the time-window data contract explicitly in the Event Analysis prompt.
- Reject unsupported positive provider claims in title, body, and factual action wording before they can set `should_alert=true`; use existing provider fallback.
- Preserve LLM-owned significance, concrete conditional Possible action copy, exact context reuse, and defensive Telegram rendering.
- Revalidate timestamp-dependent since-alert wording on exact reuse without adding observation timestamps to the reuse fingerprint.
- Cover unavailable/misattributed window claims, one-snapshot trajectories, valid rounded/window/24-hour/since-alert claims, fallback, all-invalid behavior, and defensive presentation.

## Boundaries and risks

No schema or migration change is required. This task must not add a numeric significance threshold, alter entitlement/cooldown policy, merge, or deploy. Provider-output interpretation is heuristic, so tests cover explicit time, direction, rounding, and mixed-claim wording.

## Verification

Run focused Event Analysis/pipeline/reuse/presentation tests, full pytest, ruff, py_compile, diff check, Compose config, and available migration checks. Record unavailable Docker/PostgreSQL checks accurately.
