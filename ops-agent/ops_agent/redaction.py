from __future__ import annotations

import hashlib
import hmac
import os
import re
from dataclasses import dataclass, field
from typing import Any

SECRET_URL_RE = re.compile(r"([a-z][a-z0-9+.-]*://[^:\s/@]+:)([^@\s]+)(@)", re.IGNORECASE)
DATABASE_URL_RE = re.compile(
    r"\b(?:postgres(?:ql)?|mysql|mariadb|mongodb)(?:\+[a-z0-9_]+)?://[^\s,\"'}]+",
    re.IGNORECASE,
)
KEY_VALUE_SECRET_RE = re.compile(
    r"(?i)([\"']?\b[a-z0-9_-]*(?:token|api[_-]?key|password|secret|database[_-]?url|"
    r"private[_-]?key)[a-z0-9_-]*[\"']?\s*[:=]\s*[\"']?)([^\"'\s,}]+)([\"']?)"
)
TELEGRAM_ID_RE = re.compile(
    r"(?i)([\"']?\b(?:telegram_user_id|telegram_chat_id|chat_id|sent_to_chat_id|user_id)"
    r"[\"']?\s*[:=]\s*)(-?\d+)"
)
PAYMENT_ID_RE = re.compile(
    r"(?i)([\"']?\b[a-z0-9_-]*(?:charge[_-]?id|payment[_-]?id|invoice[_-]?payload|"
    r"provider[_-]?subscription[_-]?id|subscription[_-]?id)[a-z0-9_-]*[\"']?"
    r"\s*[:=]\s*[\"']?)([^\"'\s,}]+)([\"']?)"
)
USERNAME_RE = re.compile(
    r"(?i)([\"']?\b(?:username|first_name)[\"']?\s*[:=]\s*[\"']?)"
    r"([^\"'\s,}]+)([\"']?)"
)
LONG_SECRET_RE = re.compile(
    r"\b(?=[A-Za-z0-9_./+=-]{32,}\b)(?=[A-Za-z0-9_./+=-]*[A-Za-z])"
    r"(?=[A-Za-z0-9_./+=-]*\d)[A-Za-z0-9_./+=-]{32,}\b"
)
# Structural, non-secret tokens the long-secret heuristic must not mask. These previously
# rendered as [REDACTED_SECRET] in reports: LLM model identifiers (llm_usage_summary and
# analysis samples), backend event keys such as event_instance_key, and traceback file
# paths. Real secrets stay masked: key-like prefixes (sk-, bearer, api keys) are handled
# by the dedicated patterns above and none of them fit these structural shapes.
_KNOWN_MODEL_FAMILY = (
    r"(?:meta-)?(?:llama|mixtral|mistral|magistral|gemma|gemini|qwen|deepseek|gpt|claude|"
    r"kimi|command|phi|grok|sonar)"
)
LONG_SECRET_ALLOWLIST_RES = (
    # LLM model identifiers, optionally vendor-prefixed: meta-llama/llama-4-scout-17b-...,
    # llama-3.3-70b-versatile, gemini-2.0-flash.
    re.compile(rf"(?i)^(?:[a-z0-9._-]+/)?{_KNOWN_MODEL_FAMILY}[a-z0-9._/-]*$"),
    # Absolute POSIX file paths with a file extension (traceback locations).
    re.compile(r"^/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.[A-Za-z0-9]{1,5}$"),
    # Lowercase snake_case structural keys (event_instance_key, canonical event keys,
    # semantic families): at least three short segments. The per-segment cap keeps
    # key-with-long-random-tail secrets (e.g. sk_live_<40 chars>) masked.
    re.compile(r"^[a-z0-9]{1,16}(?:_[a-z0-9]{1,16}){2,}$"),
)
# Snake_case tokens starting with a credential-style prefix are never structural keys.
_SECRET_PREFIX_RE = re.compile(
    r"(?i)^(?:sk|pk|rk|whsec|ghp|gho|xox[a-z]|api|key|token|secret|bearer|aws|akia)_"
)


def _is_allowlisted_long_token(value: str) -> bool:
    # LONG_SECRET_RE spans can include a key= prefix (its character class contains '='),
    # so allowlist by the value part: "model=llama-3.3-70b-versatile" passes on the model
    # name while "api_key=<random>" still masks because the value fits no structural shape.
    candidate = value.rsplit("=", 1)[-1]
    if not candidate or _SECRET_PREFIX_RE.match(candidate):
        return False
    return any(pattern.match(candidate) for pattern in LONG_SECRET_ALLOWLIST_RES)


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
    redacted, db_url_count = DATABASE_URL_RE.subn("[REDACTED_DATABASE_URL]", redacted)
    redacted, key_count = KEY_VALUE_SECRET_RE.subn(r"\1[REDACTED]\3", redacted)

    long_secret_count = 0

    def _replace_long_secret(match: re.Match[str]) -> str:
        nonlocal long_secret_count
        value = match.group(0)
        if _is_allowlisted_long_token(value):
            return value
        long_secret_count += 1
        return "[REDACTED_SECRET]"

    redacted = LONG_SECRET_RE.sub(_replace_long_secret, redacted)
    if url_count or db_url_count or key_count or long_secret_count:
        report.replacements["secret"] = (
            report.replacements.get("secret", 0)
            + url_count
            + db_url_count
            + key_count
            + long_secret_count
        )

    def replace_id(match: re.Match[str]) -> str:
        key = match.group(1).lower()
        namespace = "chat" if "chat" in key else "user"
        report.increment(namespace)
        return f"{match.group(1)}{mapper.ref(namespace, match.group(2))}"

    redacted = TELEGRAM_ID_RE.sub(replace_id, redacted)

    def replace_payment(match: re.Match[str]) -> str:
        report.increment("payment")
        return f"{match.group(1)}{mapper.ref('payment', match.group(2))}{match.group(3)}"

    redacted = PAYMENT_ID_RE.sub(replace_payment, redacted)
    redacted, count = USERNAME_RE.subn(
        lambda match: f"{match.group(1)}[REDACTED]{match.group(3)}",
        redacted,
    )
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
    # "invoice_payload" / the exact payments.payload column — not any key containing
    # "payload", which previously mislabeled non-payment fields (e.g. payload_points)
    # as payment_ref:p_... references.
    if normalized == "payload" or any(
        token in normalized
        for token in ("payment_id", "charge_id", "invoice_payload", "subscription_id")
    ):
        report.increment("payment")
        return mapper.ref("payment", value)
    if normalized in {"username", "first_name"}:
        report.increment("name")
        return "[REDACTED]"
    return redact_value(value, mapper, report)
