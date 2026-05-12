from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Update
from telegram.error import NetworkError, TimedOut
from telegram.ext import ContextTypes

from bot.permissions import sync_user_from_update
from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL, log
from config import PREMIUM_MONTHLY_STARS
from database import (
    TELEGRAM_STARS_PROVIDER,
    activate_premium_from_telegram_stars_payment,
    get_user_by_telegram_user_id,
)
from premium import is_user_premium_active
from supported_coins import premium_symbols_display

logger = logging.getLogger(__name__)

PREMIUM_SUBSCRIPTION_PERIOD_SECONDS = 2_592_000
PREMIUM_INVOICE_TITLE = "CCWBot Premium"
PREMIUM_INVOICE_DESCRIPTION = "Monthly Premium for automatic non-BTC crypto alerts."
PREMIUM_PAYLOAD_PREFIX = "ccwbot-premium-v1"
STARS_CURRENCY = "XTR"


@dataclass(frozen=True)
class PaymentValidationResult:
    ok: bool
    error_message: str | None = None


def build_premium_invoice_payload(telegram_user_id: int) -> str:
    return f"{PREMIUM_PAYLOAD_PREFIX}:u{int(telegram_user_id)}"


def validate_premium_invoice_payload(payload: str, telegram_user_id: int) -> bool:
    return payload == build_premium_invoice_payload(telegram_user_id)


def build_premium_prices(price_stars: int = PREMIUM_MONTHLY_STARS) -> list[LabeledPrice]:
    return [LabeledPrice("Premium monthly", int(price_stars))]


def build_subscribe_message(price_stars: int = PREMIUM_MONTHLY_STARS) -> str:
    return (
        "CCWBot Premium\n\n"
        f"Price: {price_stars} Stars / month.\n"
        "BTC alerts remain free.\n"
        "Manual /price remains free for all supported coins.\n"
        f"Premium unlocks automatic alerts for {premium_symbols_display()}.\n\n"
        "After payment, use /watchlist to choose your coins."
    )


def build_already_premium_message(active_until) -> str:
    if isinstance(active_until, datetime):
        active_until_text = active_until.date().isoformat()
    else:
        active_until_text = "your current expiry date"
    return (
        f"You already have Premium active until {active_until_text}.\n\n"
        "Manage or cancel recurring payments in Telegram Stars settings."
    )


def _get_payment_attr(payment: Any, name: str) -> Any:
    value = getattr(payment, name, None)
    if value is not None:
        return value
    api_kwargs = getattr(payment, "api_kwargs", None) or {}
    if isinstance(api_kwargs, dict):
        return api_kwargs.get(name)
    return None


def _coerce_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


async def _safe_reply_text(message, text: str, **kwargs) -> bool:
    try:
        await message.reply_text(text, **kwargs)
    except (TimedOut, NetworkError) as error:
        log(f"Telegram payment reply failed: {type(error).__name__}")
        return False
    return True


async def send_subscribe_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await sync_user_from_update(update)
    if not update.message or not update.effective_user:
        return
    if not (DB_ENABLED and DB_SESSION_LOCAL):
        await _safe_reply_text(update.message, "Premium payments are temporarily unavailable.")
        return

    async with DB_SESSION_LOCAL() as session:
        user = await get_user_by_telegram_user_id(
            session,
            update.effective_user.id,
            include_plan=True,
        )
        if user is not None and is_user_premium_active(user.premium_subscription):
            await _safe_reply_text(
                update.message,
                build_already_premium_message(user.premium_subscription.active_until),
            )
            return

    payload = build_premium_invoice_payload(update.effective_user.id)
    invoice_link = await context.bot.create_invoice_link(
        title=PREMIUM_INVOICE_TITLE,
        description=PREMIUM_INVOICE_DESCRIPTION,
        payload=payload,
        currency=STARS_CURRENCY,
        prices=build_premium_prices(),
        subscription_period=PREMIUM_SUBSCRIPTION_PERIOD_SECONDS,
    )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(f"Pay {PREMIUM_MONTHLY_STARS} Stars", url=invoice_link)]]
    )
    await _safe_reply_text(
        update.message,
        build_subscribe_message(),
        reply_markup=keyboard,
    )


