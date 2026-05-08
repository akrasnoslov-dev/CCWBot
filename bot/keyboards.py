from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def build_price_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("BTC", callback_data="price:btc"),
                InlineKeyboardButton("ETH", callback_data="price:eth"),
            ],
            [
                InlineKeyboardButton("TON", callback_data="price:ton"),
                InlineKeyboardButton("USDT", callback_data="price:usdt"),
            ],
        ]
    )


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
