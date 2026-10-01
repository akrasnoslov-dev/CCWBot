# Product analytics

This is an operator reference for reconstructing the CCWBot growth funnel. Product events link to
the internal `users.id`; they do not store Telegram identities, raw deep-link payloads, invoice
payloads, or arbitrary event dictionaries.

## Attribution payload

Telegram start links use `a1_<opaque-link-code>`. The opaque code resolves server-side to an
operator-managed, active acquisition-link record containing the allowlisted source, campaign,
creative, and optional referrer code. Invalid, inactive, and expired links are ignored. The first
valid attribution is immutable.

## Create and inspect acquisition links

Use the following commands only from a private chat as a configured bot admin. The bot must have
PostgreSQL enabled and `TELEGRAM_BOT_USERNAME` must be its public production username (without
`@`). Production must set `TELEGRAM_BOT_USERNAME=YFCCWbot`. The commands are intentionally not
included in Telegram command menus.

Create a link with named, lowercase code values. The allowed sources are `reddit`, `telegramdir`,
`telegramads`, and `product-hunt`; optional `campaign`, `creative`, and `referrer_code` values
must be lowercase letters, digits, and hyphens, start with a letter, and be at most 32 characters.

```text
/acquisitionlink source=reddit campaign=cryptotelegrambots
/acquisitionlink source=reddit campaign=telegrambots
/acquisitionlink source=reddit campaign=cryptomarkets
/acquisitionlink source=telegramdir
/acquisitionlink source=product-hunt
/acquisitionlink source=telegramads campaign=general-crypto creative=ad01
```

The bot creates a new opaque code and replies with a shareable URL such as:

```text
https://t.me/<production_bot_username>?start=a1_<opaque-code>
```

To add optional metadata, include it as named fields:

```text
/acquisitionlink source=reddit campaign=cryptotelegrambots creative=launch-post referrer_code=mod-a
```

Use `telegramads` acquisition links only on distribution surfaces that preserve their full
`?start=a1_<code>` parameter. They are not usable for direct Telegram Ads; see the measurement
section below.

Run `/acquisitionlinks` to list up to 100 currently attributable links with source, campaign,
creative, and their generated Telegram URLs. It does not display referrer codes or user data.

## Funnel query

Run this only through the approved read-only investigation workflow:

```sql
SELECT
  COALESCE(a.source, 'unattributed') AS source,
  COALESCE(a.campaign, 'unattributed') AS campaign,
  COUNT(DISTINCT e.user_id) FILTER (WHERE e.event_name = 'bot_started') AS started,
  COUNT(DISTINCT e.user_id) FILTER (WHERE e.event_name = 'onboarding_completed') AS onboarded,
  COUNT(DISTINCT e.user_id) FILTER (WHERE e.event_name = 'trial_started') AS trials_started,
  COUNT(DISTINCT e.user_id) FILTER (WHERE e.event_name = 'checkout_started') AS checkouts,
  COUNT(DISTINCT e.user_id) FILTER (WHERE e.event_name = 'payment_succeeded') AS paid
FROM product_events AS e
LEFT JOIN user_acquisition_attributions AS a ON a.user_id = e.user_id
GROUP BY 1, 2
ORDER BY started DESC, source, campaign;
```

## Direct Telegram Ads measurement

Direct Telegram Ads for the bot currently accepts `t.me/YFCCWbot`; its UI rejects the
`?start=a1_<code>` parameter. These users therefore do not receive `source=telegramads`,
`campaign`, or `creative` attribution in CCWBot. Continue using acquisition links for channels
that preserve the parameter, but do not use an attribution query to measure direct Telegram Ads.

For direct Telegram Ads, this is an **observed new-user cohort during the Telegram Ads window**,
not an exactly attributed cohort: organic users created during the same window can be included.
Run the query only through the approved read-only investigation workflow. It uses half-open UTC
boundaries and counts downstream events only after the user's cohort entry and before the
experiment end. Trial, checkout, and payment columns are explicitly within-experiment-window
measures; they are not mature conversion rates for users who enter close to the end.

```sql
WITH cohort AS (
  SELECT users.id AS user_id, users.created_at
  FROM users
  WHERE users.created_at >= :experiment_start
    AND users.created_at < :experiment_end
), cohort_events AS (
  SELECT c.user_id, e.event_name
  FROM cohort AS c
  LEFT JOIN product_events AS e
    ON e.user_id = c.user_id
   AND e.occurred_at >= c.created_at
   AND e.occurred_at < :experiment_end
)
SELECT
  COUNT(DISTINCT user_id) AS new_users,
  COUNT(DISTINCT user_id) FILTER (
    WHERE event_name = 'onboarding_completed'
  ) AS onboarding_completed,
  COUNT(DISTINCT user_id) FILTER (
    WHERE event_name = 'instant_brief_viewed'
  ) AS instant_brief_viewed,
  COUNT(DISTINCT user_id) FILTER (
    WHERE event_name = 'onboarding_customize_opened'
  ) AS onboarding_customize_opened,
  COUNT(DISTINCT user_id) FILTER (
    WHERE event_name = 'coin_interest_selected'
  ) AS coin_interest_selected,
  COUNT(DISTINCT user_id) FILTER (
    WHERE event_name = 'trial_offered'
  ) AS trial_offered,
  COUNT(DISTINCT user_id) FILTER (
    WHERE event_name = 'trial_started'
  ) AS trial_started_within_window,
  COUNT(DISTINCT user_id) FILTER (
    WHERE event_name = 'checkout_started'
  ) AS checkout_started_within_window,
  COUNT(DISTINCT user_id) FILTER (
    WHERE event_name = 'payment_succeeded'
  ) AS payment_succeeded_within_window
FROM cohort_events;
```

For mature trial or payment conversion, keep the same `users.created_at` cohort but replace the
experiment-end event bound with a fixed, predeclared follow-up horizon after each user's
`created_at`; do not present an experiment-end-truncated result as mature conversion.

## Onboarding value-delivery semantics

For a new private-chat user, `/start` records `onboarding_started` before attempting Telegram
delivery of the deterministic cached BTC brief. `onboarding_completed` and
`instant_brief_viewed` are recorded only after that brief has been delivered successfully; they
therefore represent first value delivery rather than merely rendering an onboarding screen.
Optional coin selection follows through the `Add ETH, SOL & GRAM →` action.
`onboarding_customize_opened` records that activation click once per onboarding version, before
the selector is rendered. Premium intent, trial, and paywall events retain their existing meanings.

The old 25.0% (2 of 8) baseline represented active progression to the brief: a user pressed the
old flow's confirmation CTA. In v2, `/start` automatically delivers the brief, so
`onboarding_completed / new_users` now measures successful first-value delivery rather than the
same engagement conversion. Do not compare those two percentages as one conversion metric.

Judge the experiment's meaningful engagement with downstream events: unique users with
`onboarding_customize_opened`, `coin_interest_selected`, `trial_offered`, `trial_started`,
`checkout_started`, and `payment_succeeded`, each divided by `new_users` from the observed
window cohort. The direct-Ads query above reports those counts; calculate and compare rates using
the same UTC window definition.

The allowed event names are `bot_started`, `onboarding_started`,
`onboarding_customize_opened`, `coin_interest_selected`, `onboarding_completed`,
`instant_brief_viewed`, `watchlist_updated`, `trial_offered`,
`trial_started`, `trial_expired`, `paywall_viewed`, `checkout_started`, `payment_succeeded`, and
`premium_value_delivered`. Trial start and expiry are idempotent lifecycle events keyed to the
internal user and trial row; payment conversion remains keyed to the internal payment row.
