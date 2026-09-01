"""Validated Telegram deep-link acquisition attribution."""

from __future__ import annotations

import re
from dataclasses import dataclass

_PAYLOAD_RE = re.compile(r"^a1_(?P<link_code>[a-z0-9-]{6,48})$")
TELEGRAM_START_PAYLOAD_MAX_LENGTH = 64


@dataclass(frozen=True)
class AttributionLinkToken:
    link_code: str


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
