import importlib
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.payments import (
    PREMIUM_SUBSCRIPTION_PERIOD_SECONDS,
    STARS_CURRENCY,
    _coerce_datetime,
    build_premium_invoice_payload,
    build_subscribe_message,
    send_subscribe_invoice,
    successful_payment_handler,
    validate_pre_checkout_query,
)
from bot.watchlist import build_plan_message, build_watchlist_message
from config import PREMIUM_MONTHLY_STARS
from database import (
    Base,
    Payment,
    User,
    activate_premium_from_telegram_stars_payment,
    ensure_default_coin_subscriptions,
    grant_user_premium,
    revoke_user_premium,
    set_user_coin_subscription,
)
from premium import is_user_premium_active


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


async def create_user(session, telegram_user_id=1001):
    user = User(
        telegram_user_id=telegram_user_id,
        telegram_chat_id=2001,
        username="user",
        first_name="User",
        role="user",
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
    def __init__(self, successful_payment=None):
        self.successful_payment = successful_payment
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append((text, kwargs))


class FakeBot:
    def __init__(self):
        self.invoice_calls = []

    async def create_invoice_link(self, **kwargs):
        self.invoice_calls.append(kwargs)
        return "https://t.me/test_bot?start=invoice"


class FakePreCheckoutQuery:
    def __init__(
        self,
        *,
        telegram_user_id=1001,
        payload=None,
        currency=STARS_CURRENCY,
        total_amount=PREMIUM_MONTHLY_STARS,
    ):
        self.from_user = SimpleNamespace(id=telegram_user_id)
        self.invoice_payload = payload or build_premium_invoice_payload(telegram_user_id)
        self.currency = currency
        self.total_amount = total_amount
        self.answers = []

    async def answer(self, **kwargs):
        self.answers.append(kwargs)


@pytest.mark.asyncio
async def test_subscribe_creates_recurring_stars_invoice_link(monkeypatch):
    engine, session = await build_session()
    try:
        await create_user(session)
        monkeypatch.setattr("bot.payments.sync_user_from_update", AsyncNoop())
        monkeypatch.setattr("bot.payments.DB_ENABLED", True)
        monkeypatch.setattr("bot.payments.DB_SESSION_LOCAL", lambda: SessionContext(session))
        bot = FakeBot()
        message = FakeMessage()

        await send_subscribe_invoice(
            SimpleNamespace(
                message=message,
                effective_user=SimpleNamespace(id=1001),
                effective_chat=SimpleNamespace(id=2001),
            ),
            SimpleNamespace(bot=bot),
        )

        invoice = bot.invoice_calls[0]
        assert invoice["currency"] == "XTR"
        assert invoice["prices"][0].amount == 199
        assert invoice["subscription_period"] == PREMIUM_SUBSCRIPTION_PERIOD_SECONDS
        assert invoice["payload"] == build_premium_invoice_payload(1001)
        assert "provider_token" not in invoice
        assert message.replies[0][0] == build_subscribe_message()
        assert message.replies[0][1]["reply_markup"].inline_keyboard[0][0].url.startswith(
            "https://t.me/"
        )
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_subscribe_creates_invoice_for_expired_premium_user(monkeypatch):
    engine, session = await build_session()
    try:
        user = await create_user(session)
        await grant_user_premium(
            session,
            telegram_user_id=user.telegram_user_id,
            days=1,
            now=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        monkeypatch.setattr("bot.payments.sync_user_from_update", AsyncNoop())
        monkeypatch.setattr("bot.payments.DB_ENABLED", True)
        monkeypatch.setattr("bot.payments.DB_SESSION_LOCAL", lambda: SessionContext(session))
        bot = FakeBot()
        message = FakeMessage()

        await send_subscribe_invoice(
            SimpleNamespace(
                message=message,
                effective_user=SimpleNamespace(id=user.telegram_user_id),
                effective_chat=SimpleNamespace(id=2001),
            ),
            SimpleNamespace(bot=bot),
        )

        assert len(bot.invoice_calls) == 1
        assert message.replies[0][0] == build_subscribe_message()
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_subscribe_creates_invoice_for_active_premium_user(monkeypatch):
    engine, session = await build_session()
    try:
        user = await create_user(session)
        await grant_user_premium(
            session,
            telegram_user_id=user.telegram_user_id,
            days=30,
            now=datetime.now(timezone.utc),
        )
        monkeypatch.setattr("bot.payments.sync_user_from_update", AsyncNoop())
        monkeypatch.setattr("bot.payments.DB_ENABLED", True)
        monkeypatch.setattr("bot.payments.DB_SESSION_LOCAL", lambda: SessionContext(session))
        bot = FakeBot()
        message = FakeMessage()

        await send_subscribe_invoice(
            SimpleNamespace(
                message=message,
                effective_user=SimpleNamespace(id=user.telegram_user_id),
                effective_chat=SimpleNamespace(id=2001),
            ),
            SimpleNamespace(bot=bot),
        )

        assert len(bot.invoice_calls) == 1
        assert "You already have paid access until" in message.replies[0][0]
        assert "Paying again adds another month to your paid access." in message.replies[0][0]
        assert message.replies[0][1]["reply_markup"].inline_keyboard[0][0].url.startswith(
            "https://t.me/"
        )
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_subscribe_allows_invoice_after_premium_revoke(monkeypatch):
    engine, session = await build_session()
    try:
        user = await create_user(session)
        await grant_user_premium(
            session,
            telegram_user_id=user.telegram_user_id,
            days=30,
            now=datetime.now(timezone.utc),
        )
        await revoke_user_premium(session, telegram_user_id=user.telegram_user_id)
        monkeypatch.setattr("bot.payments.sync_user_from_update", AsyncNoop())
        monkeypatch.setattr("bot.payments.DB_ENABLED", True)
        monkeypatch.setattr("bot.payments.DB_SESSION_LOCAL", lambda: SessionContext(session))
        bot = FakeBot()
        message = FakeMessage()

        await send_subscribe_invoice(
            SimpleNamespace(
                message=message,
                effective_user=SimpleNamespace(id=user.telegram_user_id),
                effective_chat=SimpleNamespace(id=2001),
            ),
            SimpleNamespace(bot=bot),
        )

        assert len(bot.invoice_calls) == 1
        assert message.replies[0][0] == build_subscribe_message()
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_pre_checkout_validation_accepts_valid_query(monkeypatch):
    engine, session = await build_session()
    try:
        await create_user(session)
        monkeypatch.setattr("bot.payments.DB_ENABLED", True)
        monkeypatch.setattr("bot.payments.DB_SESSION_LOCAL", lambda: SessionContext(session))

        result = await validate_pre_checkout_query(FakePreCheckoutQuery())

        assert result.ok is True
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("query", "message"),
    [
        (FakePreCheckoutQuery(payload="bad"), "Invalid payment request."),
        (FakePreCheckoutQuery(currency="USD"), "Invalid payment currency."),
        (FakePreCheckoutQuery(total_amount=198), "Invalid payment amount."),
    ],
)
async def test_pre_checkout_validation_rejects_invalid_payment(monkeypatch, query, message):
    engine, session = await build_session()
    try:
        await create_user(session)
        monkeypatch.setattr("bot.payments.DB_ENABLED", True)
        monkeypatch.setattr("bot.payments.DB_SESSION_LOCAL", lambda: SessionContext(session))

        result = await validate_pre_checkout_query(query)

        assert result.ok is False
        assert result.error_message == message
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_pre_checkout_validation_rejects_unknown_user(monkeypatch):
    engine, session = await build_session()
    try:
        monkeypatch.setattr("bot.payments.DB_ENABLED", True)
        monkeypatch.setattr("bot.payments.DB_SESSION_LOCAL", lambda: SessionContext(session))

        result = await validate_pre_checkout_query(FakePreCheckoutQuery())

        assert result.ok is False
        assert result.error_message == "Please send /start before subscribing."
        assert await session.scalar(select(func.count()).select_from(User)) == 0
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_successful_payment_activates_premium_and_unlocks_without_auto_enabling(monkeypatch):
    engine, session = await build_session()
    now = datetime(2026, 5, 11, tzinfo=timezone.utc)
    try:
        user = await create_user(session)
        await ensure_default_coin_subscriptions(session, user_id=user.id)
        await set_user_coin_subscription(session, user_id=user.id, symbol="eth", is_enabled=True)
        monkeypatch.setattr("bot.payments.DB_ENABLED", True)
        monkeypatch.setattr("bot.payments.DB_SESSION_LOCAL", lambda: SessionContext(session))

        message = FakeMessage(
            successful_payment=SimpleNamespace(
                currency="XTR",
                total_amount=199,
                invoice_payload=build_premium_invoice_payload(user.telegram_user_id),
                telegram_payment_charge_id="tg-charge-1",
                provider_payment_charge_id="provider-charge-1",
                is_recurring=True,
                is_first_recurring=True,
                subscription_expiration_date=datetime(2026, 6, 10, tzinfo=timezone.utc),
            )
        )
        await successful_payment_handler(
            SimpleNamespace(
                message=message,
                effective_user=SimpleNamespace(id=user.telegram_user_id),
            ),
            SimpleNamespace(),
        )

        reloaded = await session.get(User, user.id)
        await session.refresh(reloaded, ["premium_subscription", "coin_subscriptions"])
        assert message.replies == [
            ("Premium activated ✅\nUse /watchlist to choose your coins.", {})
        ]
        assert is_user_premium_active(reloaded.premium_subscription, now)
        plan_message = build_plan_message(reloaded, now)
        assert "Plan: Premium" in plan_message
        assert "Paid access until:" in plan_message
        subscriptions = await ensure_default_coin_subscriptions(session, user_id=user.id)
        _, rows = build_watchlist_message(reloaded, subscriptions, now)
        assert ("eth", True, True) in rows
        assert ("sol", False, True) in rows
        stored_payment = await session.scalar(select(Payment).limit(1))
        assert stored_payment.is_recurring is True
        assert stored_payment.is_first_recurring is True
        assert stored_payment.subscription_expiration_date == datetime(2026, 6, 10)
        assert stored_payment.provider_subscription_id is None
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_successful_payment_extends_from_max_active_until_and_is_idempotent():
    engine, session = await build_session()
    now = datetime(2026, 5, 11, tzinfo=timezone.utc)
    try:
        user = await create_user(session)

        first_payment, first_subscription, created = (
            await activate_premium_from_telegram_stars_payment(
                session,
                telegram_user_id=user.telegram_user_id,
                provider_payment_id="tg-charge-1",
                telegram_payment_charge_id="tg-charge-1",
                provider_payment_charge_id="provider-charge-1",
                amount=199,
                currency="XTR",
                payload=build_premium_invoice_payload(user.telegram_user_id),
                now=now,
            )
        )
        duplicate_payment, duplicate_subscription, duplicate_created = (
            await activate_premium_from_telegram_stars_payment(
                session,
                telegram_user_id=user.telegram_user_id,
                provider_payment_id="tg-charge-1",
                telegram_payment_charge_id="tg-charge-1",
                provider_payment_charge_id="provider-charge-1",
                amount=199,
                currency="XTR",
                payload=build_premium_invoice_payload(user.telegram_user_id),
                now=now + timedelta(days=1),
            )
        )
        second_payment, second_subscription, second_created = (
            await activate_premium_from_telegram_stars_payment(
                session,
                telegram_user_id=user.telegram_user_id,
                provider_payment_id="tg-charge-2",
                telegram_payment_charge_id="tg-charge-2",
                provider_payment_charge_id="provider-charge-2",
                amount=199,
                currency="XTR",
                payload=build_premium_invoice_payload(user.telegram_user_id),
                now=now + timedelta(days=1),
            )
        )

        assert created is True
        assert duplicate_created is False
        assert second_created is True
        assert first_payment.id == duplicate_payment.id
        assert first_subscription.id == duplicate_subscription.id == second_subscription.id
        assert first_subscription.active_until == now.replace(tzinfo=None) + timedelta(days=60)
        assert second_subscription.last_payment_id == str(second_payment.id)
        assert await session.scalar(select(func.count()).select_from(Payment)) == 2
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_successful_payment_metadata_accepts_unix_expiration_timestamp(monkeypatch):
    engine, session = await build_session()
    try:
        user = await create_user(session)
        monkeypatch.setattr("bot.payments.DB_ENABLED", True)
        monkeypatch.setattr("bot.payments.DB_SESSION_LOCAL", lambda: SessionContext(session))
        message = FakeMessage(
            successful_payment=SimpleNamespace(
                currency="XTR",
                total_amount=199,
                invoice_payload=build_premium_invoice_payload(user.telegram_user_id),
                telegram_payment_charge_id="tg-charge-ts",
                provider_payment_charge_id="provider-charge-ts",
                is_recurring=False,
                is_first_recurring=False,
                subscription_expiration_date=1_778_976_000,
            )
        )

        await successful_payment_handler(
            SimpleNamespace(
                message=message,
                effective_user=SimpleNamespace(id=user.telegram_user_id),
            ),
            SimpleNamespace(),
        )

        stored_payment = await session.scalar(select(Payment).limit(1))
        assert stored_payment.is_recurring is False
        assert stored_payment.is_first_recurring is False
        assert stored_payment.subscription_expiration_date == datetime(2026, 5, 17)
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_successful_payment_unknown_user_does_not_create_user(monkeypatch):
    engine, session = await build_session()
    try:
        monkeypatch.setattr("bot.payments.DB_ENABLED", True)
        monkeypatch.setattr("bot.payments.DB_SESSION_LOCAL", lambda: SessionContext(session))
        message = FakeMessage(
            successful_payment=SimpleNamespace(
                currency="XTR",
                total_amount=199,
                invoice_payload=build_premium_invoice_payload(404),
                telegram_payment_charge_id="tg-charge-404",
                provider_payment_charge_id="provider-charge-404",
            )
        )

        await successful_payment_handler(
            SimpleNamespace(message=message, effective_user=SimpleNamespace(id=404)),
            SimpleNamespace(),
        )

        assert await session.scalar(select(func.count()).select_from(User)) == 0
        assert await session.scalar(select(func.count()).select_from(Payment)) == 0
        assert "user record was not found" in message.replies[0][0]
    finally:
        await session.close()
        await engine.dispose()


class AsyncNoop:
    async def __call__(self, *args, **kwargs):
        return None


def test_premium_monthly_stars_default_config():
    assert PREMIUM_MONTHLY_STARS == 199


def test_premium_monthly_stars_invalid_config_falls_back(monkeypatch):
    import config

    monkeypatch.setenv("PREMIUM_MONTHLY_STARS", "not-a-number")
    reloaded = importlib.reload(config)

    assert reloaded.PREMIUM_MONTHLY_STARS == 199


def test_payment_schema_has_no_ton_wallet_storage():
    column_names = set(Payment.__table__.columns.keys())

    assert "wallet" not in " ".join(column_names).lower()
    assert "ton" not in " ".join(column_names).lower()


def test_payment_schema_has_recurring_metadata_columns():
    columns = Payment.__table__.columns

    assert columns["is_recurring"].nullable is True
    assert columns["is_first_recurring"].nullable is True
    assert columns["subscription_expiration_date"].nullable is True


def test_coerce_datetime_treats_zero_as_missing_metadata():
    assert _coerce_datetime(0) is None
