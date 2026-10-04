"""Which preview PNGs agents should open first."""

from __future__ import annotations

from typing import Any

from mason.tools.blender.preview import (
    BEAUTY_VIEWS,
    DIAGNOSTIC_VIEWS,
    PRIMARY_VIEW,
    SILHOUETTE_VIEWS,
)


def spec_is_garment(spec: Any) -> bool:
    """True when the spec builds clothes around a character."""
    geom = getattr(spec, "geometry", None)
    return bool(getattr(geom, "garment", None))


def preview_roles_for(
    asset_type: str, *, garment: bool = False,
) -> dict[str, Any]:
    """Return primary / beauty / diagnostic roles for one asset type."""
    if asset_type == "layered_raster":
        return {
            "primary": "full",
            "beauty": ["full"],
            "diagnostic": ["compare", "gameplay"],
            "silhouette": ["silhouette"],
            "context": None,
        }
    if asset_type in ("sprite_sheet", "image_process"):
        return {
            "primary": "full",
            "beauty": ["full"],
            "diagnostic": ["compare", "gameplay"],
            "silhouette": [],
            "context": None,
        }
    if garment:
        return {
            "primary": "worn",
            "beauty": ["worn", "worn_sheet", *BEAUTY_VIEWS],
            "diagnostic": list(DIAGNOSTIC_VIEWS) + ["gameplay"],
            "silhouette": list(SILHOUETTE_VIEWS),
            "context": "worn",
        }
    return {
        "primary": PRIMARY_VIEW,
        "beauty": list(BEAUTY_VIEWS),
        "diagnostic": list(DIAGNOSTIC_VIEWS) + ["gameplay"],
        "silhouette": list(SILHOUETTE_VIEWS),
        "context": None,
    }
