from __future__ import annotations

import re

NEWS_TITLE_SOURCE_SUFFIXES = (
    "CoinDesk: Bitcoin, Ethereum, Crypto News and Price Data",
    "Cointelegraph.com News",
)


def clean_related_news_text(text: str, *, source: str | None = None) -> str:
    cleaned = str(text or "").strip()
    suffixes = list(NEWS_TITLE_SOURCE_SUFFIXES)
    source_text = str(source or "").strip()
    if source_text:
        suffixes.append(source_text)

    while cleaned:
        previous = cleaned
        for suffix in suffixes:
            cleaned = re.sub(
                rf"\s+-\s+{re.escape(suffix)}\s*$",
                "",
                cleaned,
                flags=re.IGNORECASE,
            ).rstrip()
        if cleaned == previous:
            break
    return cleaned


def clean_news_title(title: str) -> str:
    return clean_related_news_text(title)
