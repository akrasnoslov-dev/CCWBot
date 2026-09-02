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

Telegram Ads examples:

```text
/acquisitionlink source=telegramads campaign=general-crypto creative=ad01
/acquisitionlink source=telegramads campaign=btc-eth creative=ad01
/acquisitionlink source=telegramads campaign=solana creative=ad01
```

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

The allowed event names are `bot_started`, `onboarding_started`, `coin_interest_selected`,
`onboarding_completed`, `instant_brief_viewed`, `watchlist_updated`, `trial_offered`,
`trial_started`, `trial_expired`, `paywall_viewed`, `checkout_started`, `payment_succeeded`, and
`premium_value_delivered`. Trial start and expiry are idempotent lifecycle events keyed to the
internal user and trial row; payment conversion remains keyed to the internal payment row.
