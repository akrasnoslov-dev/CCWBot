# CCWBot Growth Strategy: 0 -> 1 Premium

**Original research:** 2026-09-01  
**Production audit:** 2026-10-05  
**Basis:** current `dev` implementation plus read-only production aggregates.

This is research/strategy, not a canonical product contract.

## What is already done

The original P0 foundation exists:

- product-event analytics and first-touch attribution;
- tracked acquisition links;
- automatic first BTC brief;
- Premium coin customisation;
- one-time 7-day Premium trial;
- paywall, checkout, payment, and Premium-value events;
- successful-payment Premium/watchlist enrichment.

The next work is driven by production funnel evidence, not by the old September checklist.

## Production Growth Funnel Audit

The production session was verified as `ccwbot_investigator` with both transaction read-only
settings enabled.

Do not use the full Sep 2-Oct 5 totals as one conversion funnel because they mix different
onboarding versions. The clean pre-v3 activation cohort starts at the first
`onboarding_customize_opened` event: **2026-10-01 17:29 UTC**.

### Current comparable cohort

| Stage | Users | Conversion from previous meaningful stage |
|---|---:|---:|
| Bot started | 23 | - |
| Instant brief viewed | 22 | 95.7% of starts |
| Customize opened | 10 | 45.5% of brief viewers |
| Any coin-selection event | 6 | 60.0% of customize openers |
| Trial offered | 2 | 20.0% of customize openers |
| Trial started | 2 | 100% of offers |
| Premium value delivered | 2 | 100% of trial starts |
| Checkout started | 1 | sample too small |
| Payment succeeded | 0 | sample too small |

### What the selector data says

This is the clearest verified loss.

- 10 users opened Customize.
- 6 users toggled at least one coin.
- All 6 generated a `BTC -> selected_count=0` event at some point.
- 4 of those users never reached any selected coin above zero.
- Only 2 users reached Premium intent; both were offered a trial, both started it, and both received
  Premium value.

**CONFIRMED:** once a user reaches the trial offer, the current tiny sample converts cleanly.  
**CONFIRMED:** most loss happens before Premium intent is formed inside the selector.  
**LIKELY:** the selector is confusing because the CTA says "Add ETH, SOL & GRAM", but the next screen
shows BTC as the first active toggle and Premium coins with lock icons.  
**UNKNOWN:** paid conversion. The current comparable cohort is too young/small.

### Acquisition limitation

Across all product-event history, 136 of 137 users with `bot_started` are unattributed; only one
has a tracked `telegramads/general-crypto` attribution. Source-level optimisation is therefore not
yet statistically useful.

## Experiment 1 - Premium-only onboarding selector

**Owner:** ChatGPT implements and verifies.  
**User action:** none for development; production release remains a separate explicit release step.

### Change

For first-run onboarding only:

1. Leave the existing free BTC default untouched and do not show BTC as a toggle on the "Add ETH, SOL & GRAM" screen.
2. Show ETH, SOL, and GRAM as normal selectable Premium choices, without a lock icon that looks
   disabled.
3. Use a clear `Continue ->` action.
4. Keep full BTC/watchlist control available later in `/watchlist`.
5. Bump onboarding analytics version to `v3` so the new cohort is separable from v2.

No pricing, trial duration, entitlement, payment, or Event Alert behavior changes.

### Primary metric

`trial_offered / onboarding_customize_opened`

Pre-v3 baseline: **2 / 10 = 20%**.

### Decision rule

Evaluate after at least **30 v3 Customize opens**:

- **KEEP:** >=40% reach `trial_offered`, first-brief delivery remains >=95%, and
  `trial_started / trial_offered` does not materially deteriorate.
- **REVERT / redesign:** <=20% reach `trial_offered`.
- **INCONCLUSIVE:** 21-39%; continue to 50 Customize opens before deciding.

Do not start a second onboarding experiment before this one is measured.

## What happens after Experiment 1

1. Release v3 to production explicitly.
2. Wait for the minimum sample.
3. Run the same read-only funnel query.
4. Keep/revert using the rule above.
5. Then address the next largest verified bottleneck.
6. Use tracked links for future founder-led cohorts; do not optimise acquisition source while almost
   all users remain unattributed.

## Handoff prompt for a new chat

> Continue CCWBot growth work from current `dev`. Read
> `docs/research/growth_strategy_2026-09-01.md` and `docs/product_analytics.md`. Check whether
> onboarding v3 is already in production. If not, prepare the explicit production release; if yes,
> use the approved read-only `ccwbot_investigator` path to measure the v3 experiment. Do not start
> another growth experiment until at least 30 v3 `onboarding_customize_opened` events exist.
> Evaluate `trial_offered / onboarding_customize_opened` against the documented keep/revert rule,
> and mark conclusions CONFIRMED / LIKELY / UNKNOWN.
