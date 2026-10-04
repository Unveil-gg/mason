"""Expand a semantic mark into dabs. One layer stays one PNG."""

from __future__ import annotations

import math

from mason.core.assets import RasterLayer
from mason.core.entropy import signed, unit
from mason.core.marks import (
    DabMark,
    HatchMark,
    Mark,
    MarkRect,
    MassMark,
    ScatterMark,
    StrokeMark,
    StrokePathMark,
    WashMark,
)
from mason.core.styles import StyleProcess, StyleProfile

# x, y, radius, strength
Dab = tuple[float, float, float, float]
_CAP = 240


def layer_dabs(
    layer: RasterLayer,
    seed: int,
    style: StyleProfile,
) -> list[Dab] | None:
    """Dabs for a mark or stroke. None when the layer is neither.

    seed: asset seed. style.process fills knobs when hand is set.
    """
    if layer.mark is not None:
        return expand_mark(
            layer.mark, seed, layer.name, style.process,
        )
    if layer.stroke is None:
        return None
    jitter = 0.0
    irregularity = 0.0
    if layer.hand:
        jitter = style.process.jitter
        irregularity = style.process.irregularity
    stroke = layer.stroke
    return polyline_dabs(
        stroke.points,
        stroke.radius,
        stroke.spacing,
        stroke.strength,
        seed=seed,
        name=layer.name,
        jitter=jitter,
        irregularity=irregularity,
    )


def expand_mark(
    mark: Mark,
    seed: int,
    name: str,
    process: StyleProcess,
) -> list[Dab]:
    """Compile one mark. name keys the draws so siblings stay put."""
    if isinstance(mark, DabMark):
        return _dab(mark, seed, name, process)
    if isinstance(mark, StrokeMark):
        return _stroke(mark, seed, name, process, None)
    if isinstance(mark, StrokePathMark):
        return _stroke(mark, seed, name, process, mark.radius_end)
    if isinstance(mark, WashMark):
        return _wash(mark, seed, name, process)
    if isinstance(mark, ScatterMark):
        return _scatter(mark, seed, name, process)
    if isinstance(mark, HatchMark):
        return _hatch(mark, seed, name, process)
    return _mass(mark, seed, name, process)


def polyline_dabs(
    points: list[tuple[float, float]],
    radius: float,
    spacing: float,
    strength: float,
    *,
    seed: int,
    name: str,
    jitter: float,
    irregularity: float,
    radius_end: float | None = None,
    index_base: int = 0,
) -> list[Dab]:
    """Step a polyline. Zero jitter and irregularity leave the path."""
    step = max(radius * 2.0 * spacing, 1.0)
    lengths = [_span(points[i], points[i + 1]) for i in range(len(points) - 1)]
    total = sum(lengths)
    found: list[Dab] = []
    travelled = 0.0
    n = index_base
    for i, length in enumerate(lengths):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        count = max(int(length / step), 1)
        inv = length if length > 1e-8 else 1.0
        nx = -(y1 - y0) / inv
        ny = (x1 - x0) / inv
        for k in range(count + 1):
            t = k / count
            dist = travelled + length * t
            x = x0 + (x1 - x0) * t
            y = y0 + (y1 - y0) * t
            local = radius
            if radius_end is not None and total > 0:
                local = radius + (radius_end - radius) * (dist / total)
            if jitter:
                local *= 1.0 + signed(seed, name, n, 0) * jitter
            if irregularity:
                push = signed(seed, name, n, 1) * irregularity * local
                x += nx * push
                y += ny * push
            found.append((x, y, max(local, 0.5), strength))
            n += 1
        travelled += length
    return found


def _knob(
    explicit: float | None,
    hand: bool,
    style_value: float,
) -> float:
    """Explicit wins. Otherwise the style hand, or 0."""
    if explicit is not None:
        return explicit
    if hand:
        return style_value
    return 0.0


def _strength(explicit: float | None, default: float) -> float:
    """Kind default unless the mark sets strength."""
    if explicit is None:
        return default
    return explicit


def _span(a: tuple[float, float], b: tuple[float, float]) -> float:
    return float(math.hypot(b[0] - a[0], b[1] - a[1]))


def _dab(
    mark: DabMark,
    seed: int,
    name: str,
    process: StyleProcess,
) -> list[Dab]:
    jitter = _knob(mark.jitter, mark.hand, process.jitter)
    strength = _strength(mark.strength, 0.85)
    x, y = mark.at
    radius = mark.radius
    if jitter:
        radius *= 1.0 + signed(seed, name, 0, 0) * jitter
        x += signed(seed, name, 0, 1) * jitter * mark.radius
        y += signed(seed, name, 0, 2) * jitter * mark.radius
    return [(x, y, max(radius, 0.5), strength)]


