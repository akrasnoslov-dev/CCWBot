"""Presentation-only Rich Telegram reports from persisted, validated report data.

One inline comparative chart, one message. No new market/LLM/news lookups.
The source-of-truth report text remains the legacy plain fallback.
"""
from __future__ import annotations

import io
import json
import math
import re
from html import escape
from urllib.parse import urlparse

from PIL import Image, ImageDraw, ImageFont

from bot.coin_icons import build_coin_icon_html
from bot.domain.supported_coins import SUPPORTED_SYMBOLS, display_symbol

_TITLES = {
    "daily": "📊 Daily Market Report",
    "weekly": "📊 Weekly Market Report",
}
_SECTIONS = {
    "Market pulse:": "🌍 Market pulse",
    "Dashboard:": "📊 Dashboard",
    "Tracked assets:": "💹 Tracked assets",
    "What moved today:": "📌 What moved today",
    "Coin-specific news:": "📰 Coin-specific news",
    "What to watch next:": "🔎 What to watch next",
    "Week in one line:": "🌍 Week in one line",
    "Weekly scoreboard:": "💹 Weekly scoreboard",
    "Market breadth:": "📊 Market breadth",
    "Themes of the week:": "📌 Themes of the week",
    "Week timeline:": "🗓️ Week timeline",
    "Coin-specific recap:": "🪙 Coin-specific recap",
    "Top catalysts of the week:": "📰 Top catalysts of the week",
    "Next week in focus:": "🔎 Next week in focus",
}
_COIN_ROW = re.compile(r"^•\s+(BTC|ETH|GRAM|SOL):")
_URL = re.compile(r"https?://\S+")


def _safe_rich_line(line: str) -> str:
    """Escape all model/news wording; only safely link explicit HTTP(S) sources."""
    found = _URL.search(line)
    if found:
        url = found.group(0).rstrip(".,)")
        parsed = urlparse(url)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            before = escape(line[:found.start()])
            after = escape(line[found.end():])
            text = before + (
                f' <a href="{escape(url, quote=True)}">Source ↗</a>' + after
            )
        else:
            text = escape(line)
    else:
        text = escape(line)
    match = _COIN_ROW.match(line)
    if match:
        return f"{build_coin_icon_html(match.group(1))} {text}"
    return text


def format_rich_market_report(
    plain_text: str, *, report_type: str, chart_available: bool
) -> str:
    """Rich headings and sections, using exactly the persisted plain report content."""
    if report_type not in _TITLES:
        raise ValueError("Unsupported market report type")
    blocks = [f"<h2>{escape(_TITLES[report_type])}</h2>"]
    for section in plain_text.split("\n\n"):
        lines = [line.strip() for line in section.splitlines() if line.strip()]
        if not lines or lines[0] == _TITLES[report_type]:
            continue
        if lines[0] == "Not financial advice.":
            blocks.append("<footer>Not financial advice.</footer>")
            continue
        header = lines[0]
        if header in _SECTIONS:
            blocks.append(f"<h3>{escape(_SECTIONS[header])}</h3>")
            lines = lines[1:]
        for line in lines:
            blocks.append(f"<p>{_safe_rich_line(line)}</p>")
        if header in {"Tracked assets:", "Weekly scoreboard:"}:
            label = "24h" if report_type == "daily" else "7d"
            blocks.append(f"<h3>📈 Verified {label} coin performance</h3>")
            if chart_available:
                blocks.append('<img src="tg://photo?id=chart"/>')
            else:
                blocks.append("<p>Chart unavailable: verified changes missing.</p>")
    if not any(block.startswith("<footer>") for block in blocks):
        blocks.append("<footer>Not financial advice.</footer>")
    return "".join(blocks)


def format_html_market_report(plain_text: str, *, report_type: str) -> str:
    """Valid ordinary Telegram HTML when native Rich is definitively rejected."""
    if report_type not in _TITLES:
        raise ValueError("Unsupported market report type")
    result: list[str] = []
    for section in plain_text.split("\n\n"):
        lines = [line.strip() for line in section.splitlines() if line.strip()]
        if not lines:
            continue
        if lines[0] == _TITLES[report_type]:
            result.append(f"<b>{escape(lines[0])}</b>")
            continue
        if lines[0] in _SECTIONS:
            result.append(f"<b>{escape(_SECTIONS[lines[0]])}</b>")
            lines = lines[1:]
        if lines:
            result.append("\n".join(_safe_rich_line(line) for line in lines))
    return "\n\n".join(result)


def _font(size: int):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def market_report_change_chart(raw_input_json: str | None, *, report_type: str) -> bytes | None:
    """Plot real, already-cached relative moves; no invented intraday/weekly paths."""
    if report_type not in _TITLES or not raw_input_json:
        return None
    try:
        payload = json.loads(raw_input_json)
    except (ValueError, TypeError):
        return None
    if not isinstance(payload, dict) or payload.get("report_type") != report_type:
        return None
    coins = payload.get("coins")
    if not isinstance(coins, list):
        return None
    selected: dict[str, float] = {}
    period = "24h" if report_type == "daily" else "7d"
    for coin in coins:
        if not isinstance(coin, dict):
            continue
        symbol = str(coin.get("symbol") or "").upper()
        if symbol not in {display_symbol(s) for s in SUPPORTED_SYMBOLS} or symbol in selected:
            continue
        value = coin.get(f"change_{period}_percent")
        if value is None:
            value = coin.get(f"change_{period}")  # historical report inputs
        try:
            move = float(value) if value is not None else math.nan
        except (TypeError, ValueError, OverflowError):
            continue
        if math.isfinite(move):
            selected[symbol] = move
    if not selected:
        return None
    # Absolute percentage-point scale, always centered at zero. Missing coins
    # are not drawn and missing bars are never represented as 0% changes.
    canvas = Image.new("RGB", (980, 465), "#121d30")
    draw = ImageDraw.Draw(canvas)
    title_font, row_font, note_font = _font(31), _font(25), _font(18)
    draw.text((42, 30), f"Tracked coins | verified {period} changes", fill="#f1f5fb", font=title_font)
    zero, scale = 480, 370 / max(0.2, *(abs(x) for x in selected.values()))
    draw.line((zero, 101, zero, 380), fill="#7c90ab", width=2)
    for index, symbol in enumerate(("BTC", "ETH", "GRAM", "SOL")):
        y = 114 + index * 65
        draw.text((45, y), symbol, fill="#e0e9f6", font=row_font)
        if symbol not in selected:
            draw.text((600, y), "No verified data", fill="#a5b3c6", font=note_font)
            continue
        value = selected[symbol]
        end = max(100, min(860, zero + value * scale))
        if abs(end - zero) < 2:
            end = zero + (2 if value >= 0 else -2)
        color = "#38bfa8" if value >= 0 else "#ee938d"
        draw.rounded_rectangle(
            (min(zero, end), y, max(zero, end), y + 33),
            radius=5, fill=color,
        )
        draw.text((868, y + 3), f"{value:+.2f}%", fill="#f1f5fb", font=note_font)
    draw.text(
        (42, 420),
        "Percent move, not a price-history curve. Missing values are omitted.",
        fill="#9daec6", font=note_font,
    )
    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
