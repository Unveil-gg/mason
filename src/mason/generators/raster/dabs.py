"""Bake a stroke layer into a PNG of overlapping round dabs."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from mason.core.assets import DabStroke, LayeredRasterSpec, RasterLayer
from mason.core.styles import StyleProfile


def bake_strokes(
    spec: LayeredRasterSpec,
    style: StyleProfile,
    dest: Path,
    width: int,
    height: int,
) -> LayeredRasterSpec:
    """Replace stroke layers with image layers. Other layers stay.

    dest: directory for the baked PNGs.
    width, height: canvas size in pixels.
    Returns a spec Krita can paint without a brush preset.
    """
    if not any(layer.stroke for layer in spec.layers):
        return spec
    dest.mkdir(parents=True, exist_ok=True)
    layers: list[RasterLayer] = []
    for layer in spec.layers:
        if layer.stroke is None:
            layers.append(layer)
            continue
        path = dest / f"{layer.name}.png"
        _write(path, width, height, layer.stroke, style.color(layer.fill or "ink"))
        layers.append(layer.model_copy(update={
            "stroke": None,
            "image": str(path),
            "fill": None,
        }))
    return spec.model_copy(update={"layers": layers})


def _write(
    path: Path,
    width: int,
    height: int,
    stroke: DabStroke,
    color: str,
) -> None:
    """Stamp discs along the polyline. color is #RRGGBB."""
    mask = np.zeros((height, width), np.float32)
    yy, xx = np.mgrid[0:height, 0:width]
    rgb = _hex(color)
    for x, y, radius in _marks(stroke):
        dist = np.hypot(xx - x, yy - y) / max(radius, 0.8)
        tip = np.clip(1.0 - dist, 0.0, 1.0)
        tip = tip * tip * (3.0 - 2.0 * tip)
        mask = np.maximum(mask, tip * stroke.strength)
    img = np.zeros((height, width, 4), np.uint8)
    img[..., 0] = rgb[0]
    img[..., 1] = rgb[1]
    img[..., 2] = rgb[2]
    img[..., 3] = np.clip(mask * 255.0, 0, 255).astype(np.uint8)
    Image.fromarray(img, mode="RGBA").save(path)


def _marks(stroke: DabStroke) -> list[tuple[float, float, float]]:
    """Centers stepped along the polyline. radius is in pixels."""
    step = max(stroke.radius * 2.0 * stroke.spacing, 1.0)
    found: list[tuple[float, float, float]] = []
    points = stroke.points
    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        length = float(np.hypot(x1 - x0, y1 - y0))
        count = max(int(length / step), 1)
        for k in range(count + 1):
            t = k / count
            found.append((
                x0 + (x1 - x0) * t,
                y0 + (y1 - y0) * t,
                stroke.radius,
            ))
    return found


def _hex(value: str) -> tuple[int, int, int]:
    """Parse #RRGGBB."""
    text = value.strip().lstrip("#")
    return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)
