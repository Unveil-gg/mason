"""Height-to-normal conversion."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from mason.generators.raster.normal import (
    height_array_to_normal,
    height_to_normal,
)


def test_flat_height_is_up() -> None:
    flat = np.full((8, 8), 0.5, dtype=np.float32)
    rgb = height_array_to_normal(flat)
    pixel = rgb[4, 4]
    assert abs(int(pixel[0]) - 128) <= 1
    assert abs(int(pixel[1]) - 128) <= 1
    assert int(pixel[2]) >= 250


def test_height_to_normal_writes_png(tmp_path: Path) -> None:
    src = tmp_path / "h.png"
    dest = tmp_path / "n.png"
    Image.new("L", (16, 16), 128).save(src)
    height_to_normal(src, dest, strength=1.0)
    with Image.open(dest) as img:
        assert img.size == (16, 16)
        assert img.mode == "RGB"
