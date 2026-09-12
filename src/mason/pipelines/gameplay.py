"""Downscale the primary beauty preview to gameplay size."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, UnidentifiedImageError

from mason.core.assets import AssetSpec
from mason.core.jobs import AssetJob
from mason.core.preview_roles import preview_roles_for, spec_is_garment

GAMEPLAY_PX = {"far": 64, "medium": 128, "close": 256}


def gameplay_size(spec: AssetSpec) -> int:
    """Pixel edge length from usage.viewing_distance."""
    direction = spec.art_direction
    distance = "medium"
    if direction is not None:
        distance = direction.usage.viewing_distance
    return GAMEPLAY_PX.get(distance, 128)


def write_gameplay_preview(job: AssetJob, spec: AssetSpec) -> Path | None:
    """Write previews/gameplay.png from the primary beauty still."""
    src = _primary_preview(job, spec)
    if src is None:
        return None
    try:
        image = Image.open(src)
        image.load()
    except (OSError, UnidentifiedImageError):
        return None
    edge = gameplay_size(spec)
    image.thumbnail((edge, edge))
    dest = job.previews / "gameplay.png"
    job.previews.mkdir(parents=True, exist_ok=True)
    image.save(dest)
    return dest


def _primary_preview(job: AssetJob, spec: AssetSpec) -> Path | None:
    roles = preview_roles_for(spec.type, garment=spec_is_garment(spec))
    names = [f"{roles['primary']}.png", "three_quarter.png", "worn.png",
             "full.png", "front.png"]
    for name in names:
        path = job.previews / name
        if path.is_file():
            return path
    return None
