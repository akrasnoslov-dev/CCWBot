from __future__ import annotations

from datetime import datetime, timezone

from ops_agent.redaction import RedactionReport, ReferenceMapper, redact_text, redact_value
from ops_agent.state import record_report_success, resolve_period


def test_auto_period_uses_last_successful_report():
    state = {
        "last_successful_report": {
            "period_end": "2026-06-01T00:00:00Z",
        }
    }
    now = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)

    period = resolve_period(state=state, period="auto", since=None, until=None, now=now)

    assert period.start.isoformat() == "2026-06-01T00:00:00+00:00"
    assert period.end == now
    assert period.source == "auto"


def test_auto_period_defaults_to_last_24_hours_without_success():
    now = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)

    period = resolve_period(state={}, period="auto", since=None, until=None, now=now)

    assert (period.end - period.start).total_seconds() == 24 * 3600


def test_record_report_success_advances_period():
    period = resolve_period(
        state={},
        period=None,
        since="2026-06-01T00:00:00Z",
        until="2026-06-01T12:00:00Z",
    )

    state = record_report_success(
        {},
        report_id="report",
        bundle_id="bundle",
        period=period,
        report_path="report.md",  # type: ignore[arg-type]
        bundle_path="bundle",  # type: ignore[arg-type]
        bundle_sha256="abc",
    )

    assert state["last_successful_report"]["period_end"] == "2026-06-01T12:00:00Z"


def test_redaction_masks_private_identifiers_and_secrets():
    mapper = ReferenceMapper(salt=b"test-salt")
    report = RedactionReport()

    redacted = redact_text(
        "user_id=123 chat_id=-456 token=abc123 username=satoshi "
        "postgresql://user:pass@postgres/db",
        mapper,
        report,
    )

    assert "123" not in redacted
    assert "-456" not in redacted
    assert "abc123" not in redacted
    assert "satoshi" not in redacted
    assert "pass" not in redacted
    assert "user_ref:u_" in redacted
    assert "chat_ref:c_" in redacted


def test_refs_are_stable_only_within_bundle_salt():
    first = ReferenceMapper(salt=b"one").ref("user", 123)
    assert first == ReferenceMapper(salt=b"one").ref("user", 123)
    assert first != ReferenceMapper(salt=b"two").ref("user", 123)


def test_redact_value_redacts_payment_fields():
    mapper = ReferenceMapper(salt=b"test-salt")
    report = RedactionReport()

    payload = redact_value(
        {"provider_payment_id": "pay_123", "telegram_user_id": 123},
        mapper,
        report,
    )

    assert payload["provider_payment_id"].startswith("payment_ref:p_")
    assert payload["telegram_user_id"].startswith("user_ref:u_")


def test_redaction_masks_json_colon_identifiers_and_payment_fields():
    mapper = ReferenceMapper(salt=b"test-salt")
    report = RedactionReport()

    redacted = redact_text(
        '"chat_id": 123, "user_id": 456, payment_id: pay_123, '
        'charge_id: ch_123, invoice_payload: ccwbot-premium-v1:u456, '
        'provider_subscription_id: sub_123',
        mapper,
        report,
    )

    assert '"chat_id": 123' not in redacted
    assert '"user_id": 456' not in redacted
    assert "pay_123" not in redacted
    assert "ch_123" not in redacted
    assert "ccwbot-premium-v1" not in redacted
    assert "sub_123" not in redacted
    assert "chat_ref:c_" in redacted
    assert "user_ref:u_" in redacted
    assert "payment_ref:p_" in redacted


def test_redaction_masks_secret_urls_database_urls_and_long_secret_like_values():
    mapper = ReferenceMapper(salt=b"test-salt")
    report = RedactionReport()
    long_secret = "sk_live_1234567890abcdefghijklmnopqrstuvwxyz"

    redacted = redact_text(
        'token: abc123 "api_key": "key-456" '
        "https://user:pass@example.com/path "
        "postgresql+asyncpg://user:dbpass@postgres:5432/ccwbot "
        f"{long_secret}",
        mapper,
        report,
    )

    assert "abc123" not in redacted
    assert "key-456" not in redacted
    assert "pass@example" not in redacted
    assert "dbpass" not in redacted
    assert long_secret not in redacted
    assert "[REDACTED_DATABASE_URL]" in redacted
