"""Structure and ornament component expanders."""

from __future__ import annotations

import math

from mason.core.parts import PropPart


def _params(part: PropPart) -> dict[str, float]:
    return dict(part.component_params)


def _child(
    part: PropPart,
    suffix: str,
    *,
    shape: str,
    size: tuple[float, float, float],
    location: tuple[float, float, float],
    rotation: tuple[float, float, float] | None = None,
) -> PropPart:
    return PropPart(
        name=f"{part.name}_{suffix}",
        shape=shape,  # type: ignore[arg-type]
        size=size,
        location=location,
        rotation=rotation or part.rotation,
        material=part.material,
        family=part.family,
        wear=part.wear,
        parent=part.parent,
        bevel=part.bevel,
    )


def x_brace(part: PropPart) -> list[PropPart]:
    """Two diagonal bars filling the part AABB."""
    w, d, h = part.size
    x, y, z = part.location
    t = _params(part).get("thickness") or min(w, d, h) * 0.12
    t = max(t, 0.004)
    if d <= w and d <= h:
        diag = math.hypot(w, h)
        ang = math.atan2(h, w)
        return [
            _child(
                part, "a", shape="box",
                size=(diag, t, t), location=(x, y, z),
                rotation=(0.0, ang, 0.0),
            ),
            _child(
                part, "b", shape="box",
                size=(diag, t, t), location=(x, y, z),
                rotation=(0.0, -ang, 0.0),
            ),
        ]
    if w <= d and w <= h:
        diag = math.hypot(d, h)
        ang = math.atan2(h, d)
        return [
            _child(
                part, "a", shape="box",
                size=(t, diag, t), location=(x, y, z),
                rotation=(ang, 0.0, 0.0),
            ),
            _child(
                part, "b", shape="box",
                size=(t, diag, t), location=(x, y, z),
                rotation=(-ang, 0.0, 0.0),
            ),
        ]
    diag = math.hypot(w, d)
    ang = math.atan2(d, w)
    return [
        _child(
            part, "a", shape="box",
            size=(diag, t, t), location=(x, y, z),
            rotation=(0.0, 0.0, ang),
        ),
        _child(
            part, "b", shape="box",
            size=(diag, t, t), location=(x, y, z),
            rotation=(0.0, 0.0, -ang),
        ),
    ]


def rail(part: PropPart) -> list[PropPart]:
    """Four thin boxes around the part perimeter."""
    w, d, h = part.size
    x, y, z = part.location
    t = _params(part).get("thickness") or min(w, d, h) * 0.12
    t = max(t, 0.004)
    if h <= w and h <= d:
        return [
            _child(
                part, "s", shape="box",
                size=(w, t, h), location=(x, y - d / 2.0 + t / 2.0, z),
            ),
            _child(
                part, "n", shape="box",
                size=(w, t, h), location=(x, y + d / 2.0 - t / 2.0, z),
            ),
            _child(
                part, "w", shape="box",
                size=(t, d, h), location=(x - w / 2.0 + t / 2.0, y, z),
            ),
            _child(
                part, "e", shape="box",
                size=(t, d, h), location=(x + w / 2.0 - t / 2.0, y, z),
            ),
        ]
    if d <= w and d <= h:
        return [
            _child(
                part, "bot", shape="box",
                size=(w, d, t), location=(x, y, z - h / 2.0 + t / 2.0),
            ),
            _child(
                part, "top", shape="box",
                size=(w, d, t), location=(x, y, z + h / 2.0 - t / 2.0),
            ),
            _child(
                part, "l", shape="box",
                size=(t, d, h), location=(x - w / 2.0 + t / 2.0, y, z),
            ),
            _child(
                part, "r", shape="box",
                size=(t, d, h), location=(x + w / 2.0 - t / 2.0, y, z),
            ),
        ]
    return [
        _child(
            part, "bot", shape="box",
            size=(w, t, h), location=(x, y - d / 2.0 + t / 2.0, z),
        ),
        _child(
            part, "top", shape="box",
            size=(w, t, h), location=(x, y + d / 2.0 - t / 2.0, z),
        ),
        _child(
            part, "l", shape="box",
            size=(w, d, t), location=(x, y, z - h / 2.0 + t / 2.0),
        ),
        _child(
            part, "r", shape="box",
            size=(w, d, t), location=(x, y, z + h / 2.0 - t / 2.0),
        ),
    ]


