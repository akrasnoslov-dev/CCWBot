"""First-time Telegram onboarding and deterministic cached market brief."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from telegram import InlineKeyboardMarkup, Update

from bot.db.analytics import record_product_event
from bot.db.database import User, utc_now
from bot.db.premium import (
    ensure_default_coin_subscriptions,
    set_user_coin_subscription,
    start_user_premium_trial,
)
from bot.db.prices import get_price_state
from bot.db.users import get_user_by_telegram_user_id
from bot.domain.premium import (
    get_user_trial,
    has_premium_entitlement,
    is_coin_unlocked_for_user,
    is_user_trial_active,
)
from bot.domain.supported_coins import SUPPORTED_SYMBOLS, display_symbol, is_symbol_free
from bot.keyboards import (
    build_onboarding_keyboard,
    build_premium_paywall_keyboard,
    build_trial_offer_keyboard,
)
from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL

ONBOARDING_VERSION = "v1"
INSTANT_BRIEF_MAX_AGE = timedelta(hours=6)


def _is_private_message(message) -> bool:
    return getattr(getattr(message, "chat", None), "type", None) == "private"


def _selected_symbols(subscriptions) -> list[str]:
    enabled = {row.symbol for row in subscriptions if row.is_enabled}
    return [symbol for symbol in SUPPORTED_SYMBOLS if symbol in enabled]


def _premium_active(user: User) -> bool:
    return has_premium_entitlement(user)


def build_onboarding_message(user: User, subscriptions) -> tuple[str, InlineKeyboardMarkup]:
    selected_symbols = _selected_symbols(subscriptions)
    selected = ", ".join(display_symbol(symbol) for symbol in selected_symbols) or "None yet"
    text = (
        "CCWBot keeps your crypto watchlist simple.\n\n"
        "Choose the coins you want monitored. BTC monitoring is free; ETH, SOL, and GRAM "
        "are Premium capabilities. You can select them now to save your intent.\n\n"
        f"Selected: {selected}"
    )
    return text, build_onboarding_keyboard(selected_symbols, premium_active=_premium_active(user))


def build_returning_user_message() -> tuple[str, InlineKeyboardMarkup]:
    return (
        "Welcome back to CCWBot.\n\nYour watchlist and monitoring settings are ready.",
        build_onboarding_keyboard((), returning_user=True),
    )


def _format_price(value: float) -> str:
    return f"${value:,.2f}" if value < 1000 else f"${value:,.0f}"


def _format_change(value: float | None) -> str:
    return f"{value:+.1f}%" if value is not None else "24h unavailable"


def _as_aware_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _premium_intent_count(subscriptions) -> int:
    return sum(1 for symbol in _selected_symbols(subscriptions) if not is_symbol_free(symbol))


def _trial_end_text(user: User) -> str:
    trial = get_user_trial(user)
    active_until = getattr(trial, "active_until", None)
    if active_until is None:
        return "Your Premium trial is active."
    return f"Your 7-day Premium trial is active until {active_until.date().isoformat()}."


async def build_instant_brief(
    session,
    *,
    user: User,
    subscriptions,
    now: datetime | None = None,
) -> str:
    """Render a brief from persisted PriceState only; never call LLMs or providers."""
    selected_symbols = _selected_symbols(subscriptions)
    brief_now = _as_aware_utc(now) or utc_now()
    lines = ["Your market brief", ""]
    for symbol in selected_symbols:
        state = await get_price_state(session, symbol)
        label = display_symbol(symbol)
        if state is None:
            lines.append(f"{label}: current data is warming up.")
            continue
        checked_at = _as_aware_utc(state.last_checked_at)
        if checked_at is None or brief_now - checked_at > INSTANT_BRIEF_MAX_AGE:
            lines.append(f"{label}: latest cached data is stale; waiting for refresh.")
            continue
        price = _format_price(float(state.last_price))
        change = _format_change(state.last_24h_change)
        lines.append(f"{label}: {price} · 24h {change}")

    active = [
        display_symbol(symbol)
        for symbol in selected_symbols
        if is_coin_unlocked_for_user(user, symbol)
    ]
    locked = [
        display_symbol(symbol)
        for symbol in selected_symbols
        if not is_coin_unlocked_for_user(user, symbol)
    ]
    lines.extend(["", f"Active monitoring: {', '.join(active) if active else 'None'}."])
    if locked:
        lines.append(f"Saved Premium intent: {', '.join(locked)}.")
    lines.append("Event alerts can arrive separately when meaningful market events are detected.")
    return "\n".join(lines)


async def _load_private_callback_user(query):
    if (
        not query
        or not query.from_user
        or not query.message
        or not _is_private_message(query.message)
    ):
        return None, None
    if not (DB_ENABLED and DB_SESSION_LOCAL):
        return None, None
    async with DB_SESSION_LOCAL() as session:
        user = await get_user_by_telegram_user_id(session, query.from_user.id, include_plan=True)
        if user is None or int(user.telegram_chat_id) != int(query.message.chat_id):
            return None, None
        subscriptions = await ensure_default_coin_subscriptions(session, user_id=user.id)
        return user, subscriptions


async def _edit_onboarding_message(query, text: str, **kwargs) -> bool:
    """Use the shared no-op edit handling but surface real delivery failures."""
    # Import locally because bot.handlers imports this module during callback registration.
    from bot.handlers.common import safe_edit_callback_message

    return await safe_edit_callback_message(
        query, text, suppress_errors=False, **kwargs
    )


async def send_start_experience(update: Update) -> bool:
    """Send either first-time selection or a concise returning-user dashboard."""
    if not update.message:
        return False
    chat_type = getattr(getattr(update.message, "chat", None), "type", None)
    if chat_type is not None and chat_type != "private":
        if update.message:
            await update.message.reply_text("Please use /start in a private chat with CCWBot.")
        return True
    if not (DB_ENABLED and DB_SESSION_LOCAL) or not update.effective_user:
        return False
    async with DB_SESSION_LOCAL() as session:
        user = await get_user_by_telegram_user_id(
            session, update.effective_user.id, include_plan=True
        )
        if user is None:
            return False
        subscriptions = await ensure_default_coin_subscriptions(session, user_id=user.id)
        if user.onboarding_completed_at is not None:
            text, keyboard = build_returning_user_message()
        else:
            await record_product_event(
                session,
                user_id=user.id,
                event_name="onboarding_started",
                event_key=f"onboarding:{ONBOARDING_VERSION}",
            )
            await session.commit()
            text, keyboard = build_onboarding_message(user, subscriptions)
    await update.message.reply_text(text, reply_markup=keyboard)
    return True


async def handle_onboarding_callback(update: Update, data: str) -> bool:
    query = update.callback_query
    if not data.startswith("onboarding:"):
        return False
    if not (DB_ENABLED and DB_SESSION_LOCAL):
        await query.answer("Onboarding storage is unavailable.", show_alert=True)
        return True
    user, subscriptions = await _load_private_callback_user(query)
    if user is None or subscriptions is None:
        await query.answer("Open CCWBot in your private chat.", show_alert=True)
        return True

    parts = data.split(":")
    if len(parts) == 3 and parts[1] == "toggle" and parts[2] in SUPPORTED_SYMBOLS:
        symbol = parts[2]
        current = symbol in _selected_symbols(subscriptions)
        async with DB_SESSION_LOCAL() as session:
            user = await get_user_by_telegram_user_id(
                session, query.from_user.id, include_plan=True
            )
            await set_user_coin_subscription(
                session, user_id=user.id, symbol=symbol, is_enabled=not current
            )
            subscriptions = await ensure_default_coin_subscriptions(session, user_id=user.id)
            selected_count = len(_selected_symbols(subscriptions))
            await record_product_event(
                session,
                user_id=user.id,
                event_name="coin_interest_selected",
                event_key=f"onboarding:{symbol}:{int(not current)}",
                symbol=symbol,
                selected_coin_count=selected_count,
            )
            await session.commit()
        text, keyboard = build_onboarding_message(user, subscriptions)
        await query.answer("Selection saved.")
        await _edit_onboarding_message(query, text, reply_markup=keyboard)
        return True

    if len(parts) == 2 and parts[1] == "confirm":
        async with DB_SESSION_LOCAL() as session:
            user = await get_user_by_telegram_user_id(
                session, query.from_user.id, include_plan=True
            )
            subscriptions = await ensure_default_coin_subscriptions(session, user_id=user.id)
            selected_count = len(_selected_symbols(subscriptions))
            brief = await build_instant_brief(session, user=user, subscriptions=subscriptions)
            premium_intent_count = _premium_intent_count(subscriptions)
            can_offer_trial = (
                premium_intent_count > 0
                and not has_premium_entitlement(user)
                and get_user_trial(user) is None
            )
            needs_paywall = premium_intent_count > 0 and not has_premium_entitlement(user)
        if can_offer_trial:
            brief = (
                f"{brief}\n\n{premium_intent_count} selected coin"
                f"{'s require' if premium_intent_count != 1 else ' requires'} Premium. "
                "Start a free 7-day trial to activate them now."
            )
            keyboard = build_trial_offer_keyboard()
        elif needs_paywall:
            brief = f"{brief}\n\nYour saved Premium choices need paid Premium to activate."
            keyboard = build_premium_paywall_keyboard()
        else:
            keyboard = build_onboarding_keyboard(
                _selected_symbols(subscriptions),
                completed=True,
                premium_active=_premium_active(user),
            )
        await query.answer()
        await _edit_onboarding_message(query, brief, reply_markup=keyboard)
        async with DB_SESSION_LOCAL() as session:
            user = await get_user_by_telegram_user_id(
                session, query.from_user.id, include_plan=True
            )
            user.onboarding_completed_at = utc_now()
            await record_product_event(
                session,
                user_id=user.id,
                event_name="onboarding_completed",
                event_key=f"onboarding:{ONBOARDING_VERSION}",
                selected_coin_count=selected_count,
            )
            if can_offer_trial:
                await record_product_event(
                    session,
                    user_id=user.id,
                    event_name="trial_offered",
                    event_key="trial:v1",
                    selected_coin_count=selected_count,
                )
            elif needs_paywall:
                await record_product_event(
                    session,
                    user_id=user.id,
                    event_name="paywall_viewed",
                    event_key="onboarding:premium:v1",
                    selected_coin_count=selected_count,
                )
            await record_product_event(
                session,
                user_id=user.id,
                event_name="watchlist_updated",
                event_key=f"onboarding:{ONBOARDING_VERSION}",
                selected_coin_count=selected_count,
            )
            await record_product_event(
                session,
                user_id=user.id,
                event_name="instant_brief_viewed",
                event_key=f"onboarding:{ONBOARDING_VERSION}",
                selected_coin_count=selected_count,
            )
            await session.commit()
        return True

    if len(parts) == 3 and parts[1:] == ["trial", "start"]:
        async with DB_SESSION_LOCAL() as session:
            user = await get_user_by_telegram_user_id(
                session, query.from_user.id, include_plan=True
            )
            subscriptions = await ensure_default_coin_subscriptions(session, user_id=user.id)
            selected_count = len(_selected_symbols(subscriptions))
            if _premium_intent_count(subscriptions) == 0:
                await query.answer("Choose a Premium coin first.", show_alert=True)
                return True
            trial, created = await start_user_premium_trial(
                session,
                telegram_user_id=query.from_user.id,
            )
            user = await get_user_by_telegram_user_id(
                session, query.from_user.id, include_plan=True
            )
            brief = await build_instant_brief(session, user=user, subscriptions=subscriptions)
        if trial is not None and is_user_trial_active(trial):
            text = f"{_trial_end_text(user)}\n\n{brief}"
            keyboard = build_onboarding_keyboard(
                _selected_symbols(subscriptions),
                completed=True,
                premium_active=True,
            )
            answer = "Trial started." if created else "Premium access is already active."
        elif has_premium_entitlement(user):
            text = f"Premium is already active.\n\n{brief}"
            keyboard = build_onboarding_keyboard(
                _selected_symbols(subscriptions),
                completed=True,
                premium_active=True,
            )
            answer = "Premium access is already active."
        else:
            text = "Your free trial has ended. Your Premium choices are still saved."
            keyboard = build_premium_paywall_keyboard()
            answer = "Your free trial has ended."
        await query.answer(answer)
        await _edit_onboarding_message(query, text, reply_markup=keyboard)
        if trial is not None and is_user_trial_active(trial):
            async with DB_SESSION_LOCAL() as session:
                delivered_user = await get_user_by_telegram_user_id(
                    session, query.from_user.id, include_plan=True
                )
                await record_product_event(
                    session,
                    user_id=delivered_user.id,
                    event_name="premium_value_delivered",
                    event_key="trial:v1",
                    selected_coin_count=selected_count,
                )
                await session.commit()
        return True

    if len(parts) == 2 and parts[1] == "brief":
        async with DB_SESSION_LOCAL() as session:
            user = await get_user_by_telegram_user_id(
                session, query.from_user.id, include_plan=True
            )
            subscriptions = await ensure_default_coin_subscriptions(session, user_id=user.id)
            brief = await build_instant_brief(session, user=user, subscriptions=subscriptions)
        await query.answer()
        await _edit_onboarding_message(
            query,
            brief,
            reply_markup=build_onboarding_keyboard(
                _selected_symbols(subscriptions),
                completed=True,
                premium_active=_premium_active(user),
            ),
        )
        return True
    return True