async def validate_pre_checkout_query(query) -> PaymentValidationResult:
    if not query or not query.from_user:
        return PaymentValidationResult(False, "Payment could not be validated.")
    if not validate_premium_invoice_payload(query.invoice_payload, query.from_user.id):
        return PaymentValidationResult(False, "Invalid payment request.")
    if query.currency != STARS_CURRENCY:
        return PaymentValidationResult(False, "Invalid payment currency.")
    if int(query.total_amount) != int(PREMIUM_MONTHLY_STARS):
        return PaymentValidationResult(False, "Invalid payment amount.")
    if not (DB_ENABLED and DB_SESSION_LOCAL):
        return PaymentValidationResult(False, "Premium payments are temporarily unavailable.")

    async with DB_SESSION_LOCAL() as session:
        user = await get_user_by_telegram_user_id(session, query.from_user.id)
        if user is None:
            return PaymentValidationResult(False, "Please send /start before subscribing.")

    return PaymentValidationResult(True)


async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.pre_checkout_query
    result = await validate_pre_checkout_query(query)
    if result.ok:
        await query.answer(ok=True)
        return
    await query.answer(ok=False, error_message=result.error_message or "Payment rejected.")


async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    payment = getattr(message, "successful_payment", None) if message else None
    telegram_user = update.effective_user
    if not message or not payment or not telegram_user:
        return
    if not (DB_ENABLED and DB_SESSION_LOCAL):
        await _safe_reply_text(message, "Premium payment was received, but storage is unavailable.")
        logger.warning("Telegram Stars payment received while database is unavailable.")
        return
    if not validate_premium_invoice_payload(payment.invoice_payload, telegram_user.id):
        await _safe_reply_text(message, "Payment could not be validated. Please contact the admin.")
        logger.warning("Rejected Telegram Stars successful_payment with invalid payload.")
        return
    if payment.currency != STARS_CURRENCY or int(payment.total_amount) != int(
        PREMIUM_MONTHLY_STARS
    ):
        await _safe_reply_text(message, "Payment could not be validated. Please contact the admin.")
        logger.warning(
            "Rejected Telegram Stars successful_payment with invalid amount or currency."
        )
        return

    async with DB_SESSION_LOCAL() as session:
        try:
            _, _, created = await activate_premium_from_telegram_stars_payment(
                session,
                telegram_user_id=telegram_user.id,
                provider_payment_id=payment.telegram_payment_charge_id,
                telegram_payment_charge_id=payment.telegram_payment_charge_id,
                provider_payment_charge_id=payment.provider_payment_charge_id,
                amount=payment.total_amount,
                currency=payment.currency,
                payload=payment.invoice_payload,
                provider_subscription_id=_get_payment_attr(payment, "provider_subscription_id"),
                is_recurring=_get_payment_attr(payment, "is_recurring"),
                is_first_recurring=_get_payment_attr(payment, "is_first_recurring"),
                subscription_expiration_date=_coerce_datetime(
                    _get_payment_attr(payment, "subscription_expiration_date")
                ),
            )
        except ValueError:
            logger.warning(
                "Telegram Stars payment received for unknown telegram_user_id=%s.",
                telegram_user.id,
            )
            await _safe_reply_text(
                message,
                "Payment received, but your user record was not found. Please contact the admin.",
            )
            return

    if created:
        log(
            "Processed Telegram Stars Premium payment "
            f"for telegram_user_id={telegram_user.id} provider={TELEGRAM_STARS_PROVIDER}."
        )
    else:
        log(
            "Ignored duplicate Telegram Stars Premium payment "
            f"for telegram_user_id={telegram_user.id}."
        )
    await _safe_reply_text(message, "Premium activated ✅\nUse /watchlist to choose your coins.")
