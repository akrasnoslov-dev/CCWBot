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
    markers: tuple[ReferenceMarker, ...] = ()


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


def _render_legacy_chart(snapshots: list, *, as_of: datetime, symbol: str) -> ChartResult:
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


@dataclass(frozen=True)
class ReferenceMarker:
    """Auditable reference value and its actual, not nominal, UTC timestamp."""
    label: str
    timestamp: datetime | None
    price: float | None
    plotted: bool
    reason: str | None = None
    label_box: tuple[int, int, int, int] | None = None


# Nominal 30-minute persistence cadence with bounded scheduling tolerance.
_THREE_H_TOLERANCE = timedelta(minutes=20)
_DAY_TOLERANCE = timedelta(minutes=40)
_MARKER_STYLE = {
    "NOW": ("#f4f9ff", "circle"),
    "PREVIOUS ALERT": ("#dca5ff", "diamond"),
    "−3H": ("#ffd274", "square"),
    "−24H": ("#81beff", "triangle"),
}


def _observed(
    reference: tuple[datetime, float | None] | None,
) -> tuple[datetime | None, float | None]:
    if not isinstance(reference, (tuple, list)) or len(reference) != 2:
        return None, None
    stamp, value = reference
    if not isinstance(stamp, datetime):
        return None, None
    try:
        price = float(value) if value is not None else None
    except (ValueError, TypeError, OverflowError):
        price = None
    if price is not None and (not isfinite(price) or price <= 0):
        price = None
    stamp = (
        stamp.replace(tzinfo=timezone.utc)
        if stamp.tzinfo is None else stamp.astimezone(timezone.utc)
    )
    return stamp, price


def _reference_markers(
    points: tuple[tuple[datetime, float], ...], *,
    as_of: datetime,
    axis_start: datetime,
    current_observation: tuple[datetime, float] | None,
    previous_alert: tuple[datetime, float | None] | None,
) -> tuple[ReferenceMarker, ...]:
    current_at, current_price = _observed(current_observation)
    previous_at, previous_price = _observed(previous_alert)
    found: list[ReferenceMarker] = []

    def add(
        label: str, stamp: datetime | None, price: float | None,
        missing: str = "unavailable",
    ) -> None:
        if stamp is None:
            found.append(ReferenceMarker(label, None, None, False, missing))
        elif stamp < axis_start or stamp > as_of:
            found.append(ReferenceMarker(label, stamp, price, False, "outside visible window"))
        elif price is None:
            found.append(ReferenceMarker(label, stamp, None, False, "price unavailable"))
        else:
            found.append(ReferenceMarker(label, stamp, price, True))

    add("NOW", current_at, current_price, "current observation unavailable")
    add("PREVIOUS ALERT", previous_at, previous_price, "no previous market event")
    for label, hours, tolerance in (("−3H", 3, _THREE_H_TOLERANCE), ("−24H", 24, _DAY_TOLERANCE)):
        target = as_of - timedelta(hours=hours)
        closest = min(points, key=lambda pair: abs(pair[0] - target))
        if abs(closest[0] - target) <= tolerance:
            add(label, closest[0], closest[1])
        else:
            add(label, None, None, f"no sample within ±{int(tolerance.total_seconds() // 60)}m")
    return tuple(found)


def _reference_price(price: float) -> str:
    decimals = 2 if price >= 1 else 4 if price >= 0.01 else 6
    return f"${price:,.{decimals}f}"


def _draw_reference_shape(
    draw: ImageDraw.ImageDraw, shape: str, x: int, y: int, color: str,
) -> None:
    radius = 10
    if shape == "circle":
        draw.ellipse(
            (x-radius, y-radius, x+radius, y+radius),
            fill=color, outline="#111b2c", width=2,
        )
    elif shape == "diamond":
        draw.polygon(
            ((x, y-radius-2), (x+radius+2, y), (x, y+radius+2), (x-radius-2, y)),
            fill=color,
        )
    elif shape == "square":
        draw.rectangle((x-radius, y-radius, x+radius, y+radius), fill=color)
    else:
        draw.polygon(((x, y-radius-3), (x+radius+3, y+radius), (x-radius-3, y+radius)), fill=color)


