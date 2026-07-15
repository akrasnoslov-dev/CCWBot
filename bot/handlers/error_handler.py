"""Global python-telegram-bot error handler.

Log-only: never sends anything to Telegram users. Transient network errors
(``telegram.error.NetworkError`` and subclasses, e.g. Bad Gateway / timeouts during
polling) produce one concise WARNING line instead of the multi-line unhandled-exception
traceback PTB dumps when no error handler is registered. Everything else keeps a full
ERROR with traceback.
"""

import logging

from telegram.error import NetworkError

logger = logging.getLogger(__name__)


async def handle_application_error(update: object, context) -> None:
    error = getattr(context, "error", None)
    if isinstance(error, NetworkError):
        message = " ".join(str(error).split())[:200]
        logger.warning(
            "ops_event=telegram_transient_network_error error_class=%s message=%s",
            type(error).__name__,
            message,
        )
        return
    logger.error(
        "ops_event=telegram_application_error error_class=%s",
        type(error).__name__,
        exc_info=error,
    )
