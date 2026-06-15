"""Manual price lookup and text-message utility handlers."""

import time

from telegram import MessageEntity, Update
from telegram.ext import ContextTypes

from bot.domain.supported_coins import normalize_symbol
from bot.keyboards import build_price_keyboard
from bot.prices import (
    build_supported_symbols_message,
    send_manual_rate_limit_message,
    send_price_message,
)
from bot.services.price_service import COIN_SYMBOL_TO_ID, CoinGeckoRateLimitError

from .common import handlers_module, log_request, logger

PRICE_RATE_LIMIT_SECONDS = 10
PRICE_RATE_LIMIT_PRUNE_AFTER_SECONDS = 3600
_user_last_price_call: dict[int, float] = {}


@log_request("/price")
async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id_value = update.effective_user.id if update.effective_user else None
        now = time.monotonic()
        if user_id_value is not None:
            stale_before = now - PRICE_RATE_LIMIT_PRUNE_AFTER_SECONDS
            for cached_user_id, last_seen_at in list(_user_last_price_call.items()):
                if last_seen_at < stale_before:
                    _user_last_price_call.pop(cached_user_id, None)
            last_call_at = _user_last_price_call.get(user_id_value)
            if last_call_at is not None and now - last_call_at < PRICE_RATE_LIMIT_SECONDS:
                await update.message.reply_text(
                    "⏳ Please wait a few seconds before requesting again."
                )
                return
            _user_last_price_call[user_id_value] = now

        if not context.args:
            await update.message.reply_text(
                "Choose a coin symbol:",
                reply_markup=build_price_keyboard(),
            )
            return
        requested_symbol = normalize_symbol(context.args[0])
        if requested_symbol not in COIN_SYMBOL_TO_ID:
            supported_symbols = build_supported_symbols_message()
            await update.message.reply_text(
                f"Unsupported symbol '{context.args[0].lower()}'.\n"
                f"Supported symbols: {supported_symbols}"
            )
            return
        await send_price_message(update.message, requested_symbol)
    except CoinGeckoRateLimitError:
        await send_manual_rate_limit_message(
            update.message, update.effective_chat.id if update.effective_chat else None
        )
    except ValueError as error:
        logger.warning("Manual price lookup failed: %s", error)
        await update.message.reply_text("Price data is temporarily unavailable.")
    except Exception as error:
        await update.message.reply_text("Sorry, I could not get the price right now.")
        logger.exception("Price command failed: %s", error)


async def log_custom_emoji_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await handlers_module().is_admin_update(update):
        return
    message = update.effective_message
    if message is None:
        return
    entities = list(message.entities or ()) + list(message.caption_entities or ())
    for entity in entities:
        if entity.type != MessageEntity.CUSTOM_EMOJI:
            continue
        custom_emoji_id = getattr(entity, "custom_emoji_id", None)
        if not custom_emoji_id:
            continue
        logger.info(
            "custom_emoji_entity type=%s offset=%s length=%s custom_emoji_id=%s",
            entity.type,
            entity.offset,
            entity.length,
            custom_emoji_id,
        )
