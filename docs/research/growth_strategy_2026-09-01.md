# CCWBot Growth Strategy: 0 → 1 Premium

**Дата анализа:** 1 сентября 2026  
**Проверенная версия продукта:** dev, commit 797a56a  
**Главная цель:** рост числа пользователей, которые покупают и продолжают оплачивать Premium.

> Status: dated growth research / strategy snapshot. This file is not a canonical source of product or workflow rules. Current behavior and guardrails are owned by docs/project_context.md and docs/codex_instructions.md.

## 1. Executive diagnosis

CCWBot пока не проблема acquisition. Главный bottleneck — продукт не превращает нового пользователя в человека, который понял ценность, сформировал привычку и увидел естественную причину платить.

Техническое ядро уже сильнее, чем текущая упаковка:

- бот автоматически анализирует значимые рыночные события;
- объединяет цену, движение, новости и AI-интерпретацию;
- защищается от повторов и информационного шума;
- создаёт один анализ события и доставляет его многим пользователям;
- формирует market heartbeat, daily report и weekly report;
- принимает recurring-платежи Telegram Stars.

Но новый пользователь этого почти не видит. /start показывает список команд, не спрашивает, какие монеты важны, не даёт моментальную демонстрацию ценности и не ведёт к настройке. Free-пользователь в фактическом /watchlist видит только BTC; заблокированные Premium-монеты скрыты. Поэтому ограничения Premium почти невозможно почувствовать. Paywall открывается в основном только если пользователь сам зайдёт в /plan и нажмёт Subscribe.

Дополнительная проблема: после покупки Premium выбранные non-BTC монеты не включаются автоматически. Пользователь должен отдельно открыть /watchlist. При этом сохранённая Free-частота 4 часа становится Premium-default 6 часов, если пользователь сам не переключит её на 1 час. Первая минута после оплаты может выглядеть не как upgrade, а как отсутствие изменений.

Главный вывод: до масштабирования трафика надо построить цепочку:

релевантный deep link → выбор монет → моментальный персональный brief → первая полезная доставка → попытка отслеживать несколько монет → trial/paywall → немедленная Premium-ценность → регулярный персональный digest → referral/share.

Пока этой цепочки нет, платное привлечение будет покупать /start, а не Premium.

## 2. Что подтверждено, а что является гипотезой

### Подтверждённые факты из продукта

1. /start содержит короткое описание и команды /price, /watchlist, /reports, /plan; inline onboarding отсутствует.
2. Поддерживаются BTC, ETH, GRAM и SOL. BTC automatic alerts бесплатны; non-BTC требуют Premium.
3. Free heartbeat frequency — 4 часа. Premium может выбрать 1, 6 или 24 часа; default Premium — 6 часов.
4. Event Alert analysis работает глобально каждые 30 минут по монете. Heartbeat frequency управляет регулярными heartbeat-сообщениями, а не скоростью обнаружения Event Alerts.
5. Daily и weekly reports доступны бесплатно и создаются один раз для всех пользователей.
6. Premium стоит 199 Stars в месяц. После оплаты пользователь должен вручную выбрать монеты в /watchlist.
7. Бот хранит пользователей, watchlist, Premium entitlement, платежи, доставки, reports и LLM usage.
8. Отдельных product/growth events для onboarding, campaign attribution, paywall impression, checkout start, referral и activation нет.
9. Referral-механики и group growth loop нет. Пользовательский профиль сохраняется только для private chat.
10. Пользовательские сообщения только на английском.

### Непроверенные данные

- Фактические production-конверсии и retention не анализировались.
- Реализованная цена 199 Stars известна, но фактическая чистая выручка после Telegram/Fragment не определена.
- Нет данных, какие из BTC, ETH, SOL и GRAM чаще всего интересуют реальных пользователей.

### Growth-гипотезы

- Лучший первый ICP — Telegram-native владелец 2–4 крупных монет, который хочет быть в курсе, но не хочет постоянно смотреть графики.
- Главный wedge — не «больше алертов», а «меньше шума + объяснение события прямо в Telegram».
- Самый сильный Premium trigger — выбор второй/третьей монеты после демонстрации полезного brief.
- Trial будет работать лучше немедленного жёсткого paywall, потому что значимые Event Alerts нерегулярны и пользователь может не увидеть ценность в первый день.

## 3. Product audit и текущий user journey

### Текущий путь

