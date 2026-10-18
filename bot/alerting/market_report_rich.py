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

from bot.coin_icons import coin_fallback_emoji
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
        return f"{coin_fallback_emoji(match.group(1))} {text}"
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
    # Bars show the actual verified percentage returns. Weekly mini-lines
    # use only the source's pre-existing normalized 12-step sparkline buckets;
    # they are a visual trend, not invented high-resolution price samples.
    chart_width = 1080 if report_type == "weekly" else 980
    canvas = Image.new("RGB", (chart_width, 465), "#121d30")
    draw = ImageDraw.Draw(canvas)
    title_font, row_font, note_font = _font(29), _font(24), _font(17)
    draw.text(
        (40, 26), f"Tracked coins | verified {period} changes",
        fill="#f1f5fb", font=title_font,
    )
    bar_zero = 350 if report_type == "weekly" else 480
    bar_half_width = 225 if report_type == "weekly" else 370
    scale = bar_half_width / max(0.2, *(abs(x) for x in selected.values()))
    draw.line((bar_zero, 96, bar_zero, 388), fill="#7c90ab", width=2)
    sparkline_by_symbol = {}
    if report_type == "weekly":
        for coin in coins:
            if isinstance(coin, dict):
                symbol = str(coin.get("symbol") or "").upper()
                sparkline_by_symbol[symbol] = str(coin.get("sparkline_7d") or "")
        draw.text((668, 95), "7d mini-trend", fill="#a5b3c6", font=note_font)
    for index, symbol in enumerate(("BTC", "ETH", "GRAM", "SOL")):
        y = 122 + index * 65
        draw.text((39, y), symbol, fill="#e0e9f6", font=row_font)
        if symbol not in selected:
            draw.text((145, y), "No verified return", fill="#a5b3c6", font=note_font)
            continue
        value = selected[symbol]
        end = max(
            bar_zero - bar_half_width,
            min(bar_zero + bar_half_width, bar_zero + value * scale),
        )
        if abs(end - bar_zero) < 2:
            end = bar_zero + (2 if value >= 0 else -2)
        color = "#38bfa8" if value >= 0 else "#ee938d"
        draw.rounded_rectangle(
            (min(bar_zero, end), y, max(bar_zero, end), y + 30),
            radius=5, fill=color,
        )
        if report_type == "weekly":
            buckets = "▁▂▃▄▅▆▇█"
            glyphs = [
                buckets.index(ch) for ch in sparkline_by_symbol.get(symbol, "")
                if ch in buckets
            ]
            if len(glyphs) >= 2:
                x_start, x_end = 665, 876
                polyline = [
                    (
                        x_start + i * (x_end - x_start) / (len(glyphs) - 1),
                        y + 30 - glyph * 29 / 7,
                    )
                    for i, glyph in enumerate(glyphs)
                ]
                draw.line(polyline, fill="#83bce9", width=3, joint="curve")
            else:
                draw.text((670, y + 5), "No 7d path", fill="#a5b3c6", font=note_font)
        value_x = 925 if report_type == "weekly" else 866
        draw.text((value_x, y + 4), f"{value:+.2f}%", fill="#f1f5fb", font=note_font)
    footer = (
        "Bars: verified 7d changes. Mini-lines: normalized source 7d paths."
        if report_type == "weekly"
        else "Bars: verified 24h changes. Missing values are omitted."
    )
    draw.text((40, 418), footer, fill="#9daec6", font=note_font)
    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
