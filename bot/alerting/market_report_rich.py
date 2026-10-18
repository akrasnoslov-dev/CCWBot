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

from bot.coin_icons import coin_custom_emoji_id, coin_fallback_emoji
from bot.domain.supported_coins import SUPPORTED_SYMBOLS, display_symbol

_TITLES = {
    "daily": "📊 Daily Market Report",
    "weekly": "📊 Weekly Market Report",
}
_SECTIONS = {
    "Market pulse:": "🌍 Market pulse",
    "Dashboard:": "📊 Dashboard",
    "Tracked assets:": "💹 Tracked assets",
    "What to monitor:": "🔎 What to monitor",
    "What moved today:": "📌 What moved today",
    "Coin-specific news:": "📰 Coin-specific news",
    "What to watch next:": "🔎 What to watch next",
    "Week in one line:": "🌍 Week in one line",
    "Weekly scoreboard:": "💹 Weekly scoreboard",
    "Coin watchpoints:": "🔎 Coin watchpoints",
    "Market breadth:": "📊 Market breadth",
    "Themes of the week:": "📌 Themes of the week",
    "Week timeline:": "🗓️ Week timeline",
    "Coin-specific recap:": "🪙 Coin-specific recap",
    "Top catalysts of the week:": "📰 Top catalysts of the week",
    "Next week in focus:": "🔎 Next week in focus",
}
# Exact Unicode alts returned by Telegram getCustomEmojiStickers for the
# CCWBotIcons pack on 2026-10-18. A mismatched alt causes Telegram clients
# to show a generic fallback rather than the intended coin image.
_REPORT_CUSTOM_EMOJI_ALTS = {
    "BTC": "🖕",
    "ETH": "👨‍⚕️",
    "GRAM": "✌️",
    "SOL": "👩‍🚀",
}


def _report_coin_icon_html(symbol: str) -> str:
    emoji_id = coin_custom_emoji_id(symbol)
    alt = _REPORT_CUSTOM_EMOJI_ALTS.get(symbol)
    if emoji_id and alt:
        return f'<tg-emoji emoji-id="{escape(emoji_id, quote=True)}">{alt}</tg-emoji>'
    return coin_fallback_emoji(symbol)


_COIN_ROW = re.compile(r"^•\s+(BTC|ETH|GRAM|SOL):")
_URL = re.compile(r"https?://\S+")


# Cached reports generated before this release keep their canonical evidence.
# Compact only their *display*, so manual requests improve immediately without
# silently overwriting historical market-report rows or forcing a new LLM run.
_DISPLAY_SECTIONS = {
    "daily": {
        "Market pulse:", "Tracked assets:", "What to monitor:", "Coin-specific news:",
        "What to watch next:",
    },
    "weekly": {
        "Week in one line:", "Weekly scoreboard:", "Market breadth:",
        "Coin watchpoints:",
        "Top catalysts of the week:", "Next week in focus:",
    },
}
_WEEKLY_LEGACY_ROW_SUFFIX = re.compile(r",\s*24h\s+[^,\n]*(?:,\s*[▁▂▃▄▅▆▇█]+[^\n]*)?$")


def compact_report_for_display(plain_text: str, *, report_type: str) -> str:
    """Preserve unique facts/URLs while filtering redundant legacy sections."""
    if report_type not in _DISPLAY_SECTIONS:
        raise ValueError("Unsupported market report type")
    if not plain_text.strip().startswith(_TITLES[report_type]):
        return plain_text
    output: list[str] = []
    seen_urls: set[str] = set()
    for chunk in plain_text.split("\n\n"):
        lines = [value.strip() for value in chunk.splitlines() if value.strip()]
        if not lines:
            continue
        heading = lines[0]
        if heading not in _DISPLAY_SECTIONS[report_type] and heading not in {
            _TITLES[report_type], "Not financial advice.",
        }:
            continue
        if heading == "Not financial advice.":
            output.append(heading)
            continue
        if heading == _TITLES[report_type]:
            output.append(heading)
            continue
        is_news = heading in {"Coin-specific news:", "Top catalysts of the week:"}
        kept: list[str] = []
        for line in lines[1:]:
            if heading == "Weekly scoreboard:":
                line = _WEEKLY_LEGACY_ROW_SUFFIX.sub("", line)
            if is_news:
                found = _URL.search(line)
                if found:
                    key = found.group(0).rstrip(".,)")
                    if key in seen_urls:
                        continue
                    seen_urls.add(key)
                if len(kept) >= 4:
                    break
                if line == "No clearly relevant fresh news found for tracked coins":
                    period = "seven days" if report_type == "weekly" else "24 hours"
                    line = f"No verified relevant news selected for the last {period}."
            kept.append(line)
        if heading in {"Market pulse:", "Week in one line:", "What to watch next:",
                       "Next week in focus:"} and kept:
            # Keep a short natural sentence instead of model verbosity.
            text = " ".join(kept)
            if len(text) > 280:
                last_end = text.rfind(". ", 0, 280)
                text = text[:last_end + 1] if last_end > 60 else text[:279] + "…"
            kept = [text]
        output.append(heading + ("\n" + "\n".join(kept) if kept else ""))
    if output and output[-1] != "Not financial advice.":
        output.append("Not financial advice.")
    return "\n\n".join(output)


