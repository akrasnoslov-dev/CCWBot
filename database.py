"""Database infrastructure for optional PostgreSQL runtime storage."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
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

    source = _collapse_whitespace(str(news_item.get("source") or "")).lower()
    title = _collapse_whitespace(str(news_item.get("title") or "")).lower()
    if title:
        fallback_identity = f"{source}:{title}" if source else title
        return f"source_title:{sha256(fallback_identity.encode('utf-8')).hexdigest()}"

    return ""


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(64), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    user: Mapped[User] = relationship(back_populates="settings")


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    btc_alert_threshold_percent: Mapped[float] = mapped_column(Float)
    automatic_check_interval_seconds: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class PriceState(Base):
    __tablename__ = "price_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    last_price: Mapped[float] = mapped_column(Float)
    last_24h_change: Mapped[float] = mapped_column(Float)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_alert_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
    market_event_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event_ai_analysis_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class MarketEvent(Base):
    __tablename__ = "market_events"
    __table_args__ = (UniqueConstraint("event_key", name="uq_market_events_event_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    event_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    price: Mapped[float] = mapped_column(Float)
    previous_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_change_percent: Mapped[float] = mapped_column(Float)
    last_24h_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_7d_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    ai_analyses: Mapped[list[EventAiAnalysis]] = relationship(back_populates="market_event")


class EventAiAnalysis(Base):
    __tablename__ = "event_ai_analyses"
    __table_args__ = (
        UniqueConstraint(
            "market_event_id",
            "input_hash",
            name="uq_event_ai_analyses_market_event_input_hash",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    market_event_id: Mapped[int] = mapped_column(ForeignKey("market_events.id"), index=True)
    provider: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(255))
    input_hash: Mapped[str] = mapped_column(String(128), index=True)
    analysis_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    plain_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    html_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(64), default="completed", index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    market_event: Mapped[MarketEvent] = relationship(back_populates="ai_analyses")


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

    project_root = Path(__file__).resolve().parent
    config = Config(str(project_root / "alembic.ini"))
    config.set_main_option("script_location", str(project_root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    config.attributes["database_url"] = database_url
    config.attributes["configure_logger"] = False
    command.upgrade(config, "head")


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
    """Create or update a user row for current Telegram interaction."""
    user = await session.scalar(
        select(User).where(User.telegram_user_id == telegram_user_id).limit(1)
    )
    role = "admin" if _same_telegram_user_id(telegram_user_id, admin_user_id) else "user"
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
    await session.commit()
    await session.refresh(user)
    return user


async def get_user_role(session: AsyncSession, telegram_user_id: int) -> str | None:
    user = await session.scalar(
        select(User).where(User.telegram_user_id == telegram_user_id).limit(1)
    )
    return user.role if user else None


async def get_active_users_with_chat_ids(session: AsyncSession) -> list[User]:
    """Return active users that can receive automatic Telegram alerts."""
    result = await session.scalars(
        select(User)
        .where(User.telegram_chat_id.isnot(None))
        .where(User.is_active.is_(True))
        .order_by(User.id.asc())
    )
    return list(result.all())


async def _get_app_settings_row(
    session: AsyncSession, *, default_threshold: float, default_interval: int
):
    settings = await session.scalar(select(AppSettings).order_by(AppSettings.id.asc()).limit(1))
    if settings is None:
        settings = AppSettings(
            btc_alert_threshold_percent=default_threshold,
            automatic_check_interval_seconds=default_interval,
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
    }


async def update_app_settings(
    session: AsyncSession,
    *,
    default_threshold: float,
    default_interval: int,
    threshold: float | None = None,
    interval_seconds: int | None = None,
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


async def save_alert(
    session: AsyncSession,
    *,
    symbol: str,
    alert_type: str,
    message: str,
    sent_to_chat_id: int,
    market_event_id: int | None = None,
    event_ai_analysis_id: int | None = None,
    user_id: int | None = None,
    status: str | None = None,
    error_message: str | None = None,
):
    alert = Alert(
        symbol=symbol.upper(),
        alert_type=alert_type,
        message=message,
        sent_to_chat_id=sent_to_chat_id,
        market_event_id=market_event_id,
        event_ai_analysis_id=event_ai_analysis_id,
        user_id=user_id,
        status=status,
        error_message=error_message,
    )
    session.add(alert)
    await session.commit()
    await session.refresh(alert)
    return alert


async def get_or_create_market_event(
    session: AsyncSession,
    *,
    symbol: str,
    event_type: str,
    event_key: str,
    price: float,
    price_change_percent: float,
    previous_price: float | None = None,
    last_24h_change: float | None = None,
    last_7d_change: float | None = None,
    detected_at: datetime | None = None,
) -> MarketEvent:
    """Return the market event for event_key, creating it when needed."""
    existing = await session.scalar(
        select(MarketEvent).where(MarketEvent.event_key == event_key).limit(1)
    )
    if existing:
        return existing

    market_event = MarketEvent(
        symbol=symbol.upper(),
        event_type=event_type,
        event_key=event_key,
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
            select(MarketEvent).where(MarketEvent.event_key == event_key).limit(1)
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
