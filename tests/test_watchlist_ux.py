from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from telegram.error import TimedOut

from bot.keyboards import build_price_keyboard
from bot.setup import setup_bot_commands
from bot.watchlist import (
    build_plan_message,
    build_subscribe_message,
    build_watchlist_message,
    build_watchlist_render,
    grant_premium_command,
    handle_watchlist_callback,
    myplan_command,
    revoke_premium_command,
)
from database import (
    Base,
    User,
    UserCoinSubscription,
    ensure_default_coin_subscriptions,
    grant_user_premium,
)


def make_user(active_until=None, frequency=21600, role="user"):
    return SimpleNamespace(
        role=role,
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
    text, rows = build_watchlist_message(
        make_user(),
        make_subscriptions(),
        datetime(2026, 5, 11, tzinfo=timezone.utc),
    )

    assert text.startswith("📡 Alert watchlist")
    assert "BTC alerts are free." in text
    assert "ETH, SOL, XRP, BNB, DOGE, ADA, TON, LINK, TRX" in text
    assert "ETH - Premium" not in text
    assert "Frequency: Every 4 hours" in text
    assert "Use /subscribe to upgrade." in text
    assert ("btc", True, True) in rows
    assert ("eth", False, False) in rows


def test_watchlist_free_user_can_have_btc_disabled_in_keyboard_state():
    _, rows = build_watchlist_message(
        make_user(),
        make_subscriptions(btc=False),
        datetime(2026, 5, 11, tzinfo=timezone.utc),
    )

    assert ("btc", False, True) in rows


def test_watchlist_premium_user_sees_enabled_non_btc_and_frequency():
    now = datetime(2026, 5, 11, tzinfo=timezone.utc)
    text, rows = build_watchlist_message(
        make_user(active_until=now + timedelta(days=1), frequency=21600),
        make_subscriptions(eth=True, sol=False),
        now,
    )

    assert "Select coins for automatic alerts." in text
    assert "Frequency: Every 6 hours" in text
    assert "Premium active until: 2026-05-12" in text
    assert ("eth", True, True) in rows
    assert ("sol", False, True) in rows


def test_watchlist_expired_user_sees_locked_but_saved_choices_are_not_deleted():
    now = datetime(2026, 5, 11, tzinfo=timezone.utc)
    text, rows = build_watchlist_message(
        make_user(active_until=now - timedelta(days=1), frequency=3600),
        make_subscriptions(eth=True),
        now,
    )

    assert "Your Premium expired on: 2026-05-10." in text
    assert "Your premium coin choices are saved, but locked until renewal." in text
    assert "Frequency: Every 4 hours for BTC" in text
    assert ("eth", True, False) in rows


def test_admin_role_alone_does_not_unlock_premium_coins():
    _, rows = build_watchlist_message(
        make_user(role="admin"),
        make_subscriptions(),
        datetime(2026, 5, 11, tzinfo=timezone.utc),
    )

    assert ("eth", False, False) in rows


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


def test_watchlist_buttons_use_icons_and_compact_layout():
    now = datetime(2026, 5, 11, tzinfo=timezone.utc)
    _, keyboard = build_watchlist_render(
        make_user(active_until=now + timedelta(days=1), frequency=21600),
        make_subscriptions(eth=True, sol=False),
        now,
    )
    rows = keyboard.inline_keyboard
    labels = [[button.text for button in row] for row in rows]

    assert labels[0] == ["✅ BTC", "✅ ETH", "⬜ SOL"]
    assert labels[1] == ["⬜ XRP", "⬜ BNB", "⬜ DOGE"]
    assert labels[2] == ["⬜ ADA", "⬜ TON", "⬜ LINK"]
    assert labels[3] == ["⬜ TRX"]
    assert labels[4] == ["⬜ 1h", "✅ 6h", "⬜ 24h"]
    assert all(len(row) <= 3 for row in labels)


def test_watchlist_buttons_show_locked_icons_for_free_user():
    _, keyboard = build_watchlist_render(
        make_user(),
        make_subscriptions(),
        datetime(2026, 5, 11, tzinfo=timezone.utc),
    )
    labels = [button.text for row in keyboard.inline_keyboard for button in row]

    assert labels[:4] == ["✅ BTC", "🔒 ETH", "🔒 SOL", "🔒 XRP"]
    assert "Enable" not in " ".join(labels)
    assert "Disable" not in " ".join(labels)
    assert "Locked" not in " ".join(labels)


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


@pytest.mark.asyncio
async def test_grant_premium_me_uses_current_admin_telegram_user_id(monkeypatch):
    replies = []

    class FakeMessage:
        async def reply_text(self, text, **kwargs):
            replies.append(text)

    async def fake_grant_user_premium(session, *, telegram_user_id, days):
        assert telegram_user_id == 278890596
        assert days == 30
        return SimpleNamespace(active_until=datetime(2026, 6, 10, tzinfo=timezone.utc))

    monkeypatch.setattr("bot.watchlist.sync_user_from_update", AsyncNoop())
    monkeypatch.setattr("bot.watchlist.is_admin_update", AsyncTrue())
    monkeypatch.setattr("bot.watchlist.DB_ENABLED", True)
    monkeypatch.setattr("bot.watchlist.DB_SESSION_LOCAL", lambda: SessionContext(None))
    monkeypatch.setattr("bot.watchlist.grant_user_premium", fake_grant_user_premium)
    update = SimpleNamespace(
        message=FakeMessage(),
        effective_user=SimpleNamespace(id=278890596),
    )

    await grant_premium_command(update, ["me", "30"])

    assert replies == [
        "Premium granted to Telegram user ID 278890596 until 2026-06-10."
    ]


@pytest.mark.asyncio
async def test_revoke_premium_me_uses_current_admin_telegram_user_id(monkeypatch):
    replies = []

    class FakeMessage:
        async def reply_text(self, text, **kwargs):
            replies.append(text)

    async def fake_revoke_user_premium(session, *, telegram_user_id):
        assert telegram_user_id == 278890596
        return SimpleNamespace(active_until=datetime(2026, 5, 11, tzinfo=timezone.utc))

    monkeypatch.setattr("bot.watchlist.sync_user_from_update", AsyncNoop())
    monkeypatch.setattr("bot.watchlist.is_admin_update", AsyncTrue())
    monkeypatch.setattr("bot.watchlist.DB_ENABLED", True)
    monkeypatch.setattr("bot.watchlist.DB_SESSION_LOCAL", lambda: SessionContext(None))
    monkeypatch.setattr("bot.watchlist.revoke_user_premium", fake_revoke_user_premium)
    update = SimpleNamespace(
        message=FakeMessage(),
        effective_user=SimpleNamespace(id=278890596),
    )

    await revoke_premium_command(update, ["me"])

    assert replies == [
        "Premium revoked for Telegram user ID 278890596. Saved coin choices were preserved."
    ]


class AsyncNoop:
    async def __call__(self, *args, **kwargs):
        return None


class AsyncFalse:
    async def __call__(self, *args, **kwargs):
        return False


class AsyncTrue:
    async def __call__(self, *args, **kwargs):
        return True


async def build_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    return engine, SessionLocal()


async def create_user(session, telegram_user_id=1001, role="user"):
    user = User(
        telegram_user_id=telegram_user_id,
        telegram_chat_id=2001,
        username="user",
        first_name="User",
        role=role,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


class SessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False


class FakeMessage:
    def __init__(self):
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append((text, kwargs))


class TimeoutMessage:
    async def reply_text(self, text, **kwargs):
        raise TimedOut("Timed out")


class FakeQuery:
    def __init__(self, telegram_user_id):
        self.from_user = SimpleNamespace(id=telegram_user_id)
        self.message = FakeMessage()
        self.answers = []
        self.edits = []

    async def answer(self, text=None, show_alert=None, **kwargs):
        self.answers.append((text, show_alert))

    async def edit_message_text(self, text, reply_markup=None, **kwargs):
        self.edits.append((text, reply_markup, kwargs))


@pytest.mark.asyncio
async def test_locked_coin_callback_does_not_send_new_message(monkeypatch):
    engine, session = await build_session()
    try:
        user = await create_user(session, telegram_user_id=7287293904)
        await ensure_default_coin_subscriptions(session, user_id=user.id)
        monkeypatch.setattr("bot.watchlist.DB_ENABLED", True)
        monkeypatch.setattr("bot.watchlist.DB_SESSION_LOCAL", lambda: SessionContext(session))
        query = FakeQuery(telegram_user_id=7287293904)

        handled = await handle_watchlist_callback(
            SimpleNamespace(callback_query=query),
            "watchlist:set:eth:true",
        )

        eth_row = await session.scalar(
            select(UserCoinSubscription).where(
                UserCoinSubscription.user_id == user.id,
                UserCoinSubscription.symbol == "eth",
            )
        )
        assert handled is True
        assert query.answers == [("Premium required. Use /subscribe.", False)]
        assert query.message.replies == []
        assert query.edits == []
        assert eth_row.is_enabled is False
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_unlocked_coin_callback_updates_db_and_edits_message(monkeypatch):
    engine, session = await build_session()
    try:
        user = await create_user(session, telegram_user_id=7287293904)
        await ensure_default_coin_subscriptions(session, user_id=user.id)
        await grant_user_premium(
            session,
            telegram_user_id=7287293904,
            days=30,
            now=datetime(2026, 5, 11, tzinfo=timezone.utc),
        )
        monkeypatch.setattr("bot.watchlist.DB_ENABLED", True)
        monkeypatch.setattr("bot.watchlist.DB_SESSION_LOCAL", lambda: SessionContext(session))
        query = FakeQuery(telegram_user_id=7287293904)

        handled = await handle_watchlist_callback(
            SimpleNamespace(callback_query=query),
            "watchlist:set:eth:true",
        )

        eth_row = await session.scalar(
            select(UserCoinSubscription).where(
                UserCoinSubscription.user_id == user.id,
                UserCoinSubscription.symbol == "eth",
            )
        )
        edited_labels = [
            button.text for row in query.edits[0][1].inline_keyboard for button in row
        ]
        assert handled is True
        assert query.answers == [("Updated.", None)]
        assert query.message.replies == []
        assert len(query.edits) == 1
        assert eth_row.is_enabled is True
        assert "✅ ETH" in edited_labels
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_frequency_callback_for_free_user_does_not_send_new_message(monkeypatch):
    engine, session = await build_session()
    try:
        await create_user(session, telegram_user_id=7287293904)
        monkeypatch.setattr("bot.watchlist.DB_ENABLED", True)
        monkeypatch.setattr("bot.watchlist.DB_SESSION_LOCAL", lambda: SessionContext(session))
        query = FakeQuery(telegram_user_id=7287293904)

        handled = await handle_watchlist_callback(
            SimpleNamespace(callback_query=query),
            "watchlist:frequency:3600",
        )

        assert handled is True
        assert query.answers == [("Premium required. Use /subscribe.", False)]
        assert query.message.replies == []
        assert query.edits == []
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_myplan_reply_timeout_is_handled(monkeypatch):
    async def fake_load_current_user(update):
        return make_user(), []

    monkeypatch.setattr("bot.watchlist._load_current_user", fake_load_current_user)
    update = SimpleNamespace(message=TimeoutMessage())

    await myplan_command(update)