def _safe_rich_line(line: str, *, rich: bool = False) -> str:
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
        symbol = match.group(1)
        icon = _report_coin_icon_html(symbol) if rich else coin_fallback_emoji(symbol)
        return f"{icon} {text}"
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
            blocks.append(f"<p>{_safe_rich_line(line, rich=True)}</p>")
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


_CHART_BG = "#101c2e"
_CHART_PANEL = "#19293d"
_CHART_TEXT = "#f4f7fd"
_CHART_MUTED = "#acbfd3"
_CHART_GRID = "#40556c"
_CHART_GREEN = "#3bd3b3"
_CHART_RED = "#ff8887"
_CHART_BLUE = "#8ec8f8"
_COIN_NAMES = {"BTC": "Bitcoin", "ETH": "Ethereum", "GRAM": "Gram", "SOL": "Solana"}
_SPARK_BUCKETS = "▁▂▃▄▅▆▇█"


def _percent_label(value: float) -> str:
    return f"{value:+.2f}%"


def _chart_source_rows(coins: list, period: str) -> list[tuple[str, float | None, dict]]:
    """Use the first evidence record for each tracked symbol, never fabricated zeros."""
    valid_symbols = {display_symbol(symbol) for symbol in SUPPORTED_SYMBOLS}
    evidence: dict[str, tuple[float | None, dict]] = {}
    for coin in coins:
        if not isinstance(coin, dict):
            continue
        symbol = str(coin.get("symbol") or "").upper()
        if symbol not in valid_symbols or symbol in evidence:
            continue
        value = coin.get(f"change_{period}_percent")
        if value is None:
            value = coin.get(f"change_{period}")  # historical cached reports
        try:
            move = float(value) if value is not None and not isinstance(value, bool) else None
        except (TypeError, ValueError, OverflowError):
            move = None
        if move is not None and not math.isfinite(move):
            move = None
        evidence[symbol] = (move, coin)
    return [
        (symbol, *evidence.get(symbol, (None, {})))
        for symbol in ("BTC", "ETH", "GRAM", "SOL")
        if symbol in valid_symbols
    ]


def _range_label(value) -> str | None:
    """Only use a provider-derived range_position, never infer it from glyphs."""
    if value is None or isinstance(value, bool):
        return None
    try:
        position = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    if not math.isfinite(position) or not 0 <= position <= 1:
        return None
    if position <= 0.25:
        return "NEAR WEEKLY LOW"
    if position >= 0.75:
        return "NEAR WEEKLY HIGH"
    return "MID-WEEK RANGE"


def _source_path(value) -> list[int]:
    """Accept only recorded normalized buckets; never synthesize missing steps."""
    if not isinstance(value, str):
        return []
    glyphs = value.strip()
    if not 2 <= len(glyphs) <= 12 or any(glyph not in _SPARK_BUCKETS for glyph in glyphs):
        return []
    return [_SPARK_BUCKETS.index(glyph) for glyph in glyphs]


def _draw_daily_chart(
    draw: ImageDraw.ImageDraw, rows: list[tuple[str, float | None, dict]]
) -> None:
    width = 1040
    title, row_font = _font(43), _font(30)
    small, axis_font, number_font = _font(21), _font(19), _font(30)
    draw.text((36, 22), "24h Performance", font=title, fill=_CHART_TEXT)
    draw.text((37, 78), "Verified price changes  |  Four tracked assets  |  USD market data",
              font=small, fill=_CHART_MUTED)

    values = [(symbol, value) for symbol, value, _ in rows if value is not None]
    top = max(values, key=lambda item: item[1])[0] if len(values) > 1 else None
    bottom = min(values, key=lambda item: item[1])[0] if len(values) > 1 else None
    if values and max(value for _, value in values) == min(value for _, value in values):
        top = bottom = None

    left, zero, right = 278, 566, 854
    max_abs = max((abs(value) for _, value in values), default=0.0)
    # Round bounds to readable, symmetric percentage-point ticks.
    reference = max(0.02, max_abs)
    step = 10 ** math.floor(math.log10(reference / 2))
    limit = 2 * step * math.ceil(reference * 1.08 / (2 * step))
    for idx, (symbol, change, _) in enumerate(rows):
        y = 140 + idx * 72
        draw.rounded_rectangle((27, y - 10, width - 27, y + 55), 14, fill=_CHART_PANEL)
        draw.text((48, y + 4), symbol, font=row_font, fill=_CHART_TEXT)
        badge = "BEST" if symbol == top else "LOWEST" if symbol == bottom else ""
        if badge:
            badge_color = _CHART_GREEN if symbol == top else _CHART_RED
            draw.text((152, y + 13), badge, font=_font(16), fill=badge_color)
        if change is None:
            draw.text((298, y + 12), "No verified 24h return", font=small, fill=_CHART_MUTED)
            continue
        length = abs(change) / limit * (right - zero)
        color = _CHART_GREEN if change >= 0 else _CHART_RED
        if change == 0:
            draw.ellipse((zero - 5, y + 12, zero + 5, y + 22), fill=_CHART_MUTED)
        else:
            endpoint = zero + (length if change > 0 else -length)
            draw.rounded_rectangle(
                (min(zero, endpoint), y + 9, max(zero, endpoint), y + 27),
                radius=8, fill=color,
            )
        label = _percent_label(change)
        draw.text((890, y + 5), label, font=number_font if len(label) <= 8 else small,
                  fill=color)

    # Draw axis over row cards for a clearly shared zero reference.
    for position, factor in ((left, -1), ((left + zero) / 2, -0.5),
                             (zero, 0), ((zero + right) / 2, 0.5), (right, 1)):
        draw.line((position, 122, position, 419),
                  fill="#90a3ba" if factor == 0 else _CHART_GRID,
                  width=3 if factor == 0 else 1)
        tick = factor * limit
        digits = 1 if limit >= 1 else 2 if limit >= 0.1 else 3 if limit >= 0.01 else 4
        text = "0%" if factor == 0 else f"{tick:+.{digits}f}%"
        bbox = draw.textbbox((0, 0), text, font=axis_font)
        draw.text((position - (bbox[2] - bbox[0]) / 2, 430), text,
                  font=axis_font, fill=_CHART_MUTED)
    draw.text((37, 474), "Bar length = change from 0%  ·  Missing returns are not plotted",
              font=small, fill=_CHART_MUTED)


