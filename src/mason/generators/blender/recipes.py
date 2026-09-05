"""Expand crate/shelf/table recipes into box parts."""

from __future__ import annotations

from mason.core.assets import Dimensions3D, PropPart, RecipeParams
from mason.errors import MasonError


def expand_recipe(
    name: str,
    dims: Dimensions3D,
    params: RecipeParams,
    material: str,
) -> list[PropPart]:
    """Return parts for a named recipe."""
    if name == "crate":
        return crate_parts(dims, material)
    if name == "shelf":
        return shelf_parts(dims, params, material)
    if name == "table":
        return table_parts(dims, params, material)
    raise MasonError(
        f"Unknown recipe '{name}'.",
        code="unknown_recipe",
        hint="Use crate, shelf, table, or explicit parts.",
    )


def crate_parts(dims: Dimensions3D, material: str) -> list[PropPart]:
    """Single box sized to the spec, sitting on Z=0."""
    return [
        PropPart(
            name="crate",
            size=(dims.width, dims.depth, dims.height),
            location=(0.0, 0.0, dims.height / 2.0),
            material=material,
        ),
    ]


def shelf_parts(
    dims: Dimensions3D,
    params: RecipeParams,
    material: str,
) -> list[PropPart]:
    """Side panels plus evenly spaced shelves."""
    w, d, h = dims.width, dims.depth, dims.height
    t = min(params.board_thickness, w / 4, d / 4, h / 8)
    parts: list[PropPart] = []
    inner_w = w - (2 * t if params.side_panels else 0.0)

    if params.side_panels:
        parts.append(PropPart(
            name="left_side",
            size=(t, d, h),
            location=(-(w / 2.0) + t / 2.0, 0.0, h / 2.0),
            material=material,
        ))
        parts.append(PropPart(
            name="right_side",
            size=(t, d, h),
            location=((w / 2.0) - t / 2.0, 0.0, h / 2.0),
            material=material,
        ))

    count = params.shelf_count
    if count == 1:
        zs = [h / 2.0]
    else:
        span = h - t
        zs = [t / 2.0 + i * (span / (count - 1)) for i in range(count)]
    for i, z in enumerate(zs):
        parts.append(PropPart(
            name=f"shelf_{i + 1}",
            size=(inner_w, d, t),
            location=(0.0, 0.0, z),
            material=material,
        ))

    if params.back_panel:
        parts.append(PropPart(
            name="back",
            size=(w, t, h),
            location=(0.0, (d / 2.0) - t / 2.0, h / 2.0),
            material=material,
        ))
    return parts


def table_parts(
    dims: Dimensions3D,
    params: RecipeParams,
    material: str,
) -> list[PropPart]:
    """Tabletop and four legs."""
    w, d, h = dims.width, dims.depth, dims.height
    top_t = min(params.board_thickness, h / 4)
    leg = min(params.leg_thickness, w / 4, d / 4)
    inset = leg
    parts = [
        PropPart(
            name="top",
            size=(w, d, top_t),
            location=(0.0, 0.0, h - top_t / 2.0),
            material=material,
        ),
    ]
    leg_h = max(h - top_t, 0.01)
    for name, sx, sy in (
        ("leg_fl", -1, -1),
        ("leg_fr", 1, -1),
        ("leg_bl", -1, 1),
        ("leg_br", 1, 1),
    ):
        parts.append(PropPart(
            name=name,
            size=(leg, leg, leg_h),
            location=(
                sx * (w / 2.0 - inset),
                sy * (d / 2.0 - inset),
                leg_h / 2.0,
            ),
            material=material,
        ))
    return parts
