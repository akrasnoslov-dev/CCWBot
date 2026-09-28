# Release PR #247 findings follow-up

## Goal

Resolve the two valid PR #247 findings before production deployment: prevent Neo4j credentials
from appearing in Graphify instructions or process arguments, and guarantee a BTC-only v2 first-run
brief for every unfinished user.

## Clarified requirements

- Use Graphify's supported `NEO4J_PASSWORD` environment channel for authenticated Neo4j pushes;
  do not request, repeat, or interpolate a password in chat, commands, tool transcripts, or argv.
- An unfinished user receives a BTC-only first brief, even when a legacy v1 partial selection
  enables Premium coins or disables BTC.
- Preserve legacy subscriptions and Premium intent for `Customize coins`; do not change trial,
  entitlement, payment, watchlist, Event Alert, or returning-user behavior.
- Record v2 completion and first-value events with the BTC-only first-run selection count.

## Plan

1. Add failing workflow and onboarding regression contracts for the secret channel and legacy
   subscription states.
2. Render the v2 first brief from an ephemeral BTC-only selection while leaving persisted rows
   untouched; use the same BTC-only selection count for its delivery events. Derive monitoring
   status from persisted rows so a legacy disabled BTC subscription is not promised as active.
3. Replace the Graphify Neo4j example with an environment-based password handoff and explicit
   chat/transcript prohibition.
4. Run focused, full, Compose, CI, and required security/product/payment/test reviews; resolve
   PR #247 threads before the dev and release merges.

## Scope and risks

- Expected files: `bot/onboarding.py`, onboarding and workflow contract tests, Graphify export
  guidance, and this task record.
- No migration or schema change. The key risk is accidentally overwriting legacy subscriptions or
  changing downstream customization/trial behavior; tests retain those selections and intent.
