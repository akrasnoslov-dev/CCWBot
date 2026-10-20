"""Deterministic PNG chart from persisted, timestamped price observations only."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from io import BytesIO
from math import isfinite

from PIL import Image, ImageDraw, ImageFont


@dataclass(frozen=True)
class ChartResult:
    label: str
    png: bytes | None
    points: tuple[tuple[datetime, float], ...]


def _font(size: int) -> ImageFont.ImageFont:
    # Pillow bundles its default font; no system font files or network calls.
    return ImageFont.load_default(size=size)


def prepare_chart_points(snapshots: list, *, as_of: datetime) -> ChartResult:
    """Never extrapolate over missing time or label a partial day as 24h."""
    as_of = as_of.astimezone(timezone.utc)
    since = as_of - timedelta(hours=24)
    observations: dict[datetime, float] = {}
    for row in snapshots:
        stamp = getattr(row, "checked_at", None)
        try:
            price = float(getattr(row, "price", None))
        except (TypeError, ValueError, OverflowError):
            continue
        if not isinstance(stamp, datetime) or not isfinite(price) or price <= 0:
            continue
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        else:
            stamp = stamp.astimezone(timezone.utc)
        if since <= stamp <= as_of:
            observations[stamp] = price

    # Prefer the most recent continuous run of persisted 30-minute samples.
    # A missing sample (about a 60m gap) starts a new run: never connect
    # prices across a shutdown or interpolate an unseen market trajectory.
    all_points = tuple(sorted(observations.items()))
    start = 0
    for index in range(1, len(all_points)):
        if all_points[index][0] - all_points[index - 1][0] > timedelta(minutes=45):
            start = index
    points = all_points[start:]
    unavailable = ChartResult("Last 24 hours", None, points)

    # A chart needs at least five real observations spanning two hours.
    # Render runs before the current check saves its snapshot, so tolerate
    # up to 15m scheduling jitter beyond the normal 30m sampling interval.
    if len(points) < 5 or as_of - points[-1][0] > timedelta(minutes=45):
        return unavailable
    duration = points[-1][0] - points[0][0]
    if duration < timedelta(hours=2):
        return unavailable

    # Reserve the 24-hour label for near-complete, gap-free source coverage.
    # No synthetic samples are added at either axis edge.
    is_full_day = (
        points[0][0] <= since + timedelta(minutes=45)
        and points[-1][0] >= as_of - timedelta(minutes=45)
    )
    if is_full_day:
        label = "Last 24 hours"
    else:
        minutes = int(duration.total_seconds() // 60)
        label = f"Observed {minutes // 60}h {minutes % 60}m (available history)"
    return ChartResult(label, b"", points)


def render_price_chart(snapshots: list, *, as_of: datetime, symbol: str) -> ChartResult:
    selected = prepare_chart_points(snapshots, as_of=as_of)
    if selected.png is None:
        return selected
    points = selected.points
    width, height = 900, 360
    image = Image.new("RGB", (width, height), "#111b2c")
    draw = ImageDraw.Draw(image)
    f_small, f_normal = _font(17), _font(22)
    left, right, top, bottom = 72, 866, 86, 272
    prices = [price for _, price in points]
    low, high = min(prices), max(prices)
    scale = max(high - low, high * 0.0005)
    # Explicit price-axis labels make the zoomed vertical scale transparent.
    floor, ceiling = low - scale * 0.12, high + scale * 0.12
    # For a day-wide window, use its true UTC boundaries on the time axis.
    # The curve still starts/ends only at observed samples, with empty edges.
    if selected.label == "Last 24 hours":
        axis_start = as_of.astimezone(timezone.utc) - timedelta(hours=24)
        axis_end = as_of.astimezone(timezone.utc)
    else:
        axis_start, axis_end = points[0][0], points[-1][0]
    span = max((axis_end - axis_start).total_seconds(), 1)
    def x_at(stamp: datetime) -> float:
        return left + (stamp - axis_start).total_seconds() / span * (right - left)

    def y_at(value: float) -> float:
        return bottom - (value - floor) / (ceiling - floor) * (bottom - top)
    up = prices[-1] >= prices[0]
    accent = "#4ee3b0" if up else "#ff8d98"
    draw.text((left, 26), f"{symbol.upper()}  |  {selected.label}", font=f_normal, fill="#ffffff")
    draw.text((right, 30), "UTC", font=f_small, fill="#a7b6ce", anchor="ra")
    for proportion in (0, 0.5, 1):
        y = top + (bottom - top) * proportion
        draw.line((left, y, right, y), fill="#334258", width=1)
        value = ceiling - (ceiling - floor) * proportion
        draw.text((left - 8, y), f"${value:,.2f}", font=f_small, fill="#c0cee1", anchor="rm")
    # Every segment joins consecutive observed samples of the selected run.
    previous = None
    for stamp, price in points:
        xy = (round(x_at(stamp)), round(y_at(price)))
        if previous is not None:
            draw.line((*previous[1], *xy), fill=accent, width=4, joint="curve")
        previous = (stamp, xy)
    if previous:
        draw.ellipse((previous[1][0] - 5, previous[1][1] - 5,
                      previous[1][0] + 5, previous[1][1] + 5), fill=accent)
    draw.text((left, 291), axis_start.strftime("%d %b %H:%M"), font=f_small, fill="#c0cee1")
    draw.text(
        (right, 291), axis_end.strftime("%d %b %H:%M"),
        font=f_small, fill="#c0cee1", anchor="ra",
    )
    draw.text((left, 329), "Price axis: observed range  |  persisted samples only",
              font=f_small, fill="#a7b6ce")
    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return ChartResult(selected.label, buffer.getvalue(), points)
