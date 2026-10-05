# CCWBot Growth Strategy: 0 -> 1 Premium

**Original research:** 2026-09-01  
**Status refresh:** 2026-10-05  
**Basis:** current `dev` implementation.

This is research/strategy, not a canonical product contract.

## What is already done

The original P0 foundation is largely implemented:

- product-event analytics;
- first-touch acquisition attribution;
- tracked acquisition links;
- onboarding instead of command-only first use;
- deterministic/cached instant brief;
- Premium coin customisation;
- one-time 7-day Premium trial;
- paywall, checkout, payment, and Premium-value events;
- successful-payment Premium/watchlist enrichment;
- regression tests around onboarding, attribution, trials, and payments.

So the next job is **not** "build more growth features". The next job is to use production data and
find the biggest real funnel loss.

## Next task

**Owner:** ChatGPT.  
**User action required now:** none, except granting/using the approved read-only production access if
the active chat cannot reach it.

### Goal

Produce one production Growth Funnel Audit and choose exactly one next experiment.

### ChatGPT must do

1. Read `docs/product_analytics.md` and use its approved read-only production workflow.
2. Measure the latest useful cohort/window with at least:
   - attributed starts;
   - onboarding started/completed;
   - instant brief viewed;
   - customise opened;
   - trial offered/started;
   - paywall viewed;
   - checkout started;
   - payment succeeded;
   - Premium value delivered.
3. Calculate conversion between meaningful adjacent stages. Do not compare unrelated denominators.
4. Split by acquisition source/campaign where sample size is meaningful.
5. Check early value/retention evidence that already exists: alert deliveries, report usage, return
   activity, or trial/Premium lifecycle events.
6. Mark every conclusion:
   - `CONFIRMED` - directly shown by production evidence;
   - `LIKELY` - plausible but sample/evidence is weak;
   - `UNKNOWN` - not measurable yet.
7. Identify the single largest **verified** bottleneck.
8. Recommend one experiment only. State:
   - exact product change;
   - why this bottleneck matters;
   - success metric;
   - minimum sample/window;
   - stop/keep rule.
9. Do not implement a new growth feature until this audit is complete.

### Expected output

A compact report like:

```text
Cohort/window:
Users:

START -> BRIEF: x / y = z%
BRIEF -> CUSTOMISE: ...
CUSTOMISE -> TRIAL: ...
TRIAL -> PAYWALL: ...
PAYWALL -> CHECKOUT: ...
CHECKOUT -> PAID: ...
PAID/TRIAL -> PREMIUM VALUE: ...

Biggest confirmed loss:
Evidence:
Next experiment:
Success metric:
Stop/keep rule:
Unknowns:
```

## If this work moves to another chat

Copy only this prompt:

> Continue CCWBot growth work. Use current `dev` repository evidence and the approved read-only
> production investigation path. Read `docs/research/growth_strategy_2026-09-01.md` and
> `docs/product_analytics.md`. Execute the **Next task** in the growth strategy: produce the
> production Growth Funnel Audit, identify the single biggest confirmed bottleneck, and recommend
> exactly one measurable experiment. Do not build a new growth feature before the audit. Mark
> conclusions CONFIRMED / LIKELY / UNKNOWN.

## After the audit

Only then:
1. implement the chosen experiment;
2. measure again;
3. keep or revert based on the stated rule;
4. consider a small 20-50 user founder-led acquisition cohort;
5. postpone paid scale and referral mechanics until activation/retention are proven.

Current decision loop:

```text
measure -> find biggest verified loss -> change one thing -> measure again
```
