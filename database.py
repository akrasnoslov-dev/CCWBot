"""Database infrastructure for optional PostgreSQL support.

This module is intentionally lightweight and does not replace existing JSON state.
If DATABASE_URL is configured, main.py can initialize these tables for future use.
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.exc import IntegrityError
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

    title = _collapse_whitespace(str(news_item.get("title") or "")).lower()
    if title:
        return f"title:{sha256(title.encode('utf-8')).hexdigest()}"

    return ""


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(Integer, index=True)
    telegram_chat_id: Mapped[int] = mapped_column(Integer, index=True)
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
    sent_to_chat_id: Mapped[int] = mapped_column(Integer, index=True)
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


def was_news_seen(session, news_key: str) -> bool:
    """Return True when a news key already exists in seen_news."""
    if not news_key:
        return False
    return session.query(SeenNews).filter_by(news_key=news_key).first() is not None


def mark_news_seen(session, news_item: dict):
    """Store one news item in seen_news if it has not been stored before."""
    news_key = make_news_key(news_item)
    if not news_key:
        return None

    existing = session.query(SeenNews).filter_by(news_key=news_key).first()
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
        session.commit()
    except IntegrityError:
        session.rollback()
        return session.query(SeenNews).filter_by(news_key=news_key).first()
    session.refresh(row)
    return row


def mark_news_items_seen(session, news_items: list[dict]) -> list[SeenNews]:
    """Store multiple news items while skipping duplicates."""
    rows = []
    for item in news_items:
        news_key = make_news_key(item)
        if not news_key or was_news_seen(session, news_key):
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
        session.commit()
    except IntegrityError:
        session.rollback()
        stored_rows = []
        for item in news_items:
            row = mark_news_seen(session, item)
            if row:
                stored_rows.append(row)
        return stored_rows

    for row in rows:
        session.refresh(row)
    return rows


def get_recent_seen_news(session, limit: int = 100) -> list[SeenNews]:
    """Return recent seen news rows, newest first."""
    return (
        session.query(SeenNews)
        .order_by(SeenNews.seen_at.desc(), SeenNews.id.desc())
        .limit(limit)
        .all()
    )


def cleanup_seen_news(session, keep_latest: int = 100) -> int:
    """Keep only the latest seen_news rows and return how many were deleted."""
    if keep_latest < 1:
        raise ValueError("keep_latest must be at least 1.")

    rows_to_delete = (
        session.query(SeenNews)
        .order_by(SeenNews.seen_at.desc(), SeenNews.id.desc())
        .offset(keep_latest)
        .all()
    )
    for row in rows_to_delete:
        session.delete(row)
    session.commit()
    return len(rows_to_delete)


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
