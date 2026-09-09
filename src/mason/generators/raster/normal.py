"""Height maps to tangent-space normals for 2D and 3D."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


def height_array_to_normal(
    height: np.ndarray,
    strength: float = 1.0,
) -> np.ndarray:
    """Sobel a [0,1] height field to RGB uint8 normals.

    Params: height float32 HxW, strength scale. Returns HxWx3.
    """
    h = np.asarray(height, dtype=np.float32)
    dx = np.zeros_like(h)
    dy = np.zeros_like(h)
    dx[:, 1:-1] = (h[:, 2:] - h[:, :-2]) * 0.5
    dy[1:-1, :] = (h[2:, :] - h[:-2, :]) * 0.5
    nx = -dx * float(strength)
    ny = -dy * float(strength)
    nz = np.ones_like(h)
    stacked = np.stack((nx, ny, nz), axis=-1)
    norm = np.linalg.norm(stacked, axis=-1, keepdims=True)
    stacked = stacked / np.clip(norm, 1e-6, None)
    return ((stacked * 0.5 + 0.5) * 255.0).clip(0, 255).astype(np.uint8)


def height_to_normal(
    src: Path,
    dest: Path,
    strength: float = 1.0,
) -> Path:
    """Read a height PNG, write an RGB normal map. Returns dest."""
    with Image.open(src) as img:
        gray = np.asarray(img.convert("L"), dtype=np.float32) / 255.0
    rgb = height_array_to_normal(gray, strength)
    dest.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgb, mode="RGB").save(dest)
    return dest
