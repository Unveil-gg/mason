"""Expand raster layer stamps into fill rects."""

from __future__ import annotations

from mason.core.assets import LayerRect, RasterLayer

STAMPS = ("l_corner", "gem", "rule")


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


def _fill(
    layer: RasterLayer,
    name: str,
    rect: LayerRect,
    fill: str | None = None,
) -> RasterLayer:
    return RasterLayer(
        name=name,
        role=layer.role or "fill",
        fill=fill or layer.fill,
        rect=rect,
    )
