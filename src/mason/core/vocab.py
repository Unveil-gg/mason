"""Compact catalog of Mason authoring vocabulary."""

from __future__ import annotations

from typing import Any

from mason.generators.blender.components import COMPONENTS
from mason.generators.krita.stamps import STAMPS

SHAPES = (
    "box", "cylinder", "plane", "cone", "torus",
    "tapered_box", "sphere",
)
RECIPES = ("crate", "shelf", "table", "hydrant", "cart")
LAYER_ROLES = ("background", "fill", "text", "image", "overlay")
FAMILIES = (
    "painted_metal", "bare_metal", "varnished_wood",
    "rubber", "plastic", "cardboard",
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
            "part.texture {path|asset+file} is albedo. "
            "Planes stretch UV (decals). Other shapes tile. "
            "Style family.albedo applies when the file exists."
        ),
        "inspect": (
            "Open compare.png, then silhouette_front/side/"
            "three_quarter. Do not ship if silhouette_regressed."
        ),
        "snap": (
            "part.snap {to, on: top|bottom|front|back|left|right} "
            "meets named faces before components expand."
        ),
    }
