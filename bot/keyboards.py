from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.domain.supported_coins import PREMIUM_ALERT_FREQUENCY_SECONDS, SUPPORTED_SYMBOLS


def build_price_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(symbol.upper(), callback_data=f"price:{symbol}")
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
                f"{marker} {symbol.upper()}",
                callback_data=f"watchlist:set:{symbol}:{callback_value}",
            )
        )
    keyboard = [
        coin_buttons[index : index + 3] for index in range(0, len(coin_buttons), 3)
    ]

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
            [InlineKeyboardButton("Alert frequency", callback_data="watchlist:open")],
        ]
    )


def build_admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Alert settings", callback_data="admin:alert_settings")],
            [InlineKeyboardButton("System status", callback_data="admin:system_status")],
            [InlineKeyboardButton("Export logs", callback_data="admin:export_logs")],
        ]
    )


def build_admin_alert_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Current settings", callback_data="admin:current")],
            [InlineKeyboardButton("Check interval", callback_data="admin:interval_menu")],
        ]
    )


def build_interval_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("60 sec", callback_data="admin:set_interval:60")],
            [InlineKeyboardButton("300 sec", callback_data="admin:set_interval:300")],
            [InlineKeyboardButton("600 sec", callback_data="admin:set_interval:600")],
        ]
    )


def build_reports_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Daily report", callback_data="reports:daily")],
            [InlineKeyboardButton("Weekly report", callback_data="reports:weekly")],
        ]
    )
