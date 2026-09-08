"""Which preview PNGs agents should open first."""

from __future__ import annotations

from typing import Any

from mason.tools.blender.preview import (
    BEAUTY_VIEWS,
    DIAGNOSTIC_VIEWS,
    PRIMARY_VIEW,
    SILHOUETTE_VIEWS,
)


def preview_roles_for(asset_type: str) -> dict[str, Any]:
    """Return primary / beauty / diagnostic roles for one asset type."""
    if asset_type in ("layered_raster", "sprite_sheet", "image_process"):
        return {
            "primary": "full",
            "beauty": ["full"],
            "diagnostic": ["compare"],
            "silhouette": [],
            "context": None,
        }
    return {
        "primary": PRIMARY_VIEW,
        "beauty": list(BEAUTY_VIEWS),
        "diagnostic": list(DIAGNOSTIC_VIEWS),
        "silhouette": list(SILHOUETTE_VIEWS),
        "context": None,
    }
