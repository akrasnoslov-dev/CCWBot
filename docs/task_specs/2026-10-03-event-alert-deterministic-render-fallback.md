# Event Alert deterministic render fallback

## Problem

Production bundle `20261003T172117Z_cc57fa09` shows the two-stage Event Alert flow is degraded after the render-schema hotfix: 42 of 67 `event_alert_render` logical operations ended in terminal failure. All 42 failed chains began with a Groq client-side schema validation failure; Gemini/Mistral fallback attempts then failed or were skipped. Event Analysis significance itself remained healthy (204/204 provider calls succeeded), Telegram delivery was healthy once reached (967/967), semantic cooldown had zero inside-cooldown deliveries, and duplicate-delivery detectors were clear.

## Confirmed failure mechanism

Groq did return parseable render JSON in the failing operations. The terminal
`schema_validation_failed` category was emitted by the client-side render validator, after JSON
parsing, not by the provider's strict JSON-schema transport. The current bundle did not retain the
specific application-validation subreason, so the historical split between market-claim,
trajectory, and related-news validation remains unknown.

The architectural defect is broader than one provider response: the render LLM was asked to
generate event identity, factual title, urgency, news selection, and prose, then the backend
strictly revalidated those fields. A presentation-model phrasing error could therefore destroy an
already-approved significance decision and unnecessarily consume fallback-provider capacity.
The fix moves the factual/identity fields (event_key and title) to the backend while preserving
LLM-owned presentation urgency.

## Goal

Reduce the brittle render contract at its source and also prevent an already-approved Event Alert
from being lost when presentation providers fail. Preserve the existing LLM-owned significance
decision and all factual/news validation, cooldown, recipient eligibility, and delivery safeguards.

## Requirements

- Keep Event Alert significance fully owned by the existing schema-validated significance LLM call.
- Keep the render LLM as the preferred optional presentation-copy path.
- Limit render-model ownership to `message_body`, supporting `related_news_ids`,
  `possible_action`, and `urgency`; keep event identity and factual title backend-owned.
- Filter unknown/duplicate render-selected news ids before full validation.
- Emit a stable value-free validation-reason log category when application validation rejects
  render copy, so future ops bundles can identify the exact validator class without raw LLM text.
- If the complete render provider chain still fails, build deterministic presentation fields only from supplied market evidence.
- Deterministic fallback must not introduce a numeric significance threshold, new-news bypass, urgency bypass, or cooldown bypass.
- Deterministic fallback must pass the existing full Event Analysis validation before any market event or delivery can be created.
- Use no related-news attachment in fallback unless it can be selected deterministically without inventing causality.
- Persist render logical-operation telemetry as a completed deterministic fallback while retaining provider-attempt failures in `llm_usage_logs`.
- Add an operator-visible sanitized log event for deterministic render fallback.
- Do not change Premium/payment/watchlist behavior.
- Do not change the four-hour semantic cooldown.

## Out of scope

- Provider billing/tier changes.
- Production deployment or restart.
- Relaxing factual market validation.
- Changing Event Analysis significance criteria.
- Tuning semantic cooldown.
- Solving ops-agent structured-evidence truncation in this PR unless required for the fix.

## Expected files

- `bot/alerts.py`
- `tests/test_event_alert_pipeline.py`
- `docs/alert_logic.md`
- `docs/llm_usage.md`
- possibly focused observability tests if telemetry contract requires it

## Data / migration impact

No schema or migration change expected.

## Test strategy

1. Regression test first: positive significance + exhausted render chain must produce a valid deterministic Event Alert decision instead of `None`.
2. Verify deterministic fallback uses only backend-derived title/situation/action and no attached news.
3. Verify render logical outcome records deterministic completed fallback with the original sanitized failure reason.
4. Verify existing factual validation, news-only guard, cooldown, duplicate-delivery, and normal render success tests remain green.
5. Run focused Event Alert/LLM suites, then repository-required verification if feasible.

## Acceptance criteria

- Old implementation fails the new regression test.
- Updated implementation passes it.
- Normal render success behavior is unchanged.
- Fallback decision is schema/factual-validation clean.
- Provider attempt failures remain observable.
- Cooldown and duplicate-delivery behavior remain unchanged.
- Focused tests and required verification pass.
