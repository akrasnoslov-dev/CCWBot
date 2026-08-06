"""Database infrastructure for optional PostgreSQL runtime storage."""

from __future__ import annotations

import asyncio
import importlib
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)

TELEGRAM_STARS_PROVIDER = "telegram_stars"
PREMIUM_PAYMENT_STATUS_PAID = "paid"
PREMIUM_PAYMENT_PERIOD_DAYS = 30


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


def utc_now() -> datetime:
    """Return timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def _collapse_whitespace(value: str) -> str:
    """Normalize repeated spaces so keys stay stable across feed formatting."""
    return " ".join(value.strip().split())


def _normalize_news_link(link: str) -> str:
    """Return a stable URL string for news identity checks."""
    parsed = urlsplit(link.strip())
    query_params = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
    ]
    normalized_path = parsed.path.rstrip("/") or parsed.path
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            normalized_path,
            urlencode(sorted(query_params)),
            "",
        )
    )


def make_news_key(news_item: dict) -> str:
    """Build a stable key for a news item.

    Links are preferred because RSS titles can change slightly. The normalized
    value is hashed to keep the key short enough for the database index.
    """
    link = _collapse_whitespace(str(news_item.get("link") or ""))
    if link:
        normalized = _normalize_news_link(link)
        return f"link:{sha256(normalized.encode('utf-8')).hexdigest()}"

    source = _collapse_whitespace(str(news_item.get("source") or "")).lower()
    title = _collapse_whitespace(str(news_item.get("title") or "")).lower()
    if title:
        fallback_identity = f"{source}:{title}" if source else title
        return f"source_title:{sha256(fallback_identity.encode('utf-8')).hexdigest()}"

    return ""


def normalize_stored_severity(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    normalized = {
        "info": "low",
        "watch": "medium",
        "moderate": "medium",
        "critical": "extreme",
    }.get(normalized, normalized)
    if normalized not in {"low", "medium", "high", "extreme"}:
        return "low"
    return normalized


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("telegram_user_id", name="uq_users_telegram_user_id"),
        {"comment": "Telegram users known to the bot and their delivery profile."},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="Internal user row id.")
    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        index=True,
        comment="Telegram user id that identifies the person using the bot.",
    )
    telegram_chat_id: Mapped[int] = mapped_column(
        BigInteger,
        index=True,
        comment="Telegram chat id where the bot sends messages for this user.",
    )
    username: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Latest Telegram username seen for the user."
    )
    first_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Latest Telegram first name seen for the user."
    )
    role: Mapped[str] = mapped_column(
        String(64), default="user", comment="Bot authorization role such as user or admin."
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="Whether the user may receive automatic bot messages."
    )
    bot_blocked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether Telegram reported that this user blocked the bot.",
    )
    blocked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When Telegram first reported that this user blocked the bot.",
    )
    alert_frequency_seconds: Mapped[int] = mapped_column(
        Integer, default=14400, comment="User's selected minimum interval between alert deliveries."
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, comment="When this user row was created."
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        comment="When this user row was last updated.",
    )

    settings: Mapped[list[UserSettings]] = relationship(back_populates="user")
    coin_subscriptions: Mapped[list[UserCoinSubscription]] = relationship(back_populates="user")
    premium_subscription: Mapped[UserPremiumSubscription | None] = relationship(
        back_populates="user", uselist=False
    )
    payments: Mapped[list[Payment]] = relationship(back_populates="user")


class UserSettings(Base):
    __tablename__ = "user_settings"
    __table_args__ = {"comment": "Legacy per-user alert settings retained for compatibility."}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="Internal settings row id.")
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True, comment="User these legacy settings belong to."
    )
    price_move_alert_percent: Mapped[float] = mapped_column(
        Float, comment="Legacy per-user price movement threshold percent."
    )
    automatic_check_interval_seconds: Mapped[int] = mapped_column(
        Integer, comment="Legacy per-user automatic price check interval in seconds."
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, comment="When this settings row was created."
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        comment="When this settings row was last updated.",
    )

    user: Mapped[User] = relationship(back_populates="settings")


class UserCoinSubscription(Base):
    __tablename__ = "user_coin_subscriptions"
    __table_args__ = (
        UniqueConstraint("user_id", "symbol", name="uq_user_coin_subscriptions_user_symbol"),
        CheckConstraint("symbol = lower(symbol)", name="ck_user_coin_subscriptions_symbol_lower"),
        {"comment": "Per-user watchlist choices for automatic coin alerts."},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="Internal watchlist row id.")
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True, comment="User who owns this coin alert choice."
    )
    symbol: Mapped[str] = mapped_column(
        String(32), index=True, comment="Lowercase coin symbol controlled by this watchlist row."
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="Whether automatic alerts are enabled for this coin."
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, comment="When this watchlist row was created."
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        comment="When this watchlist row was last updated.",
    )

    user: Mapped[User] = relationship(back_populates="coin_subscriptions")


class UserPremiumSubscription(Base):
    __tablename__ = "user_premium_subscriptions"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_premium_subscriptions_user_id"),
        {"comment": "Source of truth for each user's bot Premium entitlement."},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="Internal Premium row id.")
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True, comment="User whose Premium entitlement this records."
    )
    plan: Mapped[str] = mapped_column(
        String(64), default="premium", comment="Premium plan name granted to the user."
    )
    status: Mapped[str] = mapped_column(
        String(64),
        default="inactive",
        index=True,
        comment="Current Premium lifecycle status for operator visibility.",
    )
    active_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Source of truth for bot Premium access; active only while this is in the future.",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When Premium access first started."
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When Premium access was revoked or ended."
    )
    provider: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="Payment or grant source that last set this entitlement."
    )
    provider_subscription_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Provider subscription identifier when one is supplied."
    )
    last_payment_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Latest provider payment id used to extend Premium."
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, comment="When this Premium row was created."
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        comment="When this Premium row was last updated.",
    )

    user: Mapped[User] = relationship(back_populates="premium_subscription")


class UserSymbolAlertState(Base):
    __tablename__ = "user_symbol_alert_state"
    __table_args__ = (
        UniqueConstraint("user_id", "symbol", name="uq_user_symbol_alert_state_user_symbol"),
        CheckConstraint("symbol = lower(symbol)", name="ck_user_symbol_alert_state_symbol_lower"),
        {"comment": "Per-user per-symbol alert timestamps used by automatic monitoring."},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="Internal state row id.")
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True, comment="User this per-symbol alert state belongs to."
    )
    symbol: Mapped[str] = mapped_column(
        String(32), index=True, comment="Lowercase coin symbol for this alert state."
    )
    last_market_update_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When a Market Update was last successfully sent for this user and symbol.",
    )
    last_important_alert_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When an Important Alert was last successfully sent for this user and symbol.",
    )
    last_critical_alert_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When a Critical Alert was last successfully sent for this user and symbol.",
    )
    last_notification_type: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="Latest user-facing notification type sent for this user and symbol.",
    )
    last_notification_severity: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        comment="Latest normalized notification severity for this user and symbol.",
    )
    last_notification_direction: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        comment="Latest notification direction for this user and symbol.",
    )
    last_cumulative_movement_percent: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Latest cumulative movement percent stored for suppression decisions.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, comment="When this state row was created."
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        comment="When this state row was last updated.",
    )


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("provider", "provider_payment_id", name="uq_payments_provider_payment_id"),
        {"comment": "Payment events processed for Premium entitlement activation."},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="Internal payment row id.")
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
        comment="User whose Premium access this payment affects.",
    )
    provider: Mapped[str] = mapped_column(
        String(64), index=True, comment="Payment provider namespace, such as telegram_stars."
    )
    provider_payment_id: Mapped[str] = mapped_column(
        String(255),
        comment=(
            "Bot idempotency key for this provider payment; Telegram Stars uses the Telegram "
            "charge id."
        ),
    )
    provider_subscription_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Provider subscription id if Telegram supplies one."
    )
    telegram_payment_charge_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Telegram's own charge id from successful_payment."
    )
    provider_payment_charge_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Underlying payment provider charge id passed through by Telegram.",
    )
    is_recurring: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        comment="Telegram metadata indicating whether the payment is recurring.",
    )
    is_first_recurring: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        comment="Telegram metadata indicating the first payment in a recurring sequence.",
    )
    subscription_expiration_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment=(
            "Provider/Telegram subscription metadata; not the source of truth for Premium access."
        ),
    )
    amount: Mapped[int] = mapped_column(
        Integer, comment="Payment amount in the provider currency unit."
    )
    currency: Mapped[str] = mapped_column(
        String(16), index=True, comment="Payment currency code received from Telegram."
    )
    payload: Mapped[str] = mapped_column(
        String(255),
        index=True,
        comment="Validated invoice payload tying payment to a Telegram user.",
    )
    status: Mapped[str] = mapped_column(
        String(64),
        default=PREMIUM_PAYMENT_STATUS_PAID,
        index=True,
        comment="Stored processing status for this payment event.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, comment="When this payment row was created."
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        comment="When this payment row was last updated.",
    )

    user: Mapped[User] = relationship(back_populates="payments")


class AppSettings(Base):
    __tablename__ = "app_settings"
    __table_args__ = {"comment": "Global bot settings controlled by admins."}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="Internal settings row id.")
    btc_alert_threshold_percent: Mapped[float] = mapped_column(
        Float, comment="Global BTC movement percent that triggers automatic alerts."
    )
    major_movement_threshold_percent: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        comment="Admin-controlled movement percent threshold for BTC and ETH alerts.",
    )
    alt_movement_threshold_percent: Mapped[float] = mapped_column(
        Float,
        default=2.0,
        comment="Admin-controlled movement percent threshold for non-BTC and non-ETH alerts.",
    )
    major_24h_medium_threshold_percent: Mapped[float] = mapped_column(
        Float,
        default=3.0,
        comment="Admin-controlled 24 hour medium trend threshold for BTC and ETH alerts.",
    )
    major_24h_high_threshold_percent: Mapped[float] = mapped_column(
        Float,
        default=5.0,
        comment="Admin-controlled 24 hour high trend threshold for BTC and ETH alerts.",
    )
    alt_24h_medium_threshold_percent: Mapped[float] = mapped_column(
        Float,
        default=5.0,
        comment="Admin-controlled 24 hour medium trend threshold for altcoin alerts.",
    )
    alt_24h_high_threshold_percent: Mapped[float] = mapped_column(
        Float,
        default=8.0,
        comment="Admin-controlled 24 hour high trend threshold for altcoin alerts.",
    )
    automatic_check_interval_seconds: Mapped[int] = mapped_column(
        Integer, comment="Global automatic market check interval in seconds."
    )
    error_file_logging_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether admins enabled persistent WARNING and ERROR file logging.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        comment="When this global settings row was created.",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        comment="When this global settings row was last updated.",
    )


class PriceState(Base):
    __tablename__ = "price_state"
    __table_args__ = (
        UniqueConstraint("symbol", name="uq_price_state_symbol"),
        {"comment": "Latest stored market snapshot used to detect price movements."},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, comment="Internal price state row id."
    )
    symbol: Mapped[str] = mapped_column(
        String(32), index=True, comment="Uppercase coin symbol for this market state."
    )
    last_price: Mapped[float] = mapped_column(
        Float, comment="Most recent market price stored for movement detection."
    )
    last_24h_change: Mapped[float] = mapped_column(
        Float, comment="Most recent 24 hour percentage change from market data."
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When market data was last checked."
    )
    last_alert_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When an automatic alert was last sent."
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        comment="When this market state row was last updated.",
    )


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"
    __table_args__ = (
        Index("ix_price_snapshots_symbol_checked_at", "symbol", "checked_at"),
        {"comment": "Historical market snapshots used for user-frequency alert windows."},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, comment="Internal price snapshot row id."
    )
    symbol: Mapped[str] = mapped_column(
        String(32), index=True, comment="Uppercase coin symbol for this market snapshot."
    )
    price: Mapped[float] = mapped_column(
        Float, comment="Market price captured at this snapshot time."
    )
    change_24h: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="24 hour percentage change captured with this snapshot."
    )
    change_7d: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="7 day percentage change captured with this snapshot."
    )
    source: Mapped[str] = mapped_column(
        String(64), default="coingecko", comment="Market data provider for this snapshot."
    )
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, comment="When this market snapshot was captured."
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, comment="When this snapshot row was created."
    )


class SeenNews(Base):
    __tablename__ = "seen_news"
    __table_args__ = {"comment": "RSS/news items already processed for deduplication."}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="Internal news row id.")
    news_key: Mapped[str] = mapped_column(
        String(500), unique=True, index=True, comment="Stable deduplication key for the news item."
    )
    title: Mapped[str] = mapped_column(
        String(1000), comment="News title shown or analyzed by the bot."
    )
    link: Mapped[str] = mapped_column(String(2000), comment="Canonical link for the news item.")
    source: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Publisher or feed source for the news item."
    )
    seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, comment="When the news item was first stored."
    )


class NewsItem(Base):
    __tablename__ = "news_items"
    __table_args__ = (
        UniqueConstraint("news_key", name="uq_news_items_news_key"),
        Index("ix_news_items_published_at", "published_at"),
        Index("ix_news_items_primary_symbol", "primary_symbol"),
        Index("ix_news_items_category", "category"),
        Index("ix_news_items_impact_level", "impact_level"),
        Index("ix_news_items_dedup_group_id", "dedup_group_id"),
        Index("ix_news_items_llm_status", "llm_status"),
        {"comment": "Structured RSS news intelligence cached before alert selection."},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, comment="Internal structured news row id."
    )
    news_key: Mapped[str] = mapped_column(
        String(500), index=True, comment="Stable news identity compatible with seen_news keys."
    )
    title: Mapped[str] = mapped_column(
        String(1000), comment="Normalized RSS title for this news item."
    )
    source: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Normalized publisher or feed source."
    )
    url: Mapped[str] = mapped_column(
        String(2000), default="", comment="Normalized article URL from RSS metadata."
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Publication timestamp from RSS metadata."
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, comment="When this item was last fetched."
    )
    raw_summary: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Compact RSS summary or description before LLM analysis."
    )
    llm_summary: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Validated short user-facing summary returned by the LLM."
    )
    llm_raw_response: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Raw compact JSON response returned by the news LLM."
    )
    related_symbols: Mapped[list | None] = mapped_column(
        JSON, nullable=True, comment="Lowercase supported symbols related to this news item."
    )
    primary_symbol: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        comment="Primary lowercase supported symbol selected for the item.",
    )
    category: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="Validated news category such as market or regulation."
    )
    impact_score: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Validated impact score from 0 to 100."
    )
    impact_level: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="Validated impact level such as low or high."
    )
    relevance_score: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Validated relevance score from 0 to 100."
    )
    dedup_group_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="Stable group id for duplicate or similar news items."
    )
    is_duplicate: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="Whether this item duplicates a previously processed item."
    )
    is_noise: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="Whether this item is low-quality or not useful context."
    )
    is_alert_worthy: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether intelligence considers the item alert-worthy later.",
    )
    llm_provider: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="LLM provider used for news intelligence."
    )
    llm_model: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="LLM model used for news intelligence."
    )
    llm_input_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="SHA-256 hash of the compact LLM input payload."
    )
    llm_status: Mapped[str] = mapped_column(
        String(64),
        default="pending",
        comment="News intelligence status such as success or skipped.",
    )
    llm_error: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Sanitized news intelligence error message, if any."
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        comment="When this structured news row was created.",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        comment="When this structured news row was last updated.",
    )


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "symbol",
            "market_event_id",
            name="uq_alerts_user_symbol_market_event",
        ),
        Index(
            "uq_alerts_user_symbol_type_heartbeat",
            "user_id",
            "symbol",
            "alert_type",
            "market_heartbeat_id",
            unique=True,
            postgresql_where=Column("market_heartbeat_id").isnot(None),
            sqlite_where=Column("market_heartbeat_id").isnot(None),
        ),
        {"comment": "One delivery record per recipient for a market alert."},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, comment="Internal alert delivery row id."
    )
    symbol: Mapped[str] = mapped_column(
        String(32), index=True, comment="Uppercase coin symbol for this delivered alert."
    )
    alert_type: Mapped[str] = mapped_column(
        String(64), index=True, comment="Alert category such as price movement."
    )
    message: Mapped[str] = mapped_column(Text, comment="Sanitized Telegram message sent or queued.")
    sent_to_chat_id: Mapped[int] = mapped_column(
        BigInteger, index=True, comment="Telegram chat id targeted by this delivery."
    )
    market_event_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Market event this delivery belongs to."
    )
    market_heartbeat_id: Mapped[int | None] = mapped_column(
        ForeignKey("market_heartbeats.id", name="fk_alerts_market_heartbeat_id"),
        nullable=True,
        comment="Market heartbeat this delivery belongs to when the alert is a heartbeat.",
    )
    event_ai_analysis_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="AI analysis reused for this delivery."
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Recipient user row for this delivery."
    )
    status: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="Delivery state such as pending, sent, or failed."
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Failure detail for a failed delivery, if any."
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Number of Telegram delivery attempts already made for this alert.",
    )
    last_error: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Most recent Telegram delivery error for this alert."
    )
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the next Telegram delivery retry is due, if retryable.",
    )
    final_failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When Telegram delivery retries were exhausted or marked permanent.",
    )
    trigger_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Concise reason that triggered this delivered alert."
    )
    trigger_source: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="Machine-readable signal source for this alert."
    )
    numeric_context: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="JSON numeric market context used for this alert decision."
    )
    thresholds_used: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="JSON alert thresholds used for this alert decision."
    )
    llm_severity: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="Severity selected or accepted for this alert."
    )
    llm_reasoning_summary: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Short reasoning summary from the LLM or backend fallback."
    )
    fallback_mode: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether this delivery used a deterministic fallback instead of AI analysis.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, comment="When this delivery row was created."
    )


class AlertDeliveryOutcome(Base):
    __tablename__ = "alert_delivery_outcomes"
    __table_args__ = (
        Index("ix_alert_delivery_outcomes_event_status", "market_event_id", "status"),
        {
            "comment": (
                "Queryable alert decision outcome for a market event, recipient, or "
                "event-level non-delivery reason."
            )
        },
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, comment="Internal alert delivery outcome row id."
    )
    symbol: Mapped[str] = mapped_column(
        String(32), index=True, comment="Uppercase coin symbol for this alert outcome."
    )
    alert_type: Mapped[str] = mapped_column(
        String(64), index=True, comment="Alert category this outcome belongs to."
    )
    market_event_id: Mapped[int | None] = mapped_column(
        ForeignKey("market_events.id"),
        nullable=True,
        index=True,
        comment="Market event this outcome explains, when one exists.",
    )
    event_ai_analysis_id: Mapped[int | None] = mapped_column(
        ForeignKey("event_ai_analyses.id"),
        nullable=True,
        index=True,
        comment="AI analysis this outcome explains, when one exists.",
    )
    alert_id: Mapped[int | None] = mapped_column(
        ForeignKey("alerts.id"),
        nullable=True,
        index=True,
        comment="Delivery row this outcome summarizes, when Telegram delivery was attempted.",
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
        index=True,
        comment="Recipient user considered for this alert outcome, if recipient-specific.",
    )
    sent_to_chat_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        index=True,
        comment="Telegram chat id considered for this outcome, when available.",
    )
    status: Mapped[str] = mapped_column(
        String(64),
        index=True,
        comment="Queryable outcome status such as delivered, filtered, suppressed, or failed.",
    )
    reason_code: Mapped[str] = mapped_column(
        String(64), index=True, comment="Machine-readable reason code for this outcome."
    )
    recipient_considered: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether a concrete recipient was evaluated for this alert.",
    )
    recipient_eligible: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        comment="Whether the considered recipient was eligible for Telegram delivery.",
    )
    trigger_source: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="Machine-readable signal source for this outcome."
    )
    event_instance_key: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Stable idempotency key for the market event."
    )
    semantic_family: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="Canonical semantic family used for suppression."
    )
    decision_stage: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="Decision stage that produced this operator-facing outcome.",
    )
    decision_reason: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="Machine-readable event alert decision reason for operator reports.",
    )
    previous_alert_id: Mapped[int | None] = mapped_column(
        ForeignKey("alerts.id"),
        nullable=True,
        index=True,
        comment="Previous alert row considered for repeat or cooldown decisions.",
    )
    context_fingerprint: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
        comment="Safe hash of the sanitized decision context used for observability.",
    )
    detail: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Sanitized secondary diagnostic detail for operators."
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, comment="When this outcome row was created."
    )


class MarketEvent(Base):
    __tablename__ = "market_events"
    __table_args__ = (
        UniqueConstraint("event_instance_key", name="uq_market_events_event_instance_key"),
        {"comment": "Deduplicated market movements that can trigger many deliveries."},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, comment="Internal market event row id."
    )
    symbol: Mapped[str] = mapped_column(
        String(32), index=True, comment="Uppercase coin symbol for the market event."
    )
    event_type: Mapped[str] = mapped_column(
        String(64), index=True, comment="Type of market condition that was detected."
    )
    event_key: Mapped[str] = mapped_column(
        String(255),
        index=True,
        comment="Semantic event key reported by the LLM or generated by the backend.",
    )
    event_instance_key: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        comment="Stable idempotency key for this concrete market event occurrence.",
    )
    price: Mapped[float] = mapped_column(Float, comment="Current price captured for the event.")
    previous_price: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Previous stored price used to calculate movement."
    )
    price_change_percent: Mapped[float] = mapped_column(
        Float, comment="Percentage move from previous price to current price."
    )
    last_24h_change: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="24 hour percentage change at detection time."
    )
    last_7d_change: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="7 day percentage change at detection time."
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), comment="When the market event was detected."
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        comment="When this market event row was created.",
    )

    ai_analyses: Mapped[list[EventAiAnalysis]] = relationship(back_populates="market_event")


class EventAiAnalysis(Base):
    __tablename__ = "event_ai_analyses"
    __table_args__ = (
        UniqueConstraint(
            "market_event_id",
            "input_hash",
            name="uq_event_ai_analyses_market_event_input_hash",
        ),
        Index(
            "uq_event_ai_analyses_one_attached_event_analysis_per_event",
            "market_event_id",
            unique=True,
            sqlite_where=text(
                "market_event_id IS NOT NULL "
                "AND analysis_type = 'event_analysis'"
            ),
            postgresql_where=text(
                "market_event_id IS NOT NULL "
                "AND analysis_type = 'event_analysis'"
            ),
        ),
        {"comment": "One reusable AI analysis for a market event and exact input payload."},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, comment="Internal AI analysis row id."
    )
    market_event_id: Mapped[int | None] = mapped_column(
        ForeignKey("market_events.id"),
        nullable=True,
        index=True,
        comment="Market event analyzed by the LLM when an event alert is created.",
    )
    analysis_id: Mapped[str | None] = mapped_column(
        String(128),
        unique=True,
        nullable=True,
        index=True,
        comment="External stable id for this LLM analysis attempt.",
    )
    symbol: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        index=True,
        comment="Uppercase coin symbol analyzed by this LLM attempt.",
    )
    analysis_type: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="Analysis purpose such as event_analysis.",
    )
    provider: Mapped[str] = mapped_column(
        String(64), comment="LLM provider used for this analysis."
    )
    model: Mapped[str] = mapped_column(
        String(255), comment="LLM model name used for this analysis."
    )
    input_hash: Mapped[str] = mapped_column(
        String(128), index=True, comment="Hash of the exact AI input used for idempotency."
    )
    raw_input_json: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Raw JSON input payload sent to the LLM."
    )
    raw_output_json: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Raw JSON or text output returned by the LLM."
    )
    parsed_result_json: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Validated JSON result fields from the LLM response."
    )
    should_alert: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True, comment="Whether the LLM decided this analysis should alert users."
    )
    event_key: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True, comment="LLM event key when should_alert is true."
    )
    title: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="LLM alert title for an event alert."
    )
    message_body: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="LLM alert body for an event alert."
    )
    related_news_ids: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="JSON array of candidate news ids selected by the LLM."
    )
    possible_action: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Possible action text returned by the LLM."
    )
    urgency: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="LLM event urgency: low, normal, or high."
    )
    confidence: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="LLM confidence: low, medium, or high."
    )
    reason_for_no_alert: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="LLM explanation when no event alert should be sent."
    )
    analysis_text: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Raw or legacy analysis text returned by the AI."
    )
    plain_text: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Plain Telegram-safe analysis text for delivery."
    )
    html_text: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="HTML-formatted analysis text when available."
    )
    prompt_tokens: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Prompt token count reported by the LLM provider."
    )
    completion_tokens: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Completion token count reported by the LLM provider."
    )
    total_tokens: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Total token count reported by the LLM provider."
    )
    estimated_cost: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Estimated provider cost for this analysis."
    )
    status: Mapped[str] = mapped_column(
        String(64),
        default="completed",
        index=True,
        comment="Analysis state such as completed or failed.",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Failure detail when analysis generation fails."
    )
    error_reason: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="Normalized LLM failure reason for admin status.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, comment="When this AI analysis row was created."
    )

    market_event: Mapped[MarketEvent] = relationship(back_populates="ai_analyses")


class MarketHeartbeat(Base):
    __tablename__ = "market_heartbeats"
    __table_args__ = (
        Index("ix_market_heartbeats_symbol_generated_at", "symbol", "generated_at"),
        {"comment": "Cached AI market heartbeat updates generated independently of delivery."},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, comment="Internal market heartbeat row id."
    )
    symbol: Mapped[str] = mapped_column(
        String(32), index=True, comment="Uppercase coin symbol this heartbeat describes."
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, comment="When this heartbeat generation ran."
    )
    raw_input_json: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Raw JSON input payload sent to the LLM."
    )
    raw_output_json: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Raw JSON or text output returned by the LLM."
    )
    title: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="LLM heartbeat title for Telegram delivery."
    )
    message_body: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="LLM heartbeat body for Telegram delivery."
    )
    related_news_ids: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="JSON array of candidate news ids selected by the LLM."
    )
    possible_action: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Possible action text returned by the LLM."
    )
    confidence: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="LLM heartbeat confidence: low, medium, or high."
    )
    status: Mapped[str] = mapped_column(
        String(64),
        default="completed",
        index=True,
        comment="Heartbeat generation state such as completed or failed.",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Failure detail when heartbeat generation fails."
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, comment="When this heartbeat row was created."
    )


class MarketReport(Base):
    __tablename__ = "market_reports"
    __table_args__ = (
        Index("ix_market_reports_type_generated_at", "report_type", "generated_at"),
        CheckConstraint("report_type IN ('daily', 'weekly')", name="ck_market_reports_type"),
        CheckConstraint("status IN ('completed', 'failed')", name="ck_market_reports_status"),
        {"comment": "Cached AI market-wide reports generated independently of user requests."},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, comment="Internal market report row id."
    )
    report_type: Mapped[str] = mapped_column(
        String(32), index=True, comment="Report cadence, either daily or weekly."
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, comment="When this report generation ran."
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, comment="When this cached report should be refreshed."
    )
    status: Mapped[str] = mapped_column(
        String(64),
        default="completed",
        index=True,
        comment="Report generation state, either completed or failed.",
    )
    raw_input_json: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Raw JSON input payload sent to the report LLM."
    )
    raw_output_json: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Raw JSON or text output returned by the report LLM."
    )
    telegram_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Sanitized Telegram report message when generation succeeded."
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Failure detail when report generation failed."
    )
    provider: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="LLM provider used for this report generation."
    )
    model: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="LLM model used for this report generation."
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, comment="When this report row was created."
    )


class LlmUsageLog(Base):
    __tablename__ = "llm_usage_logs"
    __table_args__ = (
        Index("ix_llm_usage_logs_call_type_model_status", "call_type", "model", "status"),
        Index("ix_llm_usage_logs_symbol_created_at", "symbol", "created_at"),
        {
            "comment": (
                "Per-call LLM usage and rate-limit telemetry captured without extra provider calls."
            )
        },
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="Internal LLM usage row id.")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True, comment="When this LLM call ran."
    )
    provider: Mapped[str] = mapped_column(
        String(64), comment="LLM provider that handled the request."
    )
    model: Mapped[str] = mapped_column(
        String(255), index=True, comment="Exact LLM model requested for this call."
    )
    call_type: Mapped[str] = mapped_column(
        String(64), index=True, comment="Purpose of the LLM call such as event_analysis."
    )
    symbol: Mapped[str | None] = mapped_column(
        String(32), nullable=True, index=True, comment="Uppercase coin symbol for this call."
    )
    status: Mapped[str] = mapped_column(
        String(64), index=True, comment="Final call status such as success or rate_limit."
    )
    prompt_tokens: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Prompt tokens reported by the provider."
    )
    completion_tokens: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Completion tokens reported by the provider."
    )
    total_tokens: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Total tokens reported by the provider."
    )
    input_chars: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Character count of messages sent to the provider."
    )
    output_chars: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Character count of the provider response body."
    )
    max_tokens: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Maximum completion tokens configured for the call."
    )
    rate_limit_limit_requests: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="Provider request limit header value when available."
    )
    rate_limit_remaining_requests: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="Provider remaining requests header when available."
    )
    rate_limit_reset_requests: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="Provider request limit reset header when available."
    )
    rate_limit_limit_tokens: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="Provider token limit header value when available."
    )
    rate_limit_remaining_tokens: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="Provider remaining tokens header when available."
    )
    rate_limit_reset_tokens: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="Provider token limit reset header when available."
    )
    retry_after: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="Provider retry-after header when rate limited."
    )
    error_reason: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="Normalized safe error reason for failed calls."
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Sanitized provider or parser error message."
    )


async def init_db(database_url: str, *, run_migrations: bool = False):
    """Create SQLAlchemy async engine/session factory.

    Alembic migrations are intentionally explicit and run through
    ``run_async_upgrade`` or the documented operator command, not normal bot
    startup.
    """
    if run_migrations:
        await run_async_upgrade(database_url)
    engine = create_async_engine(database_url, future=True)
    session_local = async_sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    return engine, session_local


async def run_async_upgrade(database_url: str) -> None:
    """Run Alembic migrations without blocking the active event loop."""
    await asyncio.to_thread(_run_upgrade, database_url)


def _run_upgrade(database_url: str) -> None:
    from alembic.config import Config

    from alembic import command

    project_root = Path(__file__).resolve().parents[2]
    alembic_config = Config(str(project_root / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(project_root / "alembic"))
    alembic_config.set_main_option("sqlalchemy.url", database_url)
    alembic_config.attributes["database_url"] = database_url
    alembic_config.attributes["configure_logger"] = False
    command.upgrade(alembic_config, "head")

# Compatibility re-exports for existing imports from bot.db.database.
_REEXPORTS = {
    "premium": (
        "TELEGRAM_STARS_PROVIDER",
        "PREMIUM_PAYMENT_STATUS_PAID",
        "PREMIUM_PAYMENT_PERIOD_DAYS",
        "ensure_default_coin_subscriptions",
        "set_user_coin_subscription",
        "set_user_alert_frequency",
        "get_user_premium_subscription",
        "get_payment_by_provider_id",
        "_normalize_utc",
        "activate_premium_from_telegram_stars_payment",
        "_activate_premium_from_telegram_stars_payment_locked",
        "grant_user_premium",
        "revoke_user_premium",
    ),
    "users": (
        "_same_telegram_user_id",
        "get_or_create_user",
        "get_user_role",
        "get_user_by_telegram_user_id",
        "get_active_users_with_chat_ids",
        "get_active_users_with_alert_preferences",
        "get_user_by_telegram_chat_id",
        "is_telegram_chat_delivery_enabled",
        "mark_user_bot_blocked",
        "backfill_blocked_users_from_alerts",
    ),
    "settings": (
        "_get_app_settings_row",
        "get_or_create_app_settings",
        "update_app_settings",
        "get_or_create_user_settings",
        "update_user_settings",
    ),
    "prices": (
        "get_price_state",
        "update_price_state",
        "save_price_snapshot",
        "get_reference_price_snapshot",
        "get_price_snapshots_since",
        "get_user_symbol_alert_state",
        "upsert_user_symbol_alert_state",
    ),
    "news": (
        "was_news_seen",
        "mark_news_seen",
        "mark_news_items_seen",
        "get_recent_seen_news",
        "cleanup_seen_news",
        "get_news_item_by_key",
        "get_cached_news_item_analysis",
        "count_recent_news_intelligence_llm_calls",
        "upsert_news_item",
    ),
    "alerts": (
        "save_alert",
        "get_last_sent_alert_at",
        "get_last_sent_event_alert_at_for_event_key",
        "get_latest_sent_event_alert_for_event_key",
        "get_last_sent_alert",
        "get_latest_sent_alert_for_symbol",
        "get_latest_sent_event_alert_context_for_symbol",
        "get_alert_delivery",
        "get_market_heartbeat_delivery",
        "reserve_alert_delivery",
        "reserve_market_heartbeat_delivery",
        "update_alert_delivery_status",
        "save_alert_delivery_outcome",
        "get_recent_alert_delivery_outcome_by_context_fingerprint",
        "get_or_create_market_event",
        "get_market_event_by_instance_key",
        "get_event_ai_analysis",
        "get_latest_success_event_ai_analysis",
        "save_event_ai_analysis",
        "save_event_llm_analysis",
        "attach_analysis_to_market_event",
        "save_market_heartbeat",
        "get_latest_market_heartbeat",
        "get_latest_event_analysis_attempt",
        "get_latest_event_analysis_by_statuses",
        "get_latest_event_analysis_success_at",
        "count_market_events",
        "get_recent_market_events",
    ),
    "reports": (
        "save_market_report",
        "get_latest_market_report",
    ),
    "llm_usage": (
        "save_llm_usage_log",
        "update_llm_usage_log_status",
    ),
}

for _module_name, _names in _REEXPORTS.items():
    _module = importlib.import_module(f"bot.db.{_module_name}")
    for _name in _names:
        globals()[_name] = getattr(_module, _name)

del _module, _module_name, _name, _names
