"""Regression coverage for CCW-9 transient command screens and CCW-10 price cache."""
import asyncio
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.handlers.transient import (
    TransientSessions,
    with_close_button,
)
from bot.services import price_service


@pytest.mark.asyncio
async def test_consecutive_commands_retire_all_prior_results_by_chat_and_user():
    sessions = TransientSessions()
    bot = SimpleNamespace(delete_message=AsyncMock())
    first = await sessions.begin((11, 20), bot)
    sessions.add((11, 20), first, 100)
    sessions.add((11, 20), first, 101)
    other = await sessions.begin((12, 20), bot)
    sessions.add((12, 20), other, 900)

    second = await sessions.begin((11, 20), bot)

    assert second != first
    assert sessions.is_retired(11, 100)
    assert sessions.is_retired(11, 101)
    assert not sessions.is_retired(12, 900)
    assert bot.delete_message.await_count == 2
    sessions.add((11, 20), first, 102)
    assert not sessions.is_active(11, 20, 102)


@pytest.mark.asyncio
async def test_close_deletes_entire_result_and_stale_callback_is_rejected():
    sessions = TransientSessions()
    bot = SimpleNamespace(delete_message=AsyncMock(side_effect=RuntimeError("cannot delete")))
    token = await sessions.begin((11, 20), bot)
    sessions.add((11, 20), token, 50)
    sessions.add((11, 20), token, 51)

    assert await sessions.close(11, 20, 51, bot)
    assert not sessions.is_active(11, 20, 50)
    assert sessions.is_retired(11, 50)
    assert sessions.is_retired(11, 51)
    assert not await sessions.close(11, 20, 51, bot)


def test_close_markup_preserves_other_actions_and_does_not_duplicate():
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    original = InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="admin:back")]])
    one = with_close_button(original)
    two = with_close_button(one)
    assert [[button.callback_data for button in row] for row in two.inline_keyboard] == [
        ["admin:back"], ["transient:close"],
    ]


@pytest.mark.asyncio
async def test_price_requests_coalesce_per_coin_and_refresh_after_ttl(monkeypatch):
    price_service._PRICE_CACHE.clear()
    price_service._PRICE_IN_FLIGHT.clear()
    current_time = [1000.0]
    monkeypatch.setattr(price_service.time, "time", lambda: current_time[0])
    fetch = AsyncMock(return_value={"bitcoin": {"usd": "42000", "usd_24h_change": "1.2"}})

    async def delayed(*args, **kwargs):
        await asyncio.sleep(0)
        return await fetch(*args, **kwargs)

    monkeypatch.setattr(price_service, "_get_with_retry", delayed)
    values = await asyncio.gather(*(price_service.get_coin_price("btc") for _ in range(5)))
    assert values == [(Decimal("42000"), Decimal("1.2"), "btc")] * 5
    assert fetch.await_count == 1
    current_time[0] = 1299.99
    await price_service.get_coin_price("btc")
    assert fetch.await_count == 1
    current_time[0] = 1301.0
    await price_service.get_coin_price("btc")
    assert fetch.await_count == 2


@pytest.mark.asyncio
async def test_manual_price_never_uses_silently_stale_provider_fallback(monkeypatch):
    price_service._PRICE_CACHE.clear()
    price_service._PRICE_IN_FLIGHT.clear()
    called = {}

    async def capture(_client, _url, _params, **kwargs):
        called.update(kwargs)
        return {"bitcoin": {"usd": "45000", "usd_24h_change": "0.5"}}

    monkeypatch.setattr(price_service, "_get_with_retry", capture)
    await price_service.get_coin_price("btc")
    assert called["allow_stale_price_fallback"] is False

@pytest.mark.asyncio
async def test_transient_bot_tracks_manual_output_but_not_automatic_output(monkeypatch):
    from telegram.ext import ExtBot

    from bot.handlers.transient import TransientBot, _active, sessions

    bot = TransientBot(token="123:TEST")
    key = (88811, 88820)
    generation = await sessions.begin(key, SimpleNamespace(delete_message=AsyncMock()))
    mock_send = AsyncMock(side_effect=[
        SimpleNamespace(message_id=700), SimpleNamespace(message_id=701)
    ])
    monkeypatch.setattr(ExtBot, "send_message", mock_send)
    context_token = _active.set((key, generation, asyncio.current_task()))
    try:
        await bot.send_message(key[0], "Manual screen")
    finally:
        _active.reset(context_token)
    await bot.send_message(key[0], "Automatic alert")

    assert sessions.is_active(*key, 700)
    assert not sessions.is_active(*key, 701)
    markup = mock_send.await_args_list[0].kwargs["reply_markup"]
    assert markup.inline_keyboard[-1][0].callback_data == "transient:close"
    assert "reply_markup" not in mock_send.await_args_list[1].kwargs


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("origin", "expected_back"),
    [("/settings", "transient:close"), ("/admin", "admin:back")],
)
async def test_admin_settings_navigation_remembers_entry_origin(
    monkeypatch, origin, expected_back
):
    from importlib import import_module

    from bot.handlers.transient import sessions

    admin_module = import_module("bot.handlers.admin")
    chat_id, user_id = 88831, 88832
    generation = await sessions.begin(
        (chat_id, user_id), SimpleNamespace(delete_message=AsyncMock()), origin=origin
    )
    sessions.add((chat_id, user_id), generation, 88840)
    query = SimpleNamespace(
        message=SimpleNamespace(chat_id=chat_id),
        from_user=SimpleNamespace(id=user_id),
        edit_message_text=AsyncMock(),
    )
    monkeypatch.setattr(admin_module, "handlers_module", lambda: SimpleNamespace(
        DB_ENABLED=False, DB_SESSION_LOCAL=None
    ))
    monkeypatch.setattr(admin_module, "get_state_alert_settings", lambda state: {
        "automatic_check_interval_seconds": 1800
    })
    monkeypatch.setattr(admin_module, "load_state", lambda: {})

    assert await admin_module.send_admin_callback_response(
        "admin:current", query, object()
    )
    markup = query.edit_message_text.await_args.kwargs["reply_markup"]
    assert markup.inline_keyboard[-1][0].callback_data == expected_back


@pytest.mark.asyncio
async def test_coingecko_429_sets_provider_backoff_without_ui_rate_limit(monkeypatch):
    from bot.services.price_service import CoinGeckoRateLimitError

    price_service._PRICE_CACHE.clear()
    price_service._PRICE_IN_FLIGHT.clear()
    price_service._PRICE_PROVIDER_BACKOFF_UNTIL.clear()
    call = AsyncMock(side_effect=CoinGeckoRateLimitError("429"))
    monkeypatch.setattr(price_service, "_get_with_retry", call)

    with pytest.raises(CoinGeckoRateLimitError):
        await price_service.get_coin_price("eth")
    with pytest.raises(CoinGeckoRateLimitError):
        await price_service.get_coin_price("eth")
    call.assert_awaited_once()
    price_service._PRICE_PROVIDER_BACKOFF_UNTIL.clear()
