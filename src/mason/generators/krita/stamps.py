"""Expand raster layer stamps into fill rects."""

from __future__ import annotations

from typing import Literal

from mason.core.assets import LayerRect, RasterLayer

STAMPS = (
    "l_corner", "gem", "rule", "bond",
    "dapple", "vignette", "figure",
)


def expand_stamps(layers: list[RasterLayer]) -> list[RasterLayer]:
    """Replace stamped layers with the fill rects they describe."""
    out: list[RasterLayer] = []
    for layer in layers:
        if not layer.stamp:
            out.append(layer)
            continue
        if layer.stamp == "l_corner":
            out.extend(_l_corner(layer))
        elif layer.stamp == "gem":
            out.extend(_gem(layer))
        elif layer.stamp == "rule":
            out.extend(_rule(layer))
        elif layer.stamp == "bond":
            out.extend(_bond(layer))
        elif layer.stamp == "dapple":
            out.extend(_dapple(layer))
        elif layer.stamp == "vignette":
            out.extend(_vignette(layer))
        elif layer.stamp == "figure":
            out.extend(_figure(layer))
        else:
            out.append(layer)
    return out


def _l_corner(layer: RasterLayer) -> list[RasterLayer]:
    rect = layer.rect
    assert rect is not None
    t = max(3, min(rect.width, rect.height) // 5)
    corner = layer.stamp_corner
    if corner == "tr":
        h = LayerRect(
            x=rect.x, y=rect.y, width=rect.width, height=t,
        )
        v = LayerRect(
            x=rect.x + rect.width - t, y=rect.y,
            width=t, height=rect.height,
        )
    elif corner == "bl":
        h = LayerRect(
            x=rect.x, y=rect.y + rect.height - t,
            width=rect.width, height=t,
        )
        v = LayerRect(
            x=rect.x, y=rect.y, width=t, height=rect.height,
        )
    elif corner == "br":
        h = LayerRect(
            x=rect.x, y=rect.y + rect.height - t,
            width=rect.width, height=t,
        )
        v = LayerRect(
            x=rect.x + rect.width - t, y=rect.y,
            width=t, height=rect.height,
        )
    else:
        h = LayerRect(
            x=rect.x, y=rect.y, width=rect.width, height=t,
        )
        v = LayerRect(
            x=rect.x, y=rect.y, width=t, height=rect.height,
        )
    return [
        _fill(layer, f"{layer.name}_h", h),
        _fill(layer, f"{layer.name}_v", v),
    ]


def _gem(layer: RasterLayer) -> list[RasterLayer]:
    rect = layer.rect
    assert rect is not None
    inset = max(3, min(rect.width, rect.height) // 6)
    inner = LayerRect(
        x=rect.x + inset,
        y=rect.y + inset,
        width=max(rect.width - 2 * inset, 2),
        height=max(rect.height - 2 * inset, 2),
    )
    shine_s = max(2, inset)
    shine = LayerRect(
        x=inner.x + 2,
        y=inner.y + 2,
        width=shine_s,
        height=shine_s,
    )
    inner_fill = layer.stamp_inner or layer.fill
    return [
        _fill(layer, f"{layer.name}_bezel", rect),
        _fill(layer, f"{layer.name}_stone", inner, fill=inner_fill),
        _fill(layer, f"{layer.name}_shine", shine),
    ]


def _rule(layer: RasterLayer) -> list[RasterLayer]:
    rect = layer.rect
    assert rect is not None
    if rect.width >= rect.height:
        cap = rect.height
        left = LayerRect(x=rect.x, y=rect.y, width=cap, height=cap)
        right = LayerRect(
            x=rect.x + rect.width - cap, y=rect.y,
            width=cap, height=cap,
        )
    else:
        cap = rect.width
        left = LayerRect(x=rect.x, y=rect.y, width=cap, height=cap)
        right = LayerRect(
            x=rect.x, y=rect.y + rect.height - cap,
            width=cap, height=cap,
        )
    return [
        _fill(layer, f"{layer.name}_bar", rect),
        _fill(layer, f"{layer.name}_a", left),
        _fill(layer, f"{layer.name}_b", right),
    ]


def _bond(layer: RasterLayer) -> list[RasterLayer]:
    """Running-bond joints: courses plus staggered tabs."""
    rect = layer.rect
    assert rect is not None
    courses = 8
    tabs = 8
    joint = 3
    ch = max(rect.height // courses, joint + 1)
    tw = max(rect.width // tabs, joint + 1)
    out: list[RasterLayer] = []
    for row in range(1, courses + 1):
        y = min(rect.y + row * ch - joint, rect.y + rect.height - joint)
        out.append(_fill(
            layer,
            f"{layer.name}_h{row}",
            LayerRect(x=rect.x, y=y, width=rect.width, height=joint),
        ))
    for row in range(courses):
        shift = (tw // 2) if row % 2 else 0
        y0 = rect.y + row * ch
        h = min(ch, rect.y + rect.height - y0)
        col = 0
        x = rect.x + shift
        while x < rect.x + rect.width:
            out.append(_fill(
                layer,
                f"{layer.name}_v{row}_{col}",
                LayerRect(
                    x=x, y=y0, width=joint,
                    height=max(h, 1),
                ),
            ))
            col += 1
            x += tw
    return out


def _dapple(layer: RasterLayer) -> list[RasterLayer]:
    """Overlapping ellipses that read as leaf clusters, not tiles."""
    rect = layer.rect
    assert rect is not None
    out: list[RasterLayer] = []
    for i in range(32):
        seed = (
            i * 1103515245 + 12345 + rect.width * 31 + rect.height
        ) & 0x7FFFFFFF
        bw = 5 + (seed % 8)
        bh = 4 + ((seed >> 6) % 7)
        if bw >= rect.width or bh >= rect.height:
            continue
        x = rect.x + ((seed >> 3) % max(rect.width - bw, 1))
        y = rect.y + ((seed >> 11) % max(rect.height - bh, 1))
        out.append(_fill(
            layer,
            f"{layer.name}_{i}",
            LayerRect(x=x, y=y, width=bw, height=bh),
            shape="ellipse",
        ))
    return out


def _vignette(layer: RasterLayer) -> list[RasterLayer]:
    """Three hollow frames inset from the rect (poster edge)."""
    rect = layer.rect
    assert rect is not None
    t = max(4, min(rect.width, rect.height) // 16)
    out: list[RasterLayer] = []
    for ring in range(3):
        inset = ring * t
        x = rect.x + inset
        y = rect.y + inset
        w = rect.width - 2 * inset
        h = rect.height - 2 * inset
        if w < t * 2 or h < t * 2:
            break
        prefix = f"{layer.name}_r{ring}"
        ring_h = max(h - 2 * t, 1)
        out.extend([
            _fill(
                layer, f"{prefix}_t",
                LayerRect(x=x, y=y, width=w, height=t),
            ),
            _fill(
                layer, f"{prefix}_b",
                LayerRect(x=x, y=y + h - t, width=w, height=t),
            ),
            _fill(
                layer, f"{prefix}_l",
                LayerRect(x=x, y=y + t, width=t, height=ring_h),
            ),
            _fill(
                layer, f"{prefix}_r",
                LayerRect(x=x + w - t, y=y + t, width=t, height=ring_h),
            ),
        ])
    return out


def _figure(layer: RasterLayer) -> list[RasterLayer]:
    """Stacked person mass: hat, head, coat. Scales with the rect."""
    rect = layer.rect
    assert rect is not None
    x, y, w, h = rect.x, rect.y, rect.width, rect.height

    def box(name: str, u: float, v: float, uw: float, vh: float):
        return _fill(
            layer,
            f"{layer.name}_{name}",
            LayerRect(
                x=x + int(w * u),
                y=y + int(h * v),
                width=max(int(w * uw), 2),
                height=max(int(h * vh), 2),
            ),
        )

    head = LayerRect(
        x=x + int(w * 0.38),
        y=y + int(h * 0.16),
        width=max(int(w * 0.24), 2),
        height=max(int(h * 0.14), 2),
    )
    return [
        box("hat", 0.42, 0.05, 0.16, 0.08),
        box("brim", 0.28, 0.12, 0.44, 0.04),
        _fill(layer, f"{layer.name}_head", head, shape="ellipse"),
        box("shoulders", 0.30, 0.30, 0.40, 0.08),
        box("coat", 0.28, 0.38, 0.44, 0.34),
        box("flare", 0.24, 0.70, 0.52, 0.26),
    ]


def _fill(
    layer: RasterLayer,
    name: str,
    rect: LayerRect,
    fill: str | None = None,
    shape: Literal["rect", "ellipse"] = "rect",
) -> RasterLayer:
    return RasterLayer(
        name=name,
        role=layer.role or "fill",
        fill=fill or layer.fill,
        rect=rect,
        shape=shape,
    )
