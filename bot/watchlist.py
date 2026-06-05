from __future__ import annotations

from datetime import datetime, timezone

from telegram import InlineKeyboardMarkup, Message, Update
from telegram.error import NetworkError, TimedOut

from bot.db.database import (
    ensure_default_coin_subscriptions,
    get_user_by_telegram_user_id,
    grant_user_premium,
    revoke_user_premium,
    set_user_alert_frequency,
    set_user_coin_subscription,
)
from bot.domain.premium import (
    get_effective_frequency_seconds,
    get_user_plan,
    is_coin_unlocked_for_user,
    is_user_premium_active,
)
from bot.domain.supported_coins import (
    FREE_ALERT_FREQUENCY_SECONDS,
    PREMIUM_ALERT_FREQUENCY_SECONDS,
    SUPPORTED_COINS,
    SUPPORTED_SYMBOLS,
    is_symbol_free,
    premium_symbols_display,
)
from bot.keyboards import build_watchlist_keyboard
from bot.payments import build_subscribe_message as _build_subscribe_message
from bot.permissions import is_admin_update
from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL, log


def _format_date(value: datetime | None) -> str:
    if value is None:
        return "unknown"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).date().isoformat()


def _format_frequency(seconds: int) -> str:
    labels = {
        3600: "Every 1 hour",
        FREE_ALERT_FREQUENCY_SECONDS: "Every 4 hours",
        21600: "Every 6 hours",
        86400: "Every 24 hours",
    }
    return labels.get(seconds, f"Every {seconds} seconds")


def _subscription_by_symbol(subscriptions) -> dict[str, bool]:
    return {row.symbol: bool(row.is_enabled) for row in subscriptions}


async def _safe_reply_text(message: Message, text: str, **kwargs) -> bool:
    try:
        await message.reply_text(text, **kwargs)
    except (TimedOut, NetworkError) as error:
        log(f"Telegram reply failed for Premium/watchlist command: {type(error).__name__}")
        return False
    return True


async def _safe_edit_message_text(query, *, text: str, reply_markup: InlineKeyboardMarkup) -> bool:
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup)
    except (TimedOut, NetworkError) as error:
        log(f"Telegram watchlist edit failed: {type(error).__name__}")
        return False
    return True


def build_watchlist_message(user, subscriptions, now: datetime | None = None) -> tuple[str, list]:
    now = now or datetime.now(timezone.utc)
    plan = get_user_plan(user)
    premium_active = is_user_premium_active(plan, now)
    had_premium = plan is not None and getattr(plan, "active_until", None) is not None
    enabled_by_symbol = _subscription_by_symbol(subscriptions)

    keyboard_rows = []
    for symbol in SUPPORTED_SYMBOLS:
        enabled = enabled_by_symbol.get(symbol, is_symbol_free(symbol))
        unlocked = is_coin_unlocked_for_user(user, symbol, now)
        keyboard_rows.append((symbol, enabled, unlocked))

    lines = ["📡 Alert watchlist", ""]
    if premium_active:
        lines.append("Select coins for automatic alerts.")
        lines.append("")
        lines.append(
            "Heartbeat frequency: "
            f"{_format_frequency(get_effective_frequency_seconds(user, now))}"
        )
        lines.append("Event alerts may arrive separately when market events are detected.")
        lines.append("")
        lines.append(f"Paid access until: {_format_date(getattr(plan, 'active_until', None))}")
    elif had_premium:
        expired_on = _format_date(getattr(plan, "active_until", None))
        lines.append(f"Your Premium expired on: {expired_on}.")
        lines.append("Your premium coin choices are saved, but locked until renewal.")
        lines.append("")
        lines.append("Heartbeat frequency: Every 4 hours for BTC")
        lines.append("Event alerts may arrive separately when market events are detected.")
        lines.append("")
        lines.append("Use /subscribe to renew.")
    else:
        lines.append("BTC alerts are free.")
        lines.append(
            f"Premium unlocks automatic alerts for {premium_symbols_display()}."
        )
        lines.append("")
        lines.append(
            "Heartbeat frequency: "
            f"{_format_frequency(get_effective_frequency_seconds(user, now))}"
        )
        lines.append("Event alerts may arrive separately when market events are detected.")
        lines.append("")
        lines.append("Use /subscribe to upgrade.")
    return "\n".join(lines), keyboard_rows


