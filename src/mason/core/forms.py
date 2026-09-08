"""Curve, skin, outline, and body-join models for static props."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CurvePoint(BaseModel):
    """One Bezier control. `at` is local to the part location."""

    model_config = ConfigDict(extra="forbid")

    at: tuple[float, float, float]
    handle_left: tuple[float, float, float] | None = None
    handle_right: tuple[float, float, float] | None = None
    radius: float = Field(default=1.0, ge=0)
    tilt: float = 0.0


class PartCurve(BaseModel):
    """Path construction: bevel, taper, optional cross-section."""

    model_config = ConfigDict(extra="forbid")

    points: list[CurvePoint] = Field(min_length=2)
    bevel_depth: float = Field(default=0.01, ge=0)
    bevel_resolution: int = Field(default=4, ge=0, le=16)
    resolution_u: int = Field(default=12, ge=2, le=64)
    taper: float | None = Field(default=None, ge=0, le=2)
    fill: Literal["full", "half", "none"] = "full"
    cyclic: bool = False
    bevel_profile: list[tuple[float, float]] | None = None


class SkinNode(BaseModel):
    """One skeleton node with a local radius."""

    model_config = ConfigDict(extra="forbid")

    id: str
    at: tuple[float, float, float]
    radius: float = Field(gt=0)


class PartSkin(BaseModel):
    """Node volumes. skeleton = Skin pipes; blob = spheres."""

    model_config = ConfigDict(extra="forbid")

    nodes: list[SkinNode] = Field(min_length=2)
    edges: list[tuple[str, str]] = Field(default_factory=list)
    mode: Literal["skeleton", "blob"] = "skeleton"
    subdivide: int = Field(default=1, ge=0, le=3)
    smooth: bool = True

    @model_validator(mode="after")
    def edges_exist(self) -> PartSkin:
        ids = [node.id for node in self.nodes]
        if len(set(ids)) != len(ids):
            raise ValueError("skin node ids must be unique")
        if self.mode == "skeleton" and len(self.edges) < 1:
            raise ValueError("skeleton skin needs edges")
        known = set(ids)
        for start, end in self.edges:
            if start not in known or end not in known:
                raise ValueError(
                    f"skin edge {start}->{end} has unknown node",
                )
            if start == end:
                raise ValueError("skin edge cannot be a self-loop")
        return self


class PartOutline(BaseModel):
    """Closed XZ silhouette, extruded along local Y."""

    model_config = ConfigDict(extra="forbid")

    points: list[tuple[float, float]] = Field(min_length=3)
    depth: float = Field(gt=0)


class PartFollow(BaseModel):
    """Deform this mesh along a named curve part."""

    model_config = ConfigDict(extra="forbid")

    curve: str
    stretch: bool = True


class BodyRemesh(BaseModel):
    """Voxel remesh settings after a volume union."""

    model_config = ConfigDict(extra="forbid")

    voxel_size: float = Field(gt=0)
    adaptivity: float = Field(default=0.0, ge=0, le=1)


class BodySpec(BaseModel):
    """Join named parts into one continuous mesh."""

    model_config = ConfigDict(extra="forbid")

    name: str
    members: list[str] = Field(min_length=1)
    method: Literal["union", "remesh"] = "remesh"
    remesh: BodyRemesh | None = None
    inflate: float = Field(default=0.0, ge=0)
    smooth: int = Field(default=0, ge=0, le=8)
    subdivide: int = Field(default=0, ge=0, le=3)
    material: str | None = None

    @model_validator(mode="after")
    def remesh_defaults(self) -> BodySpec:
        if self.method == "remesh" and self.remesh is None:
            self.remesh = BodyRemesh(voxel_size=0.01)
        return self


def curve_local_bounds(
    curve: PartCurve,
) -> tuple[list[float], list[float]]:
    """Local min/max of path points plus bevel padding."""
    pad = float(curve.bevel_depth)
    return _points_bounds([point.at for point in curve.points], pad)


def skin_local_bounds(skin: PartSkin) -> tuple[list[float], list[float]]:
    """Local min/max of nodes expanded by each radius."""
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    for node in skin.nodes:
        r = node.radius
        xs.extend((node.at[0] - r, node.at[0] + r))
        ys.extend((node.at[1] - r, node.at[1] + r))
        zs.extend((node.at[2] - r, node.at[2] + r))
    return (
        [min(xs), min(ys), min(zs)],
        [max(xs), max(ys), max(zs)],
    )


def outline_local_bounds(
    outline: PartOutline,
) -> tuple[list[float], list[float]]:
    """Local min/max of an XZ silhouette extruded along Y."""
    half = float(outline.depth) * 0.5
    xs = [point[0] for point in outline.points]
    zs = [point[1] for point in outline.points]
    return (
        [min(xs), -half, min(zs)],
        [max(xs), half, max(zs)],
    )


def curve_derived_size(curve: PartCurve) -> tuple[float, float, float]:
    """AABB of path points plus bevel padding."""
    lo, hi = curve_local_bounds(curve)
    return _span(lo, hi)


def skin_derived_size(skin: PartSkin) -> tuple[float, float, float]:
    """AABB of nodes expanded by each node's radius."""
    lo, hi = skin_local_bounds(skin)
    return _span(lo, hi)


