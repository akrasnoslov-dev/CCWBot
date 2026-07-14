from __future__ import annotations

from datetime import datetime, timezone

from ops_agent.redaction import RedactionReport, ReferenceMapper, redact_text, redact_value
from ops_agent.state import record_collection, record_report_success, resolve_period


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


def test_record_collection_persists_failed_collector_names():
    period = resolve_period(
        state={},
        period=None,
        since="2026-06-01T00:00:00Z",
        until="2026-06-01T12:00:00Z",
    )

    state = record_collection(
        {},
        bundle_id="bundle",
        status="partial",
        period=period,
        failed_collectors=["logs.bot.log", "db.alerts_summary"],
    )

    assert state["last_collection"]["failed_collectors"] == [
        "db.alerts_summary",
        "logs.bot.log",
    ]
    assert state["recent_runs"][0]["failed_collectors"] == [
        "db.alerts_summary",
        "logs.bot.log",
    ]


def test_record_collection_records_empty_failed_collectors_for_complete_runs():
    period = resolve_period(
        state={},
        period=None,
        since="2026-06-01T00:00:00Z",
        until="2026-06-01T12:00:00Z",
    )

    state = record_collection({}, bundle_id="bundle", status="complete", period=period)

    assert state["last_collection"]["failed_collectors"] == []


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


def test_redaction_does_not_mask_structural_non_secrets():
    # July 2026 over-masking regression: model names, event_instance_key, and traceback
    # file paths rendered as [REDACTED_SECRET].
    mapper = ReferenceMapper(salt=b"test-salt")
    report = RedactionReport()
    structural_values = [
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "llama-3.3-70b-versatile",
        "btc_price_downtrend_20260710_1300_window60",
        "/opt/CCWBot/bot/services/ai_agent_groq.py",
    ]

    for value in structural_values:
        redacted = redact_text(f"field={value}", mapper, report)
        assert value in redacted, value
        assert "[REDACTED_SECRET]" not in redacted, value


def test_redaction_still_masks_real_secret_shapes():
    mapper = ReferenceMapper(salt=b"test-salt")
    report = RedactionReport()
    secret_values = [
        "sk-Abc123Def456Ghi789Jkl012Mno345Pqr678",
        "sk_live_1234567890abcdefghijklmnopqrstuvwxyz",
        "ghp_16c1234567890abcdefghijklmnopqrstu42",
    ]

    for value in secret_values:
        redacted = redact_text(value, mapper, report)
        assert value not in redacted, value
        assert "[REDACTED_SECRET]" in redacted, value


def test_redact_value_does_not_mislabel_non_payment_payload_fields():
    # payload_points (a numeric evidence field) was previously rewritten to a
    # payment_ref:p_... reference because its key contains "payload".
    mapper = ReferenceMapper(salt=b"test-salt")
    report = RedactionReport()

    payload = redact_value(
        {"payload_points": 6, "invoice_payload": "ccwbot-premium-v1:u456", "payload": "x1"},
        mapper,
        report,
    )

    assert payload["payload_points"] == 6
    assert payload["invoice_payload"].startswith("payment_ref:p_")
    # The exact payments.payload column stays protected.
    assert payload["payload"].startswith("payment_ref:p_")


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
