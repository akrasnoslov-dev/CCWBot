# CCWBot Growth Strategy: current execution

**Original research date:** 1 September 2026  
**Current review:** 5 October 2026  
**Verified development state:** `dev`, commit `14b091289d14d8e050ee4cda584b2333313dfb23`

> Status: growth research / strategy. This is not a canonical product or workflow contract.
> Current behavior is owned by `docs/project_context.md`, `docs/product_analytics.md`, and the
> runtime code.

## What changed since the original research

The original report correctly identified the biggest early problem: CCWBot had useful backend
behavior but weak first-run activation and almost no measurable funnel.

Most of that P0 work is now implemented:

- New private-chat users get an immediate deterministic cached BTC brief from `/start`.
- The first brief has an explicit `Add ETH, SOL & GRAM →` action.
- BTC remains the free default.
- Premium coin intent is saved before payment.
- An eligible user who selects Premium coins can start a free 7-day Premium trial.
- Trial, paywall, checkout, payment, and Premium-value events are recorded.
- Successful payment activates Premium and shows the user's current monitoring/watchlist state.
- First-touch acquisition attribution exists through opaque `a1_<code>` Telegram start links.
- Admins can create and inspect acquisition links.
- Direct Telegram Ads cannot preserve the deep-link parameter, so those experiments must be
  measured as time-bounded observed new-user cohorts.
- The funnel now records first-value delivery and the click from the BTC brief into coin
  customization.

So the old recommendation "build measurable onboarding before buying traffic" is largely complete.

## What should be done now

### 1. Stop adding growth features until the current funnel has real users

The next bottleneck is evidence, not another onboarding feature.

Run a small controlled acquisition test with roughly **20-50 qualified users**. Prefer sources that
can preserve an acquisition link, for example founder-led Telegram community partnerships or
carefully placed community posts.

For direct Telegram Ads, define the UTC experiment window before launch and use the cohort query in
`docs/product_analytics.md`.

### 2. Measure the existing funnel

For each source/cohort, measure unique users through:

```text
start
-> instant BTC brief delivered
-> Add ETH/SOL/GRAM opened
-> Premium coin selected
-> trial offered
-> trial started
-> checkout started
-> payment succeeded
-> premium value delivered
```

Do not optimize `/start` delivery rate alone. The useful question is where qualified users stop
after receiving the first value.

### 3. Fix only the biggest observed drop-off

After the first cohort, choose the largest meaningful drop and run one change at a time.

Examples:

- many briefs, few customization opens -> improve the post-brief CTA/value proposition;
- many Premium selections, few trial starts -> simplify/clarify trial activation;
- many trials, few checkouts -> improve trial-end/value recap before touching price;
- many checkouts, few payments -> inspect payment UX/reliability;
- paid users but weak continued use -> improve delivered Premium value before acquiring more users.

### 4. Only then build the next growth layer

The original P1/P2 ideas are still mostly unimplemented:

- trial-end / weekly value recap based on actual delivered value;
- explicit share CTA;
- referral reward loop;
- group/community growth loop.

Do not build referral rewards first. They amplify whatever conversion/retention already exists. First
prove that the current trial -> paid -> continued-value path works.

## Current recommended sequence

```text
1. Get 20-50 qualified users
2. Measure the funnel
3. Find the largest real drop-off
4. Fix that one step
5. Repeat once
6. Only after healthy activation/retention: referral/share experiments
```

## Current product thesis

The strongest positioning remains:

> Stop watching charts. CCWBot watches your coins and explains meaningful moves in Telegram.

The intended user is still a Telegram-native holder of a few major coins who wants less noise and
does not want to configure trading-style thresholds.

The product should continue competing on calm explanation and useful monitoring, not on the number
of indicators, charts, or supported speculative assets.

## Decision for now

**Do not start another broad growth-feature build.** The product now has enough instrumentation and
activation mechanics to test the original thesis. The next concrete action is a small, attributable
user-acquisition experiment followed by funnel analysis.
