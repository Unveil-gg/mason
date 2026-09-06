"""Expand crate/shelf/table recipes into box parts."""

from __future__ import annotations

from mason.core.assets import Dimensions3D, PropPart, RecipeParams
from mason.core.parts import PartArray, RadialArray
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
    if name == "hydrant":
        return hydrant_parts(dims, params, material)
    if name == "cart":
        from mason.generators.blender.recipes_cart import cart_parts
        return cart_parts(dims, params, material)
    if name in ("house", "tree", "pool", "estate"):
        from mason.generators.blender.recipes_estate import expand_estate
        return expand_estate(name, dims, params, material)
    raise MasonError(
        f"Unknown recipe '{name}'.",
        code="unknown_recipe",
        hint="Use crate, shelf, table, hydrant, cart, house, "
        "tree, pool, estate, or parts.",
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


def hydrant_parts(
    dims: Dimensions3D,
    params: RecipeParams,
    material: str,
) -> list[PropPart]:
    """Stylized fire hydrant: barrel, dome, outlets, flange, bolts."""
    _ = dims  # envelope is validation-only; params drive construction
    body_r = params.body_radius
    body_h = params.body_height
    paint = material
    steel = "steel"
    brass = "brass"
    base_h = body_r * 0.72
    barrel_z = base_h + body_h / 2.0
    dome_z = base_h + body_h + body_r * 0.35
    stem_h = body_r * 0.62
    stem_z = dome_z + body_r * 0.45
    nut_z = stem_z + stem_h * 0.55
    outlet_z = barrel_z + body_h * 0.08
    parts: list[PropPart] = [
        PropPart(
            name="base",
            shape="cylinder",
            size=(body_r * 2.6, body_r * 2.6, base_h),
            location=(0.0, 0.0, base_h / 2.0),
            material=paint,
            family="painted_metal",
        ),
        PropPart(
            name="barrel",
            shape="cylinder",
            size=(body_r * 2.0, body_r * 2.0, body_h),
            location=(0.0, 0.0, barrel_z),
            material=paint,
            family="painted_metal",
            wear=0.12,
        ),
        PropPart(
            name="dome",
            shape="sphere",
            size=(body_r * 2.05, body_r * 2.05, body_r * 1.7),
            location=(0.0, 0.0, dome_z),
            material=paint,
            family="painted_metal",
        ),
        PropPart(
            name="stem",
            shape="cylinder",
            size=(body_r * 0.7, body_r * 0.7, stem_h),
            location=(0.0, 0.0, stem_z),
            material=brass,
            family="bare_metal",
        ),
        PropPart(
            name="nut",
            shape="cylinder",
            size=(body_r * 0.72, body_r * 0.72, body_r * 0.42),
            location=(0.0, 0.0, nut_z),
            material=brass,
            family="bare_metal",
        ),
        PropPart(
            name="collar_e",
            shape="torus",
            size=(body_r * 0.95, body_r * 0.95, body_r * 0.22),
            location=(body_r * 1.35, 0.0, outlet_z),
            rotation=(0.0, 1.5708, 0.0),
            material=paint,
            family="painted_metal",
        ),
        PropPart(
            name="collar_w",
            shape="torus",
            size=(body_r * 0.95, body_r * 0.95, body_r * 0.22),
            location=(-body_r * 1.35, 0.0, outlet_z),
            rotation=(0.0, 1.5708, 0.0),
            material=paint,
            family="painted_metal",
        ),
        PropPart(
            name="flange",
            shape="torus",
            size=(body_r * 2.35, body_r * 2.35, body_r * 0.42),
            location=(0.0, 0.0, base_h + 0.01),
            material=paint,
            family="painted_metal",
        ),
        PropPart(
            name="outlet_e",
            shape="cylinder",
            size=(body_r * 0.72, body_r * 0.72, body_r * 0.85),
            location=(body_r * 1.15, 0.0, outlet_z),
            rotation=(0.0, 1.5708, 0.0),
            material=paint,
            family="painted_metal",
        ),
        PropPart(
            name="cap_e",
            shape="cylinder",
            size=(body_r * 0.88, body_r * 0.88, body_r * 0.28),
            location=(body_r * 1.55, 0.0, outlet_z),
            rotation=(0.0, 1.5708, 0.0),
            material=brass,
            family="bare_metal",
        ),
        PropPart(
            name="outlet_w",
            shape="cylinder",
            size=(body_r * 0.72, body_r * 0.72, body_r * 0.85),
            location=(-body_r * 1.15, 0.0, outlet_z),
            rotation=(0.0, 1.5708, 0.0),
            material=paint,
            family="painted_metal",
        ),
        PropPart(
            name="cap_w",
            shape="cylinder",
            size=(body_r * 0.88, body_r * 0.88, body_r * 0.28),
            location=(-body_r * 1.55, 0.0, outlet_z),
            rotation=(0.0, 1.5708, 0.0),
            material=brass,
            family="bare_metal",
        ),
        PropPart(
            name="pumper",
            shape="cylinder",
            size=(body_r * 0.95, body_r * 0.95, body_r * 0.7),
            location=(0.0, -body_r * 1.05, outlet_z - body_h * 0.06),
            rotation=(1.5708, 0.0, 0.0),
            material=paint,
            family="painted_metal",
        ),
        PropPart(
            name="pumper_cap",
            shape="cylinder",
            size=(body_r * 1.08, body_r * 1.08, body_r * 0.3),
            location=(0.0, -body_r * 1.42, outlet_z - body_h * 0.06),
            rotation=(1.5708, 0.0, 0.0),
            material=brass,
            family="bare_metal",
        ),
        PropPart(
            name="bolt",
            component="bolt",
            size=(0.028, 0.028, 0.022),
            location=(0.0, 0.0, base_h + 0.02),
            material=steel,
            family="bare_metal",
            array=PartArray(
                count=params.bolt_count,
                radial=RadialArray(radius=body_r * 1.05, axis="z"),
            ),
        ),
    ]
    if params.cap_count >= 3:
        parts.append(PropPart(
            name="outlet_n",
            shape="cylinder",
            size=(body_r * 0.62, body_r * 0.62, body_r * 0.7),
            location=(0.0, body_r * 1.1, outlet_z),
            rotation=(1.5708, 0.0, 0.0),
            material=paint,
            family="painted_metal",
        ))
    return parts