def wire_wall(part: PropPart) -> list[PropPart]:
    """Bars spanning the wall, spaced along the long face axis."""
    w, d, h = part.size
    x, y, z = part.location
    count = max(2, int(_params(part).get("count") or 6))
    t = _params(part).get("thickness") or min(w, d) * 0.8
    t = max(t, 0.004)
    bars: list[PropPart] = []
    if w <= d and w <= h:
        span = d
        for i in range(count):
            frac = i / (count - 1)
            yy = y - span / 2.0 + frac * span
            bars.append(_child(
                part, str(i + 1), shape="box",
                size=(t, t, h), location=(x, yy, z),
            ))
        return bars
    if d <= w and d <= h:
        span = w
        for i in range(count):
            frac = i / (count - 1)
            xx = x - span / 2.0 + frac * span
            bars.append(_child(
                part, str(i + 1), shape="box",
                size=(t, t, h), location=(xx, y, z),
            ))
        return bars
    span = w
    for i in range(count):
        frac = i / (count - 1)
        xx = x - span / 2.0 + frac * span
        bars.append(_child(
            part, str(i + 1), shape="box",
            size=(t, d, t), location=(xx, y, z),
        ))
    return bars


def rivet_strip(part: PropPart) -> list[PropPart]:
    """Linear or radial bolts along the part AABB."""
    w, d, h = part.size
    x, y, z = part.location
    p = _params(part)
    count = max(2, int(p.get("count") or 4))
    radius = p.get("radius") or max(min(w, d, h) * 0.35, 0.004)
    depth = p.get("depth") or max(h, 0.008)
    locs: list[tuple[float, float, float]] = []
    ring = p.get("ring") or 0.0
    if ring > 0:
        for i in range(count):
            ang = 2.0 * math.pi * i / count
            locs.append((
                x + ring * math.cos(ang),
                y + ring * math.sin(ang),
                z,
            ))
    elif w >= d:
        for i in range(count):
            frac = i / (count - 1)
            locs.append((x - w / 2.0 + frac * w, y, z))
    else:
        for i in range(count):
            frac = i / (count - 1)
            locs.append((x, y - d / 2.0 + frac * d, z))
    parts: list[PropPart] = []
    head_h = max(depth * 0.35, 0.003)
    shank_h = max(depth - head_h, 0.003)
    for i, (lx, ly, lz) in enumerate(locs):
        n = str(i + 1)
        parts.append(_child(
            part, f"{n}_head", shape="box",
            size=(radius * 2.2, radius * 2.2, head_h),
            location=(lx, ly, lz + shank_h * 0.5),
        ))
        parts.append(_child(
            part, f"{n}_shank", shape="cylinder",
            size=(radius * 2.0, radius * 2.0, shank_h),
            location=(lx, ly, lz - head_h * 0.25),
        ))
    return parts


def cornice(part: PropPart) -> list[PropPart]:
    """Stacked molding steps, larger toward +Z."""
    w, d, h = part.size
    x, y, z = part.location
    steps = max(2, int(_params(part).get("steps") or 3))
    step_h = h / float(steps)
    inset_step = min(w, d) * 0.12
    parts: list[PropPart] = []
    for i in range(steps):
        inset = (steps - 1 - i) * inset_step
        zz = z - h / 2.0 + step_h * (i + 0.5)
        parts.append(_child(
            part, str(i + 1), shape="box",
            size=(
                max(w - 2.0 * inset, 0.008),
                max(d - 2.0 * inset, 0.008),
                step_h,
            ),
            location=(x, y, zz),
        ))
    return parts
