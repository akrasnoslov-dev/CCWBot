import logging

from bot.observability.error_file_logging import AttributableFormatter
from bot.observability.operational_logging import enable_operational_file_logging

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    # Apply the same continuation-line prefixing to the console stream that the persistent
    # file handlers use, so a traceback captured from `docker compose logs` stays attributable
    # line by line instead of trailing off into unlabelled context.
    #
    # Restricted to plain stream handlers on purpose: the file handlers install
    # RedactingFormatter, and overwriting one of those with the non-redacting formatter would
    # let secrets reach a log file an admin can export.
    for handler in logging.getLogger().handlers:
        if type(handler) is logging.StreamHandler:
            handler.setFormatter(AttributableFormatter(LOG_FORMAT))
    logging.getLogger("alembic").setLevel(logging.WARNING)
    logging.getLogger("alembic.runtime.migration").setLevel(logging.WARNING)
    logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    enable_operational_file_logging()
