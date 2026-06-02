from __future__ import annotations

import os
import re

_SECRET_URL_RE = re.compile(r"([a-z][a-z0-9+.-]*://[^:\s/@]+:)([^@\s]+)(@)", re.IGNORECASE)
_KEY_VALUE_SECRET_RE = re.compile(
    r"(?i)\b([a-z0-9_-]*(?:token|api[_-]?key|password|secret|session[_-]?token|"
    r"database[_-]?url|private[_-]?key)[a-z0-9_-]*)(\s*[:=]\s*)([^\s]+)"
)
_PRIVATE_KEY_VALUE_RE = re.compile(
    r"(?i)\b(telegram_user_id|telegram_chat_id|sent_to_chat_id|chat_id|user_id|"
    r"username|first_name|provider_payment_id|telegram_payment_charge_id|"
    r"provider_payment_charge_id|provider_subscription_id|invoice_payload|payload)"
    r"(\s*[:=]\s*)([^\s,]+)"
)


def collect_secret_values() -> tuple[str, ...]:
    secret_names = {
        "TELEGRAM_BOT_TOKEN",
        "GROQ_API_KEY",
        "DATABASE_URL",
        "POSTGRES_PASSWORD",
    }
    values = []
    for name in secret_names:
        value = os.getenv(name)
        if value and len(value) >= 6:
            values.append(value)
    return tuple(values)


def redact_message(message: str, secret_values: tuple[str, ...] = ()) -> str:
    redacted = message
    for value in secret_values:
        redacted = redacted.replace(value, "[REDACTED]")
    redacted = _SECRET_URL_RE.sub(r"\1[REDACTED]\3", redacted)
    redacted = _KEY_VALUE_SECRET_RE.sub(r"\1\2[REDACTED]", redacted)
    return _PRIVATE_KEY_VALUE_RE.sub(r"\1\2[REDACTED]", redacted)
