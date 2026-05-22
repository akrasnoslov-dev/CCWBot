from __future__ import annotations

import re

NEWS_TITLE_SOURCE_SUFFIXES = (
    "CoinDesk: Bitcoin, Ethereum, Crypto News and Price Data",
    "Cointelegraph.com News",
)


def clean_news_title(title: str) -> str:
    cleaned = str(title or "").strip()
    while cleaned:
        previous = cleaned
        for suffix in NEWS_TITLE_SOURCE_SUFFIXES:
            cleaned = re.sub(
                rf"\s+-\s+{re.escape(suffix)}\s*$",
                "",
                cleaned,
                flags=re.IGNORECASE,
            ).rstrip()
        if cleaned == previous:
            break
    return cleaned
