# CCWBot — Premium + Multi-Coin Alerts Plan (V2)

This revision keeps the original product direction and adds production-hardening items:
- strict idempotency,
- concurrency safety,
- deterministic news relevance pre-filter,
- explicit active-user eligibility rules,
- stable domain contracts between PR1/PR2/PR3.

## Core invariant (must not break)

1 market event per coin -> 1 AI analysis -> many deliveries.

LLM calls are forbidden inside recipient loops.

---

## Final product model

### Free
- Manual `/price` for all supported coins.
- Automatic alerts: BTC-only.
- BTC enabled by default, user can disable it.
- Frequency fixed at 4h (14400s), not editable.
- Non-BTC shown as locked with `/subscribe` hint.

### Premium
- Unlock automatic non-BTC alerts.
- User chooses any subset of premium coins.
- Frequency presets: 1h / 6h / 24h.
- No auto-enable of non-BTC after payment.

### Premium expired
- BTC remains free and uses free policy.
- Non-BTC stays saved in DB but appears locked and is not delivered.
- After renewal, saved non-BTC choices become effective again.

---

## Supported coins and mapping

Symbols:
`btc, eth, sol, xrp, bnb, doge, ada, ton, link, trx`

USDT removed from supported `/price` and watchlist/premium flows.

CoinGecko IDs:
- btc -> bitcoin
- eth -> ethereum
- sol -> solana
- xrp -> ripple
- bnb -> binancecoin
- doge -> dogecoin
- ada -> cardano
- ton -> toncoin
- link -> chainlink
- trx -> tron

---

## Operational model

### Global market check
- Technical interval: 60s test / 300s production.
- Interval stays global admin-controlled.
- Use one batch CoinGecko request per cycle for currently needed symbols.

### Symbols-to-check eligibility (explicit)
Define eligible watchers using a single repository query:
- BTC: include only if >=1 active eligible user has BTC enabled.
- Non-BTC: include only if >=1 active premium user has coin enabled and premium active.

"Active user" must be explicitly defined in code (e.g., not deactivated/blocked + present in users table).

### Trigger threshold
- One global threshold for all symbols (admin-only).
- No per-user/per-coin threshold in this phase.

### Delivery frequency
- Market polling is global.
- Delivery gate is per-user+symbol via min time window.
- Use last sent alert (`alerts.status='sent'`) to enforce window.

---

## Reliability and data-integrity requirements (new, mandatory)

### Idempotency keys and unique constraints
- Market event identity key (symbol + normalized trigger window/signature).
- Delivery identity key (`user_id + symbol + market_event_id`).
- Payment identity key (`provider + provider_payment_id`).

### Concurrency safety
- Event->analysis->delivery flow must be retry-safe.
- Duplicate updates must not create duplicate premium activations.
- Use transactional upsert/ON CONFLICT patterns.

### Renewal logic
- Premium extension uses `max(now, active_until) + period`.
- Keep audit trail for manual grant/revoke and provider renewals.

---

## News and AI relevance safeguards (new)

### Deterministic pre-filter before LLM
Classify news into:
1. direct symbol relevance,
2. market-wide relevance,
3. irrelevant.

LLM receives only direct + limited market-wide items.
If none exist: pass explicit "no relevant news" marker.

### Symbol-aware AI payload
Input must include symbol, coin name, price delta, trend context, threshold, check interval, and filtered news.

---

## Commands and UX

Add:
- `/watchlist`
- `/myplan`
- `/subscribe`

Admin-only test commands:
- `/grantpremium <telegram_user_id> <days>`
- `/revokepremium <telegram_user_id>`

Admin commands must remain hidden from normal user menu.

---

## DB-first model

### Config (or table-backed later)
`SUPPORTED_COINS` with `free` flag and human-readable names.

### `user_coin_subscriptions`
- `id, user_id, symbol, is_enabled, created_at, updated_at`
- unique `(user_id, symbol)`
- defaults: BTC enabled, non-BTC disabled

### User frequency preference
- `alert_frequency_seconds`
- Free fixed effective 14400
- Premium allowed 3600/21600/86400

### `user_premium_subscriptions` (or `user_plans`)
Recommended fields:
- `id, user_id, plan, status, active_until, started_at, cancelled_at`
- `provider, provider_subscription_id, last_payment_id`
- `created_at, updated_at`

Access is determined by `active_until > now` first.

### `payments`
- `id, user_id, provider, provider_payment_id, amount, currency, payload, status, created_at`
- optional `raw_event_json`
- unique idempotency on provider payment id

---

## Domain contracts to establish in PR1 (to avoid PR2 refactors)

Create reusable rule helpers used by handlers and delivery pipeline:
- `is_coin_unlocked_for_user(user, symbol, now)`
- `get_effective_frequency_seconds(user, now)`
- `can_deliver_now(user, symbol, now, last_sent_at)`
- `resolve_symbols_to_check(now)`

---

## PR breakdown (updated)

### PR1 — Premium-aware watchlist foundation
Scope:
- top-10 coin config and `/price` update (remove USDT)
- schema: coin subscriptions, premium plan, frequency
- `/watchlist`, `/myplan`
- admin grant/revoke
- locked-state UX for free/expired
- define and test domain contracts (eligibility/frequency)

Tests:
- defaults, free locks, premium unlock, expiry lock with saved state
- admin grant/revoke
- `/price` top-10 only
- effective frequency policy

### PR2 — Multi-coin global monitoring and delivery
Scope:
- batch CoinGecko fetch for needed symbols only
- explicit `resolve_symbols_to_check`
- per-symbol event detection
- one analysis per symbol event
- symbol-aware messaging + news pre-filter
- recipient resolution with premium and frequency gates
- no LLM in recipient loop
- idempotent deliveries

Tests:
- symbols-to-check correctness
- free BTC-only, premium non-BTC enabled
- expired premium blocked
- frequency gate
- one analysis reused across recipients
- no duplicate delivery on retries

### PR3 — Telegram Stars recurring premium
Scope:
- `/subscribe`, config price (`PREMIUM_MONTHLY_STARS=199`)
- pre-checkout + successful_payment handlers
- recurring period handling (if PTB supports cleanly)
- robust idempotency and renew logic
- payments + subscription persistence
- docs on support limits/workarounds

Tests:
- invoice payload creation
- successful payment activates/extends premium
- duplicate payment update idempotent
- expiry transitions
- `/myplan` and `/watchlist` reflect plan state

---

## Definition of done

- Core invariant preserved: 1 event = 1 analysis = many deliveries.
- No LLM calls inside recipient loop.
- Idempotency and retry-safety covered by schema + tests.
- Premium expiry behavior matches UX spec.
- Telegram Stars handling implemented safely, with documented limitations if SDK gaps exist.
