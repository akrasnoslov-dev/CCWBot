import importlib
import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import bot.prices as prices
import bot.storage as storage
from bot.services.price_service import CoinGeckoRateLimitError

price_handler = importlib.import_module("bot.handlers.price")


def _update(*, user_id: int = 1001, chat_id: int = 2001):
    message = SimpleNamespace(reply_text=AsyncMock())
    return SimpleNamespace(
        effective_user=SimpleNamespace(id=user_id),
        effective_chat=SimpleNamespace(id=chat_id),
        message=message,
    )


def _context(args: list[str]):
    return SimpleNamespace(args=args, user_data={})


@pytest.fixture(autouse=True)
def clear_manual_price_rate_limits():
    price_handler._user_last_price_call.clear()
    prices._MANUAL_RATE_LIMIT_LAST_SENT_AT_BY_CHAT.clear()
    yield
    price_handler._user_last_price_call.clear()
    prices._MANUAL_RATE_LIMIT_LAST_SENT_AT_BY_CHAT.clear()


@pytest.mark.asyncio
async def test_price_without_symbol_shows_the_price_keyboard(monkeypatch):
    update = _update()
    keyboard = object()
    monkeypatch.setattr(price_handler, "build_price_keyboard", lambda: keyboard)

    await price_handler.price(update, _context([]))

    update.message.reply_text.assert_awaited_once_with(
        "Choose a coin symbol:", reply_markup=keyboard
    )


@pytest.mark.asyncio
async def test_price_normalizes_legacy_ton_alias_before_lookup(monkeypatch):
    update = _update()
    send_price = AsyncMock()
    monkeypatch.setattr(price_handler, "send_price_message", send_price)

    await price_handler.price(update, _context(["TON"]))

    send_price.assert_awaited_once_with(update.message, "gram")
    update.message.reply_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_price_rejects_unsupported_symbol_without_provider_call(monkeypatch):
    update = _update()
    send_price = AsyncMock()
    monkeypatch.setattr(price_handler, "send_price_message", send_price)

    await price_handler.price(update, _context(["USDT"]))

    send_price.assert_not_awaited()
    reply = update.message.reply_text.await_args.args[0]
    assert reply.startswith("Unsupported symbol 'usdt'.")
    assert "BTC, ETH, GRAM, SOL" in reply


@pytest.mark.asyncio
async def test_price_rate_limits_each_user_before_provider_call(monkeypatch):
    update = _update()
    send_price = AsyncMock()
    monkeypatch.setattr(price_handler, "send_price_message", send_price)
    monkeypatch.setattr(price_handler.time, "monotonic", lambda: 100.0)
    price_handler._user_last_price_call[1001] = 95.0

    await price_handler.price(update, _context(["btc"]))

    send_price.assert_not_awaited()
    update.message.reply_text.assert_awaited_once_with(
        "⏳ Please wait a few seconds before requesting again."
    )


@pytest.mark.asyncio
async def test_price_maps_provider_errors_to_safe_user_messages(monkeypatch):
    update = _update()
    rate_limit_message = AsyncMock()
    monkeypatch.setattr(
        price_handler,
        "send_price_message",
        AsyncMock(side_effect=CoinGeckoRateLimitError("provider internals")),
    )
    monkeypatch.setattr(price_handler, "send_manual_rate_limit_message", rate_limit_message)

    await price_handler.price(update, _context(["btc"]))

    rate_limit_message.assert_awaited_once_with(update.message, 2001)
    update.message.reply_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_price_hides_value_error_details_from_users(monkeypatch):
    update = _update()
    monkeypatch.setattr(
        price_handler,
        "send_price_message",
        AsyncMock(side_effect=ValueError("raw provider response: secret")),
    )

    await price_handler.price(update, _context(["btc"]))

    update.message.reply_text.assert_awaited_once_with("Price data is temporarily unavailable.")


@pytest.mark.asyncio
async def test_send_price_message_persists_manual_btc_decimal_fallback_state(monkeypatch, tmp_path):
    target = SimpleNamespace(reply_text=AsyncMock())
    saved_state = {}
    state_file = tmp_path / "state.json"
    monkeypatch.setattr(prices, "DB_ENABLED", False)
    monkeypatch.setattr(
        prices,
        "get_coin_price",
        AsyncMock(return_value=(Decimal("100000.123456789012345678"), Decimal("2.5"), "btc")),
    )
    monkeypatch.setattr(prices, "load_state", lambda: saved_state)
    monkeypatch.setattr(storage, "STATE_FILE", state_file)

    await prices.send_price_message(target, "btc")

    assert saved_state["last_price"] == Decimal("100000.123456789012345678")
    assert saved_state["last_24h_change"] == Decimal("2.5")
    assert saved_state["last_alert_at"] is None
    assert json.loads(state_file.read_text(encoding="utf-8")) == {
        "last_price": "100000.123456789012345678",
        "last_24h_change": "2.5",
        "last_checked_at": saved_state["last_checked_at"],
        "last_alert_at": None,
    }
    assert "BTC price" in target.reply_text.await_args.args[0]


@pytest.mark.asyncio
async def test_manual_rate_limit_message_is_suppressed_per_chat():
    target = SimpleNamespace(reply_text=AsyncMock())

    await prices.send_manual_rate_limit_message(target, 2001)
    await prices.send_manual_rate_limit_message(target, 2001)

    target.reply_text.assert_awaited_once_with(
        "CoinGecko rate limit reached. Please wait a bit and try again."
    )
