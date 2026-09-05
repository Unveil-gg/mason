"""Blender argv construction."""

from __future__ import annotations

from pathlib import Path


def headless_python(script: Path, extra: list[str]) -> list[str]:
    """Return args after the blender executable."""
    return [
        "--background",
        "--python",
        str(script),
        "--",
        *extra,
    ]


def preview_from_blend(
    blend: Path,
    script: Path,
    extra: list[str],
) -> list[str]:
    """Open a .blend and run the preview script."""
    return [
        "--background",
        str(blend),
        "--python",
        str(script),
        "--",
        *extra,
    ]
