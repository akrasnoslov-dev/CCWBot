"""Runtime helpers for admin-configured Telegram forum topic routing."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from bot.db.database import (
    delete_coin_topic_route,
    get_coin_topic_route,
    list_coin_topic_routes,
    upsert_coin_topic_route,
)
from bot.domain.supported_coins import SUPPORTED_SYMBOLS, is_supported_symbol, normalize_symbol
from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL
from bot.storage import load_state, save_state

logger = logging.getLogger(__name__)
STATE_TOPIC_ROUTES_KEY = "coin_topic_routes"


@dataclass(frozen=True)
class CoinTopicRouteConfig:
    symbol: str
    chat_id: int
    message_thread_id: int


def _route_from_state(symbol: str, payload: object) -> CoinTopicRouteConfig | None:
    if not isinstance(payload, dict):
        return None
    try:
        return CoinTopicRouteConfig(
            symbol=normalize_symbol(symbol),
            chat_id=int(payload["chat_id"]),
            message_thread_id=int(payload["message_thread_id"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _route_from_db(row) -> CoinTopicRouteConfig:
    return CoinTopicRouteConfig(
        symbol=normalize_symbol(row.symbol),
        chat_id=int(row.chat_id),
        message_thread_id=int(row.message_thread_id),
    )


async def get_runtime_coin_topic_route(symbol: str) -> CoinTopicRouteConfig | None:
    normalized_symbol = normalize_symbol(symbol)
    if not is_supported_symbol(normalized_symbol):
        return None
    if DB_ENABLED and DB_SESSION_LOCAL:
        async with DB_SESSION_LOCAL() as session:
            row = await get_coin_topic_route(session, normalized_symbol)
        return _route_from_db(row) if row else None

    state = load_state()
    routes = state.get(STATE_TOPIC_ROUTES_KEY, {})
    if not isinstance(routes, dict):
        return None
    return _route_from_state(normalized_symbol, routes.get(normalized_symbol))


async def list_runtime_coin_topic_routes() -> list[CoinTopicRouteConfig]:
    if DB_ENABLED and DB_SESSION_LOCAL:
        async with DB_SESSION_LOCAL() as session:
            rows = await list_coin_topic_routes(session)
        return [_route_from_db(row) for row in rows if is_supported_symbol(row.symbol)]

    state = load_state()
    routes = state.get(STATE_TOPIC_ROUTES_KEY, {})
    if not isinstance(routes, dict):
        return []
    configured = []
    for symbol in SUPPORTED_SYMBOLS:
        route = _route_from_state(symbol, routes.get(symbol))
        if route:
            configured.append(route)
    return configured


async def save_runtime_coin_topic_route(
    *,
    symbol: str,
    chat_id: int,
    message_thread_id: int,
) -> CoinTopicRouteConfig:
    normalized_symbol = normalize_symbol(symbol)
    if not is_supported_symbol(normalized_symbol):
        raise ValueError("Unsupported symbol.")
    if DB_ENABLED and DB_SESSION_LOCAL:
        async with DB_SESSION_LOCAL() as session:
            row = await upsert_coin_topic_route(
                session,
                symbol=normalized_symbol,
                chat_id=chat_id,
                message_thread_id=message_thread_id,
            )
        logger.info(
            "ops_event=coin_topic_route_configured symbol=%s chat_id=%s message_thread_id=%s",
            normalized_symbol.upper(),
            int(chat_id),
            int(message_thread_id),
        )
        return _route_from_db(row)

    state = load_state()
    routes = state.get(STATE_TOPIC_ROUTES_KEY)
    if not isinstance(routes, dict):
        routes = {}
    routes[normalized_symbol] = {
        "chat_id": int(chat_id),
        "message_thread_id": int(message_thread_id),
    }
    state[STATE_TOPIC_ROUTES_KEY] = routes
    save_state(state)
    logger.info(
        "ops_event=coin_topic_route_configured symbol=%s chat_id=%s message_thread_id=%s",
        normalized_symbol.upper(),
        int(chat_id),
        int(message_thread_id),
    )
    return CoinTopicRouteConfig(
        symbol=normalized_symbol,
        chat_id=int(chat_id),
        message_thread_id=int(message_thread_id),
    )


async def clear_runtime_coin_topic_route(symbol: str) -> bool:
    normalized_symbol = normalize_symbol(symbol)
    if not is_supported_symbol(normalized_symbol):
        raise ValueError("Unsupported symbol.")
    if DB_ENABLED and DB_SESSION_LOCAL:
        async with DB_SESSION_LOCAL() as session:
            removed = await delete_coin_topic_route(session, normalized_symbol)
        if removed:
            logger.info(
                "ops_event=coin_topic_route_cleared symbol=%s",
                normalized_symbol.upper(),
            )
        return removed

    state = load_state()
    routes = state.get(STATE_TOPIC_ROUTES_KEY)
    if not isinstance(routes, dict) or normalized_symbol not in routes:
        return False
    routes.pop(normalized_symbol, None)
    state[STATE_TOPIC_ROUTES_KEY] = routes
    save_state(state)
    logger.info("ops_event=coin_topic_route_cleared symbol=%s", normalized_symbol.upper())
    return True
