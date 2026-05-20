from __future__ import annotations

from telegram import MessageEntity

from bot.domain.supported_coins import normalize_symbol

# Fill these values after sending the CCWBotIcons custom emojis to the bot as admin
# and copying custom_emoji_id values from logs.
COIN_CUSTOM_EMOJI_IDS: dict[str, str] = {
    "BTC": "5220072735815802195",
    "ETH": "5219946347813182032",
    "SOL": "5220183077820601140",
    "XRP": "5220105935913000440",
    "BNB": "5219798295995521250",
    "DOGE": "5220160524947332359",
    "ADA": "5219979977407111501",
    "TON": "5219964412445631201",
    "LINK": "5219729344590554883",
    "TRX": "5219851227172479406",
}

COIN_FALLBACK_EMOJI: dict[str, str] = {
    "BTC": "\U0001f7e0",
    "ETH": "\U0001f537",
    "SOL": "\U0001f7e3",
    "XRP": "\u26ab",
    "BNB": "\U0001f7e1",
    "DOGE": "\U0001f436",
    "ADA": "\U0001f535",
    "TON": "\U0001f48e",
    "LINK": "\U0001f517",
    "TRX": "\U0001f534",
}


def coin_fallback_emoji(symbol: str) -> str:
    return COIN_FALLBACK_EMOJI.get(normalize_symbol(symbol).upper(), "\U0001fa99")


def coin_custom_emoji_id(symbol: str) -> str | None:
    value = COIN_CUSTOM_EMOJI_IDS.get(normalize_symbol(symbol).upper())
    return value.strip() if value and value.strip() else None


def build_coin_icon_prefix(symbol: str) -> tuple[str, list[MessageEntity] | None]:
    emoji = coin_fallback_emoji(symbol)
    custom_emoji_id = coin_custom_emoji_id(symbol)
    if not custom_emoji_id:
        return emoji, None
    return emoji, [
        MessageEntity(
            type=MessageEntity.CUSTOM_EMOJI,
            offset=0,
            length=len(emoji.encode("utf-16-le")) // 2,
            custom_emoji_id=custom_emoji_id,
        )
    ]
