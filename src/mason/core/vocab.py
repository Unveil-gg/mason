"""Compact catalog of Mason authoring vocabulary."""

from __future__ import annotations

from typing import Any

from mason.generators.blender.components import COMPONENTS
from mason.generators.krita.stamps import STAMPS

SHAPES = (
    "box", "cylinder", "plane", "cone", "torus",
    "tapered_box", "sphere",
)
RECIPES = (
    "crate", "shelf", "table", "hydrant", "cart",
    "house", "tree", "pool", "estate",
)
LAYER_ROLES = ("background", "fill", "text", "image", "overlay")
FAMILIES = (
    "painted_metal", "bare_metal", "varnished_wood",
    "rubber", "plastic", "cardboard",
    "masonry", "roofing", "foliage", "water",
)


def vocab_payload() -> dict[str, Any]:
    """Return the agent vocabulary card."""
    return {
        "shapes": list(SHAPES),
        "components": sorted(COMPONENTS),
        "recipes": list(RECIPES),
        "layer_roles": list(LAYER_ROLES),
        "stamps": list(STAMPS),
        "families": list(FAMILIES),
        "texture": (
            "Prefer materials.strategy palette, then atlas, "
            "then bespoke. part.texture {path|asset+file} is "
            "albedo. Planes stretch UV (decals). Other "
            "textured shapes use world-space UVs. "
            "family.tile_size overrides style tile_size. "
            "Style family.albedo applies when the file "
            "exists."
        ),
        "inspect": (
            "preview_roles.primary is three_quarter beauty. "
            "Inspect beauty first, clay for modeling, "
            "silhouette only for readability. "
            "silhouette_regressed is advisory. "
            "context is future in-engine preview."
        ),
        "snap": (
            "part.snap {to, on: top|bottom|front|back|left|right, "
            "embed} meets a named face. embed pushes into the "
            "target so sloped roofs get a through-joint."
        ),
        "decimate": (
            "geometry.decimate is an optional keep-ratio "
            "(0-1) Blender collapse after cutouts. Off by default."
        ),
        "cutout": (
            "part.cutout {target} subtracts this mesh from the "
            "named part, then discards the cutter. One subtract "
            "each. No nested CSG."
        ),
    }