1. Пользователь открывает бота и нажимает Start.
2. Видит название, общее описание и четыре slash-команды.
3. Должен самостоятельно решить, куда идти.
4. /price позволяет вручную проверить одну из четырёх монет.
5. /reports открывает бесплатные daily/weekly reports.
6. /watchlist у Free-пользователя фактически показывает только BTC и частоту 4 часа.
7. /plan открывает My plan и Subscribe.
8. /subscribe показывает invoice на 199 Stars.
9. После платежа бот сообщает: «Use /watchlist to choose your coins».
10. Пользователь вручную включает ETH/GRAM/SOL и при желании меняет частоту с 6h на 1h.

### Где теряется Premium

- /start — справка, а не onboarding.
- Нет выбора интересующих монет.
- Нет instant preview.
- Premium-монеты скрыты в Free-watchlist.
- Paywall не связан с естественным пользовательским действием.
- Reports полностью бесплатны и одинаковы для всех.
- После оплаты нужна повторная настройка.
- Premium default = 6h против Free = 4h.
- Нет trial.
- Нет attribution и product events.
- Нет referral/share CTA.

### Функции с наибольшим perceived value

1. Event Alert с объяснением: что изменилось, рыночный контекст, связанная новость, что наблюдать дальше.
2. Noise reduction: semantic cooldown и significance filtering уменьшают повторы.
3. Multi-coin monitoring.
4. Market Heartbeat.
5. Daily/weekly report.

## 4. Job To Be Done

Самый сильный JTBD:

«Пока я занимаюсь своей жизнью, наблюдай за моими основными криптоактивами и сообщай в Telegram только о действительно важных изменениях — сразу с понятным контекстом».

Другие сильные задачи:

- быстро объяснить, почему рынок двинулся;
- контролировать 2–4 актива без постоянного просмотра графиков;
- снизить шум и не получать повторяющиеся алерты;
- получать понятный daily/weekly итог.

## 5. Первый ICP

Beachhead #1:

English-speaking Telegram users who hold BTC plus ETH and/or SOL, check prices several times per day, but do not use advanced professional tooling.

Почему:

- владеют несколькими поддерживаемыми монетами;
- естественно чувствуют ограничение Free;
- Telegram уже является привычным notification layer;
- им важнее объяснение и спокойствие, чем RSI, webhooks и сотни индикаторов;
- multi-coin monitoring создаёт постоянную причину платить.

Beachhead #2 после group MVP:

Админы Telegram crypto communities 5k–100k участников.

Не брать первым:

- memecoin traders;
- advanced traders;
- BTC-only holders как основной платящий сегмент.

## 6. Рыночный wedge и positioning

CCWBot не должен конкурировать количеством монет, charts, custom alerts или on-chain данными.

Потенциальный wedge:

Calm, explanation-first crypto monitoring inside Telegram. No charts to watch, no thresholds to configure, no exchange connection.

Короткий value proposition:

Stop watching charts. CCWBot watches your coins and explains meaningful moves in Telegram.

Чего нельзя обещать:

- guaranteed profit;
- AI prediction accuracy;
- «buy/sell before everyone»;
- «never miss a move» без оговорки о provider availability;
- персональные инвестиционные рекомендации.

## 7. Free → Premium: рекомендуемая модель

Один план: Free + Premium.

### Free

- BTC Event Alerts;
- BTC heartbeat раз в 4 часа;
- manual price для четырёх монет;
- общий daily report;
- возможность выбрать интерес к ETH/SOL/GRAM и увидеть, что они входят в Premium;
- один instant personalized preview во время onboarding.

### 7-day Premium trial, запускаемый при выборе второй монеты

- все выбранные монеты сразу активируются;
- heartbeat default 1 час;
- персональный daily digest только по выбранным монетам;
- фиксируются delivered value events;
- trial не требует Stars до окончания.

### Premium 199 Stars/month

- до четырёх активных монет;
- 1h heartbeat по умолчанию;
- Event Alerts по всем выбранным монетам;
- персональный daily digest и weekly recap;
- сохранение watchlist и delivery history;
- share/referral rewards.

Trial лучше запускать не на первом /start, а когда пользователь выбирает вторую Premium-монету.

### После оплаты

- автоматически включить trial/watchlist choices;
- установить 1h frequency;
- показать активные монеты и дату доступа;
- дать кнопки View my watchlist, Get today’s brief, Invite a friend;
- не заставлять пользователя вводить /watchlist вручную.

## 8. Growth funnel

Рекомендуемые этапы:

1. Impression.
2. Bot Start.
3. Activation.
4. Habit.
5. Paywall exposure.
6. Purchase.
7. Premium retention.
8. Referral.

Рекомендуемое activation event:

watchlist_intent_completed = пользователь выбрал не менее двух монет и открыл первый персональный market brief в течение 10 минут после /start.