def outline_derived_size(
    outline: PartOutline,
) -> tuple[float, float, float]:
    """Width from X, depth from extrusion, height from Z."""
    lo, hi = outline_local_bounds(outline)
    return _span(lo, hi)


def part_local_bounds(part) -> tuple[list[float], list[float]] | None:
    """Local AABB relative to location, or None if location is center."""
    if part.skin is not None:
        return skin_local_bounds(part.skin)
    if part.curve is not None:
        return curve_local_bounds(part.curve)
    if part.outline is not None:
        return outline_local_bounds(part.outline)
    return None


def finalize_form_part(part) -> bool:
    """Validate form fields and derive size. True if form shape."""
    if part.curve is not None and part.shape != "curve":
        raise ValueError("curve is only valid on shape: curve")
    if part.skin is not None and part.shape != "skin":
        raise ValueError("skin is only valid on shape: skin")
    if part.outline is not None and part.shape != "outline":
        raise ValueError("outline is only valid on shape: outline")
    if part.shape == "curve":
        if part.curve is None:
            raise ValueError("curve shape needs curve.points")
        if part.size is None:
            part.size = curve_derived_size(part.curve)
        return True
    if part.shape == "skin":
        if part.skin is None:
            raise ValueError("skin shape needs skin.nodes")
        if part.size is None:
            part.size = skin_derived_size(part.skin)
        return True
    if part.shape == "outline":
        if part.outline is None:
            raise ValueError("outline shape needs outline.points")
        if part.size is None:
            part.size = outline_derived_size(part.outline)
        return True
    return False


def member_to_body(
    part_names: list[str],
    bodies: list[BodySpec],
) -> dict[str, str]:
    """Map part names (including _m / _N copies) to a body name."""
    known = set(part_names)
    mapping: dict[str, str] = {}
    for body in bodies:
        for member in body.members:
            if member in known:
                mapping[member] = body.name
            prefix = member + "_"
            for name in part_names:
                if name.startswith(prefix):
                    mapping[name] = body.name
    return mapping


def _points_bounds(
    pts: list[tuple[float, float, float]],
    pad: float,
) -> tuple[list[float], list[float]]:
    xs = [point[0] for point in pts]
    ys = [point[1] for point in pts]
    zs = [point[2] for point in pts]
    return (
        [min(xs) - pad, min(ys) - pad, min(zs) - pad],
        [max(xs) + pad, max(ys) + pad, max(zs) + pad],
    )


def _span(
    lo: list[float],
    hi: list[float],
) -> tuple[float, float, float]:
    return (
        max(hi[0] - lo[0], 0.001),
        max(hi[1] - lo[1], 0.001),
        max(hi[2] - lo[2], 0.001),
    )
