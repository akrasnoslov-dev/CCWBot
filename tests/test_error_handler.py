"""Global PTB error handler: concise WARNING for transient network errors, ERROR otherwise."""

import logging
from types import SimpleNamespace

import pytest
from telegram.error import NetworkError, TimedOut

from bot.handlers.error_handler import handle_application_error


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [NetworkError("Bad Gateway"), TimedOut("Timed out")],
)
async def test_transient_network_error_logs_one_concise_warning(error, caplog):
    with caplog.at_level(logging.DEBUG):
        await handle_application_error(None, SimpleNamespace(error=error))

    records = [
        record
        for record in caplog.records
        if "telegram_transient_network_error" in record.getMessage()
    ]
    assert len(records) == 1
    record = records[0]
    assert record.levelno == logging.WARNING
    assert f"error_class={type(error).__name__}" in record.getMessage()
    # One concise line: no traceback attached and no multi-line dump.
    assert record.exc_info is None
    assert "\n" not in record.getMessage()
    assert not any(record.levelno >= logging.ERROR for record in caplog.records)


@pytest.mark.asyncio
async def test_non_network_error_logs_error_with_traceback(caplog):
    try:
        raise ValueError("unexpected handler failure")
    except ValueError as raised:
        error = raised

    with caplog.at_level(logging.DEBUG):
        await handle_application_error(None, SimpleNamespace(error=error))

    records = [
        record
        for record in caplog.records
        if "telegram_application_error" in record.getMessage()
    ]
    assert len(records) == 1
    record = records[0]
    assert record.levelno == logging.ERROR
    assert "error_class=ValueError" in record.getMessage()
    assert record.exc_info is not None
