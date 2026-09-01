import inspect
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import bot.onboarding as onboarding
from bot.db.database import Base, PriceState, ProductEvent, User, UserCoinSubscription
from bot.handlers import callbacks as callback_handlers
from bot.handlers import common as common_handlers
from bot.handlers import user as user_handlers
from bot.onboarding import (
    build_instant_brief,
    handle_onboarding_callback,
    send_start_experience,
)


async def build_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    return engine, session_factory()


async def create_user(session) -> User:
    user = User(
        telegram_user_id=123456,
        telegram_chat_id=123456,
        username="user",
        first_name="User",
        role="user",
        is_active=True,
        onboarding_completed_at=None,
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
        self.chat = SimpleNamespace(type="private")
        self.chat_id = 123456
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append((text, kwargs))

    async def delete(self):
        return None


class FakeQuery:
    def __init__(self):
        self.from_user = SimpleNamespace(id=123456)
        self.message = FakeMessage()
        self.answers = []
        self.edits = []
        self.data = ""

    async def answer(self, text=None, **kwargs):
        self.answers.append((text, kwargs))

    async def edit_message_text(self, text, **kwargs):
        self.edits.append((text, kwargs))


@pytest.mark.asyncio
async def test_new_user_start_opens_inline_onboarding(monkeypatch):
    engine, session = await build_session()
    try:
        user = await create_user(session)
        monkeypatch.setattr("bot.onboarding.DB_ENABLED", True)
        monkeypatch.setattr("bot.onboarding.DB_SESSION_LOCAL", lambda: SessionContext(session))
        message = FakeMessage()
        update = SimpleNamespace(
            message=message, effective_user=SimpleNamespace(id=user.telegram_user_id)
        )

        handled = await send_start_experience(update)

        assert handled is True
        text, kwargs = message.replies[0]
        assert "Choose the coins" in text
        buttons = [button.text for row in kwargs["reply_markup"].inline_keyboard for button in row]
        assert any("BTC · Free" in button for button in buttons)
        assert any("🔒" in button and "ETH · Premium" in button for button in buttons)
        assert await session.scalar(
            select(ProductEvent).where(ProductEvent.event_name == "onboarding_started")
        )
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_existing_user_start_returns_to_dashboard_without_restarting_onboarding(monkeypatch):
    engine, session = await build_session()
    try:
        user = await create_user(session)
        user.onboarding_completed_at = datetime(2026, 9, 1, tzinfo=timezone.utc)
        await session.commit()
        monkeypatch.setattr("bot.onboarding.DB_ENABLED", True)
        monkeypatch.setattr("bot.onboarding.DB_SESSION_LOCAL", lambda: SessionContext(session))
        message = FakeMessage()
        update = SimpleNamespace(
            message=message,
            effective_user=SimpleNamespace(id=user.telegram_user_id),
        )

        assert await send_start_experience(update) is True

        assert "Welcome back" in message.replies[0][0]
        assert await session.scalar(
            select(ProductEvent).where(ProductEvent.event_name == "onboarding_started")
        ) is None
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_start_handler_routes_a_private_new_user_to_onboarding(monkeypatch):
    engine, session = await build_session()
    try:
        user = await create_user(session)
        monkeypatch.setattr("bot.onboarding.DB_ENABLED", True)
        monkeypatch.setattr("bot.onboarding.DB_SESSION_LOCAL", lambda: SessionContext(session))
        root = SimpleNamespace(
            sync_user_from_update=AsyncMock(),
            is_admin_user=AsyncMock(return_value=False),
            is_admin_update=AsyncMock(return_value=False),
        )
        monkeypatch.setattr(user_handlers, "handlers_module", lambda: root)
        monkeypatch.setattr(common_handlers, "handlers_module", lambda: root)
        message = FakeMessage()
        update = SimpleNamespace(
            message=message,
            effective_user=SimpleNamespace(id=user.telegram_user_id),
            effective_chat=message.chat,
        )

        await user_handlers.start(update, SimpleNamespace(args=[], user_data={}))

        assert root.sync_user_from_update.await_count == 1
        assert "Choose the coins" in message.replies[0][0]
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_callback_router_dispatches_onboarding_actions(monkeypatch):
    root = SimpleNamespace(
        sync_user_from_update=AsyncMock(),
        is_admin_user=AsyncMock(return_value=False),
        handle_watchlist_callback=AsyncMock(return_value=False),
        handle_onboarding_callback=AsyncMock(return_value=True),
    )
    monkeypatch.setattr(callback_handlers, "handlers_module", lambda: root)
    monkeypatch.setattr(common_handlers, "handlers_module", lambda: root)
    query = FakeQuery()
    query.data = "onboarding:toggle:btc"

    await callback_handlers.button_router(
        SimpleNamespace(callback_query=query, effective_user=query.from_user),
        SimpleNamespace(user_data={}),
    )

    root.handle_onboarding_callback.assert_awaited_once()
    assert query.answers == []


@pytest.mark.asyncio
async def test_onboarding_multiselect_persists_premium_intent_and_completes(monkeypatch):
    engine, session = await build_session()
    try:
        user = await create_user(session)
        monkeypatch.setattr("bot.onboarding.DB_ENABLED", True)
        monkeypatch.setattr("bot.onboarding.DB_SESSION_LOCAL", lambda: SessionContext(session))
        query = FakeQuery()
        update = SimpleNamespace(callback_query=query)

        assert await handle_onboarding_callback(update, "onboarding:toggle:eth") is True
        intent = await session.scalar(
            select(UserCoinSubscription).where(
                UserCoinSubscription.user_id == user.id,
                UserCoinSubscription.symbol == "eth",
            )
        )
        assert intent.is_enabled is True
        assert "ETH" in query.edits[-1][0]

        assert await handle_onboarding_callback(update, "onboarding:confirm") is True
        await session.refresh(user)
        assert user.onboarding_completed_at is not None
        assert "Saved Premium intent: ETH." in query.edits[-1][0]
        event_names = list(
            (await session.scalars(select(ProductEvent.event_name).order_by(ProductEvent.id))).all()
        )
        assert "coin_interest_selected" in event_names
        assert "onboarding_completed" in event_names
        assert "instant_brief_viewed" in event_names
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_instant_brief_uses_persisted_market_state_without_llm():
    engine, session = await build_session()
    try:
        user = await create_user(session)
        state = PriceState(
            symbol="BTC",
            last_price=100000.0,
            last_24h_change=2.5,
            last_checked_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        )
        subscription = UserCoinSubscription(user_id=user.id, symbol="btc", is_enabled=True)
        session.add_all([state, subscription])
        await session.commit()
        brief = await build_instant_brief(
            session,
            user=user,
            subscriptions=[subscription],
            now=datetime(2026, 9, 1, 1, tzinfo=timezone.utc),
        )

        assert "BTC: $100,000 · 24h +2.5%" in brief
        assert "Active monitoring: BTC." in brief
        source = inspect.getsource(onboarding)
        assert "bot.reports" not in source
        assert "bot.services.ai" not in source
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_instant_brief_hides_stale_market_price():
    engine, session = await build_session()
    try:
        user = await create_user(session)
        state = PriceState(
            symbol="BTC",
            last_price=100000.0,
            last_24h_change=2.5,
            last_checked_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        )
        subscription = UserCoinSubscription(user_id=user.id, symbol="btc", is_enabled=True)
        session.add_all([state, subscription])
        await session.commit()

        brief = await build_instant_brief(
            session,
            user=user,
            subscriptions=[subscription],
            now=datetime(2026, 9, 1, 7, tzinfo=timezone.utc),
        )

        assert "latest cached data is stale" in brief
        assert "$100,000" not in brief
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_instant_brief_handles_missing_market_state_safely():
    engine, session = await build_session()
    try:
        user = await create_user(session)
        subscription = UserCoinSubscription(user_id=user.id, symbol="btc", is_enabled=True)
        session.add(subscription)
        await session.commit()

        brief = await build_instant_brief(session, user=user, subscriptions=[subscription])

        assert "BTC: current data is warming up." in brief
        assert "Active monitoring: BTC." in brief
    finally:
        await session.close()
        await engine.dispose()
