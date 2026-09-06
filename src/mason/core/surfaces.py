"""Palette swatch layout and atlas cell UV math."""

from __future__ import annotations

from pathlib import Path

import yaml
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field

from mason.core.parts import ImageSource
from mason.core.paths import resolve_image_source
from mason.core.styles import hex_rgba
from mason.errors import MasonError

PALETTE_SIZE = 64
PALETTE_GRID = 4
SWATCH_PX = PALETTE_SIZE // PALETTE_GRID
UV_INSET = 2 / PALETTE_SIZE


class AtlasGrid(BaseModel):
    model_config = ConfigDict(extra="forbid")

    columns: int = Field(ge=1)
    rows: int = Field(ge=1)


class AtlasResource(BaseModel):
    """Shared artwork sheet: entries map to grid cells."""

    model_config = ConfigDict(extra="forbid")

    id: str
    image: ImageSource | None = None
    grid: AtlasGrid
    entries: dict[str, int] = Field(default_factory=dict)


def palette_keys(palette: dict[str, str]) -> list[str]:
    """Stable key order for swatch slots."""
    return sorted(palette)


def cell_uv_rect(
    index: int,
    columns: int,
    rows: int,
    inset: float = UV_INSET,
) -> tuple[float, float, float, float]:
    """Return (u0, v0, u1, v1) for a grid cell. V=1 is image top."""
    col = index % columns
    row = index // columns
    u0 = col / columns + inset
    u1 = (col + 1) / columns - inset
    v1 = 1.0 - row / rows - inset
    v0 = 1.0 - (row + 1) / rows + inset
    return (u0, v0, u1, v1)


def swatch_uv_rect(
    index: int,
    inset: float = UV_INSET,
) -> tuple[float, float, float, float]:
    """UV rect for one 4x4 palette swatch."""
    return cell_uv_rect(index, PALETTE_GRID, PALETTE_GRID, inset)


def swatch_rects_for(
    palette: dict[str, str],
) -> dict[str, list[float]]:
    """Map each palette key to a UV rect list."""
    keys = palette_keys(palette)
    rects: dict[str, list[float]] = {}
    for i, key in enumerate(keys[: PALETTE_GRID * PALETTE_GRID]):
        rects[key] = list(swatch_uv_rect(i))
    return rects


def write_palette_png(palette: dict[str, str], dest: Path) -> Path:
    """Write a 64x64 4x4 swatch sheet from style palette hexes."""
    keys = palette_keys(palette)
    img = Image.new("RGB", (PALETTE_SIZE, PALETTE_SIZE), (0, 0, 0))
    pixels = img.load()
    limit = PALETTE_GRID * PALETTE_GRID
    for i, key in enumerate(keys[:limit]):
        rgba = hex_rgba(palette[key])
        col = i % PALETTE_GRID
        row = i // PALETTE_GRID
        x0, y0 = col * SWATCH_PX, row * SWATCH_PX
        color = (rgba[0], rgba[1], rgba[2])
        for y in range(y0, y0 + SWATCH_PX):
            for x in range(x0, x0 + SWATCH_PX):
                pixels[x, y] = color
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest)
    return dest


def write_atlas_grid_png(
    dest: Path,
    columns: int,
    rows: int,
    size: int = 64,
) -> Path:
    """Write a simple colored grid used when an atlas has no image."""
    img = Image.new("RGB", (size, size), (20, 20, 20))
    pixels = img.load()
    cell_w = size // columns
    cell_h = size // rows
    colors = (
        (200, 70, 60), (60, 140, 200),
        (80, 170, 90), (210, 180, 70),
    )
    for row in range(rows):
        for col in range(columns):
            color = colors[(row * columns + col) % len(colors)]
            x0, y0 = col * cell_w, row * cell_h
            for y in range(y0, y0 + cell_h):
                for x in range(x0, x0 + cell_w):
                    pixels[x, y] = color
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest)
    return dest


def load_atlas(project_root: Path, name: str) -> AtlasResource:
    """Load atlases/<id>.yaml or examples/atlases/<id>.yaml."""
    candidates = (
        project_root / "atlases" / f"{name}.yaml",
        project_root / "examples" / "atlases" / f"{name}.yaml",
    )
    path = next((p for p in candidates if p.is_file()), None)
    if path is None:
        raise MasonError(
            f"Atlas '{name}' not found.",
            code="atlas_not_found",
            hint="Add atlases/<id>.yaml.",
            context={"atlas": name},
        )
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise MasonError(
            f"Atlas file must be a mapping: {path}",
            code="invalid_atlas",
        )
    try:
        return AtlasResource.model_validate(data)
    except Exception as exc:
        raise MasonError(
            f"Invalid atlas {path}: {exc}",
            code="invalid_atlas",
            context={"path": str(path)},
        ) from exc


def atlas_cell_rect(
    atlas: AtlasResource,
    entry: str,
) -> tuple[float, float, float, float]:
    """UV rect for a named atlas entry."""
    if entry not in atlas.entries:
        raise MasonError(
            f"Atlas '{atlas.id}' has no entry '{entry}'.",
            code="unknown_atlas_entry",
            hint="Use an entry from the atlas YAML.",
            context={
                "entry": entry,
                "available": sorted(atlas.entries),
            },
        )
    index = atlas.entries[entry]
    cells = atlas.grid.columns * atlas.grid.rows
    if index < 0 or index >= cells:
        raise MasonError(
            f"Atlas entry '{entry}' index {index} is out of range.",
            code="invalid_atlas_index",
            context={"index": index, "cells": cells},
        )
    return cell_uv_rect(index, atlas.grid.columns, atlas.grid.rows)


def resolve_atlas_image(
    project_root: Path,
    atlas: AtlasResource,
    dest: Path,
) -> Path:
    """Use the atlas PNG, or write a generated grid."""
    if atlas.image is not None:
        path = resolve_image_source(atlas.image, project_root)
        if path.is_file():
            return path
    return write_atlas_grid_png(
        dest, atlas.grid.columns, atlas.grid.rows,
    )


def prepare_surface_maps(job, spec, style) -> dict:
    """Build palette/atlas image paths and UV rects when opted in."""
    strategy = spec.materials.strategy
    if strategy == "palette":
        dest = job.dir / "palette.png"
        write_palette_png(style.palette, dest)
        return {
            "palette_image": str(dest),
            "swatch_rects": swatch_rects_for(style.palette),
        }
    if strategy == "atlas":
        atlas = load_atlas(job.project_root, spec.materials.atlas or "")
        dest = job.dir / "atlas.png"
        image = resolve_atlas_image(job.project_root, atlas, dest)
        rect = atlas_cell_rect(atlas, spec.materials.entry or "")
        return {
            "atlas_image": str(image),
            "atlas_rect": list(rect),
        }
    return {}
