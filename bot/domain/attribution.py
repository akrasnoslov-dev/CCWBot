"""Validated Telegram deep-link acquisition attribution."""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass

_PAYLOAD_RE = re.compile(r"^a1_(?P<link_code>[a-z0-9-]{6,48})$")
_METADATA_CODE_RE = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
_TELEGRAM_BOT_USERNAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{1,28}bot$", re.IGNORECASE)
TELEGRAM_START_PAYLOAD_MAX_LENGTH = 64
ACQUISITION_LINK_CODE_BYTES = 16
ACQUISITION_SOURCES = frozenset({"reddit", "telegramads", "telegramdir", "product-hunt"})


@dataclass(frozen=True)
class AttributionLinkToken:
    link_code: str


@dataclass(frozen=True)
class AcquisitionLinkMetadata:
    """Allowlisted, bounded metadata stored behind an opaque acquisition link."""

    source: str
    campaign: str | None
    creative: str | None
    referrer_code: str | None


def parse_start_attribution(payload: object) -> AttributionLinkToken | None:
    """Parse only an opaque, versioned acquisition-link token.

    The payload itself contains no campaign, creator, or referral claim. The
    server resolves it against an operator-managed allowlist before persisting
    any attribution.
    """
    if not isinstance(payload, str) or not 0 < len(payload) <= TELEGRAM_START_PAYLOAD_MAX_LENGTH:
        return None
    match = _PAYLOAD_RE.fullmatch(payload)
    if match is None:
        return None
    return AttributionLinkToken(link_code=match.group("link_code"))


def validate_acquisition_link_metadata(
    *,
    source: object,
    campaign: object = None,
    creative: object = None,
    referrer_code: object = None,
) -> AcquisitionLinkMetadata:
    """Return safe operator metadata or reject values outside the attribution allowlist."""

    if not isinstance(source, str) or source not in ACQUISITION_SOURCES:
        raise ValueError("Unsupported acquisition source.")

    values: list[str | None] = []
    for value in (campaign, creative, referrer_code):
        if value is None:
            values.append(None)
            continue
        if not isinstance(value, str) or _METADATA_CODE_RE.fullmatch(value) is None:
            raise ValueError("Acquisition metadata must be lowercase codes up to 32 characters.")
        values.append(value)

    return AcquisitionLinkMetadata(
        source=source,
        campaign=values[0],
        creative=values[1],
        referrer_code=values[2],
    )


def generate_acquisition_link_code() -> str:
    """Generate a Telegram-safe opaque code with 128 bits of entropy."""

    return secrets.token_hex(ACQUISITION_LINK_CODE_BYTES)


def build_acquisition_telegram_url(*, bot_username: object, link_code: object) -> str:
    """Build a Telegram deep link only from a valid configured bot username and opaque code."""

    if (
        not isinstance(bot_username, str)
        or _TELEGRAM_BOT_USERNAME_RE.fullmatch(bot_username) is None
    ):
        raise ValueError("Telegram bot username is not configured correctly.")
    if parse_start_attribution(f"a1_{link_code}") is None:
        raise ValueError("Invalid acquisition link code.")
    return f"https://t.me/{bot_username}?start=a1_{link_code}"
