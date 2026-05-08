from datetime import datetime, timezone

from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL, log
from database import get_price_state, update_price_state
from price_service import COIN_SYMBOL_TO_ID, DEFAULT_SYMBOL, get_coin_price
from storage import load_state, save_state

MANUAL_RATE_LIMIT_MESSAGE_COOLDOWN_SECONDS = 120
_MANUAL_RATE_LIMIT_LAST_SENT_AT_BY_CHAT: dict[int, float] = {}


def build_supported_symbols_message() -> str:
    return ", ".join(COIN_SYMBOL_TO_ID.keys())


async def send_price_message(target, symbol: str) -> None:
    coin_price, change_24h, resolved_symbol = await get_coin_price(symbol)
    checked_at = datetime.now(timezone.utc).isoformat()

    if resolved_symbol == DEFAULT_SYMBOL and DB_ENABLED and DB_SESSION_LOCAL:
        async with DB_SESSION_LOCAL() as session:
            existing = await get_price_state(session, DEFAULT_SYMBOL)
            await update_price_state(
                session,
                symbol=DEFAULT_SYMBOL,
                last_price=coin_price,
                last_24h_change=change_24h,
                last_checked_at=datetime.now(timezone.utc),
                last_alert_at=existing.last_alert_at if existing else None,
            )
    else:
        state = load_state()
        if resolved_symbol == DEFAULT_SYMBOL:
            state["last_price"] = coin_price
            state["last_24h_change"] = change_24h
            state["last_checked_at"] = checked_at
            if "last_alert_at" not in state:
                state["last_alert_at"] = None
            save_state(state)

    await target.reply_text(
        f"{resolved_symbol.upper()} price\n\n"
        f"Current USD price: ${coin_price:,.2f}\n"
        f"24h change: {change_24h:.2f}%"
    )


async def send_manual_rate_limit_message(target, chat_id: int | None) -> None:
    log("CoinGecko rate limit reached during manual price request.")
    if chat_id is None:
        await target.reply_text("CoinGecko rate limit reached. Please wait a bit and try again.")
        return

    now_ts = datetime.now(timezone.utc).timestamp()
    last_sent_ts = _MANUAL_RATE_LIMIT_LAST_SENT_AT_BY_CHAT.get(chat_id)
    if (
        last_sent_ts is not None
        and (now_ts - last_sent_ts) < MANUAL_RATE_LIMIT_MESSAGE_COOLDOWN_SECONDS
    ):
        return

    _MANUAL_RATE_LIMIT_LAST_SENT_AT_BY_CHAT[chat_id] = now_ts
    await target.reply_text("CoinGecko rate limit reached. Please wait a bit and try again.")
