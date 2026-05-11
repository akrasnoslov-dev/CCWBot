from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from bot.keyboards import build_price_keyboard
from bot.setup import setup_bot_commands
from bot.watchlist import (
    build_plan_message,
    build_subscribe_message,
    build_watchlist_message,
    grant_premium_command,
    revoke_premium_command,
)


def make_user(active_until=None, frequency=21600):
    return SimpleNamespace(
        alert_frequency_seconds=frequency,
        premium_subscription=SimpleNamespace(active_until=active_until)
        if active_until is not None
        else None,
    )


def make_subscriptions(**enabled_by_symbol):
    rows = []
    for symbol in ("btc", "eth", "sol", "xrp", "bnb", "doge", "ada", "ton", "link", "trx"):
        rows.append(
            SimpleNamespace(
                symbol=symbol,
                is_enabled=enabled_by_symbol.get(symbol, symbol == "btc"),
            )
        )
    return rows


def test_watchlist_free_user_sees_btc_available_and_premium_locked():
    text, _ = build_watchlist_message(
        make_user(),
        make_subscriptions(),
        datetime(2026, 5, 11, tzinfo=timezone.utc),
    )

    assert "[x] BTC" in text
    assert "[locked] ETH - Premium" in text
    assert "Frequency: Every 4 hours" in text
    assert "Use /subscribe to upgrade." in text


def test_watchlist_free_user_can_have_btc_disabled():
    text, _ = build_watchlist_message(
        make_user(),
        make_subscriptions(btc=False),
        datetime(2026, 5, 11, tzinfo=timezone.utc),
    )

    assert "[ ] BTC - Free" in text


def test_watchlist_premium_user_sees_enabled_non_btc_and_frequency():
    now = datetime(2026, 5, 11, tzinfo=timezone.utc)
    text, _ = build_watchlist_message(
        make_user(active_until=now + timedelta(days=1), frequency=21600),
        make_subscriptions(eth=True, sol=False),
        now,
    )

    assert "[x] ETH - Premium" in text
    assert "[ ] SOL - Premium" in text
    assert "Frequency: Every 6 hours" in text


def test_watchlist_expired_user_sees_locked_but_saved_choices_are_not_deleted():
    now = datetime(2026, 5, 11, tzinfo=timezone.utc)
    text, _ = build_watchlist_message(
        make_user(active_until=now - timedelta(days=1), frequency=3600),
        make_subscriptions(eth=True),
        now,
    )

    assert "[locked] ETH - Premium expired" in text
    assert "Your Premium expired on: 2026-05-10" in text
    assert "Frequency: Every 4 hours" in text


def test_plan_messages_for_free_premium_and_expired():
    now = datetime(2026, 5, 11, tzinfo=timezone.utc)
    assert "Plan: Free" in build_plan_message(make_user(), now)
    assert "Premium: not active" in build_plan_message(make_user(), now)
    assert "Plan: Premium" in build_plan_message(
        make_user(active_until=now + timedelta(days=1)),
        now,
    )
    expired = build_plan_message(make_user(active_until=now - timedelta(days=1)), now)
    assert "Premium expired on: 2026-05-10" in expired
    assert "Your premium coin choices are saved." in expired


def test_subscribe_placeholder_mentions_pr3_not_payment_flow():
    text = build_subscribe_message()

    assert "BTC alerts remain free." in text
    assert "Manual /price remains free for all supported coins." in text
    assert "Real Telegram Stars purchase will be implemented later." in text


def test_price_keyboard_uses_supported_top_10_without_usdt():
    keyboard = build_price_keyboard()
    labels = [button.text for row in keyboard.inline_keyboard for button in row]

    assert labels == ["BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "ADA", "TON", "LINK", "TRX"]
    assert "USDT" not in labels


@pytest.mark.asyncio
async def test_admin_commands_hidden_from_normal_menu(monkeypatch):
    calls = []

    class FakeBot:
        async def set_my_commands(self, commands, scope):
            calls.append((commands, scope))

    monkeypatch.setattr("bot.setup.TELEGRAM_ADMIN_USER_ID", 123)
    await setup_bot_commands(SimpleNamespace(bot=FakeBot()))

    default_commands = [command.command for command in calls[0][0]]
    admin_commands = [command.command for command in calls[1][0]]
    assert "grantpremium" not in default_commands
    assert "revokepremium" not in default_commands
    assert "userid" not in default_commands
    assert "grantpremium" in admin_commands
    assert "revokepremium" in admin_commands


@pytest.mark.asyncio
async def test_grant_and_revoke_premium_deny_non_admin(monkeypatch):
    replies = []

    class FakeMessage:
        async def reply_text(self, text, **kwargs):
            replies.append(text)

    update = SimpleNamespace(message=FakeMessage(), effective_user=SimpleNamespace(id=1001))
    monkeypatch.setattr("bot.watchlist.sync_user_from_update", AsyncNoop())
    monkeypatch.setattr("bot.watchlist.is_admin_update", AsyncFalse())

    await grant_premium_command(update, ["1002", "30"])
    await revoke_premium_command(update, ["1002"])

    assert replies == [
        "Sorry, only the bot admin can grant Premium.",
        "Sorry, only the bot admin can revoke Premium.",
    ]


class AsyncNoop:
    async def __call__(self, *args, **kwargs):
        return None


class AsyncFalse:
    async def __call__(self, *args, **kwargs):
        return False
