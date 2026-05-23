"""Database infrastructure for optional PostgreSQL runtime storage."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
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
    func,
    select,
)
from sqlalchemy.exc import IntegrityError
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
    selectinload,
)

from bot.domain.supported_coins import (
    PREMIUM_ALERT_FREQUENCY_SECONDS,
    SUPPORTED_SYMBOLS,
    is_symbol_free,
    normalize_symbol,
)

TELEGRAM_STARS_PROVIDER = "telegram_stars"
PREMIUM_PAYMENT_STATUS_PAID = "paid"
PREMIUM_PAYMENT_PERIOD_DAYS = 30
_payment_activation_locks: dict[int, asyncio.Lock] = {}


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


async def init_db(database_url: str):
    """Create SQLAlchemy async engine/session factory and run migrations."""
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


def _same_telegram_user_id(left: int | str | None, right: int | str | None) -> bool:
    if left is None or right is None:
        return False
    try:
        return int(str(left).strip()) == int(str(right).strip())
    except ValueError:
        return False


async def get_or_create_user(
    session: AsyncSession,
    *,
    telegram_user_id: int,
    telegram_chat_id: int,
    username: str | None,
    first_name: str | None,
    admin_user_id: int | str | None,
):
    """Create or update profile fields for the current Telegram interaction."""
    user = await session.scalar(
        select(User).where(User.telegram_user_id == telegram_user_id).limit(1)
    )
    role = "admin" if _same_telegram_user_id(telegram_user_id, admin_user_id) else "user"
    created = user is None
    if user is None:
        user = User(
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
            username=username,
            first_name=first_name,
            role=role,
            is_active=True,
        )
        session.add(user)
    else:
        user.telegram_chat_id = telegram_chat_id
        user.username = username
        user.first_name = first_name
        if role == "admin":
            user.role = role
        user.updated_at = utc_now()
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        user = await session.scalar(
            select(User).where(User.telegram_user_id == telegram_user_id).limit(1)
        )
        if user is None:
            raise
        user.telegram_chat_id = telegram_chat_id
        user.username = username
        user.first_name = first_name
        if role == "admin":
            user.role = role
        user.updated_at = utc_now()
        await session.commit()
    await session.refresh(user)
    if created:
        await ensure_default_coin_subscriptions(session, user_id=user.id)
    return user


async def get_user_role(session: AsyncSession, telegram_user_id: int) -> str | None:
    user = await session.scalar(
        select(User).where(User.telegram_user_id == telegram_user_id).limit(1)
    )
    return user.role if user else None


async def get_user_by_telegram_user_id(
    session: AsyncSession,
    telegram_user_id: int,
    *,
    include_plan: bool = False,
) -> User | None:
    statement = select(User).where(User.telegram_user_id == telegram_user_id).limit(1)
    if include_plan:
        statement = statement.options(selectinload(User.premium_subscription))
    return await session.scalar(statement)


async def get_active_users_with_chat_ids(session: AsyncSession) -> list[User]:
    """Return active users that can receive automatic Telegram alerts."""
    result = await session.scalars(
        select(User)
        .where(User.telegram_chat_id.isnot(None))
        .where(User.is_active.is_(True))
        .where(User.bot_blocked.is_(False))
        .order_by(User.id.asc())
    )
    return list(result.all())


async def get_active_users_with_alert_preferences(session: AsyncSession) -> list[User]:
    """Return active users with watchlist and Premium data loaded."""
    result = await session.scalars(
        select(User)
        .options(
            selectinload(User.coin_subscriptions),
            selectinload(User.premium_subscription),
        )
        .where(User.telegram_chat_id.isnot(None))
        .where(User.is_active.is_(True))
        .where(User.bot_blocked.is_(False))
        .order_by(User.id.asc())
    )
    return list(result.all())


async def get_user_by_telegram_chat_id(session: AsyncSession, telegram_chat_id: int) -> User | None:
    """Return one user row for a Telegram chat id, if known."""
    return await session.scalar(
        select(User)
        .where(User.telegram_chat_id == telegram_chat_id)
        .order_by(User.id.asc())
        .limit(1)
    )


async def is_telegram_chat_delivery_enabled(session: AsyncSession, telegram_chat_id: int) -> bool:
    """Return whether a known chat can receive automatic bot messages."""
    user = await get_user_by_telegram_chat_id(session, telegram_chat_id)
    if user is None:
        return True
    return bool(user.is_active and not user.bot_blocked)


async def mark_user_bot_blocked(
    session: AsyncSession,
    *,
    user_id: int | None = None,
    telegram_chat_id: int | None = None,
    blocked_at: datetime | None = None,
) -> tuple[User | None, bool]:
    """Mark a user inactive after Telegram reports that the bot was blocked."""
    user = None
    if user_id is not None:
        user = await session.get(User, user_id)
    if user is None and telegram_chat_id is not None:
        user = await get_user_by_telegram_chat_id(session, telegram_chat_id)
    if user is None:
        return None, False

    changed = False
    if user.is_active:
        user.is_active = False
        changed = True
    if not user.bot_blocked:
        user.bot_blocked = True
        changed = True
    if user.blocked_at is None:
        user.blocked_at = blocked_at or utc_now()
        changed = True
    if changed:
        user.updated_at = utc_now()
        await session.commit()
        await session.refresh(user)
    return user, changed


async def backfill_blocked_users_from_alerts(session: AsyncSession) -> tuple[int, int]:
    """Disable users with historical failed Telegram blocked-user delivery records."""
    result = await session.execute(
        select(Alert.user_id, Alert.sent_to_chat_id, Alert.created_at)
        .where(Alert.error_message.isnot(None))
        .where(func.lower(Alert.error_message).contains("bot was blocked by the user"))
        .order_by(Alert.created_at.asc(), Alert.id.asc())
    )
    rows = list(result.all())
    updated_user_ids: set[int] = set()
    seen_user_ids: set[int] = set()

    for user_id, sent_to_chat_id, created_at in rows:
        user = None
        if user_id is not None:
            user = await session.get(User, user_id)
        if user is None and sent_to_chat_id is not None:
            user = await get_user_by_telegram_chat_id(session, int(sent_to_chat_id))
        if user is None or user.id in seen_user_ids:
            continue
        seen_user_ids.add(user.id)
        _, changed = await mark_user_bot_blocked(
            session,
            user_id=user.id,
            telegram_chat_id=int(sent_to_chat_id) if sent_to_chat_id is not None else None,
            blocked_at=created_at,
        )
        if changed:
            updated_user_ids.add(user.id)

    return len(rows), len(updated_user_ids)


async def ensure_default_coin_subscriptions(
    session: AsyncSession,
    *,
    user_id: int,
) -> list[UserCoinSubscription]:
    """Ensure one subscription row per supported symbol for a user."""
    existing_rows = list(
        (
            await session.scalars(
                select(UserCoinSubscription).where(UserCoinSubscription.user_id == user_id)
            )
        ).all()
    )
    active_rows = [row for row in existing_rows if row.symbol in SUPPORTED_SYMBOLS]
    existing_symbols = {row.symbol for row in active_rows}
    rows_to_add = []
    for symbol in SUPPORTED_SYMBOLS:
        if symbol in existing_symbols:
            continue
        rows_to_add.append(
            UserCoinSubscription(
                user_id=user_id,
                symbol=symbol,
                is_enabled=is_symbol_free(symbol),
            )
        )
    if rows_to_add:
        session.add_all(rows_to_add)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
        existing_rows = list(
            (
                await session.scalars(
                    select(UserCoinSubscription).where(UserCoinSubscription.user_id == user_id)
                )
            ).all()
        )
        active_rows = [row for row in existing_rows if row.symbol in SUPPORTED_SYMBOLS]
    return sorted(active_rows, key=lambda row: SUPPORTED_SYMBOLS.index(row.symbol))


async def set_user_coin_subscription(
    session: AsyncSession,
    *,
    user_id: int,
    symbol: str,
    is_enabled: bool,
) -> UserCoinSubscription:
    normalized_symbol = normalize_symbol(symbol)
    if normalized_symbol not in SUPPORTED_SYMBOLS:
        raise ValueError("Unsupported coin symbol.")
    row = await session.scalar(
        select(UserCoinSubscription)
        .where(UserCoinSubscription.user_id == user_id)
        .where(UserCoinSubscription.symbol == normalized_symbol)
        .limit(1)
    )
    if row is None:
        row = UserCoinSubscription(
            user_id=user_id,
            symbol=normalized_symbol,
            is_enabled=is_enabled,
        )
        session.add(row)
    else:
        row.is_enabled = is_enabled
        row.updated_at = utc_now()
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        row = await session.scalar(
            select(UserCoinSubscription)
            .where(UserCoinSubscription.user_id == user_id)
            .where(UserCoinSubscription.symbol == normalized_symbol)
            .limit(1)
        )
        if row is None:
            raise
        row.is_enabled = is_enabled
        row.updated_at = utc_now()
        await session.commit()
    await session.refresh(row)
    return row


async def set_user_alert_frequency(
    session: AsyncSession,
    *,
    user_id: int,
    frequency_seconds: int,
) -> User:
    if frequency_seconds not in PREMIUM_ALERT_FREQUENCY_SECONDS:
        raise ValueError("Unsupported alert frequency.")
    user = await session.get(User, user_id)
    if user is None:
        raise ValueError("User not found.")
    user.alert_frequency_seconds = int(frequency_seconds)
    user.updated_at = utc_now()
    await session.commit()
    await session.refresh(user)
    return user


async def get_user_premium_subscription(
    session: AsyncSession,
    *,
    user_id: int,
) -> UserPremiumSubscription | None:
    return await session.scalar(
        select(UserPremiumSubscription)
        .where(UserPremiumSubscription.user_id == user_id)
        .limit(1)
    )


async def get_payment_by_provider_id(
    session: AsyncSession,
    *,
    provider: str,
    provider_payment_id: str,
) -> Payment | None:
    return await session.scalar(
        select(Payment)
        .where(Payment.provider == provider)
        .where(Payment.provider_payment_id == provider_payment_id)
        .limit(1)
    )


def _normalize_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def activate_premium_from_telegram_stars_payment(
    session: AsyncSession,
    *,
    telegram_user_id: int,
    provider_payment_id: str,
    telegram_payment_charge_id: str | None,
    provider_payment_charge_id: str | None,
    amount: int,
    currency: str,
    payload: str,
    provider_subscription_id: str | None = None,
    is_recurring: bool | None = None,
    is_first_recurring: bool | None = None,
    subscription_expiration_date: datetime | None = None,
    now: datetime | None = None,
) -> tuple[Payment, UserPremiumSubscription, bool]:
    """Record one Stars payment and extend Premium once for that payment id."""
    lock = _payment_activation_locks.setdefault(int(telegram_user_id), asyncio.Lock())
    async with lock:
        return await _activate_premium_from_telegram_stars_payment_locked(
            session,
            telegram_user_id=telegram_user_id,
            provider_payment_id=provider_payment_id,
            telegram_payment_charge_id=telegram_payment_charge_id,
            provider_payment_charge_id=provider_payment_charge_id,
            amount=amount,
            currency=currency,
            payload=payload,
            provider_subscription_id=provider_subscription_id,
            is_recurring=is_recurring,
            is_first_recurring=is_first_recurring,
            subscription_expiration_date=subscription_expiration_date,
            now=now,
        )


async def _activate_premium_from_telegram_stars_payment_locked(
    session: AsyncSession,
    *,
    telegram_user_id: int,
    provider_payment_id: str,
    telegram_payment_charge_id: str | None,
    provider_payment_charge_id: str | None,
    amount: int,
    currency: str,
    payload: str,
    provider_subscription_id: str | None = None,
    is_recurring: bool | None = None,
    is_first_recurring: bool | None = None,
    subscription_expiration_date: datetime | None = None,
    now: datetime | None = None,
) -> tuple[Payment, UserPremiumSubscription, bool]:
    existing_payment = await get_payment_by_provider_id(
        session,
        provider=TELEGRAM_STARS_PROVIDER,
        provider_payment_id=provider_payment_id,
    )
    if existing_payment is not None:
        subscription = await get_user_premium_subscription(
            session,
            user_id=existing_payment.user_id,
        )
        return existing_payment, subscription, False

    user = await session.scalar(
        select(User)
        .where(User.telegram_user_id == telegram_user_id)
        .with_for_update()
        .limit(1)
    )
    if user is None:
        raise ValueError("User not found.")

    now = now or utc_now()
    payment = Payment(
        user_id=user.id,
        provider=TELEGRAM_STARS_PROVIDER,
        provider_payment_id=provider_payment_id,
        provider_subscription_id=provider_subscription_id,
        telegram_payment_charge_id=telegram_payment_charge_id,
        provider_payment_charge_id=provider_payment_charge_id,
        is_recurring=is_recurring,
        is_first_recurring=is_first_recurring,
        subscription_expiration_date=_normalize_utc(subscription_expiration_date),
        amount=int(amount),
        currency=currency,
        payload=payload,
        status=PREMIUM_PAYMENT_STATUS_PAID,
    )
    session.add(payment)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        existing_payment = await get_payment_by_provider_id(
            session,
            provider=TELEGRAM_STARS_PROVIDER,
            provider_payment_id=provider_payment_id,
        )
        if existing_payment is None:
            raise
        subscription = await get_user_premium_subscription(
            session,
            user_id=existing_payment.user_id,
        )
        return existing_payment, subscription, False

    subscription = await session.scalar(
        select(UserPremiumSubscription)
        .where(UserPremiumSubscription.user_id == user.id)
        .with_for_update()
        .limit(1)
    )
    active_until = _normalize_utc(getattr(subscription, "active_until", None))
    active_from = max(now, active_until or now)
    if subscription is None:
        subscription = UserPremiumSubscription(
            user_id=user.id,
            plan="premium",
            status="active",
            active_until=active_from + timedelta(days=PREMIUM_PAYMENT_PERIOD_DAYS),
            started_at=now,
            cancelled_at=None,
            provider=TELEGRAM_STARS_PROVIDER,
            provider_subscription_id=provider_subscription_id,
            last_payment_id=str(payment.id),
        )
        session.add(subscription)
    else:
        subscription.plan = "premium"
        subscription.status = "active"
        subscription.active_until = active_from + timedelta(days=PREMIUM_PAYMENT_PERIOD_DAYS)
        subscription.started_at = subscription.started_at or now
        subscription.cancelled_at = None
        subscription.provider = TELEGRAM_STARS_PROVIDER
        subscription.provider_subscription_id = provider_subscription_id
        subscription.last_payment_id = str(payment.id)
        subscription.updated_at = now
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing_payment = await get_payment_by_provider_id(
            session,
            provider=TELEGRAM_STARS_PROVIDER,
            provider_payment_id=provider_payment_id,
        )
        if existing_payment is None:
            raise
        subscription = await get_user_premium_subscription(
            session,
            user_id=existing_payment.user_id,
        )
        return existing_payment, subscription, False
    await session.refresh(payment)
    await session.refresh(subscription)
    return payment, subscription, True


async def grant_user_premium(
    session: AsyncSession,
    *,
    telegram_user_id: int,
    days: int,
    now: datetime | None = None,
) -> UserPremiumSubscription:
    if days <= 0:
        raise ValueError("Premium grant days must be greater than 0.")
    user = await get_user_by_telegram_user_id(session, telegram_user_id)
    if user is None:
        raise ValueError("User not found.")

    now = now or utc_now()
    subscription = await get_user_premium_subscription(session, user_id=user.id)
    if subscription is None:
        active_from = now
        subscription = UserPremiumSubscription(
            user_id=user.id,
            plan="premium",
            status="active",
            active_until=active_from + timedelta(days=days),
            started_at=now,
            cancelled_at=None,
            provider="manual",
        )
        session.add(subscription)
    else:
        active_until = subscription.active_until
        if active_until is not None and active_until.tzinfo is None:
            active_until = active_until.replace(tzinfo=timezone.utc)
        active_from = max(now, active_until or now)
        subscription.plan = "premium"
        subscription.status = "active"
        subscription.active_until = active_from + timedelta(days=days)
        subscription.started_at = subscription.started_at or now
        subscription.cancelled_at = None
        subscription.provider = "manual"
        subscription.updated_at = now
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return await grant_user_premium(
            session,
            telegram_user_id=telegram_user_id,
            days=days,
            now=now,
        )
    await session.refresh(subscription)
    return subscription


async def revoke_user_premium(
    session: AsyncSession,
    *,
    telegram_user_id: int,
    now: datetime | None = None,
) -> UserPremiumSubscription:
    user = await get_user_by_telegram_user_id(session, telegram_user_id)
    if user is None:
        raise ValueError("User not found.")
    now = now or utc_now()
    subscription = await get_user_premium_subscription(session, user_id=user.id)
    if subscription is None:
        subscription = UserPremiumSubscription(
            user_id=user.id,
            plan="premium",
            status="revoked",
            active_until=now,
            started_at=None,
            cancelled_at=now,
            provider="manual",
        )
        session.add(subscription)
    else:
        subscription.status = "revoked"
        subscription.active_until = now
        subscription.cancelled_at = now
        subscription.provider = "manual"
        subscription.updated_at = now
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return await revoke_user_premium(session, telegram_user_id=telegram_user_id, now=now)
    await session.refresh(subscription)
    return subscription


async def _get_app_settings_row(
    session: AsyncSession, *, default_threshold: float, default_interval: int
):
    settings = await session.scalar(select(AppSettings).order_by(AppSettings.id.asc()).limit(1))
    if settings is None:
        settings = AppSettings(
            btc_alert_threshold_percent=default_threshold,
            major_movement_threshold_percent=1.0,
            alt_movement_threshold_percent=2.0,
            major_24h_medium_threshold_percent=3.0,
            major_24h_high_threshold_percent=5.0,
            alt_24h_medium_threshold_percent=5.0,
            alt_24h_high_threshold_percent=8.0,
            automatic_check_interval_seconds=default_interval,
            error_file_logging_enabled=False,
        )
        session.add(settings)
        await session.commit()
        await session.refresh(settings)
        return settings

    changed = False
    if settings.btc_alert_threshold_percent is None:
        settings.btc_alert_threshold_percent = default_threshold
        changed = True
    if settings.automatic_check_interval_seconds is None:
        settings.automatic_check_interval_seconds = default_interval
        changed = True
    threshold_defaults = {
        "major_movement_threshold_percent": 1.0,
        "alt_movement_threshold_percent": 2.0,
        "major_24h_medium_threshold_percent": 3.0,
        "major_24h_high_threshold_percent": 5.0,
        "alt_24h_medium_threshold_percent": 5.0,
        "alt_24h_high_threshold_percent": 8.0,
    }
    for name, default_value in threshold_defaults.items():
        if getattr(settings, name, None) is None:
            setattr(settings, name, default_value)
            changed = True
    if settings.error_file_logging_enabled is None:
        settings.error_file_logging_enabled = False
        changed = True
    if changed:
        settings.updated_at = utc_now()
        await session.commit()
        await session.refresh(settings)
    return settings


async def get_or_create_app_settings(
    session: AsyncSession,
    *,
    default_threshold: float,
    default_interval: int,
) -> dict:
    settings = await _get_app_settings_row(
        session,
        default_threshold=default_threshold,
        default_interval=default_interval,
    )
    return {
        "btc_alert_threshold_percent": float(settings.btc_alert_threshold_percent),
        "automatic_check_interval_seconds": int(settings.automatic_check_interval_seconds),
        "error_file_logging_enabled": bool(settings.error_file_logging_enabled),
        "major_movement_threshold_percent": float(settings.major_movement_threshold_percent),
        "alt_movement_threshold_percent": float(settings.alt_movement_threshold_percent),
        "major_24h_medium_threshold_percent": float(settings.major_24h_medium_threshold_percent),
        "major_24h_high_threshold_percent": float(settings.major_24h_high_threshold_percent),
        "alt_24h_medium_threshold_percent": float(settings.alt_24h_medium_threshold_percent),
        "alt_24h_high_threshold_percent": float(settings.alt_24h_high_threshold_percent),
    }


async def update_app_settings(
    session: AsyncSession,
    *,
    default_threshold: float,
    default_interval: int,
    threshold: float | None = None,
    interval_seconds: int | None = None,
    error_file_logging_enabled: bool | None = None,
    threshold_updates: dict[str, float] | None = None,
) -> dict:
    settings = await _get_app_settings_row(
        session,
        default_threshold=default_threshold,
        default_interval=default_interval,
    )
    if threshold is not None:
        settings.btc_alert_threshold_percent = threshold
    if interval_seconds is not None:
        settings.automatic_check_interval_seconds = interval_seconds
    if error_file_logging_enabled is not None:
        settings.error_file_logging_enabled = error_file_logging_enabled
    for name, value in (threshold_updates or {}).items():
        if hasattr(settings, name):
            setattr(settings, name, float(value))
    settings.updated_at = utc_now()
    await session.commit()
    await session.refresh(settings)
    return await get_or_create_app_settings(
        session,
        default_threshold=default_threshold,
        default_interval=default_interval,
    )


async def get_or_create_user_settings(
    session: AsyncSession,
    *,
    user_id: int,
    default_threshold: float,
    default_interval: int,
):
    settings = await session.scalar(
        select(UserSettings).where(UserSettings.user_id == user_id).limit(1)
    )
    if settings is None:
        settings = UserSettings(
            user_id=user_id,
            price_move_alert_percent=default_threshold,
            automatic_check_interval_seconds=default_interval,
        )
        session.add(settings)
        await session.commit()
        await session.refresh(settings)
    return settings


async def update_user_settings(
    session: AsyncSession,
    *,
    user_id: int,
    threshold: float | None = None,
    interval_seconds: int | None = None,
):
    settings = await session.scalar(
        select(UserSettings).where(UserSettings.user_id == user_id).limit(1)
    )
    if settings is None:
        raise ValueError("User settings row not found.")
    if threshold is not None:
        settings.price_move_alert_percent = threshold
    if interval_seconds is not None:
        settings.automatic_check_interval_seconds = interval_seconds
    settings.updated_at = utc_now()
    await session.commit()
    await session.refresh(settings)
    return settings


async def get_price_state(session: AsyncSession, symbol: str):
    return await session.scalar(
        select(PriceState).where(PriceState.symbol == symbol.upper()).limit(1)
    )


async def update_price_state(
    session: AsyncSession,
    *,
    symbol: str,
    last_price: float,
    last_24h_change: float,
    last_checked_at: datetime | None,
    last_alert_at: datetime | None = None,
):
    row = await get_price_state(session, symbol)
    if row is None:
        row = PriceState(
            symbol=symbol.upper(),
            last_price=last_price,
            last_24h_change=last_24h_change,
            last_checked_at=last_checked_at,
            last_alert_at=last_alert_at,
        )
        session.add(row)
    else:
        row.last_price = last_price
        row.last_24h_change = last_24h_change
        row.last_checked_at = last_checked_at
        if last_alert_at is not None:
            row.last_alert_at = last_alert_at
    row.updated_at = utc_now()
    await session.commit()
    await session.refresh(row)
    return row


async def save_price_snapshot(
    session: AsyncSession,
    *,
    symbol: str,
    price: float,
    change_24h: float | None,
    checked_at: datetime,
    change_7d: float | None = None,
    source: str = "coingecko",
) -> PriceSnapshot:
    row = PriceSnapshot(
        symbol=symbol.upper(),
        price=price,
        change_24h=change_24h,
        change_7d=change_7d,
        source=source,
        checked_at=checked_at,
        created_at=checked_at,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def get_reference_price_snapshot(
    session: AsyncSession,
    *,
    symbol: str,
    at_or_before: datetime,
) -> PriceSnapshot | None:
    return await session.scalar(
        select(PriceSnapshot)
        .where(PriceSnapshot.symbol == symbol.upper())
        .where(PriceSnapshot.checked_at <= at_or_before)
        .order_by(PriceSnapshot.checked_at.desc(), PriceSnapshot.id.desc())
        .limit(1)
    )


async def get_price_snapshots_since(
    session: AsyncSession,
    *,
    symbol: str,
    since: datetime,
) -> list[PriceSnapshot]:
    rows = await session.scalars(
        select(PriceSnapshot)
        .where(PriceSnapshot.symbol == symbol.upper())
        .where(PriceSnapshot.checked_at >= since)
        .order_by(PriceSnapshot.checked_at.asc(), PriceSnapshot.id.asc())
    )
    return list(rows.all())


async def get_user_symbol_alert_state(
    session: AsyncSession,
    *,
    user_id: int,
    symbol: str,
) -> UserSymbolAlertState | None:
    """Return per-user per-symbol alert state, if it exists."""
    return await session.scalar(
        select(UserSymbolAlertState)
        .where(UserSymbolAlertState.user_id == user_id)
        .where(UserSymbolAlertState.symbol == normalize_symbol(symbol))
        .limit(1)
    )


async def upsert_user_symbol_alert_state(
    session: AsyncSession,
    *,
    user_id: int,
    symbol: str,
    last_market_update_time: datetime | None = None,
    last_important_alert_time: datetime | None = None,
    last_critical_alert_time: datetime | None = None,
    last_notification_type: str | None = None,
    last_notification_severity: str | None = None,
    last_notification_direction: str | None = None,
    last_cumulative_movement_percent: float | None = None,
) -> UserSymbolAlertState:
    """Create or update per-user per-symbol alert state."""
    normalized_symbol = normalize_symbol(symbol)
    row = await get_user_symbol_alert_state(
        session,
        user_id=user_id,
        symbol=normalized_symbol,
    )
    if row is None:
        row = UserSymbolAlertState(user_id=user_id, symbol=normalized_symbol)
        session.add(row)
    if last_market_update_time is not None:
        row.last_market_update_time = last_market_update_time
    if last_important_alert_time is not None:
        row.last_important_alert_time = last_important_alert_time
    if last_critical_alert_time is not None:
        row.last_critical_alert_time = last_critical_alert_time
    if last_notification_type is not None:
        row.last_notification_type = last_notification_type
    if last_notification_severity is not None:
        row.last_notification_severity = normalize_stored_severity(last_notification_severity)
    if last_notification_direction is not None:
        row.last_notification_direction = last_notification_direction
    if last_cumulative_movement_percent is not None:
        row.last_cumulative_movement_percent = last_cumulative_movement_percent
    row.updated_at = utc_now()
    await session.commit()
    await session.refresh(row)
    return row


async def was_news_seen(session: AsyncSession, news_key: str) -> bool:
    """Return True when a news key already exists in seen_news."""
    if not news_key:
        return False
    row = await session.scalar(select(SeenNews.id).where(SeenNews.news_key == news_key).limit(1))
    return row is not None


async def mark_news_seen(session: AsyncSession, news_item: dict):
    """Store one news item in seen_news if it has not been stored before."""
    news_key = make_news_key(news_item)
    if not news_key:
        return None

    existing = await session.scalar(select(SeenNews).where(SeenNews.news_key == news_key).limit(1))
    if existing:
        return existing

    row = SeenNews(
        news_key=news_key,
        title=str(news_item.get("title") or "")[:1000],
        link=str(news_item.get("link") or "")[:2000],
        source=str(news_item.get("source") or "")[:255] or None,
    )
    session.add(row)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return await session.scalar(select(SeenNews).where(SeenNews.news_key == news_key).limit(1))
    await session.refresh(row)
    return row


async def mark_news_items_seen(session: AsyncSession, news_items: list[dict]) -> list[SeenNews]:
    """Store multiple news items while skipping duplicates."""
    rows = []
    for item in news_items:
        news_key = make_news_key(item)
        if not news_key or await was_news_seen(session, news_key):
            continue
        row = SeenNews(
            news_key=news_key,
            title=str(item.get("title") or "")[:1000],
            link=str(item.get("link") or "")[:2000],
            source=str(item.get("source") or "")[:255] or None,
        )
        session.add(row)
        rows.append(row)

    if not rows:
        return []

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        stored_rows = []
        for item in news_items:
            row = await mark_news_seen(session, item)
            if row:
                stored_rows.append(row)
        return stored_rows

    for row in rows:
        await session.refresh(row)
    return rows


async def get_recent_seen_news(session: AsyncSession, limit: int = 100) -> list[SeenNews]:
    """Return recent seen news rows, newest first."""
    result = await session.scalars(
        select(SeenNews).order_by(SeenNews.seen_at.desc(), SeenNews.id.desc()).limit(limit)
    )
    return list(result.all())


async def cleanup_seen_news(session: AsyncSession, keep_latest: int = 100) -> int:
    """Keep only the latest seen_news rows and return how many were deleted."""
    if keep_latest < 1:
        raise ValueError("keep_latest must be at least 1.")

    result = await session.scalars(
        select(SeenNews).order_by(SeenNews.seen_at.desc(), SeenNews.id.desc()).offset(keep_latest)
    )
    rows_to_delete = list(result.all())
    for row in rows_to_delete:
        await session.delete(row)
    await session.commit()
    return len(rows_to_delete)


async def get_news_item_by_key(session: AsyncSession, news_key: str) -> NewsItem | None:
    """Return a structured news item by stable news key."""
    if not news_key:
        return None
    return await session.scalar(select(NewsItem).where(NewsItem.news_key == news_key).limit(1))


async def get_cached_news_item_analysis(
    session: AsyncSession,
    *,
    news_key: str,
    llm_input_hash: str,
    llm_model: str,
) -> NewsItem | None:
    """Return a reusable structured news analysis for the exact compact LLM input."""
    if not news_key or not llm_input_hash or not llm_model:
        return None
    return await session.scalar(
        select(NewsItem)
        .where(NewsItem.news_key == news_key)
        .where(NewsItem.llm_input_hash == llm_input_hash)
        .where(NewsItem.llm_model == llm_model)
        .where(NewsItem.llm_status.in_(["success", "skipped_noise", "skipped_duplicate"]))
        .limit(1)
    )


async def count_recent_news_intelligence_llm_calls(
    session: AsyncSession,
    *,
    since: datetime,
    provider: str = "groq",
) -> int:
    """Count recent news intelligence LLM attempts for budget enforcement."""
    return int(
        await session.scalar(
            select(func.count())
            .select_from(NewsItem)
            .where(NewsItem.llm_provider == provider)
            .where(NewsItem.llm_status.in_(["success", "failed"]))
            .where(NewsItem.updated_at >= since)
        )
        or 0
    )


async def upsert_news_item(
    session: AsyncSession,
    *,
    news_key: str,
    title: str,
    source: str | None,
    url: str,
    published_at: datetime | None,
    fetched_at: datetime,
    raw_summary: str | None,
    llm_summary: str | None = None,
    llm_raw_response: str | None = None,
    related_symbols: list[str] | None = None,
    primary_symbol: str | None = None,
    category: str | None = None,
    impact_score: int | None = None,
    impact_level: str | None = None,
    relevance_score: int | None = None,
    dedup_group_id: str | None = None,
    is_duplicate: bool = False,
    is_noise: bool = False,
    is_alert_worthy: bool = False,
    llm_provider: str | None = None,
    llm_model: str | None = None,
    llm_input_hash: str | None = None,
    llm_status: str = "pending",
    llm_error: str | None = None,
) -> NewsItem:
    """Create or update one structured news intelligence row."""
    row = await get_news_item_by_key(session, news_key)
    if row is None:
        row = NewsItem(news_key=news_key, title=title[:1000], url=url[:2000])
        session.add(row)

    row.title = title[:1000]
    row.source = source[:255] if source else None
    row.url = url[:2000]
    row.published_at = published_at
    row.fetched_at = fetched_at
    row.raw_summary = raw_summary
    row.llm_summary = llm_summary
    row.llm_raw_response = llm_raw_response
    row.related_symbols = related_symbols or []
    row.primary_symbol = primary_symbol
    row.category = category
    row.impact_score = impact_score
    row.impact_level = impact_level
    row.relevance_score = relevance_score
    row.dedup_group_id = dedup_group_id
    row.is_duplicate = is_duplicate
    row.is_noise = is_noise
    row.is_alert_worthy = is_alert_worthy
    row.llm_provider = llm_provider
    row.llm_model = llm_model
    row.llm_input_hash = llm_input_hash
    row.llm_status = llm_status
    row.llm_error = llm_error
    row.updated_at = utc_now()

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await get_news_item_by_key(session, news_key)
        if existing is None:
            raise
        return existing
    await session.refresh(row)
    return row


async def save_alert(
    session: AsyncSession,
    *,
    symbol: str,
    alert_type: str,
    message: str,
    sent_to_chat_id: int,
    market_event_id: int | None = None,
    market_heartbeat_id: int | None = None,
    event_ai_analysis_id: int | None = None,
    user_id: int | None = None,
    status: str | None = None,
    error_message: str | None = None,
    trigger_reason: str | None = None,
    trigger_source: str | None = None,
    numeric_context: str | None = None,
    thresholds_used: str | None = None,
    llm_severity: str | None = None,
    llm_reasoning_summary: str | None = None,
    fallback_mode: bool = False,
):
    alert = Alert(
        symbol=symbol.upper(),
        alert_type=alert_type,
        message=message,
        sent_to_chat_id=sent_to_chat_id,
        market_event_id=market_event_id,
        market_heartbeat_id=market_heartbeat_id,
        event_ai_analysis_id=event_ai_analysis_id,
        user_id=user_id,
        status=status,
        error_message=error_message,
        trigger_reason=trigger_reason,
        trigger_source=trigger_source,
        numeric_context=numeric_context,
        thresholds_used=thresholds_used,
        llm_severity=normalize_stored_severity(llm_severity),
        llm_reasoning_summary=llm_reasoning_summary,
        fallback_mode=fallback_mode,
    )
    session.add(alert)
    await session.commit()
    await session.refresh(alert)
    return alert


async def get_last_sent_alert_at(
    session: AsyncSession,
    *,
    user_id: int,
    symbol: str,
    alert_type: str | None = None,
) -> datetime | None:
    """Return latest sent delivery time for a user+symbol frequency window."""
    statement = (
        select(func.max(Alert.created_at))
        .where(Alert.user_id == user_id)
        .where(Alert.symbol == symbol.upper())
        .where(Alert.status == "sent")
    )
    if alert_type is not None:
        statement = statement.where(Alert.alert_type == alert_type)
    return await session.scalar(statement)


async def get_last_sent_alert(
    session: AsyncSession,
    *,
    user_id: int,
    symbol: str,
    alert_type: str | None = None,
) -> Alert | None:
    """Return latest sent delivery row for a user and symbol."""
    statement = (
        select(Alert)
        .where(Alert.user_id == user_id)
        .where(Alert.symbol == symbol.upper())
        .where(Alert.status == "sent")
        .order_by(Alert.created_at.desc(), Alert.id.desc())
        .limit(1)
    )
    if alert_type is not None:
        statement = statement.where(Alert.alert_type == alert_type)
    return await session.scalar(statement)


async def get_latest_sent_alert_for_symbol(
    session: AsyncSession,
    *,
    symbol: str,
    alert_type: str | None = None,
) -> Alert | None:
    """Return the latest sent delivery row for a symbol across all users."""
    statement = (
        select(Alert)
        .where(Alert.symbol == symbol.upper())
        .where(Alert.status == "sent")
        .order_by(Alert.created_at.desc(), Alert.id.desc())
        .limit(1)
    )
    if alert_type is not None:
        statement = statement.where(Alert.alert_type == alert_type)
    return await session.scalar(statement)


async def get_alert_delivery(
    session: AsyncSession,
    *,
    user_id: int,
    symbol: str,
    market_event_id: int,
) -> Alert | None:
    return await session.scalar(
        select(Alert)
        .where(Alert.user_id == user_id)
        .where(Alert.symbol == symbol.upper())
        .where(Alert.market_event_id == market_event_id)
        .limit(1)
    )


async def get_market_heartbeat_delivery(
    session: AsyncSession,
    *,
    user_id: int,
    symbol: str,
    alert_type: str,
    market_heartbeat_id: int,
) -> Alert | None:
    return await session.scalar(
        select(Alert)
        .where(Alert.user_id == user_id)
        .where(Alert.symbol == symbol.upper())
        .where(Alert.alert_type == alert_type)
        .where(Alert.market_heartbeat_id == market_heartbeat_id)
        .limit(1)
    )


async def reserve_alert_delivery(
    session: AsyncSession,
    *,
    user_id: int,
    symbol: str,
    alert_type: str,
    sent_to_chat_id: int,
    market_event_id: int,
    event_ai_analysis_id: int | None,
    message: str,
    trigger_reason: str | None = None,
    trigger_source: str | None = None,
    numeric_context: str | None = None,
    thresholds_used: str | None = None,
    llm_severity: str | None = None,
    llm_reasoning_summary: str | None = None,
    fallback_mode: bool = False,
) -> tuple[Alert, bool]:
    """Reserve one delivery identity before sending.

    Returns (alert, created_or_retryable). Existing sent/pending rows are not
    retryable; failed rows are moved back to pending for another attempt.
    """
    existing = await get_alert_delivery(
        session,
        user_id=user_id,
        symbol=symbol,
        market_event_id=market_event_id,
    )
    if existing:
        if existing.status in {"sent", "pending", "retry_pending"}:
            return existing, False
        if existing.final_failed_at is not None:
            return existing, False
        existing.status = "pending"
        existing.error_message = None
        existing.retry_count = 0
        existing.last_error = None
        existing.next_retry_at = None
        existing.final_failed_at = None
        existing.message = message
        existing.sent_to_chat_id = sent_to_chat_id
        existing.event_ai_analysis_id = event_ai_analysis_id
        existing.trigger_reason = trigger_reason
        existing.trigger_source = trigger_source
        existing.numeric_context = numeric_context
        existing.thresholds_used = thresholds_used
        existing.llm_severity = normalize_stored_severity(llm_severity)
        existing.llm_reasoning_summary = llm_reasoning_summary
        existing.fallback_mode = fallback_mode
        await session.commit()
        await session.refresh(existing)
        return existing, True

    alert = Alert(
        symbol=symbol.upper(),
        alert_type=alert_type,
        message=message,
        sent_to_chat_id=sent_to_chat_id,
        market_event_id=market_event_id,
        event_ai_analysis_id=event_ai_analysis_id,
        user_id=user_id,
        status="pending",
        trigger_reason=trigger_reason,
        trigger_source=trigger_source,
        numeric_context=numeric_context,
        thresholds_used=thresholds_used,
        llm_severity=normalize_stored_severity(llm_severity),
        llm_reasoning_summary=llm_reasoning_summary,
        fallback_mode=fallback_mode,
    )
    session.add(alert)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await get_alert_delivery(
            session,
            user_id=user_id,
            symbol=symbol,
            market_event_id=market_event_id,
        )
        if existing is None:
            raise
        return existing, existing.status == "failed"
    await session.refresh(alert)
    return alert, True


async def reserve_market_heartbeat_delivery(
    session: AsyncSession,
    *,
    user_id: int,
    symbol: str,
    alert_type: str,
    sent_to_chat_id: int,
    market_heartbeat_id: int,
    message: str,
    trigger_reason: str | None = None,
    trigger_source: str | None = None,
    numeric_context: str | None = None,
    llm_severity: str | None = None,
    llm_reasoning_summary: str | None = None,
) -> tuple[Alert, bool]:
    """Reserve one market-heartbeat delivery before sending."""
    existing = await session.scalar(
        select(Alert)
        .where(Alert.user_id == user_id)
        .where(Alert.symbol == symbol.upper())
        .where(Alert.alert_type == alert_type)
        .where(Alert.market_heartbeat_id == market_heartbeat_id)
        .with_for_update()
        .limit(1)
    )
    if existing:
        if existing.status in {"sent", "pending", "retry_pending"}:
            return existing, False
        if existing.final_failed_at is not None:
            return existing, False
        existing.status = "pending"
        existing.error_message = None
        existing.retry_count = 0
        existing.last_error = None
        existing.next_retry_at = None
        existing.final_failed_at = None
        existing.message = message
        existing.sent_to_chat_id = sent_to_chat_id
        existing.trigger_reason = trigger_reason
        existing.trigger_source = trigger_source
        existing.numeric_context = numeric_context
        existing.llm_severity = normalize_stored_severity(llm_severity)
        existing.llm_reasoning_summary = llm_reasoning_summary
        await session.commit()
        await session.refresh(existing)
        return existing, True

    alert = Alert(
        symbol=symbol.upper(),
        alert_type=alert_type,
        message=message,
        sent_to_chat_id=sent_to_chat_id,
        market_event_id=None,
        market_heartbeat_id=market_heartbeat_id,
        event_ai_analysis_id=None,
        user_id=user_id,
        status="pending",
        trigger_reason=trigger_reason,
        trigger_source=trigger_source,
        numeric_context=numeric_context,
        llm_severity=normalize_stored_severity(llm_severity),
        llm_reasoning_summary=llm_reasoning_summary,
    )
    session.add(alert)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await get_market_heartbeat_delivery(
            session,
            user_id=user_id,
            symbol=symbol,
            alert_type=alert_type,
            market_heartbeat_id=market_heartbeat_id,
        )
        if existing is None:
            raise
        return existing, existing.status == "failed" and existing.final_failed_at is None
    await session.refresh(alert)
    return alert, True


async def update_alert_delivery_status(
    session: AsyncSession,
    *,
    alert_id: int,
    status: str,
    error_message: str | None = None,
    retry_count: int | None = None,
    last_error: str | None = None,
    next_retry_at: datetime | None = None,
    final_failed_at: datetime | None = None,
) -> Alert | None:
    alert = await session.get(Alert, alert_id)
    if alert is None:
        return None
    alert.status = status
    alert.error_message = error_message
    if retry_count is not None:
        alert.retry_count = retry_count
    if last_error is not None:
        alert.last_error = last_error
    if status == "sent":
        alert.error_message = None
        alert.next_retry_at = None
        alert.final_failed_at = None
    else:
        alert.next_retry_at = next_retry_at
        if final_failed_at is not None:
            alert.final_failed_at = final_failed_at
    await session.commit()
    await session.refresh(alert)
    return alert


async def get_or_create_market_event(
    session: AsyncSession,
    *,
    symbol: str,
    event_type: str,
    event_key: str,
    event_instance_key: str | None = None,
    price: float,
    price_change_percent: float,
    previous_price: float | None = None,
    last_24h_change: float | None = None,
    last_7d_change: float | None = None,
    detected_at: datetime | None = None,
) -> MarketEvent:
    """Return the market event for event_instance_key, creating it when needed."""
    instance_key = event_instance_key or event_key
    existing = await session.scalar(
        select(MarketEvent).where(MarketEvent.event_instance_key == instance_key).limit(1)
    )
    if existing:
        return existing

    market_event = MarketEvent(
        symbol=symbol.upper(),
        event_type=event_type,
        event_key=event_key,
        event_instance_key=instance_key,
        price=price,
        previous_price=previous_price,
        price_change_percent=price_change_percent,
        last_24h_change=last_24h_change,
        last_7d_change=last_7d_change,
        detected_at=detected_at or utc_now(),
    )
    session.add(market_event)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return await session.scalar(
            select(MarketEvent).where(MarketEvent.event_instance_key == instance_key).limit(1)
        )
    await session.refresh(market_event)
    return market_event


async def get_event_ai_analysis(
    session: AsyncSession, *, market_event_id: int, input_hash: str
) -> EventAiAnalysis | None:
    """Return an existing AI analysis for the event/input pair if present."""
    return await session.scalar(
        select(EventAiAnalysis)
        .where(EventAiAnalysis.market_event_id == market_event_id)
        .where(EventAiAnalysis.input_hash == input_hash)
        .limit(1)
    )


async def get_latest_success_event_ai_analysis(
    session: AsyncSession,
    *,
    market_event_id: int,
) -> EventAiAnalysis | None:
    """Return any successful saved analysis for a market event."""
    return await session.scalar(
        select(EventAiAnalysis)
        .where(EventAiAnalysis.market_event_id == market_event_id)
        .where(EventAiAnalysis.status.in_(["success", "completed"]))
        .where(EventAiAnalysis.plain_text.isnot(None))
        .order_by(EventAiAnalysis.id.asc())
        .limit(1)
    )


async def save_event_ai_analysis(
    session: AsyncSession,
    *,
    market_event_id: int,
    provider: str,
    model: str,
    input_hash: str,
    analysis_text: str | None = None,
    plain_text: str | None = None,
    html_text: str | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
    estimated_cost: float | None = None,
    status: str = "completed",
    error_message: str | None = None,
) -> EventAiAnalysis:
    """Save one AI analysis row for a market event."""
    existing = await get_event_ai_analysis(
        session, market_event_id=market_event_id, input_hash=input_hash
    )
    if existing:
        return existing

    analysis = EventAiAnalysis(
        market_event_id=market_event_id,
        provider=provider,
        model=model,
        input_hash=input_hash,
        analysis_text=analysis_text,
        plain_text=plain_text,
        html_text=html_text,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost=estimated_cost,
        status=status,
        error_message=error_message,
    )
    session.add(analysis)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return await get_event_ai_analysis(
            session, market_event_id=market_event_id, input_hash=input_hash
        )
    await session.refresh(analysis)
    return analysis


async def save_event_llm_analysis(
    session: AsyncSession,
    *,
    analysis_id: str,
    symbol: str,
    input_hash: str,
    raw_input_json: str,
    raw_output_json: str | None,
    status: str,
    provider: str = "groq",
    model: str = "",
    analysis_type: str = "event_analysis",
    market_event_id: int | None = None,
    parsed_result_json: str | None = None,
    should_alert: bool | None = None,
    event_key: str | None = None,
    title: str | None = None,
    message_body: str | None = None,
    related_news_ids: str | None = None,
    possible_action: str | None = None,
    urgency: str | None = None,
    confidence: str | None = None,
    reason_for_no_alert: str | None = None,
    error_message: str | None = None,
    error_reason: str | None = None,
    plain_text: str | None = None,
    html_text: str | None = None,
) -> EventAiAnalysis:
    """Save one raw LLM event-analysis attempt."""
    existing = await session.scalar(
        select(EventAiAnalysis).where(EventAiAnalysis.analysis_id == analysis_id).limit(1)
    )
    if existing:
        return existing

    analysis = EventAiAnalysis(
        market_event_id=market_event_id,
        analysis_id=analysis_id,
        symbol=symbol.upper(),
        analysis_type=analysis_type,
        provider=provider,
        model=model,
        input_hash=input_hash,
        raw_input_json=raw_input_json,
        raw_output_json=raw_output_json,
        parsed_result_json=parsed_result_json,
        should_alert=should_alert,
        event_key=event_key,
        title=title,
        message_body=message_body,
        related_news_ids=related_news_ids,
        possible_action=possible_action,
        urgency=urgency,
        confidence=confidence,
        reason_for_no_alert=reason_for_no_alert,
        analysis_text=raw_output_json,
        plain_text=plain_text,
        html_text=html_text,
        status=status,
        error_message=error_message,
        error_reason=error_reason,
    )
    session.add(analysis)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return await session.scalar(
            select(EventAiAnalysis).where(EventAiAnalysis.analysis_id == analysis_id).limit(1)
        )
    await session.refresh(analysis)
    return analysis


async def attach_analysis_to_market_event(
    session: AsyncSession,
    *,
    analysis_id: str,
    market_event_id: int,
    plain_text: str | None = None,
    html_text: str | None = None,
) -> EventAiAnalysis | None:
    """Attach a previously saved event analysis to the event created from its decision."""
    analysis = await session.scalar(
        select(EventAiAnalysis).where(EventAiAnalysis.analysis_id == analysis_id).limit(1)
    )
    if analysis is None:
        return None
    analysis.market_event_id = market_event_id
    if plain_text is not None:
        analysis.plain_text = plain_text
    if html_text is not None:
        analysis.html_text = html_text
    await session.commit()
    await session.refresh(analysis)
    return analysis


async def save_market_heartbeat(
    session: AsyncSession,
    *,
    symbol: str,
    generated_at: datetime,
    raw_input_json: str | None,
    raw_output_json: str | None,
    title: str | None = None,
    message_body: str | None = None,
    related_news_ids: str | None = None,
    possible_action: str | None = None,
    confidence: str | None = None,
    status: str = "completed",
    error_message: str | None = None,
) -> MarketHeartbeat:
    heartbeat = MarketHeartbeat(
        symbol=symbol.upper(),
        generated_at=generated_at,
        raw_input_json=raw_input_json,
        raw_output_json=raw_output_json,
        title=title,
        message_body=message_body,
        related_news_ids=related_news_ids,
        possible_action=possible_action,
        confidence=confidence,
        status=status,
        error_message=error_message,
    )
    session.add(heartbeat)
    await session.commit()
    await session.refresh(heartbeat)
    return heartbeat


async def save_market_report(
    session: AsyncSession,
    *,
    report_type: str,
    generated_at: datetime,
    expires_at: datetime,
    status: str,
    raw_input_json: str | None,
    raw_output_json: str | None,
    telegram_message: str | None = None,
    error_message: str | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> MarketReport:
    """Save one cached market report generation attempt."""
    report = MarketReport(
        report_type=report_type.lower(),
        generated_at=generated_at,
        expires_at=expires_at,
        status=status,
        raw_input_json=raw_input_json,
        raw_output_json=raw_output_json,
        telegram_message=telegram_message,
        error_message=error_message,
        provider=provider,
        model=model,
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report


async def get_latest_market_report(
    session: AsyncSession,
    *,
    report_type: str,
    statuses: set[str] | None = None,
) -> MarketReport | None:
    """Return the newest cached market report for a cadence."""
    statement = (
        select(MarketReport)
        .where(MarketReport.report_type == report_type.lower())
        .order_by(MarketReport.generated_at.desc(), MarketReport.id.desc())
        .limit(1)
    )
    if statuses is not None:
        statement = statement.where(MarketReport.status.in_(sorted(statuses)))
    return await session.scalar(statement)


async def save_llm_usage_log(
    session: AsyncSession,
    *,
    provider: str,
    model: str,
    call_type: str,
    status: str,
    symbol: str | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
    input_chars: int | None = None,
    output_chars: int | None = None,
    max_tokens: int | None = None,
    rate_limit_limit_requests: str | None = None,
    rate_limit_remaining_requests: str | None = None,
    rate_limit_reset_requests: str | None = None,
    rate_limit_limit_tokens: str | None = None,
    rate_limit_remaining_tokens: str | None = None,
    rate_limit_reset_tokens: str | None = None,
    retry_after: str | None = None,
    error_reason: str | None = None,
    error_message: str | None = None,
) -> LlmUsageLog:
    """Save one LLM usage telemetry row."""
    row = LlmUsageLog(
        provider=provider,
        model=model,
        call_type=call_type,
        symbol=symbol.upper() if symbol else None,
        status=status,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        input_chars=input_chars,
        output_chars=output_chars,
        max_tokens=max_tokens,
        rate_limit_limit_requests=rate_limit_limit_requests,
        rate_limit_remaining_requests=rate_limit_remaining_requests,
        rate_limit_reset_requests=rate_limit_reset_requests,
        rate_limit_limit_tokens=rate_limit_limit_tokens,
        rate_limit_remaining_tokens=rate_limit_remaining_tokens,
        rate_limit_reset_tokens=rate_limit_reset_tokens,
        retry_after=retry_after,
        error_reason=error_reason,
        error_message=error_message,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def update_llm_usage_log_status(
    session: AsyncSession,
    *,
    usage_log_id: int,
    status: str,
    error_reason: str | None = None,
    error_message: str | None = None,
) -> LlmUsageLog | None:
    """Update a usage row when downstream JSON schema validation fails."""
    row = await session.get(LlmUsageLog, usage_log_id)
    if row is None:
        return None
    row.status = status
    row.error_reason = error_reason
    row.error_message = error_message
    await session.commit()
    await session.refresh(row)
    return row


async def get_latest_market_heartbeat(
    session: AsyncSession,
    *,
    symbol: str,
    statuses: set[str] | None = None,
) -> MarketHeartbeat | None:
    statement = (
        select(MarketHeartbeat)
        .where(MarketHeartbeat.symbol == symbol.upper())
        .order_by(MarketHeartbeat.generated_at.desc(), MarketHeartbeat.id.desc())
        .limit(1)
    )
    if statuses is not None:
        statement = statement.where(MarketHeartbeat.status.in_(sorted(statuses)))
    return await session.scalar(statement)


async def get_latest_event_analysis_attempt(
    session: AsyncSession,
) -> EventAiAnalysis | None:
    """Return the most recent LLM event-analysis attempt."""
    return await session.scalar(
        select(EventAiAnalysis)
        .where(EventAiAnalysis.analysis_type == "event_analysis")
        .order_by(EventAiAnalysis.created_at.desc(), EventAiAnalysis.id.desc())
        .limit(1)
    )


async def get_latest_event_analysis_by_statuses(
    session: AsyncSession,
    statuses: set[str],
) -> EventAiAnalysis | None:
    """Return the latest event-analysis row whose status is in statuses."""
    return await session.scalar(
        select(EventAiAnalysis)
        .where(EventAiAnalysis.analysis_type == "event_analysis")
        .where(EventAiAnalysis.status.in_(sorted(statuses)))
        .order_by(EventAiAnalysis.created_at.desc(), EventAiAnalysis.id.desc())
        .limit(1)
    )


async def count_market_events(session: AsyncSession, symbol: str | None = None) -> int:
    """Return the number of stored market events, optionally for one symbol."""
    statement = select(func.count()).select_from(MarketEvent)
    if symbol:
        statement = statement.where(MarketEvent.symbol == symbol.upper())
    return int(await session.scalar(statement) or 0)


async def get_recent_market_events(
    session: AsyncSession, *, symbol: str | None = None, limit: int = 20
) -> list[MarketEvent]:
    """Return recent market events, newest first."""
    statement = select(MarketEvent)
    if symbol:
        statement = statement.where(MarketEvent.symbol == symbol.upper())
    result = await session.scalars(
        statement.order_by(MarketEvent.detected_at.desc(), MarketEvent.id.desc()).limit(limit)
    )
    return list(result.all())