Рекомендуемый aha moment:

Пользователь получает alert по своей монете и за 20–30 секунд понимает: что изменилось, почему это важно и что наблюдать дальше — без открытия exchange, chart и news feed.

### Минимальная event taxonomy

- bot_started: is_new, source, campaign, creative, referrer_code;
- onboarding_started;
- coin_interest_selected: symbol, selected_count;
- onboarding_completed;
- instant_brief_viewed;
- trial_offered;
- trial_started;
- trial_expired;
- watchlist_updated;
- paywall_viewed: trigger, variant, current_selected_count;
- checkout_started;
- payment_succeeded: plan, price_stars, first/recurring;
- report_viewed: daily/weekly/personal;
- share_clicked: object_type, campaign;
- referral_joined;
- referral_activated;
- referral_paid;
- premium_expired;
- bot_blocked.

Deliveries уже можно связывать через текущие alerts и alert_delivery_outcomes; не нужно дублировать каждый backend decision в growth table.

## 9. Acquisition strategy

До исправления onboarding и instrumentation acquisition ограничить founder-led и маленькими тестами.

Главная цель первых 30 дней — не максимальный reach, а доказательство цепочки:

qualified start → activation → first payment → month-2 intent.

Приоритетные бесплатные и low-cost каналы:

- Telegram micro-communities;
- public CCWBot Market Pulse channel;
- creator affiliate;
- Reddit problem-led posts;
- X event commentary;
- coin-specific partnerships;
- direct user interviews.

Не делать Reddit/X paid главным каналом на стадии 0 → 1.

Paid Telegram Ads имеет смысл только после доказанной воронки и retention.

## 10. CAC rule

Не переводить 199 Stars в условные доллары по retail-цене Stars. Использовать фактическую чистую сумму, которую владелец получает после withdrawal.

Определения:

Net monthly revenue = реально полученная сумма с 199 Stars после платформенных потерь.

Gross margin contribution = net revenue − переменные LLM/data/delivery costs.

Observed LTV = monthly contribution × среднее число оплаченных месяцев.

Пока retention неизвестен:

- hard CAC ceiling: не больше contribution первых 90 дней;
- рабочая цель: CAC ≤ 30–40% осторожно рассчитанного LTV;
- scale condition: payback ≤3 месяца и M2 retention ≥60%;
- kill condition: после 30 paywall exposures нет покупок либо CAC projection >150% 90-day contribution.

## 11. Product-led growth opportunities

### P0

1. Inline onboarding: выбрать монеты, цель и частоту; закончить instant brief.
2. Показать locked coins: ETH/GRAM/SOL должны быть видимы Free-пользователю.
3. Intent-triggered trial: выбор второй монеты запускает 7 дней Premium.
4. 1h Premium default.
5. Post-payment auto-activation.
6. Growth events + attribution.

### P1

7. Personal daily digest: фильтровать уже созданный cached global report по watchlist; не делать LLM call per user.
8. Value recap: weekly и trial-end summary по фактическим доставкам.
9. Shareable report/alert card: deterministic rendering из validated backend data.
10. Deep-linked coin onboarding.
11. Referral rewards.

### P2

12. Group mode.
13. Creator watchlist/templates.
14. Mini App при необходимости.
15. Больше монет только после данных о потерянном demand; сначала добавить unsupported_coin_requested.

## 12. Viral loop hypotheses

Приоритетные механики:

- dual-sided referral Premium days;
- temporary second-coin unlock for qualified referral;
- shareable Event Alert card with tracked deep link;
- Daily Market Pulse card for forwarding;
- weekly watchlist recap card;
- coin deep link that preselects a coin;
- group bot with private Premium conversion;
- creator affiliate;
- gift Premium.

Не использовать public referral leaderboard на старте из-за spam/fake-account incentives.

## 13. Превратить продукт в content + distribution engine

Что уже можно переиспользовать:

- validated Event Alert;
- source-backed news links;
- market heartbeat;
- cached daily report;
- cached weekly report;
- deterministic price/change fields;
- semantic family и urgency.

Сохранить invariant:

1 coin market event = 1 AI analysis = many deliveries.

Public content должен быть ещё одним delivery target, а не новым LLM call.

Рекомендуемый flow:

Validated market event/report
→ deterministic content templates
→ approval queue during first 30 days
→ Telegram channel post
→ X post draft
→ Reddit draft
→ shareable PNG card
→ tracked bot deep link.

Safety:

- exact market data берётся из backend;
- Not financial advice остаётся;
- никаких price targets или guaranteed outcomes;
- первые 30 дней — human approval;
- не публиковать одинаковый контент во все communities;
- не превращать автоматизацию в reply spam.

## 14. Топ growth experiments

Приоритет по dependency:

1. Product events + deep-link attribution.
2. New /start: coin selection + instant brief.
3. Locked multi-coin UX + trial on second coin.
4. Post-payment auto-enable + 1h default.
5. Personal daily digest from cached report.
6. Public Telegram Market Pulse channel.
7. Micro-channel affiliate pilots.
8. Shareable Event/Daily cards.
9. Dual-sided referral rewards.
10. Paywall value-message test at 199 Stars.

Experiment 1 должен быть первым, затем 2–4, потом acquisition.

## 15. Execution plan

### Первые 48 часов

- Зафиксировать event taxonomy и funnel SQL.
- Сделать UX spec нового /start.
- Составить список 20 target users и 30 каналов.
- Подготовить 3 creatives.

### Первая неделя

- Ship analytics + deep links.
- Ship onboarding + instant cached brief.
- Показать locked coins.
- Исправить Premium first minute.
- Провести 10 interviews.

### Первые 30 дней

- Intent-triggered 7-day trial.
- Personal digest from cache.
- Market Pulse channel.
- 10 community/creator pilots.
- Value-message paywall test.
- Shareable cards MVP.

### 30–90 дней

- Масштабировать только каналы с доказанным activated CAC, paid conversion и D30 retention.
- Запустить dual-sided referral после fraud rules.
- Добавить group daily pulse MVP и private-chat conversion path.
- Построить creator dashboard/report вручную или через простую admin view.
- Тестировать second language только отдельной cohort.
- Собирать unsupported_coin_requested.
- Проверить 199 vs 299 Stars после ≥20 paid и измеримого M2.

90-day gates:

- ≥20 organic/partner paid users;
- M2 Premium retention ≥60%;
- paywall→paid ≥10%;
- ≥35% activated users имеют D7 habit;
- хотя бы один channel с payback projection ≤3 months;
- referred users не хуже direct users по activation/retention.

## 16. DO THIS NOW

### 1. Instrumentation и attribution

Почему: сейчас невозможно доказать, где теряются пользователи и какой канал приводит Premium.

Техническое направление:

- Alembic migration для product events;
- ProductEvent и при необходимости UserAcquisition;
- allowlisted events/properties;
- сохранять /start payload source/campaign/creative/referrer;
- записывать paywall view, checkout start и payment success;
- не хранить raw Telegram ID в event properties; использовать internal user_id FK;
- добавить funnel/cohort SQL и regression tests.

Acceptance criteria:

по одному тестовому пользователю восстанавливается путь source → start → activation → paywall → checkout → paid; duplicate payment не создаёт вторую purchase conversion.

### 2. Новый /start с instant aha

Предлагаемый flow:

Start
→ Which coins do you want me to watch?
→ BTC / ETH / SOL / GRAM multi-select
→ What do you want?: Important moves / Calm updates / Daily brief
→ Show current personalized brief from cached market/report data
→ Confirm Free or start trial when ≥2 coins selected.

Guardrail:

instant brief должен переиспользовать cache и не создавать LLM call per user.

Acceptance criteria:

новый пользователь выбирает ≥2 coins и получает персональный brief ≤60 секунд и ≤5 taps; все steps записаны в analytics.

### 3. Исправить Premium activation до покупки traffic

Изменения:

- показывать ETH/GRAM/SOL как locked в фактическом Free /watchlist;
- запускать 7-day trial при подтверждённом выборе второй монеты;
- после payment success автоматически включать выбранные coins;
- Premium default frequency сделать 1h, не 6h;
- после оплаты показывать активную watchlist и кнопку получить сегодняшний brief;
- записывать trial_started, paywall_viewed, checkout_started, payment_succeeded, premium_value_delivered.

Acceptance criteria:

payment success в том же interaction показывает работающий Premium; выбранные coins активны; первый Premium heartbeat/digest не требует дополнительной команды; повторный payment остаётся idempotent.

## Итоговое решение

Не покупать массовый traffic сейчас.

Первые деньги и разработка должны идти в измеримый onboarding, instant value и Premium activation. После этого получить 20–50 qualified users через founder-led Telegram partnerships и проверить, покупают ли они обещание:

CCWBot watches your coins, filters noise and explains meaningful moves in Telegram.

Если эта cohort активируется, платит и продлевает Premium — масштабировать Telegram content, creators и group distribution. Если нет — менять product/value proposition на основе event data и интервью, а не увеличивать рекламный бюджет.
