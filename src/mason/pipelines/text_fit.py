"""Shrink text layers so they fit their rect (no overflow)."""

from __future__ import annotations

from pathlib import Path

from PIL import ImageFont

from mason.core.assets import LayeredRasterSpec, RasterLayer

_FONT_CANDIDATES = (
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
)
_MIN_SIZE = 8


def fit_text_layers(spec: LayeredRasterSpec) -> LayeredRasterSpec:
    """Return a copy with font_size reduced until each text line fits."""
    layers = [_fit_one(layer) for layer in spec.layers]
    return spec.model_copy(update={"layers": layers})


def _fit_one(layer: RasterLayer) -> RasterLayer:
    if not layer.text or layer.rect is None:
        return layer
    size = layer.font_size
    max_w = max(layer.rect.width - 4, 1)
    while size > _MIN_SIZE and _text_width(layer.text, size) > max_w:
        size -= 2
    if size == layer.font_size:
        return layer
    return layer.model_copy(update={"font_size": size})


def _text_width(text: str, size: int) -> int:
    """Approximate rendered width in pixels. Params: text, size."""
    font = _font(size)
    if hasattr(font, "getbbox"):
        left, _, right, _ = font.getbbox(text)
        return right - left
    return int(font.getlength(text)) if hasattr(font, "getlength") else size * len(text)


def _font(size: int):
    for path in _FONT_CANDIDATES:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()