def build_plan_message(user, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    plan = get_user_plan(user)
    if is_user_premium_active(plan, now):
        return (
            "Plan: Premium\n"
            f"Paid access until: {_format_date(getattr(plan, 'active_until', None))}\n"
            "Recurring subscription: not tracked by CCWBot\n"
            "Recurring payments can be managed in Telegram Stars settings.\n"
            "Premium coins unlocked."
        )
    if plan is not None and getattr(plan, "active_until", None) is not None:
        return (
            "Plan: Free\n"
            f"Premium expired on: {_format_date(getattr(plan, 'active_until', None))}\n"
            "Your premium coin choices are saved.\n"
            "Use /subscribe to renew."
        )
    return (
        "Plan: Free\n"
        "BTC alerts: available\n"
        "Premium: not active\n"
        "Use /subscribe to unlock multi-coin alerts."
    )


def build_subscribe_message() -> str:
    return _build_subscribe_message()


def _current_telegram_user_id(update: Update) -> int | None:
    return update.effective_user.id if update.effective_user else None


def _parse_target_telegram_user_id(update: Update, value: str) -> int | None:
    normalized_value = value.strip().lower()
    if normalized_value in {"me", "self"}:
        return _current_telegram_user_id(update)
    try:
        return int(value)
    except ValueError:
        return None


async def _reply_db_required(message: Message) -> None:
    await _safe_reply_text(message, "Watchlist storage is temporarily unavailable.")


async def _load_current_user(update: Update):
    if not (DB_ENABLED and DB_SESSION_LOCAL):
        return None, None
    if not update.effective_user:
        return None, None
    async with DB_SESSION_LOCAL() as session:
        user = await get_user_by_telegram_user_id(
            session,
            update.effective_user.id,
            include_plan=True,
        )
        if user is None:
            return None, None
        subscriptions = await ensure_default_coin_subscriptions(session, user_id=user.id)
        return user, subscriptions


async def send_watchlist_message(message: Message, user, subscriptions) -> None:
    text, reply_markup = build_watchlist_render(user, subscriptions)
    await _safe_reply_text(message, text, reply_markup=reply_markup)


def build_watchlist_render(
    user,
    subscriptions,
    now: datetime | None = None,
) -> tuple[str, InlineKeyboardMarkup]:
    now = now or datetime.now(timezone.utc)
    text, rows = build_watchlist_message(user, subscriptions, now)
    return (
        text,
        build_watchlist_keyboard(
            rows=rows,
            premium_active=is_user_premium_active(get_user_plan(user), now),
            current_frequency_seconds=get_effective_frequency_seconds(user, now),
        ),
    )


def build_user_settings_message(
    user,
    subscriptions,
    now: datetime | None = None,
) -> tuple[str, list]:
    now = now or datetime.now(timezone.utc)
    plan = get_user_plan(user)
    premium_active = is_user_premium_active(plan, now)
    enabled_by_symbol = _subscription_by_symbol(subscriptions)
    symbols = SUPPORTED_SYMBOLS if premium_active else ("btc",)

    rows = []
    enabled_symbols = []
    for symbol in symbols:
        enabled = enabled_by_symbol.get(symbol, is_symbol_free(symbol))
        unlocked = is_coin_unlocked_for_user(user, symbol, now)
        rows.append((symbol, enabled, unlocked))
        if enabled and unlocked:
            enabled_symbols.append(symbol.upper())

    subscribed_text = ", ".join(enabled_symbols) if enabled_symbols else "None"
    lines = [
        "Alert settings",
        "",
        f"Subscribed coins: {subscribed_text}",
        f"Heartbeat frequency: {_format_frequency(get_effective_frequency_seconds(user, now))}",
        (
            "How often you receive regular market heartbeat updates. Event alerts may "
            "arrive separately when significant market events are detected."
        ),
        "",
    ]
    if premium_active:
        lines.extend(
            [
                "Plan: Premium",
                f"Paid access until: {_format_date(getattr(plan, 'active_until', None))}",
                "Manage subscription: /myplan",
            ]
        )
    else:
        lines.append("Plan: Free")
        active_until = getattr(plan, "active_until", None) if plan is not None else None
        if active_until is not None:
            lines.append(f"Premium expired on: {_format_date(active_until)}")
        lines.append("Upgrade: /subscribe")
    return "\n".join(lines), rows


def build_user_settings_render(
    user,
    subscriptions,
    now: datetime | None = None,
) -> tuple[str, InlineKeyboardMarkup]:
    now = now or datetime.now(timezone.utc)
    text, rows = build_user_settings_message(user, subscriptions, now)
    return (
        text,
        build_watchlist_keyboard(
            rows=rows,
            premium_active=is_user_premium_active(get_user_plan(user), now),
            current_frequency_seconds=get_effective_frequency_seconds(user, now),
        ),
    )


async def send_user_settings_message(message: Message, user, subscriptions) -> None:
    text, reply_markup = build_user_settings_render(user, subscriptions)
    await _safe_reply_text(message, text, reply_markup=reply_markup)


async def edit_user_settings_message(query, user, subscriptions) -> None:
    text, reply_markup = build_user_settings_render(user, subscriptions)
    await _safe_edit_message_text(query, text=text, reply_markup=reply_markup)


async def edit_watchlist_message(query, user, subscriptions) -> None:
    await edit_user_settings_message(query, user, subscriptions)


async def watchlist_command(update: Update) -> None:
    await settings_command(update)


async def settings_command(update: Update) -> None:
    user, subscriptions = await _load_current_user(update)
    if user is None or subscriptions is None:
        await _reply_db_required(update.message)
        return
    await send_user_settings_message(update.message, user, subscriptions)


async def myplan_command(update: Update) -> None:
    user, _ = await _load_current_user(update)
    if user is None:
        await _reply_db_required(update.message)
        return
    await _safe_reply_text(update.message, build_plan_message(user))


async def handle_watchlist_callback(update: Update, data: str) -> bool:
    query = update.callback_query
    if not query or not query.message:
        return True
    if not (DB_ENABLED and DB_SESSION_LOCAL):
        await query.answer("Watchlist storage is unavailable.", show_alert=True)
        return True
    if not query.from_user:
        return True

    parts = data.split(":")
    if len(parts) == 4 and parts[:2] == ["watchlist", "set"]:
        symbol = parts[2].lower()
        desired_enabled = parts[3].lower() == "true"
        async with DB_SESSION_LOCAL() as session:
            user = await get_user_by_telegram_user_id(
                session,
                query.from_user.id,
                include_plan=True,
            )
            if user is None:
                return True
            subscriptions = await ensure_default_coin_subscriptions(session, user_id=user.id)
            now = datetime.now(timezone.utc)
            if symbol not in SUPPORTED_COINS:
                await query.answer("Unsupported symbol.", show_alert=True)
                return True
            if not is_coin_unlocked_for_user(user, symbol, now):
                await query.answer("Premium required. Use /subscribe.", show_alert=False)
                return True
            await set_user_coin_subscription(
                session,
                user_id=user.id,
                symbol=symbol,
                is_enabled=desired_enabled,
            )
            subscriptions = await ensure_default_coin_subscriptions(session, user_id=user.id)
            await query.answer("Updated.")
            await edit_watchlist_message(query, user, subscriptions)
        return True

    if len(parts) == 3 and parts[:2] == ["watchlist", "frequency"]:
        try:
            frequency_seconds = int(parts[2])
        except ValueError:
            await query.answer("Unsupported frequency.", show_alert=True)
            return True
        if frequency_seconds not in PREMIUM_ALERT_FREQUENCY_SECONDS:
            await query.answer("Unsupported frequency.", show_alert=True)
            return True
        async with DB_SESSION_LOCAL() as session:
            user = await get_user_by_telegram_user_id(
                session,
                query.from_user.id,
                include_plan=True,
            )
            if user is None:
                return True
            if not is_user_premium_active(get_user_plan(user), datetime.now(timezone.utc)):
                await query.answer("Premium required. Use /subscribe.", show_alert=False)
                return True
            await set_user_alert_frequency(
                session,
                user_id=user.id,
                frequency_seconds=frequency_seconds,
            )
            user = await get_user_by_telegram_user_id(
                session,
                query.from_user.id,
                include_plan=True,
            )
            subscriptions = await ensure_default_coin_subscriptions(session, user_id=user.id)
            await query.answer("Frequency updated.")
            await edit_watchlist_message(query, user, subscriptions)
        return True
    return False


async def grant_premium_command(update: Update, args: list[str]) -> None:
    if not await is_admin_update(update):
        await _safe_reply_text(update.message, "Sorry, only the bot admin can grant Premium.")
        return
    if len(args) != 2:
        await _safe_reply_text(update.message, "Usage: /grantpremium <telegram_user_id|me> <days>")
        return
    telegram_user_id = _parse_target_telegram_user_id(update, args[0])
    if telegram_user_id is None:
        await _safe_reply_text(update.message, "User ID must be a whole number or me.")
        return
    try:
        days = int(args[1])
    except ValueError:
        await _safe_reply_text(update.message, "Days must be a whole number.")
        return
    if days <= 0:
        await _safe_reply_text(update.message, "Days must be greater than 0.")
        return
    if not (DB_ENABLED and DB_SESSION_LOCAL):
        await _safe_reply_text(update.message, "Premium storage is temporarily unavailable.")
        return
    try:
        async with DB_SESSION_LOCAL() as session:
            subscription = await grant_user_premium(
                session,
                telegram_user_id=telegram_user_id,
                days=days,
            )
    except ValueError:
        await _safe_reply_text(
            update.message,
            "User was not found. Ask them to start the bot first.",
        )
        return
    log(f"ops_event=premium_grant_processed days={days}")
    await _safe_reply_text(
        update.message,
        "Premium granted "
        f"to Telegram user ID {telegram_user_id} "
        f"until {_format_date(subscription.active_until)}."
    )


async def revoke_premium_command(update: Update, args: list[str]) -> None:
    if not await is_admin_update(update):
        await _safe_reply_text(update.message, "Sorry, only the bot admin can revoke Premium.")
        return
    if len(args) != 1:
        await _safe_reply_text(update.message, "Usage: /revokepremium <telegram_user_id|me>")
        return
    telegram_user_id = _parse_target_telegram_user_id(update, args[0])
    if telegram_user_id is None:
        await _safe_reply_text(update.message, "User ID must be a whole number or me.")
        return
    if not (DB_ENABLED and DB_SESSION_LOCAL):
        await _safe_reply_text(update.message, "Premium storage is temporarily unavailable.")
        return
    try:
        async with DB_SESSION_LOCAL() as session:
            await revoke_user_premium(session, telegram_user_id=telegram_user_id)
    except ValueError:
        await _safe_reply_text(
            update.message,
            "User was not found. Ask them to start the bot first.",
        )
        return
    log("ops_event=premium_revoke_processed")
    await _safe_reply_text(
        update.message,
        f"Premium revoked for Telegram user ID {telegram_user_id}. "
        "Saved coin choices were preserved.",
    )
