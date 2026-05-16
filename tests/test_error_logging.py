import logging

import pytest

from bot import error_logging


def test_error_file_logging_writes_warning_and_traceback(tmp_path):
    log_file = tmp_path / "logs" / "ccwbot-warnings-errors.log"
    logger = logging.getLogger("tests.error_logging")

    error_logging.disable_error_file_logging()
    try:
        error_logging.enable_error_file_logging(log_file)
        logger.info("not persisted")
        try:
            raise RuntimeError("test failure")
        except RuntimeError:
            logger.exception("warning with traceback token=abc123secret")

        for handler in logging.getLogger().handlers:
            handler.flush()

        content = log_file.read_text(encoding="utf-8")
        assert "INFO" not in content
        assert "ERROR" in content
        assert "tests.error_logging" in content
        assert "Traceback" in content
        assert "RuntimeError: test failure" in content
        assert "token=[REDACTED]" in content
        assert "abc123secret" not in content
    finally:
        error_logging.disable_error_file_logging()


def test_error_file_logging_disable_stops_writes(tmp_path):
    log_file = tmp_path / "ccwbot.log"
    logger = logging.getLogger("tests.error_logging.disable")

    error_logging.disable_error_file_logging()
    error_logging.enable_error_file_logging(log_file)
    logger.warning("before disable")
    error_logging.disable_error_file_logging()
    logger.warning("after disable")

    content = log_file.read_text(encoding="utf-8")
    assert "before disable" in content
    assert "after disable" not in content
    assert not error_logging.is_error_file_logging_enabled()


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("postgresql://user:password@example/db", "postgresql://user:[REDACTED]@example/db"),
        ("api_key=secret-value", "api_key=[REDACTED]"),
    ],
)
def test_redact_masks_common_secret_shapes(message, expected):
    assert error_logging._redact(message, ()) == expected
