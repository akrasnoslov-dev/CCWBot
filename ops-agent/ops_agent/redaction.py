from __future__ import annotations

import hashlib
import hmac
import os
import re
from dataclasses import dataclass, field
from typing import Any

SECRET_URL_RE = re.compile(r"([a-z][a-z0-9+.-]*://[^:\s/@]+:)([^@\s]+)(@)", re.IGNORECASE)
KEY_VALUE_SECRET_RE = re.compile(
    r"(?i)\b([a-z0-9_-]*(?:token|api[_-]?key|password|secret|database[_-]?url|"
    r"private[_-]?key|charge[_-]?id|payment[_-]?id|invoice[_-]?payload|"
    r"provider[_-]?subscription[_-]?id)[a-z0-9_-]*)(\s*[:=]\s*)([^\s,]+)"
)
TELEGRAM_ID_RE = re.compile(
    r"(?i)\b(telegram_user_id|telegram_chat_id|chat_id|sent_to_chat_id|user_id)\s*=\s*(-?\d+)"
)
USERNAME_RE = re.compile(r"(?i)\b(username|first_name)\s*=\s*([^\s,]+)")


@dataclass
class RedactionReport:
    replacements: dict[str, int] = field(default_factory=dict)

    def increment(self, key: str) -> None:
        self.replacements[key] = self.replacements.get(key, 0) + 1

    def as_dict(self) -> dict[str, Any]:
        return {"schema_version": 1, "replacements": self.replacements}


class ReferenceMapper:
    def __init__(self, salt: bytes | None = None) -> None:
        self._salt = salt or os.urandom(32)
        self.identity_map: dict[str, dict[str, str]] = {"user": {}, "chat": {}, "payment": {}}

    def ref(self, namespace: str, value: Any) -> str:
        raw = str(value)
        digest = hmac.new(self._salt, f"{namespace}:{raw}".encode(), hashlib.sha256).hexdigest()[:6]
        prefix = {"user": "user_ref:u_", "chat": "chat_ref:c_", "payment": "payment_ref:p_"}[
            namespace
        ]
        ref = f"{prefix}{digest}"
        self.identity_map.setdefault(namespace, {})[raw] = ref
        return ref


def redact_text(text: str, mapper: ReferenceMapper, report: RedactionReport) -> str:
    redacted = text
    redacted, url_count = SECRET_URL_RE.subn(r"\1[REDACTED]\3", redacted)
    redacted, key_count = KEY_VALUE_SECRET_RE.subn(r"\1\2[REDACTED]", redacted)
    if url_count or key_count:
        report.replacements["secret"] = (
            report.replacements.get("secret", 0) + url_count + key_count
        )

    def replace_id(match: re.Match[str]) -> str:
        key = match.group(1).lower()
        namespace = "chat" if "chat" in key else "user"
        report.increment(namespace)
        return f"{match.group(1)}={mapper.ref(namespace, match.group(2))}"

    redacted = TELEGRAM_ID_RE.sub(replace_id, redacted)
    redacted, count = USERNAME_RE.subn(lambda match: f"{match.group(1)}=[REDACTED]", redacted)
    if count:
        report.replacements["name"] = report.replacements.get("name", 0) + count
    return redacted


def redact_error_message(
    error: Exception,
    mapper: ReferenceMapper,
    report: RedactionReport,
    *,
    limit: int = 300,
) -> str:
    message = f"{type(error).__name__}: {str(error)[:limit]}"
    return redact_text(message, mapper, report)


def redact_value(value: Any, mapper: ReferenceMapper, report: RedactionReport) -> Any:
    if isinstance(value, dict):
        return {key: redact_value_by_key(key, item, mapper, report) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_value(item, mapper, report) for item in value]
    if isinstance(value, str):
        return redact_text(value, mapper, report)
    return value


def redact_value_by_key(
    key: str,
    value: Any,
    mapper: ReferenceMapper,
    report: RedactionReport,
) -> Any:
    normalized = key.lower()
    if value is None:
        return None
    if normalized in {"telegram_user_id", "user_id"}:
        report.increment("user")
        return mapper.ref("user", value)
    if normalized in {"telegram_chat_id", "chat_id", "sent_to_chat_id"}:
        report.increment("chat")
        return mapper.ref("chat", value)
    if any(
        token in normalized
        for token in ("payment_id", "charge_id", "payload", "subscription_id")
    ):
        report.increment("payment")
        return mapper.ref("payment", value)
    if normalized in {"username", "first_name"}:
        report.increment("name")
        return "[REDACTED]"
    return redact_value(value, mapper, report)
