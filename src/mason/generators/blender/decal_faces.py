"""Verified rotation/size table for `decal.face` shorthand.

Each entry was derived from Blender's XYZ Euler rotation matrix
(R = Rz @ Ry @ Rx) rather than guessed: it is the rotation that (a)
points the plane's outward normal at the named face and (b) keeps
the source image's V axis (or, where impossible, only U) unmirrored.
Top/front/right read the image unmirrored; back/left mirror
horizontally and bottom mirrors vertically -- unavoidable once you
are looking at a face from the far side. `create_plane` scales the
plane in local space *before* rotating, so the world-space extents
below (u_dim, v_dim) always land on the physical face without the
axis-swap bug a naive per-face rotation can hit (verified against a
regression test).
"""

from __future__ import annotations

import math

from mason.core.parts import Dimensions3D

PI = math.pi
HALF_PI = math.pi / 2.0

# face -> (rotation, u_dim, v_dim), where u_dim/v_dim name which of
# width/depth/height the decal's size (size[0], size[1]) should be.
_FACE_ROTATIONS: dict[
    str, tuple[tuple[float, float, float], str, str],
] = {
    "top": ((0.0, 0.0, 0.0), "width", "depth"),
    "bottom": ((PI, 0.0, 0.0), "width", "depth"),
    "front": ((HALF_PI, 0.0, 0.0), "width", "height"),
    "back": ((HALF_PI, 0.0, PI), "width", "height"),
    "right": ((HALF_PI, 0.0, HALF_PI), "depth", "height"),
    "left": ((HALF_PI, 0.0, -HALF_PI), "depth", "height"),
}


def resolve_face(
    face: str,
    dimensions: Dimensions3D,
    inset: float,
) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float]]:
    """Return (location, rotation, size) for a named box face.

    `dimensions` is the prop's own width/depth/height; the box is
    assumed centered on X and Y with its base at Z=0 (Mason's own
    convention for `geometry.recipe` and plain part boxes).
    """
    rotation, u_key, v_key = _FACE_ROTATIONS[face]
    dims = {
        "width": dimensions.width,
        "depth": dimensions.depth,
        "height": dimensions.height,
    }
    size = (dims[u_key], dims[v_key])
    half_w, half_d, half_h = (
        dimensions.width / 2.0, dimensions.depth / 2.0,
        dimensions.height / 2.0,
    )
    location = {
        "top": (0.0, 0.0, dimensions.height + inset),
        "bottom": (0.0, 0.0, -inset),
        "front": (0.0, -half_d - inset, half_h),
        "back": (0.0, half_d + inset, half_h),
        "right": (half_w + inset, 0.0, half_h),
        "left": (-half_w - inset, 0.0, half_h),
    }[face]
    return location, rotation, size
