# Product analytics

This is an operator reference for reconstructing the CCWBot growth funnel. Product events link to
the internal `users.id`; they do not store Telegram identities, raw deep-link payloads, invoice
payloads, or arbitrary event dictionaries.

## Attribution payload

Telegram start links use `a1_<opaque-link-code>`. The opaque code resolves server-side to an
operator-managed, active acquisition-link record containing the allowlisted source, campaign,
creative, and optional referrer code. Invalid, inactive, and expired links are ignored. The first
valid attribution is immutable.

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
`premium_value_delivered`. Later P0 phases emit the events that their flows introduce.
