from datetime import datetime, timedelta, timezone
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import bot.db.analytics as analytics
from bot.db.analytics import create_acquisition_link, list_active_acquisition_links
from bot.db.database import AcquisitionLink, Base
from bot.domain.attribution import (
    AttributionLinkToken,
    build_acquisition_telegram_url,
    parse_start_attribution,
    validate_acquisition_link_metadata,
)

admin_handlers = import_module("bot.handlers.admin")


async def build_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    return engine, session_factory()


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


def test_acquisition_metadata_accepts_configured_channels_and_rejects_untrusted_values():
    reddit = validate_acquisition_link_metadata(
        source="reddit",
        campaign="cryptotelegrambots",
        creative="launch-post",
        referrer_code="mod-a",
    )
    telegramdir = validate_acquisition_link_metadata(source="telegramdir")
    telegramads = validate_acquisition_link_metadata(
        source="telegramads",
        campaign="general-crypto",
        creative="ad01",
    )
    product_hunt = validate_acquisition_link_metadata(source="product-hunt")

    assert reddit.source == "reddit"
    assert reddit.referrer_code == "mod-a"
    assert telegramdir.campaign is None
    assert telegramads.campaign == "general-crypto"
    assert telegramads.creative == "ad01"
    assert product_hunt.source == "product-hunt"
    with pytest.raises(ValueError, match="Unsupported acquisition source"):
        validate_acquisition_link_metadata(source="arbitrary-source")
    with pytest.raises(ValueError, match="lowercase codes"):
        validate_acquisition_link_metadata(source="reddit", campaign="Crypto Telegram Bots")
    with pytest.raises(ValueError, match="lowercase codes"):
        validate_acquisition_link_metadata(source="reddit", referrer_code="123456789")


@pytest.mark.asyncio
async def test_create_acquisition_link_persists_valid_metadata_and_payload_is_compatible():
    engine, session = await build_session()
    try:
        link = await create_acquisition_link(
            session,
            source="telegramads",
            campaign="general-crypto",
            creative="ad01",
            referrer_code="mod-a",
        )

        assert link.source == "telegramads"
        assert link.campaign == "general-crypto"
        assert link.creative == "ad01"
        assert link.referrer_code == "mod-a"
        assert parse_start_attribution(f"a1_{link.link_code}") == AttributionLinkToken(
            link_code=link.link_code
        )
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_create_acquisition_link_retries_a_unique_code_collision(monkeypatch):
    engine, session = await build_session()
    try:
        collision_code = "a" * 32
        session.add(AcquisitionLink(link_code=collision_code, source="reddit", is_active=True))
        await session.commit()
        generated_codes = iter((collision_code, "b" * 32))
        monkeypatch.setattr(
            analytics,
            "generate_acquisition_link_code",
            lambda: next(generated_codes),
        )

        link = await create_acquisition_link(session, source="telegramdir")

        assert link.link_code == "b" * 32
        rows = list((await session.scalars(select(AcquisitionLink))).all())
        assert len(rows) == 2
    finally:
        await session.close()
        await engine.dispose()


def test_generated_telegram_url_has_the_supported_start_payload_format():
    url = build_acquisition_telegram_url(bot_username="CCWBot", link_code="a" * 32)

    assert url == f"https://t.me/CCWBot?start=a1_{'a' * 32}"
    assert parse_start_attribution(url.rsplit("=", maxsplit=1)[1]) == AttributionLinkToken(
        link_code="a" * 32
    )
    with pytest.raises(ValueError, match="username"):
        build_acquisition_telegram_url(bot_username="not valid", link_code="a" * 32)


