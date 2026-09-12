"""Grocery-cart recipe: flared rim, snapped walls, casters, handle."""

from __future__ import annotations

import math

from mason.core.assets import Dimensions3D, PropPart, RecipeParams
from mason.core.parts import PartSnap


def cart_parts(
    dims: Dimensions3D,
    params: RecipeParams,
    material: str,
) -> list[PropPart]:
    """Connected basket: floor, rim, walls, casters, aft handle."""
    w, d, h = dims.width, dims.depth, dims.height
    flare = params.flare
    basket_h = params.basket_height
    handle_rise = params.handle_rise
    steel = material if material else "steel"
    dark = "steel_dark"
    rubber = "rubber"
    grip = "handle"

    floor_t = 0.014
    rim_t = 0.012
    wall_t = 0.008
    post_t = 0.028
    bar_t = 0.034
    caster_h = 0.12
    natural = caster_h + floor_t + basket_h + rim_t + handle_rise
    if natural <= h:
        basket_h = basket_h + (h - natural)
    elif params.include_casters:
        caster_h = max(h - (floor_t + basket_h + rim_t + handle_rise), 0.05)

    rim_w, rim_d = w, d
    floor_w = rim_w * (1.0 - flare)
    floor_d = rim_d * (1.0 - flare)

    floor_z = caster_h + floor_t / 2.0
    floor_top = floor_z + floor_t / 2.0
    rim_z = floor_top + basket_h + rim_t / 2.0
    rim_top = rim_z + rim_t / 2.0
    mid_z = floor_top + basket_h / 2.0
    post_z = rim_top + handle_rise / 2.0
    bar_z = rim_top + handle_rise

    inset = min(floor_w, floor_d) * 0.12
    post_x = rim_w * 0.28
    post_y = rim_d / 2.0 - 0.01
    to_floor = PartSnap(to="floor", on="top")
    under_floor = PartSnap(to="floor", on="bottom")
    on_rim = PartSnap(to="rim", on="top")

    # Wire walls are flared: bars widen from the floor footprint to
    # the wider rim footprint instead of standing straight up, so the
    # rim sits on the wall tops (no floating gap from side/top views).
    dx = (rim_w - floor_w) / 2.0
    theta = math.atan2(dx, basket_h)
    wall_x_len = math.hypot(dx, basket_h)
    wall_x_center = (floor_w + rim_w) / 4.0

    dy = (rim_d - floor_d) / 2.0
    phi = math.atan2(dy, basket_h)
    wall_y_len = math.hypot(dy, basket_h)
    wall_y_center = (floor_d + rim_d) / 4.0

    parts = [
        PropPart(
            name="floor",
            size=(floor_w, floor_d, floor_t),
            location=(0.0, 0.0, floor_z),
            material=steel,
            family="bare_metal",
        ),
        PropPart(
            name="rim",
            size=(rim_w, rim_d, rim_t),
            location=(0.0, 0.0, rim_z),
            material=steel,
            family="bare_metal",
            component="rail",
        ),
        PropPart(
            name="hoop",
            size=(floor_w, floor_d, rim_t),
            location=(0.0, 0.0, mid_z),
            material=dark,
            family="bare_metal",
            component="rail",
        ),
        PropPart(
            name="wall_left",
            size=(wall_t, floor_d, wall_x_len),
            location=(-wall_x_center, 0.0, mid_z),
            rotation=(0.0, -theta, 0.0),
            material=dark,
            family="bare_metal",
            component="wire_wall",
            component_params={"count": 7},
            snap=to_floor,
        ),
        PropPart(
            name="wall_right",
            size=(wall_t, floor_d, wall_x_len),
            location=(wall_x_center, 0.0, mid_z),
            rotation=(0.0, theta, 0.0),
            material=dark,
            family="bare_metal",
            component="wire_wall",
            component_params={"count": 7},
            snap=to_floor,
        ),
        PropPart(
            name="wall_front",
            size=(floor_w, wall_t, wall_y_len),
            location=(0.0, -wall_y_center, mid_z),
            rotation=(phi, 0.0, 0.0),
            material=dark,
            family="bare_metal",
            component="wire_wall",
            component_params={"count": 7},
            snap=to_floor,
        ),
        PropPart(
            name="wall_back",
            size=(floor_w, wall_t, wall_y_len),
            location=(0.0, wall_y_center, mid_z),
            rotation=(-phi, 0.0, 0.0),
            material=dark,
            family="bare_metal",
            component="wire_wall",
            component_params={"count": 5},
            snap=to_floor,
        ),
        PropPart(
            name="seat_panel",
            size=(0.22, 0.01, 0.14),
            location=(0.0, floor_d / 2.0 - 0.02, mid_z + 0.04),
            material=steel,
            family="bare_metal",
            parent="wall_back",
        ),
        PropPart(
            name="seat_ledge",
            size=(0.22, 0.08, 0.01),
            location=(0.0, floor_d / 2.0 - 0.05, mid_z - 0.03),
            material=steel,
            family="bare_metal",
            parent="wall_back",
        ),
        PropPart(
            name="wheel_fl",
            size=(0.08, 0.05, caster_h),
            location=(-floor_w / 2.0 + inset, -floor_d / 2.0 + inset, 0.04),
            material=rubber,
            family="rubber",
            component="caster",
            snap=under_floor,
        ),
        PropPart(
            name="wheel_fr",
            size=(0.08, 0.05, caster_h),
            location=(floor_w / 2.0 - inset, -floor_d / 2.0 + inset, 0.04),
            material=rubber,
            family="rubber",
            component="caster",
            snap=under_floor,
        ),
        PropPart(
            name="wheel_bl",
            size=(0.08, 0.05, caster_h),
            location=(-floor_w / 2.0 + inset, floor_d / 2.0 - inset, 0.04),
            material=rubber,
            family="rubber",
            component="caster",
            snap=under_floor,
        ),
        PropPart(
            name="wheel_br",
            size=(0.08, 0.05, caster_h),
            location=(floor_w / 2.0 - inset, floor_d / 2.0 - inset, 0.04),
            material=rubber,
            family="rubber",
            component="caster",
            snap=under_floor,
        ),
        PropPart(
            name="handle_left",
            shape="cylinder",
            size=(post_t, post_t, handle_rise),
            location=(-post_x, post_y, post_z),
            material=steel,
            family="bare_metal",
            snap=on_rim,
        ),
        PropPart(
            name="handle_right",
            shape="cylinder",
            size=(post_t, post_t, handle_rise),
            location=(post_x, post_y, post_z),
            material=steel,
            family="bare_metal",
            snap=on_rim,
        ),
        PropPart(
            name="handle_bar",
            shape="cylinder",
            size=(bar_t, bar_t, post_x * 2.0 + 0.04),
            location=(0.0, post_y, bar_z),
            rotation=(0.0, 1.5708, 0.0),
            material=grip,
            family="painted_metal",
            wear=0.1,
            parent="handle_left",
        ),
    ]
    if not params.include_casters:
        parts = [
            part for part in parts
            if not part.name.startswith("wheel_")
        ]
    return parts
