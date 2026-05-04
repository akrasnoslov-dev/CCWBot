"""Database infrastructure for optional PostgreSQL support.

This module is intentionally lightweight and does not replace existing JSON state.
If DATABASE_URL is configured, main.py can initialize these tables for future use.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


def utc_now() -> datetime:
    """Return timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(64), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    settings: Mapped[list[UserSettings]] = relationship(back_populates="user")


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    price_move_alert_percent: Mapped[float] = mapped_column(Float)
    automatic_check_interval_seconds: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    user: Mapped[User] = relationship(back_populates="settings")


class PriceState(Base):
    __tablename__ = "price_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    last_price: Mapped[float] = mapped_column(Float)
    last_24h_change: Mapped[float] = mapped_column(Float)
    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_alert_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class SeenNews(Base):
    __tablename__ = "seen_news"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    news_key: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(1000))
    link: Mapped[str] = mapped_column(String(2000))
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    alert_type: Mapped[str] = mapped_column(String(64), index=True)
    message: Mapped[str] = mapped_column(Text)
    sent_to_chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


def init_db(database_url: str):
    """Create SQLAlchemy engine/session factory and initialise tables."""
    engine = create_engine(database_url, future=True)
    SessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    Base.metadata.create_all(bind=engine)
    return engine, SessionLocal


def get_or_create_user(
    session,
    *,
    telegram_user_id: int,
    telegram_chat_id: int,
    username: str | None,
    first_name: str | None,
    admin_user_id: int | str | None,
):
    """Create or update a user row for current Telegram interaction."""
    user = session.query(User).filter_by(telegram_user_id=telegram_user_id).first()
    role = "admin" if admin_user_id is not None and str(telegram_user_id) == str(admin_user_id) else "user"
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
        user.role = role
        user.is_active = True
        user.updated_at = utc_now()
    session.commit()
    session.refresh(user)
    return user


def get_user_role(session, telegram_user_id: int) -> str | None:
    user = session.query(User).filter_by(telegram_user_id=telegram_user_id).first()
    return user.role if user else None


def get_or_create_user_settings(
    session,
    *,
    user_id: int,
    default_threshold: float,
    default_interval: int,
):
    settings = session.query(UserSettings).filter_by(user_id=user_id).first()
    if settings is None:
        settings = UserSettings(
            user_id=user_id,
            price_move_alert_percent=default_threshold,
            automatic_check_interval_seconds=default_interval,
        )
        session.add(settings)
        session.commit()
        session.refresh(settings)
    return settings


def update_user_settings(
    session,
    *,
    user_id: int,
    threshold: float | None = None,
    interval_seconds: int | None = None,
):
    settings = session.query(UserSettings).filter_by(user_id=user_id).first()
    if settings is None:
        raise ValueError("User settings row not found.")
    if threshold is not None:
        settings.price_move_alert_percent = threshold
    if interval_seconds is not None:
        settings.automatic_check_interval_seconds = interval_seconds
    settings.updated_at = utc_now()
    session.commit()
    session.refresh(settings)
    return settings


def get_price_state(session, symbol: str):
    return session.query(PriceState).filter_by(symbol=symbol.upper()).first()


def update_price_state(
    session,
    *,
    symbol: str,
    last_price: float,
    last_24h_change: float,
    last_checked_at: datetime | None,
    last_alert_at: datetime | None = None,
):
    row = get_price_state(session, symbol)
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
    session.commit()
    session.refresh(row)
    return row


def save_alert(
    session, *, symbol: str, alert_type: str, message: str, sent_to_chat_id: int
):
    alert = Alert(
        symbol=symbol.upper(),
        alert_type=alert_type,
        message=message,
        sent_to_chat_id=sent_to_chat_id,
    )
    session.add(alert)
    session.commit()
    session.refresh(alert)
    return alert
