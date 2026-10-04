"""Bake stroke and mark layers into PNGs of round dabs."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from mason.core.assets import LayeredRasterSpec, RasterLayer
from mason.core.styles import StyleProfile
from mason.generators.raster.marks import layer_dabs


def bake_strokes(
    spec: LayeredRasterSpec,
    style: StyleProfile,
    dest: Path,
    width: int,
    height: int,
) -> LayeredRasterSpec:
    """Replace stroke and mark layers with image layers.

    dest: directory for the baked PNGs.
    width, height: canvas size in pixels.
    Returns a spec Krita can paint without a brush preset.
    """
    if not any(layer.stroke or layer.mark for layer in spec.layers):
        return spec
    dest.mkdir(parents=True, exist_ok=True)
    layers: list[RasterLayer] = []
    for layer in spec.layers:
        dabs = layer_dabs(layer, spec.seed, style)
        if dabs is None:
            layers.append(layer)
            continue
        path = dest / f"{layer.name}.png"
        _write(path, width, height, dabs, style.color(layer.fill or "ink"))
        layers.append(layer.model_copy(update={
            "stroke": None,
            "mark": None,
            "image": str(path),
            "fill": None,
        }))
    return spec.model_copy(update={"layers": layers})


def _write(
    path: Path,
    width: int,
    height: int,
    dabs: list[tuple[float, float, float, float]],
    color: str,
) -> None:
    """Stamp discs. color is #RRGGBB. Each dab is x, y, radius, strength."""
    mask = np.zeros((height, width), np.float32)
    yy, xx = np.mgrid[0:height, 0:width]
    rgb = _hex(color)
    for x, y, radius, strength in dabs:
        dist = np.hypot(xx - x, yy - y) / max(radius, 0.8)
        tip = np.clip(1.0 - dist, 0.0, 1.0)
        tip = tip * tip * (3.0 - 2.0 * tip)
        mask = np.maximum(mask, tip * strength)
    img = np.zeros((height, width, 4), np.uint8)
    img[..., 0] = rgb[0]
    img[..., 1] = rgb[1]
    img[..., 2] = rgb[2]
    img[..., 3] = np.clip(mask * 255.0, 0, 255).astype(np.uint8)
    Image.fromarray(img, mode="RGBA").save(path)


def _hex(value: str) -> tuple[int, int, int]:
    """Parse #RRGGBB."""
    text = value.strip().lstrip("#")
    return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)
