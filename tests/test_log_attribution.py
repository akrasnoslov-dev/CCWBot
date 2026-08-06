"""Multi-line log records stay attributable, and candidate crossings are recorded."""

import logging

from bot.observability.error_file_logging import AttributableFormatter, RedactingFormatter

FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def _record(message, *, exc_info=None):
    return logging.LogRecord(
        name="bot.alerts",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=exc_info,
    )


def _exc_info():
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        return sys.exc_info()


def test_single_line_records_are_untouched():
    formatted = AttributableFormatter(FORMAT).format(_record("plain message"))

    assert formatted.count("\n") == 0
    assert formatted.endswith("plain message")


def test_traceback_continuation_lines_carry_the_timestamp():
    # An unprefixed traceback tail cannot be tied back to the event that produced it once it
    # lands at the end of a captured log tail, which is exactly when a bundle gets collected.
    formatter = AttributableFormatter(FORMAT)
    record = _record("event analysis blew up", exc_info=_exc_info())

    lines = formatter.format(record).split("\n")

    assert len(lines) > 1
    timestamp = formatter.formatTime(record, formatter.datefmt)
    for line in lines[1:]:
        assert line.startswith(f"{timestamp} | ")
    assert any("ValueError: boom" in line for line in lines)


def test_redacting_formatter_keeps_both_behaviours(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "groq-secret-value-1234")
    formatter = RedactingFormatter(FORMAT)
    record = _record("failed with groq-secret-value-1234", exc_info=_exc_info())

    formatted = formatter.format(record)

    assert "groq-secret-value-1234" not in formatted
    timestamp = formatter.formatTime(record, formatter.datefmt)
    for line in formatted.split("\n")[1:]:
        assert line.startswith(f"{timestamp} | ")


def test_candidate_crossing_is_recorded_independently_of_the_llm(caplog):
    # Market events are only created after a successful analysis, so a dead LLM yields zero
    # events rather than events without analyses. This line is what makes "detections
    # happening but zero market events created" measurable rather than inferred.
    from bot import alerts

    payload = {
        "symbol": "btc",
        "market": {"chg_window": -4.2, "chg24h": -6.1},
        "analysed_window_minutes": 30,
    }

    with caplog.at_level(logging.INFO, logger="bot.alerts"):
        alerts._log_event_alert_candidate_crossing(
            "btc", payload, alert_threshold_percent=3.0
        )

    message = caplog.records[0].getMessage()
    assert "ops_event=event_alert_candidate_crossing" in message
    assert "symbol=BTC" in message
    assert "analysed_window_change_percent=-4.2" in message
    assert "crossed_threshold=true" in message


def test_candidate_crossing_reports_below_threshold_moves_too(caplog):
    from bot import alerts

    payload = {"symbol": "btc", "market": {"chg_window": 0.4, "chg24h": 1.0}}

    with caplog.at_level(logging.INFO, logger="bot.alerts"):
        alerts._log_event_alert_candidate_crossing(
            "btc", payload, alert_threshold_percent=3.0
        )

    assert "crossed_threshold=false" in caplog.records[0].getMessage()


def test_candidate_crossing_survives_a_missing_market_block(caplog):
    from bot import alerts

    with caplog.at_level(logging.INFO, logger="bot.alerts"):
        alerts._log_event_alert_candidate_crossing("btc", {}, alert_threshold_percent=None)

    message = caplog.records[0].getMessage()
    assert "crossed_threshold=false" in message
    assert "analysed_window_change_percent=None" in message


def test_candidate_crossing_carries_no_recipient_or_message_data(caplog):
    from bot import alerts

    payload = {
        "symbol": "btc",
        "market": {"chg_window": -4.2},
        "news": [{"news_id": "n1", "title": "secret headline"}],
        "recipients": [12345678],
    }

    with caplog.at_level(logging.INFO, logger="bot.alerts"):
        alerts._log_event_alert_candidate_crossing(
            "btc", payload, alert_threshold_percent=3.0
        )

    message = caplog.records[0].getMessage()
    assert "secret headline" not in message
    assert "12345678" not in message