def _draw_weekly_chart(
    draw: ImageDraw.ImageDraw, rows: list[tuple[str, float | None, dict]]
) -> None:
    width = 1040
    draw.text((36, 20), "7d Performance", font=_font(39), fill=_CHART_TEXT)
    draw.text((38, 77), "Weekly returns and source-backed relative paths",
              font=_font(21), fill=_CHART_MUTED)
    header_font = _font(18)
    draw.text((52, 117), "ASSET", font=header_font, fill=_CHART_MUTED)
    draw.text((275, 117), "7D CHANGE", font=header_font, fill=_CHART_MUTED)
    draw.text((585, 117), "NORMALIZED 7D PATH", font=header_font, fill=_CHART_MUTED)
    for index, (symbol, change, coin) in enumerate(rows):
        y = 149 + index * 101
        color = _CHART_GREEN if change is not None and change >= 0 else (
            _CHART_RED if change is not None else _CHART_MUTED
        )
        draw.rounded_rectangle((26, y, width - 26, y + 91), radius=16, fill=_CHART_PANEL)
        draw.rounded_rectangle((37, y + 20, 43, y + 71), radius=3, fill=color)
        draw.text((56, y + 15), symbol, font=_font(34), fill=_CHART_TEXT)
        draw.text((56, y + 60), _COIN_NAMES[symbol], font=_font(17), fill=_CHART_MUTED)
        if change is None:
            draw.text((277, y + 22), "No verified return", font=_font(22), fill=_CHART_MUTED)
            draw.text((590, y + 38), "7d path unavailable", font=_font(19), fill=_CHART_MUTED)
            continue
        draw.text((277, y + 13), _percent_label(change),
                  font=_font(38) if len(_percent_label(change)) <= 8 else _font(25),
                  fill=color)
        range_text = _range_label(coin.get("range_position"))
        if range_text:
            draw.text((279, y + 62), range_text, font=_font(17), fill=_CHART_MUTED)
        path = _source_path(coin.get("sparkline_7d"))
        if not path:
            draw.text((590, y + 38), "7d path unavailable", font=_font(19), fill=_CHART_MUTED)
            continue
        x0, x1 = 592, 975
        y0, y1 = y + 18, y + 74
        draw.line((x0, (y0 + y1) / 2, x1, (y0 + y1) / 2),
                  fill=_CHART_GRID, width=1)
        points = [
            (x0 + idx * (x1 - x0) / (len(path) - 1),
             y1 - bucket * (y1 - y0) / 7)
            for idx, bucket in enumerate(path)
        ]
        draw.line(points, fill=color, width=5, joint="curve")
        x, p_y = points[-1]
        draw.ellipse((x - 5, p_y - 5, x + 5, p_y + 5), fill=_CHART_TEXT)
    draw.text((35, 573),
              "Returns: verified 7d %  |  Paths: normalized source samples, not historical prices",
              font=_font(19), fill=_CHART_MUTED)


def market_report_change_chart(raw_input_json: str | None, *, report_type: str) -> bytes | None:
    """Create compact Telegram infographics solely from persisted market evidence."""
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

    period = "24h" if report_type == "daily" else "7d"
    rows = _chart_source_rows(coins, period)
    if not any(change is not None for _, change, _ in rows):
        return None
    size = (1040, 510) if report_type == "daily" else (1040, 610)
    canvas = Image.new("RGB", size, _CHART_BG)
    draw = ImageDraw.Draw(canvas)
    if report_type == "daily":
        _draw_daily_chart(draw, rows)
    else:
        _draw_weekly_chart(draw, rows)
    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
