# CCWBot Growth Strategy: 0 -> 1 Premium

**Original research:** 2026-09-01  
**Status refresh:** 2026-10-05  
**Basis:** current `dev` implementation.

This is research/strategy, not a canonical product contract.

## Original thesis

The main problem was activation, not traffic. A new user needed to understand the value, choose
relevant coins, see useful output quickly, and reach Premium naturally before acquisition was
scaled.

The positioning still makes sense:

> Stop watching charts. CCWBot watches your coins and explains meaningful moves in Telegram.

## What is implemented now

The original P0 foundation is largely done:

- product-event analytics;
- first-touch acquisition attribution;
- operator-created tracked acquisition links;
- onboarding flow instead of command-only first use;
- deterministic/cached instant brief;
- Premium coin customisation;
- one-time 7-day Premium trial flow;
- trial lifecycle events;
- paywall, checkout, and payment events;
- `premium_value_delivered` tracking;
- successful-payment enrichment of Premium/watchlist state;
- regression tests around onboarding, attribution, trials, and payments.

So the old September instruction to first build instrumentation, onboarding, and trial is outdated.

## What is still not proven

The repository does not prove:

- real production funnel conversion;
- D7/D30 habit and Premium retention;
- which acquisition source produces activated or paid users;
- whether 199 Stars converts well;
- whether trial users receive enough useful value before expiry;
- a working referral/share growth loop;
- which supported coins drive real demand;
- scalable CAC/payback.

Referral mechanics remain a hypothesis, not a current capability.

## Do this now

### 1. Measure the existing funnel

Use current attribution and product events to measure:

1. attributed start -> onboarding;
2. onboarding -> instant brief;
3. instant brief -> customise;
4. customise -> trial;
5. trial -> paywall / checkout;
6. checkout -> payment;
7. trial/payment -> first Premium value;
8. early return and useful delivery behavior.

Do not add new analytics events until a concrete measurement gap is found.

### 2. Bring a small qualified cohort

Bring roughly 20-50 targeted users through tracked founder-led Telegram/community outreach.

For each source compare:
- starts;
- activation;
- trial starts;
- paid conversion;
- early retention/value delivery.

Goal is learning, not reach.

### 3. Fix the biggest measured drop

Choose the next product change only after the first cohort gives real funnel data.

Possible experiments, only if data supports them:
- onboarding copy or CTA;
- trial timing;
- Premium value message;
- post-payment UX;
- personal digest/value recap.

### 4. Delay scale and referrals

Do not spend meaningful paid-acquisition budget or build a referral system before activation and
retention are measurable. Referral without retention only multiplies churn.

## Decision rule

Next growth development should follow:

```text
collect -> compare cohorts -> find biggest verified loss -> change one thing -> measure again
```

The September document remains useful as hypothesis history, but it is no longer an implementation
checklist.
