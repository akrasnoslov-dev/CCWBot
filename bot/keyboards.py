from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from supported_coins import PREMIUM_ALERT_FREQUENCY_SECONDS, SUPPORTED_SYMBOLS


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
    keyboard = []
    for symbol, enabled, unlocked in rows:
        marker = "Disable" if enabled and unlocked else "Enable"
        if not unlocked:
            marker = "Locked"
        callback_value = "false" if enabled else "true"
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"{symbol.upper()} {marker}",
                    callback_data=f"watchlist:set:{symbol}:{callback_value}",
                )
            ]
        )

    if premium_active:
        frequency_buttons = [
            InlineKeyboardButton(
                _frequency_label(frequency, selected=frequency == current_frequency_seconds),
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
    prefix = "* " if selected else ""
    return f"{prefix}{label_by_seconds.get(seconds, str(seconds))}"


def build_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Current settings", callback_data="settings:current")],
            [InlineKeyboardButton("Set threshold", callback_data="settings:threshold_menu")],
            [InlineKeyboardButton("Set check interval", callback_data="settings:interval_menu")],
        ]
    )


def build_threshold_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("0.5%", callback_data="settings:set_threshold:0.5")],
            [InlineKeyboardButton("1.0%", callback_data="settings:set_threshold:1.0")],
            [InlineKeyboardButton("2.0%", callback_data="settings:set_threshold:2.0")],
        ]
    )


def build_interval_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("60 sec", callback_data="settings:set_interval:60")],
            [InlineKeyboardButton("300 sec", callback_data="settings:set_interval:300")],
            [InlineKeyboardButton("600 sec", callback_data="settings:set_interval:600")],
        ]
    )


def build_reports_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Daily report", callback_data="reports:daily")],
            [InlineKeyboardButton("Weekly report", callback_data="reports:weekly")],
        ]
    )
