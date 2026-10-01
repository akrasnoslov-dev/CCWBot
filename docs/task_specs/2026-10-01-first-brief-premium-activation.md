# First-brief Premium activation

## Goal
Improve the first-run step after the BTC instant brief so new users understand that ETH, SOL, and GRAM are available through Premium and can reach the existing free-trial flow with fewer ambiguous cues.

## Clarified requirements
- Keep the first delivered value as the deterministic BTC-only brief.
- Replace the first-run `Customize coins` CTA with `Add ETH, SOL & GRAM →`.
- For trial-eligible new users, append concise copy explaining that BTC is free and adding a Premium coin unlocks the free 7-day Premium trial.
- Do not falsely advertise a free trial to users who already have Premium or have already consumed a trial.
- Record a durable `onboarding_customize_opened` event when the first-run customize action is opened so the brief-to-customize activation rate can be measured.
- Preserve the existing selector, Premium intent, trial, paywall, payment, watchlist, and returning-user behavior.

## Out of scope
- Changing Premium eligibility, trial duration, payment flow, pricing, Event Alerts, or acquisition attribution.
- Changing Telegram Ads creative or spending the remaining Stars.
- Auto-selecting Premium coins or auto-starting a trial.

## Acceptance criteria
- Fresh trial-eligible user sees the new CTA and trial-oriented explanatory copy after the BTC brief.
- Ineligible/already-Premium users see truthful non-trial copy.
- Opening the customize selector records exactly one idempotent `onboarding_customize_opened` event per onboarding version.
- Existing coin selection and trial-offer flow remains unchanged.
- Product analytics docs expose the new event for direct Telegram Ads cohort analysis.
- Focused tests fail on the old behavior and pass after implementation; full required checks and migration checks are green.

## Expected areas
`bot/onboarding.py`, `bot/keyboards.py`, analytics allowlist/model constraint, one Alembic migration, onboarding/analytics tests, and `docs/product_analytics.md`.

## Implementation plan
1. Lock the CTA/copy and customize-click analytics behavior in focused onboarding tests.
2. Update first-run copy/keyboard and persist an idempotent customize-open event.
3. Extend the analytics allowlist/check constraint with one additive migration and document the new funnel step.
4. Run focused tests, full repository verification, migration checks, diff review, and CI before merge.

## Risks / data impact
Additive analytics taxonomy change plus a check-constraint migration only; no user data rewrite and no entitlement/payment mutation.