def _stroke(
    mark: StrokeMark | StrokePathMark,
    seed: int,
    name: str,
    process: StyleProcess,
    radius_end: float | None,
) -> list[Dab]:
    return polyline_dabs(
        mark.points,
        mark.radius,
        mark.spacing,
        _strength(mark.strength, 0.85),
        seed=seed,
        name=name,
        jitter=_knob(mark.jitter, mark.hand, process.jitter),
        irregularity=_knob(
            mark.irregularity, mark.hand, process.irregularity,
        ),
        radius_end=radius_end,
    )


def _wash(
    mark: WashMark,
    seed: int,
    name: str,
    process: StyleProcess,
) -> list[Dab]:
    jitter = _knob(mark.jitter, mark.hand, process.jitter)
    density = _knob(mark.density, mark.hand, process.density)
    overlap = _knob(mark.overlap, mark.hand, process.overlap)
    strength = _strength(mark.strength, 0.4)
    radius = max(4.0, 0.22 * min(mark.rect.width, mark.rect.height))
    step = _field_step(radius, density, overlap)
    return _field(
        mark.rect, step, radius, strength, jitter, seed, name,
        ellipse=mark.shape == "ellipse",
    )


def _scatter(
    mark: ScatterMark,
    seed: int,
    name: str,
    process: StyleProcess,
) -> list[Dab]:
    jitter = _knob(mark.jitter, mark.hand, process.jitter)
    strength = _strength(mark.strength, 0.85)
    rect = mark.rect
    span_x = max(rect.width - 2.0 * mark.radius, 1.0)
    span_y = max(rect.height - 2.0 * mark.radius, 1.0)
    found: list[Dab] = []
    for i in range(mark.count):
        x = rect.x + mark.radius + unit(seed, name, i, 0) * span_x
        y = rect.y + mark.radius + unit(seed, name, i, 1) * span_y
        radius = mark.radius
        if jitter:
            radius *= 1.0 + signed(seed, name, i, 2) * jitter
        found.append((x, y, max(radius, 0.5), strength))
    return found


def _hatch(
    mark: HatchMark,
    seed: int,
    name: str,
    process: StyleProcess,
) -> list[Dab]:
    jitter = _knob(mark.jitter, mark.hand, process.jitter)
    density = _knob(mark.density, mark.hand, process.density)
    irregularity = _knob(
        mark.irregularity, mark.hand, process.irregularity,
    )
    strength = _strength(mark.strength, 0.7)
    count = mark.count if mark.count is not None else max(
        2, 2 + int(density * 10),
    )
    rect = mark.rect
    dx, dy = math.cos(mark.angle), math.sin(mark.angle)
    nx, ny = -dy, dx
    extent = abs(nx) * rect.width / 2 + abs(ny) * rect.height / 2
    along = abs(dx) * rect.width / 2 + abs(dy) * rect.height / 2 + 2
    cx = rect.x + rect.width / 2
    cy = rect.y + rect.height / 2
    nudge = irregularity * min(rect.width, rect.height) * 0.08
    found: list[Dab] = []
    cursor = 0
    for i in range(count):
        offset = -extent + ((i + 0.5) / count) * 2 * extent
        if jitter and extent > 0:
            offset += signed(seed, name, i, 0) * jitter * (extent / count)
        x0 = cx + nx * offset - dx * along
        y0 = cy + ny * offset - dy * along
        x1 = cx + nx * offset + dx * along
        y1 = cy + ny * offset + dy * along
        if nudge:
            x0 += signed(seed, name, i, 1) * nudge
            y0 += signed(seed, name, i, 2) * nudge
            x1 += signed(seed, name, i, 3) * nudge
            y1 += signed(seed, name, i, 4) * nudge
        clipped = _clip(x0, y0, x1, y1, rect)
        if clipped is None:
            continue
        radius = max(1.5, min(rect.width, rect.height) / (count * 3))
        dabs = polyline_dabs(
            [(clipped[0], clipped[1]), (clipped[2], clipped[3])],
            radius,
            0.55,
            strength,
            seed=seed,
            name=name,
            jitter=jitter,
            irregularity=0.0,
            index_base=cursor,
        )
        cursor += len(dabs)
        found.extend(dabs)
    return found