def _render_marked_chart(
    selected: ChartResult, *, as_of: datetime, symbol: str,
    current_observation: tuple[datetime, float] | None,
    previous_alert: tuple[datetime, float | None] | None,
) -> ChartResult:
    # The historical curve remains the original contiguous persisted run. NOW
    # is intentionally a separate point, not a fabricated database snapshot.
    as_of = as_of.astimezone(timezone.utc)
    points = selected.points
    width, height = 900, 615
    image = Image.new("RGB", (width, height), "#111b2c")
    draw = ImageDraw.Draw(image)
    f_small, f_normal, f_chip = _font(20), _font(25), _font(23)
    left, right, top, bottom = 118, 865, 177, 382
    axis_start = as_of - timedelta(hours=24) if selected.label == "Last 24 hours" else points[0][0]
    axis_end = as_of
    markers = list(_reference_markers(
        points, as_of=as_of, axis_start=axis_start,
        current_observation=current_observation, previous_alert=previous_alert,
    ))
    prices = [p for _, p in points] + [
        m.price for m in markers if m.plotted and m.price is not None
    ]
    low, high = min(prices), max(prices)
    scale = max(high-low, high*0.0005)
    floor, ceiling = low - scale*0.12, high + scale*0.12
    span = max((axis_end-axis_start).total_seconds(), 1)

    def x_at(stamp: datetime) -> int:
        return round(left + (stamp-axis_start).total_seconds()/span * (right-left))

    def y_at(price: float) -> int:
        return round(bottom - (price-floor)/(ceiling-floor) * (bottom-top))

    accent = "#4ee3b0" if points[-1][1] >= points[0][1] else "#ff8d98"
    draw.text((left, 21), f"{symbol.upper()}  |  {selected.label}", font=f_normal, fill="#ffffff")
    draw.text((right, 23), "UTC", font=f_small, fill="#a7b6ce", anchor="ra")
    for proportion in (0, 0.5, 1):
        y = round(top+(bottom-top)*proportion)
        draw.line((left, y, right, y), fill="#334258", width=1)
        value = ceiling - (ceiling-floor)*proportion
        draw.text((left-10, y), _reference_price(value), font=f_small, fill="#c0cee1", anchor="rm")

    last = None
    for stamp, price in points:
        xy = (x_at(stamp), y_at(price))
        if last is not None:
            draw.line((*last, *xy), fill=accent, width=4, joint="curve")
        last = xy
    if last:
        draw.ellipse((last[0]-5, last[1]-5, last[0]+5, last[1]+5), fill=accent)

    # Collision handling: separate chip lanes, clamp to graph boundaries.
    occupied: list[list[tuple[int, int]]] = [[], [], [], []]
    for i, marker in sorted(enumerate(markers),
                            key=lambda item: x_at(item[1].timestamp) if item[1].plotted else 1e9):
        if not marker.plotted or marker.timestamp is None or marker.price is None:
            continue
        color, shape = _MARKER_STYLE[marker.label]
        x, y = x_at(marker.timestamp), y_at(marker.price)
        display = marker.label.replace("−", "-")  # bundled Pillow bitmap font lacks U+2212
        label_width = round(draw.textlength(display, font=f_chip)) + 22
        chip_x = min(max(x-label_width//2, left), right-label_width)
        chip_right = chip_x + label_width
        lane = next((n for n, boxes in enumerate(occupied)
                     if all(chip_right+7 <= a or chip_x >= b+7 for a,b in boxes)), None)
        if lane is None:
            lane = min(range(4), key=lambda n: len(occupied[n]))
        occupied[lane].append((chip_x, chip_right))
        chip_y = 66 + lane*26
        bounds = (chip_x, chip_y, chip_right, chip_y+25)
        draw.line((x, chip_y+25, x, y), fill="#53657f", width=1)
        draw.rounded_rectangle(bounds, radius=6, fill="#26354a", outline=color, width=1)
        draw.text((chip_x+11, chip_y+1), display, font=f_chip, fill=color)
        _draw_reference_shape(draw, shape, x, y, color)
        markers[i] = ReferenceMarker(
            marker.label, marker.timestamp, marker.price, True, label_box=bounds,
        )

    draw.text((left, 404), axis_start.strftime("%d %b %H:%M"), font=f_small, fill="#c0cee1")
    draw.text(
        (right, 404), axis_end.strftime("%d %b %H:%M"),
        font=f_small, fill="#c0cee1", anchor="ra",
    )
    for index, marker in enumerate(markers):
        y = 444 + index*34
        color, shape = _MARKER_STYLE[marker.label]
        if index % 2 == 0:
            draw.rounded_rectangle((left-10, y-5, right+2, y+28), radius=5, fill="#1a293d")
        _draw_reference_shape(draw, shape, left+9, y+11, color)
        draw.text((left+31, y-2), marker.label.replace("−", "-"), font=f_chip, fill=color)
        if marker.timestamp is None:
            detail = marker.reason or "unavailable"
        elif marker.plotted:
            detail = f"{marker.timestamp:%d %b %H:%M} UTC  |  {_reference_price(marker.price)}"
        else:
            detail = f"{marker.timestamp:%d %b %H:%M} UTC  |  {marker.reason or 'unavailable'}"
        draw.text((right, y), detail, font=f_small, fill="#c0cee1", anchor="ra")
    draw.text(
        (left, 591), "Persisted curve only  |  NOW from event observation  |  no interpolation",
              font=_font(18), fill="#a7b6ce")
    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return ChartResult(selected.label, buffer.getvalue(), points, tuple(markers))


def render_price_chart(
    snapshots: list, *, as_of: datetime, symbol: str,
    event_markers: bool = False,
    current_observation: tuple[datetime, float] | None = None,
    previous_alert: tuple[datetime, float | None] | None = None,
) -> ChartResult:
    """Event-specific references are opt-in; Heartbeat is exactly the old chart."""
    if not event_markers:
        return _render_legacy_chart(snapshots, as_of=as_of, symbol=symbol)
    selected = prepare_chart_points(snapshots, as_of=as_of)
    if selected.png is None:
        return selected
    return _render_marked_chart(
        selected, as_of=as_of, symbol=symbol,
        current_observation=current_observation, previous_alert=previous_alert,
    )
