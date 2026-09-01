"""First-time Telegram onboarding and deterministic cached market brief."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from telegram import InlineKeyboardMarkup, Update

from bot.db.analytics import record_product_event
from bot.db.database import User, utc_now
from bot.db.premium import ensure_default_coin_subscriptions, set_user_coin_subscription
from bot.db.prices import get_price_state
from bot.db.users import get_user_by_telegram_user_id
from bot.domain.premium import is_coin_unlocked_for_user
from bot.domain.supported_coins import SUPPORTED_SYMBOLS, display_symbol
from bot.keyboards import build_onboarding_keyboard
from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL

ONBOARDING_VERSION = "v1"
INSTANT_BRIEF_MAX_AGE = timedelta(hours=6)


def _is_private_message(message) -> bool:
    return getattr(getattr(message, "chat", None), "type", None) == "private"


def _selected_symbols(subscriptions) -> list[str]:
    enabled = {row.symbol for row in subscriptions if row.is_enabled}
    return [symbol for symbol in SUPPORTED_SYMBOLS if symbol in enabled]


def _premium_active(user: User) -> bool:
    return is_coin_unlocked_for_user(user, "eth")


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
        await query.edit_message_text(text=text, reply_markup=keyboard)
        return True

    if len(parts) == 2 and parts[1] == "confirm":
        async with DB_SESSION_LOCAL() as session:
            user = await get_user_by_telegram_user_id(
                session, query.from_user.id, include_plan=True
            )
            subscriptions = await ensure_default_coin_subscriptions(session, user_id=user.id)
            selected_count = len(_selected_symbols(subscriptions))
            user.onboarding_completed_at = utc_now()
            await record_product_event(
                session,
                user_id=user.id,
                event_name="onboarding_completed",
                event_key=f"onboarding:{ONBOARDING_VERSION}",
                selected_coin_count=selected_count,
            )
            await record_product_event(
                session,
                user_id=user.id,
                event_name="watchlist_updated",
                event_key=f"onboarding:{ONBOARDING_VERSION}",
                selected_coin_count=selected_count,
            )
            brief = await build_instant_brief(session, user=user, subscriptions=subscriptions)
            await record_product_event(
                session,
                user_id=user.id,
                event_name="instant_brief_viewed",
                event_key=f"onboarding:{ONBOARDING_VERSION}",
                selected_coin_count=selected_count,
            )
            await session.commit()
        await query.answer()
        await query.edit_message_text(
            text=brief,
            reply_markup=build_onboarding_keyboard(
                _selected_symbols(subscriptions),
                completed=True,
                premium_active=_premium_active(user),
            ),
        )
        return True

    if len(parts) == 2 and parts[1] == "brief":
        async with DB_SESSION_LOCAL() as session:
            user = await get_user_by_telegram_user_id(
                session, query.from_user.id, include_plan=True
            )
            subscriptions = await ensure_default_coin_subscriptions(session, user_id=user.id)
            brief = await build_instant_brief(session, user=user, subscriptions=subscriptions)
        await query.answer()
        await query.edit_message_text(
            text=brief,
            reply_markup=build_onboarding_keyboard(
                _selected_symbols(subscriptions),
                completed=True,
                premium_active=_premium_active(user),
            ),
        )
        return True
    return True
