# First-run onboarding conversion

## Goal

Give a new private-chat user the cached BTC brief on `/start`, then expose optional coin selection
after that value delivery. Improve first-session completion without changing Premium, payment,
watchlist, attribution, or Event Alert behavior.

## Clarified requirements

- `/start` immediately sends the deterministic cached BTC brief for a new user.
- Record `onboarding_started` before the delivery attempt; record `onboarding_completed` and
  `instant_brief_viewed` only after Telegram successfully delivers the brief.
- BTC remains the enabled free default. A clear `Customize coins` action opens the optional
  multi-coin chooser after the brief.
- ETH, SOL, and GRAM selection continues to save Premium intent and continues into the existing
  trial/paywall behavior. Returning-user behavior is unchanged.

## Out of scope

- Event Alert logic, entitlement rules, trial duration, pricing, payment/subscription validation,
  acquisition attribution, and unrelated watchlist behavior.
- Schema migrations and provider/LLM calls.

## UX decision

Before: `/start` showed BTC plus locked Premium choices and required `Show my brief` to see any
market value. After: `/start` sends the BTC brief first with `Customize coins`; the optional
chooser retains its existing save-and-show-brief path for Premium intent and trial offer.

## Expected changes

- `bot/onboarding.py` and `bot/keyboards.py`: first-run delivery and deferred chooser callback.
- `tests/test_onboarding.py`: delivery ordering/failure, deferred choice, returning user, and
  existing Premium/trial regression coverage.
- `docs/product_analytics.md`: document funnel-event semantics and cohort comparison query.

## Risks and mitigations

- A failed Telegram send must leave completion and brief-view events absent: send first, persist
  value-delivery events second, with a regression test.
- A brief must stay deterministic and cached: retain `build_instant_brief` and test its source
  boundary; no migration or provider call is introduced.
- Existing partial onboarding users must still be able to choose Premium coins: retain the current
  selector and confirm/trial routes behind `Customize coins`.

## Test strategy

1. Write and run tests for immediate first-run brief delivery, delivery failure, and the deferred
   chooser before implementation.
2. Run focused onboarding tests after implementation.
3. Run required compile, Ruff, full test, and Compose validation checks.
4. Obtain required security, product-policy, test/CI, architecture, and Premium/payment reviews.