@pytest.mark.asyncio
async def test_acquisition_link_command_creates_and_returns_a_production_url(monkeypatch):
    engine, session = await build_session()
    try:
        root = SimpleNamespace(
            is_admin_update=AsyncMock(return_value=True),
            DB_ENABLED=True,
            DB_SESSION_LOCAL=lambda: SessionContext(session),
        )
        message = FakeMessage()
        update = SimpleNamespace(message=message, effective_chat=SimpleNamespace(type="private"))
        context = SimpleNamespace(
            args=[
                "source=telegramads",
                "campaign=general-crypto",
                "creative=ad01",
                "referrer_code=mod-a",
            ],
            user_data={},
        )
        monkeypatch.setattr(admin_handlers, "handlers_module", lambda: root)
        monkeypatch.setattr(admin_handlers, "TELEGRAM_BOT_USERNAME", "CCWBot")

        await admin_handlers.acquisition_link.__wrapped__(update, context)

        text = message.replies[0][0]
        link = await session.scalar(select(AcquisitionLink))
        assert "Acquisition link created:" in text
        assert f"https://t.me/CCWBot?start=a1_{link.link_code}" in text
        assert link.source == "telegramads"
        assert link.campaign == "general-crypto"
        assert link.creative == "ad01"
        assert "mod-a" not in text
        assert parse_start_attribution(f"a1_{link.link_code}") is not None
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_non_admin_cannot_create_or_list_acquisition_links(monkeypatch):
    root = SimpleNamespace(is_admin_update=AsyncMock(return_value=False))
    message = FakeMessage()
    update = SimpleNamespace(message=message)
    monkeypatch.setattr(admin_handlers, "handlers_module", lambda: root)

    await admin_handlers.acquisition_link.__wrapped__(
        update,
        SimpleNamespace(args=["source=reddit"], user_data={}),
    )
    await admin_handlers.acquisition_links.__wrapped__(
        update,
        SimpleNamespace(args=[], user_data={}),
    )

    assert [reply[0] for reply in message.replies] == [
        "Sorry, only the bot admin can manage acquisition links.",
        "Sorry, only the bot admin can manage acquisition links.",
    ]


@pytest.mark.asyncio
async def test_admin_cannot_manage_acquisition_links_in_a_group(monkeypatch):
    root = SimpleNamespace(is_admin_update=AsyncMock(return_value=True))
    message = FakeMessage()
    update = SimpleNamespace(message=message, effective_chat=SimpleNamespace(type="group"))
    monkeypatch.setattr(admin_handlers, "handlers_module", lambda: root)

    await admin_handlers.acquisition_link.__wrapped__(
        update,
        SimpleNamespace(args=["source=reddit"], user_data={}),
    )
    await admin_handlers.acquisition_links.__wrapped__(
        update,
        SimpleNamespace(args=[], user_data={}),
    )

    assert [reply[0] for reply in message.replies] == [
        "Acquisition links may only be managed in a private admin chat.",
        "Acquisition links may only be managed in a private admin chat.",
    ]


@pytest.mark.asyncio
async def test_acquisition_link_requires_a_configured_public_bot_username(monkeypatch):
    root = SimpleNamespace(
        is_admin_update=AsyncMock(return_value=True),
        DB_ENABLED=True,
        DB_SESSION_LOCAL=object(),
    )
    message = FakeMessage()
    update = SimpleNamespace(message=message, effective_chat=SimpleNamespace(type="private"))
    monkeypatch.setattr(admin_handlers, "handlers_module", lambda: root)
    monkeypatch.setattr(admin_handlers, "TELEGRAM_BOT_USERNAME", "")

    await admin_handlers.acquisition_link.__wrapped__(
        update,
        SimpleNamespace(args=["source=reddit"], user_data={}),
    )

    assert message.replies == [("Telegram bot username is not configured correctly.", {})]


@pytest.mark.asyncio
async def test_list_active_acquisition_links_excludes_inactive_and_expired_rows():
    engine, session = await build_session()
    try:
        now = datetime(2026, 9, 2, tzinfo=timezone.utc)
        session.add_all(
            [
                AcquisitionLink(link_code="a" * 32, source="reddit", is_active=True),
                AcquisitionLink(link_code="b" * 32, source="reddit", is_active=False),
                AcquisitionLink(
                    link_code="c" * 32,
                    source="reddit",
                    is_active=True,
                    expires_at=now - timedelta(seconds=1),
                ),
            ]
        )
        await session.commit()

        links = await list_active_acquisition_links(session, now=now)

        assert [link.link_code for link in links] == ["a" * 32]
    finally:
        await session.close()
        await engine.dispose()
