import asyncio
import time

from bot.config import (
    ENVIRONMENT,
    HEALTH_PORT,
    TELEGRAM_ADMIN_USER_IDS,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)
from bot.health import start_health_server, stop_health_server
from bot.observability.error_file_logging import apply_persisted_error_file_logging_state
from bot.observability.logging_setup import configure_logging
from bot.runtime import close_database, initialize_database, log
from bot.runtime.event_loop import create_event_loop, get_stop_signals
from bot.runtime.scheduler import schedule_runtime_jobs
from bot.runtime.telegram_app import build_application, register_handlers
from bot.services.price_service import warm_up_price_cache
from bot.settings import get_runtime_alert_settings
from bot.setup import setup_bot_commands


def validate_required_config() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is missing. Check your .env file.")
    if not TELEGRAM_CHAT_ID:
        raise ValueError("TELEGRAM_CHAT_ID is missing. Check your .env file.")
    if not TELEGRAM_ADMIN_USER_IDS:
        raise ValueError(
            "TELEGRAM_ADMIN_USER_ID or TELEGRAM_ADMIN_USER_IDS is missing. "
            "Check your .env file."
        )


async def initialize_runtime() -> None:
    await initialize_database()
    await apply_persisted_error_file_logging_state()
    await warm_up_price_cache()


def main() -> None:
    configure_logging()

    started_at = time.monotonic()
    health_runner = None
    loop = create_event_loop()
    asyncio.set_event_loop(loop)
    validate_required_config()

    log(f"ops_event=bot_start environment={ENVIRONMENT} health_port={HEALTH_PORT}")

    loop.run_until_complete(initialize_runtime())

    app = build_application()
    register_handlers(app)

    runtime_settings = loop.run_until_complete(get_runtime_alert_settings())
    schedule_runtime_jobs(
        app,
        automatic_check_interval_seconds=runtime_settings[
            "automatic_check_interval_seconds"
        ],
    )

    health_runner = loop.run_until_complete(
        start_health_server(HEALTH_PORT, started_at=started_at)
    )
    log(f"ops_event=health_started port={HEALTH_PORT}")
    log("ops_event=bot_polling_started automatic_market_checks=true")
    app.post_init = setup_bot_commands
    try:
        app.run_polling(close_loop=False, stop_signals=get_stop_signals())
    finally:
        log("ops_event=bot_shutdown_started")
        if not loop.is_closed():
            loop.run_until_complete(stop_health_server(health_runner))
        if not loop.is_closed():
            loop.run_until_complete(close_database())
        if not loop.is_closed():
            loop.close()
