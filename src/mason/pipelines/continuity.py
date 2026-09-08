"""Silhouette solidity: enclosed holes and islands."""

from __future__ import annotations

from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image


def preview_continuity(path: Path) -> dict:
    """Hole and island counts. Dark pixels are the subject."""
    if not path.is_file():
        return {"holes": 0, "islands": 0, "hole_pixels": 0}
    gray = np.array(Image.open(path).convert("L"))
    subject = gray < 128
    hole_mask = enclosed_holes(subject)
    return {
        "holes": _components(hole_mask),
        "islands": _components(subject),
        "hole_pixels": int(hole_mask.sum()),
    }


def enclosed_holes(subject: np.ndarray) -> np.ndarray:
    """True on white (False) regions not connected to the border."""
    background = ~subject
    visited = np.zeros_like(subject, dtype=bool)
    height, width = subject.shape
    queue: deque[tuple[int, int]] = deque()
    for x in range(width):
        queue.append((0, x))
        queue.append((height - 1, x))
    for y in range(height):
        queue.append((y, 0))
        queue.append((y, width - 1))
    while queue:
        y, x = queue.popleft()
        if y < 0 or x < 0 or y >= height or x >= width:
            continue
        if visited[y, x] or subject[y, x]:
            continue
        visited[y, x] = True
        queue.extend(((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)))
    return background & ~visited


def _components(mask: np.ndarray) -> int:
    """Count 4-connected True regions."""
    if not mask.any():
        return 0
    seen = np.zeros_like(mask, dtype=bool)
    height, width = mask.shape
    count = 0
    for y, x in zip(*np.nonzero(mask)):
        y, x = int(y), int(x)
        if seen[y, x]:
            continue
        count += 1
        queue: deque[tuple[int, int]] = deque([(y, x)])
        seen[y, x] = True
        while queue:
            cy, cx = queue.popleft()
            for ny, nx in (
                (cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1),
            ):
                if ny < 0 or nx < 0 or ny >= height or nx >= width:
                    continue
                if seen[ny, nx] or not mask[ny, nx]:
                    continue
                seen[ny, nx] = True
                queue.append((ny, nx))
    return count
