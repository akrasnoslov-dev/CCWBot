from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.db.analytics import (
    capture_first_touch_attribution,
    record_bot_started,
    record_product_event,
    resolve_start_attribution,
)
from bot.db.database import (
    AcquisitionLink,
    Base,
    Payment,
    ProductEvent,
    User,
    UserAcquisitionAttribution,
)
from bot.domain.attribution import AttributionLinkToken, parse_start_attribution


async def build_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    return engine, session_factory()


async def create_user(session, telegram_user_id: int = 123456) -> User:
    user = User(
        telegram_user_id=telegram_user_id,
        telegram_chat_id=telegram_user_id,
        username="user",
        first_name="User",
        role="user",
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def create_link(session, *, link_code: str = "creator-01") -> AcquisitionLink:
    link = AcquisitionLink(
        link_code=link_code,
        source="creator",
        campaign="launch",
        creative="banner-a",
        referrer_code="ref-9",
        is_active=True,
    )
    session.add(link)
    await session.commit()
    await session.refresh(link)
    return link


def test_start_attribution_accepts_only_opaque_compact_tokens():
    token = parse_start_attribution("a1_creator-01")

    assert token == AttributionLinkToken(link_code="creator-01")
    assert parse_start_attribution("v1_creator_launch_banner-a_ref-9") is None
    assert parse_start_attribution("a1_creator-01?utm=x") is None
    assert parse_start_attribution("x" * 65) is None
    assert parse_start_attribution(None) is None


@pytest.mark.asyncio
async def test_first_touch_attribution_is_resolved_server_side_and_immutable():
    engine, session = await build_session()
    try:
        user = await create_user(session)
        await create_link(session)
        second_link = await create_link(session, link_code="paid-link02")
        second_link.source = "paid"
        second_link.campaign = "other"
        await session.commit()

        first = await resolve_start_attribution(
            session,
            token=parse_start_attribution("a1_creator-01"),
        )
        second = await resolve_start_attribution(
            session,
            token=parse_start_attribution("a1_paid-link02"),
        )
        await record_bot_started(session, user_id=user.id, attribution=first)
        await record_bot_started(session, user_id=user.id, attribution=second)

        attribution = await session.scalar(
            select(UserAcquisitionAttribution).where(UserAcquisitionAttribution.user_id == user.id)
        )
        assert attribution.source == "creator"
        assert attribution.campaign == "launch"
        assert attribution.creative == "banner-a"
        assert attribution.referrer_code == "ref-9"
        starts = await session.scalar(
            select(func.count())
            .select_from(ProductEvent)
            .where(ProductEvent.event_name == "bot_started")
        )
        assert starts == 2
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_product_events_allow_only_typed_properties_and_are_idempotent():
    engine, session = await build_session()
    try:
        user = await create_user(session)
        occurred_at = datetime(2026, 9, 1, tzinfo=timezone.utc)
        event, created = await record_product_event(
            session,
            user_id=user.id,
            event_name="onboarding_completed",
            event_key="onboarding:1",
            selected_coin_count=2,
            occurred_at=occurred_at,
        )
        duplicate, duplicate_created = await record_product_event(
            session,
            user_id=user.id,
            event_name="onboarding_completed",
            event_key="onboarding:1",
            selected_coin_count=2,
        )
        await session.commit()

        assert created is True
        assert duplicate_created is False
        assert duplicate.id == event.id
        assert event.symbol is None
        assert event.selected_coin_count == 2
        with pytest.raises(ValueError, match="Unsupported product event"):
            await record_product_event(
                session,
                user_id=user.id,
                event_name="arbitrary_dictionary",
            )
        with pytest.raises(ValueError, match="Unsupported product event properties"):
            await record_product_event(
                session,
                user_id=user.id,
                event_name="bot_started",
                symbol="btc",
            )
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_payment_event_requires_the_internal_payment_owner():
    engine, session = await build_session()
    try:
        user = await create_user(session)
        other_user = await create_user(session, telegram_user_id=234567)
        payment = Payment(
            user_id=other_user.id,
            provider="telegram_stars",
            provider_payment_id="payment-1",
            amount=199,
            currency="XTR",
            payload="validated",
            status="paid",
        )
        session.add(payment)
        await session.commit()
        await session.refresh(payment)

        with pytest.raises(ValueError, match="does not belong"):
            await record_product_event(
                session,
                user_id=user.id,
                event_name="payment_succeeded",
                payment_id=payment.id,
            )
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_unattributed_existing_user_remains_usable():
    engine, session = await build_session()
    try:
        user = await create_user(session)

        row = await capture_first_touch_attribution(session, user_id=user.id, attribution=None)
        event, created = await record_product_event(
            session,
            user_id=user.id,
            event_name="bot_started",
        )
        await session.commit()

        assert row is None
        assert created is True
        assert event.user_id == user.id
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_start_handler_captures_a_valid_context_argument(monkeypatch):
    from bot.handlers import user as user_handlers

    engine, session = await build_session()
    try:
        user = await create_user(session)
        await create_link(session)
        monkeypatch.setattr(user_handlers, "DB_ENABLED", True)
        monkeypatch.setattr(user_handlers, "DB_SESSION_LOCAL", lambda: _SessionContext(session))
        monkeypatch.setattr(
            user_handlers,
            "handlers_module",
            lambda: SimpleNamespace(is_admin_update=AsyncMock(return_value=False)),
        )
        message = _FakeMessage()
        update = SimpleNamespace(
            message=message,
            effective_chat=SimpleNamespace(type="private"),
            effective_user=SimpleNamespace(id=user.telegram_user_id),
        )

        await user_handlers.start.__wrapped__(
            update,
            SimpleNamespace(args=["a1_creator-01"]),
        )

        attribution = await session.scalar(select(UserAcquisitionAttribution))
        assert attribution.source == "creator"
        assert "CCWBot" in message.text
    finally:
        await session.close()
        await engine.dispose()


class _SessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False


class _FakeMessage:
    text = ""

    async def reply_text(self, text, **kwargs):
        self.text = text
