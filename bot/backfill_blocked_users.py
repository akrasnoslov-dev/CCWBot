"""One-time backfill for users who previously blocked the Telegram bot."""

from __future__ import annotations

import asyncio
import logging

from bot.config import DATABASE_URL
from bot.db.database import backfill_blocked_users_from_alerts, init_db

logger = logging.getLogger(__name__)


async def run_backfill() -> tuple[int, int]:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured.")
    engine, session_local = await init_db(DATABASE_URL)
    try:
        async with session_local() as session:
            matched_alerts, updated_users = await backfill_blocked_users_from_alerts(session)
    finally:
        await engine.dispose()
    logger.info(
        "Blocked-user backfill completed: %s matching failed alerts, %s users marked inactive.",
        matched_alerts,
        updated_users,
    )
    return matched_alerts, updated_users


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_backfill())


if __name__ == "__main__":
    main()
