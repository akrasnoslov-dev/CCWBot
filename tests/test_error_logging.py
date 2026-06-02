import logging

import pytest

from bot.observability import error_file_logging as error_logging


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


def test_legacy_error_logging_module_reexports_public_helpers():
    from bot import error_logging as legacy_error_logging

    assert legacy_error_logging.enable_error_file_logging is error_logging.enable_error_file_logging
    assert (
        legacy_error_logging.build_sanitized_log_exports
        is error_logging.build_sanitized_log_exports
    )


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
        ("TELEGRAM_BOT_TOKEN: abc123", "TELEGRAM_BOT_TOKEN: [REDACTED]"),
        ("DATABASE_URL=postgresql://user:password@example/db", "DATABASE_URL=[REDACTED]"),
        ("private_key: secret-value", "private_key: [REDACTED]"),
    ],
)
def test_redact_masks_common_secret_shapes(message, expected):
    assert error_logging._redact(message, ()) == expected


def test_log_export_uses_configured_file_and_redacts(monkeypatch, tmp_path):
    log_file = tmp_path / "ccwbot-warnings-errors.log"
    log_file.write_text(
        "token=abc123\npostgresql://user:secret@db/name\nnormal line",
        encoding="utf-8",
    )
    monkeypatch.setattr(error_logging, "ERROR_LOG_FILE", log_file)
    monkeypatch.setattr(error_logging, "_active_error_log_path", lambda: None)

    exports = error_logging.build_sanitized_log_exports()

    assert [export.file_name for export in exports] == ["ccwbot-warnings-errors.log"]
    assert exports[0].content.decode("utf-8").splitlines() == [
        "token=[REDACTED]",
        "postgresql://user:[REDACTED]@db/name",
        "normal line",
    ]


def test_log_export_includes_rotated_files(monkeypatch, tmp_path):
    log_file = tmp_path / "ccwbot-warnings-errors.log"
    rotated_log_file = tmp_path / "ccwbot-warnings-errors.log.1"
    log_file.write_text("current", encoding="utf-8")
    rotated_log_file.write_text("rotated", encoding="utf-8")
    monkeypatch.setattr(error_logging, "ERROR_LOG_FILE", log_file)
    monkeypatch.setattr(error_logging, "_active_error_log_path", lambda: None)

    exports = error_logging.build_sanitized_log_exports()

    assert [export.file_name for export in exports] == [
        "ccwbot-warnings-errors.log",
        "ccwbot-warnings-errors.log.1",
    ]