def _mass(
    mark: MassMark,
    seed: int,
    name: str,
    process: StyleProcess,
) -> list[Dab]:
    jitter = _knob(mark.jitter, mark.hand, process.jitter)
    overlap = _knob(mark.overlap, mark.hand, process.overlap)
    irregularity = _knob(
        mark.irregularity, mark.hand, process.irregularity,
    )
    strength = _strength(mark.strength, 0.9)
    if mark.points and len(mark.points) >= 3:
        outline = list(mark.points)
        rect = _bounds(outline)
    else:
        assert mark.rect is not None
        rect = mark.rect
        x, y = float(rect.x), float(rect.y)
        w, h = float(rect.width), float(rect.height)
        outline = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    radius = max(3.0, 0.08 * min(rect.width, rect.height))
    step = _field_step(radius, 0.0, overlap)
    body = _field(
        rect, step, radius, strength, jitter, seed, name,
        outline=outline,
    )
    edge = polyline_dabs(
        outline + [outline[0]],
        max(1.5, radius * 0.55),
        0.45,
        min(1.0, strength + 0.1),
        seed=seed,
        name=name,
        jitter=0.0,
        irregularity=irregularity,
        index_base=len(body) + 1,
    )
    return body + edge


def _field_step(radius: float, density: float, overlap: float) -> float:
    gap = radius * (1.1 - 0.75 * overlap)
    return max(gap / (0.45 + density), 1.5)


def _field(
    rect: MarkRect,
    step: float,
    radius: float,
    strength: float,
    jitter: float,
    seed: int,
    name: str,
    *,
    ellipse: bool = False,
    outline: list[tuple[float, float]] | None = None,
) -> list[Dab]:
    """Grid of dabs. ellipse or outline keeps centers inside."""
    cols = max(1, int(rect.width / step))
    rows = max(1, int(rect.height / step))
    if cols * rows > _CAP:
        grown = math.sqrt((cols * rows) / _CAP)
        step *= grown
        cols = max(1, int(rect.width / step))
        rows = max(1, int(rect.height / step))
    found: list[Dab] = []
    n = 0
    for row in range(rows):
        for col in range(cols):
            x = rect.x + (col + 0.5) * rect.width / cols
            y = rect.y + (row + 0.5) * rect.height / rows
            local = radius
            if jitter:
                local *= 1.0 + signed(seed, name, n, 0) * jitter
                x += signed(seed, name, n, 1) * jitter * radius
                y += signed(seed, name, n, 2) * jitter * radius
            if ellipse and not _in_ellipse(x, y, rect):
                n += 1
                continue
            if outline is not None and not _inside(x, y, outline):
                n += 1
                continue
            found.append((x, y, max(local, 0.5), strength))
            n += 1
    return found


def _bounds(points: list[tuple[float, float]]) -> MarkRect:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    return MarkRect(
        x=max(0, int(min_x)),
        y=max(0, int(min_y)),
        width=max(1, int(math.ceil(max_x - min_x))),
        height=max(1, int(math.ceil(max_y - min_y))),
    )


def _in_ellipse(x: float, y: float, rect: MarkRect) -> bool:
    cx = rect.x + rect.width / 2
    cy = rect.y + rect.height / 2
    rx = max(rect.width / 2, 0.001)
    ry = max(rect.height / 2, 0.001)
    return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0


def _inside(
    x: float,
    y: float,
    points: list[tuple[float, float]],
) -> bool:
    """Even-odd test. points is the outline, unclosed."""
    inside = False
    j = len(points) - 1
    for i, (xi, yi) in enumerate(points):
        xj, yj = points[j]
        if (yi > y) != (yj > y):
            cross = (xj - xi) * (y - yi) / ((yj - yi) or 1e-9) + xi
            if x < cross:
                inside = not inside
        j = i
    return inside


def _clip(
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    rect: MarkRect,
) -> tuple[float, float, float, float] | None:
    """Cohen-Sutherland clip to the rect. None if the line misses."""
    def code(x: float, y: float) -> int:
        bits = 0
        if x < rect.x:
            bits |= 1
        elif x > rect.x + rect.width:
            bits |= 2
        if y < rect.y:
            bits |= 4
        elif y > rect.y + rect.height:
            bits |= 8
        return bits

    c0, c1 = code(x0, y0), code(x1, y1)
    for _ in range(12):
        if c0 == 0 and c1 == 0:
            return (x0, y0, x1, y1)
        if c0 & c1:
            return None
        bits = c0 or c1
        if bits & 8:
            edge = rect.y + rect.height
            x = x0 + (x1 - x0) * (edge - y0) / ((y1 - y0) or 1e-9)
            y = edge
        elif bits & 4:
            y = float(rect.y)
            x = x0 + (x1 - x0) * (y - y0) / ((y1 - y0) or 1e-9)
        elif bits & 2:
            edge = rect.x + rect.width
            y = y0 + (y1 - y0) * (edge - x0) / ((x1 - x0) or 1e-9)
            x = edge
        else:
            x = float(rect.x)
            y = y0 + (y1 - y0) * (x - x0) / ((x1 - x0) or 1e-9)
        if bits == c0:
            x0, y0, c0 = x, y, code(x, y)
        else:
            x1, y1, c1 = x, y, code(x, y)
    return None
