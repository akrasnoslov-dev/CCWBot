from __future__ import annotations

from html import escape

from telegram import MessageEntity

from bot.domain.supported_coins import display_symbol

# Fill these values after sending the CCWBotIcons custom emojis to the bot as admin
# and copying custom_emoji_id values from logs.
COIN_CUSTOM_EMOJI_IDS: dict[str, str] = {
    "BTC": "5220072735815802195",
    "ETH": "5219946347813182032",
    "SOL": "5220183077820601140",
    "GRAM": "5219964412445631201",
}

COIN_FALLBACK_EMOJI: dict[str, str] = {
    "BTC": "\U0001f7e0",
    "ETH": "\U0001f537",
    "SOL": "\U0001f7e3",
    "GRAM": "\U0001f48e",
}


def coin_fallback_emoji(symbol: str) -> str:
    return COIN_FALLBACK_EMOJI.get(display_symbol(symbol), "\U0001fa99")


def coin_custom_emoji_id(symbol: str) -> str | None:
    value = COIN_CUSTOM_EMOJI_IDS.get(display_symbol(symbol))
    return value.strip() if value and value.strip() else None


def build_coin_icon_html(symbol: str) -> str:
    emoji = coin_fallback_emoji(symbol)
    custom_emoji_id = coin_custom_emoji_id(symbol)
    if not custom_emoji_id:
        return emoji
    return (
        f'<tg-emoji emoji-id="{escape(custom_emoji_id, quote=True)}">'
        f"{escape(emoji)}</tg-emoji>"
    )


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
