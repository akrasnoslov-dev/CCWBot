from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.domain.supported_coins import (
    PREMIUM_ALERT_FREQUENCY_SECONDS,
    SUPPORTED_SYMBOLS,
    display_symbol,
)


def build_onboarding_keyboard(
    selected_symbols: tuple[str, ...] | list[str],
    *,
    completed: bool = False,
    premium_active: bool = False,
    returning_user: bool = False,
) -> InlineKeyboardMarkup:
    if returning_user:
        return InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Current brief", callback_data="onboarding:brief")],
                [InlineKeyboardButton("Watchlist", callback_data="watchlist:open")],
                [InlineKeyboardButton("Plan", callback_data="plan:my_plan")],
            ]
        )
    selected = set(selected_symbols)
    buttons = []
    for symbol in SUPPORTED_SYMBOLS:
        is_selected = symbol in selected
        status = "✅" if is_selected else "⬜"
        plan = "Free" if symbol == "btc" else "Premium"
        lock = "" if symbol == "btc" or premium_active else "🔒 "
        buttons.append(
            InlineKeyboardButton(
                f"{lock}{status} {display_symbol(symbol)} · {plan}",
                callback_data=f"onboarding:toggle:{symbol}",
            )
        )
    rows = [buttons[index : index + 2] for index in range(0, len(buttons), 2)]
    if completed:
        rows.append([InlineKeyboardButton("Refresh brief", callback_data="onboarding:brief")])
    else:
        rows.append([InlineKeyboardButton("Show my brief", callback_data="onboarding:confirm")])
    return InlineKeyboardMarkup(rows)


def build_premium_activation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Current brief", callback_data="onboarding:brief")],
            [InlineKeyboardButton("Manage watchlist", callback_data="watchlist:open")],
        ]
    )


def build_trial_offer_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Start free 7-day trial", callback_data="onboarding:trial:start"
                )
            ],
            [InlineKeyboardButton("Current brief", callback_data="onboarding:brief")],
            [InlineKeyboardButton("See Premium price", callback_data="plan:subscribe")],
        ]
    )


def build_premium_paywall_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("See Premium price", callback_data="plan:subscribe")],
            [InlineKeyboardButton("Current brief", callback_data="onboarding:brief")],
        ]
    )


def build_price_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(display_symbol(symbol), callback_data=f"price:{symbol}")
        for symbol in SUPPORTED_SYMBOLS
    ]
    rows = [buttons[index : index + 2] for index in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(rows)


def build_watchlist_keyboard(
    *,
    rows: list[tuple[str, bool, bool]],
    premium_active: bool,
    current_frequency_seconds: int,
) -> InlineKeyboardMarkup:
    coin_buttons = []
    for symbol, enabled, unlocked in rows:
        marker = "✅" if enabled and unlocked else "⬜"
        if not unlocked:
            marker = "🔒"
        callback_value = "false" if enabled else "true"
        coin_buttons.append(
            InlineKeyboardButton(
                f"{marker} {display_symbol(symbol)}",
                callback_data=f"watchlist:set:{symbol}:{callback_value}",
            )
        )
    keyboard = [coin_buttons[index : index + 3] for index in range(0, len(coin_buttons), 3)]

    if premium_active:
        frequency_buttons = [
            InlineKeyboardButton(
                _frequency_label(
                    frequency,
                    selected=frequency == current_frequency_seconds,
                ),
                callback_data=f"watchlist:frequency:{frequency}",
            )
            for frequency in PREMIUM_ALERT_FREQUENCY_SECONDS
        ]
        keyboard.append(frequency_buttons)
    return InlineKeyboardMarkup(keyboard)


def _frequency_label(seconds: int, *, selected: bool) -> str:
    label_by_seconds = {
        3600: "1h",
        21600: "6h",
        86400: "24h",
    }
    prefix = "✅ " if selected else "⬜ "
    return f"{prefix}{label_by_seconds.get(seconds, str(seconds))}"


def build_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Subscribed coins", callback_data="watchlist:open")],
            [InlineKeyboardButton("Heartbeat frequency", callback_data="watchlist:open")],
        ]
    )


def build_plan_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("My plan", callback_data="plan:my_plan")],
            [InlineKeyboardButton("Subscribe", callback_data="plan:subscribe")],
        ]
    )


def build_my_plan_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Subscribe", callback_data="plan:subscribe")],
            [InlineKeyboardButton("Back", callback_data="plan:back")],
        ]
    )


def build_admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Alert settings", callback_data="admin:alert_settings")],
            [InlineKeyboardButton("System status", callback_data="admin:system_status")],
            [InlineKeyboardButton("LLM diagnostics", callback_data="admin:llm_diagnostics")],
            [InlineKeyboardButton("Premium management", callback_data="admin:premium_menu")],
            [InlineKeyboardButton("Logs", callback_data="admin:logs_menu")],
        ]
    )


def build_admin_alert_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Current settings", callback_data="admin:current")],
            [InlineKeyboardButton("Event analysis interval", callback_data="admin:interval_menu")],
            [InlineKeyboardButton("Back", callback_data="admin:back")],
        ]
    )


def build_admin_premium_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Grant premium", callback_data="admin:premium_grant")],
            [InlineKeyboardButton("Revoke premium", callback_data="admin:premium_revoke")],
            [InlineKeyboardButton("Back", callback_data="admin:back")],
        ]
    )


def build_admin_logs_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("ON / OFF", callback_data="admin:logs_toggle")],
            [InlineKeyboardButton("Status", callback_data="admin:logs_status")],
            [InlineKeyboardButton("Export logs", callback_data="admin:logs_export")],
            [InlineKeyboardButton("Back", callback_data="admin:back")],
        ]
    )


def build_admin_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="admin:back")]])


def build_interval_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("1800 sec", callback_data="admin:set_interval:1800")],
            [InlineKeyboardButton("Back", callback_data="admin:alert_settings")],
        ]
    )


def build_reports_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Daily report", callback_data="reports:daily")],
            [InlineKeyboardButton("Weekly report", callback_data="reports:weekly")],
        ]
    )
