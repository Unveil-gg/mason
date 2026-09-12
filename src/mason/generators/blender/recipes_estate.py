"""House, tree, pool, and estate recipe expanders."""

from __future__ import annotations

from mason.core.assets import Dimensions3D, PropPart, RecipeParams
from mason.core.parts import PartArray, PartCutout, PartSnap
from mason.errors import MasonError


def expand_estate(
    name: str,
    dims: Dimensions3D,
    params: RecipeParams,
    material: str,
) -> list[PropPart]:
    """Dispatch house / tree / pool / estate clusters."""
    if name == "house":
        return house_parts(dims, params, material)
    if name == "tree":
        return tree_parts(dims, params, material)
    if name == "pool":
        return pool_parts(dims, params, material)
    if name == "estate":
        return estate_parts(dims, params, material)
    raise MasonError(f"Unknown estate recipe '{name}'.", code="unknown_recipe")


def house_parts(
    dims: Dimensions3D,
    params: RecipeParams,
    material: str,
) -> list[PropPart]:
    """Classical house: plinth, wings, hip roof, portico, cut windows."""
    _ = dims
    stone = material or "stone"
    wing_w = params.wing_width
    on_plinth = PartSnap(to="plinth", on="top")
    return [
        PropPart(
            name="plinth",
            size=(3.28, 1.58, 0.14),
            location=(0.0, 0.0, 0.07),
            material="stone_dark",
            family="masonry",
        ),
        PropPart(
            name="main",
            size=(2.05, 1.48, 1.42),
            location=(0.0, 0.0, 0.8),
            material=stone,
            family="masonry",
            snap=on_plinth,
        ),
        PropPart(
            name="wing",
            size=(wing_w, 1.28, 0.92),
            location=(-1.42, 0.08, 0.55),
            material=stone,
            family="masonry",
            snap=on_plinth,
            mirror="x",
        ),
        PropPart(
            name="cornice",
            size=(2.18, 1.58, 0.10),
            location=(0.0, 0.0, 1.5),
            material="cream",
            family="masonry",
            component="cornice",
            component_params={"steps": 3.0},
            snap=PartSnap(to="main", on="top"),
        ),
        PropPart(
            name="roof",
            shape="tapered_box",
            taper=(0.16, 0.22),
            size=(2.28, 1.64, 0.52),
            location=(0.0, 0.0, 1.9),
            material="roof",
            family="roofing",
            snap=PartSnap(to="cornice", on="top"),
        ),
        PropPart(
            name="wing_roof",
            shape="tapered_box",
            taper=(0.20, 0.20),
            size=(wing_w + 0.10, 1.38, 0.34),
            location=(-1.42, 0.08, 1.2),
            material="roof",
            family="roofing",
            snap=PartSnap(to="wing", on="top"),
            mirror="x",
        ),
        PropPart(
            name="chimney",
            size=(0.16, 0.22, 0.42),
            location=(-0.42, 0.30, 1.8),
            material="stone_dark",
            family="masonry",
            snap=PartSnap(to="roof", on="top", embed=0.24),
            mirror="x",
        ),
        PropPart(
            name="chimney_cap",
            size=(0.20, 0.26, 0.04),
            location=(-0.42, 0.30, 2.0),
            material="roof",
            family="roofing",
            snap=PartSnap(to="chimney", on="top"),
            mirror="x",
        ),
        PropPart(
            name="portico",
            size=(1.48, 0.72, 0.12),
            location=(0.0, -1.10, 0.3),
            material=stone,
            family="masonry",
            snap=on_plinth,
            flush=PartSnap(to="main", on="front"),
        ),
        PropPart(
            name="column",
            shape="cylinder",
            size=(0.20, 0.20, 1.18),
            location=(-0.50, -1.28, 0.7),
            material="cream",
            family="plastic",
            snap=PartSnap(to="portico", on="top"),
            mirror="x",
        ),
        PropPart(
            name="column_in",
            shape="cylinder",
            size=(0.20, 0.20, 1.18),
            location=(-0.50, -0.88, 0.7),
            material="cream",
            family="plastic",
            snap=PartSnap(to="portico", on="top"),
            flush=PartSnap(to="main", on="front", embed=0.04),
            mirror="x",
        ),
        PropPart(
            name="entablature",
            size=(1.56, 0.70, 0.12),
            location=(0.0, -1.10, 1.4),
            material="cream",
            family="plastic",
            snap=PartSnap(to="column", on="top"),
            flush=PartSnap(to="main", on="front"),
        ),
        PropPart(
            name="pediment",
            shape="tapered_box",
            taper=(0.08, 1.0),
            size=(1.64, 0.40, 0.62),
            location=(0.0, -1.48, 1.75),
            material="cream",
            family="plastic",
            snap=PartSnap(to="entablature", on="top"),
        ),
        PropPart(
            name="door",
            size=(0.28, 0.06, 0.58),
            location=(0.0, -0.76, 0.55),
            material="wood",
            family="varnished_wood",
            snap=PartSnap(to="main", on="front"),
        ),
        PropPart(
            name="win_cut_lo",
            size=(0.20, 0.14, 0.28),
            location=(-0.58, -0.80, 0.58),
            material="ink",
            bevel=False,
            snap=PartSnap(to="main", on="front", embed=0.08),
            cutout=PartCutout(target="main"),
            mirror="x",
        ),
        PropPart(
            name="win_cut_hi",
            size=(0.18, 0.14, 0.26),
            location=(-0.58, -0.80, 1.22),
            material="ink",
            bevel=False,
            snap=PartSnap(to="main", on="front", embed=0.08),
            cutout=PartCutout(target="main"),
            array=PartArray(count=3, offset=(0.58, 0.0, 0.0)),
        ),
        PropPart(
            name="win_glass_lo",
            size=(0.18, 0.03, 0.26),
            location=(-0.58, -0.74, 0.58),
            material="ink",
            family="plastic",
            snap=PartSnap(to="main", on="front", embed=0.02),
            mirror="x",
        ),
        PropPart(
            name="win_glass_hi",
            size=(0.16, 0.03, 0.24),
            location=(-0.58, -0.74, 1.22),
            material="ink",
            family="plastic",
            snap=PartSnap(to="main", on="front", embed=0.02),
            array=PartArray(count=3, offset=(0.58, 0.0, 0.0)),
        ),
        PropPart(
            name="stair",
            size=(0.88, 0.18, 0.08),
            location=(0.0, -1.70, 0.2),
            material="stone_dark",
            family="masonry",
            snap=PartSnap(to="portico", on="front"),
        ),
    ]


def tree_parts(
    dims: Dimensions3D,
    params: RecipeParams,
    material: str,
    *,
    origin: tuple[float, float, float] | None = None,
    prefix: str = "tree",
    snap_ground: str | None = None,
) -> list[PropPart]:
    """Trunk plus a squat sphere crown. Height from params or dims."""
    _ = material
    ox, oy, oz = origin or (0.0, 0.0, 0.0)
    total = params.tree_height if origin else dims.height
    trunk_h = min(0.28, total * 0.28)
    crown_h = max(total - trunk_h, 0.2)
    crown = max(crown_h * 0.85, 0.35)
    ground = (
        PartSnap(to=snap_ground, on="top") if snap_ground else None
    )
    return [
        PropPart(
            name=f"{prefix}_trunk",
            shape="cylinder",
            size=(0.10, 0.10, trunk_h),
            location=(ox, oy, oz + trunk_h / 2.0),
            material="wood",
            family="varnished_wood",
            snap=ground,
        ),
        PropPart(
            name=f"{prefix}_crown",
            shape="sphere",
            size=(crown, crown, crown_h * 0.92),
            location=(ox, oy, oz + trunk_h + crown_h / 2.0),
            material="hedge",
            family="foliage",
            snap=PartSnap(to=f"{prefix}_trunk", on="top"),
        ),
    ]


def pool_parts(
    dims: Dimensions3D,
    params: RecipeParams,
    material: str,
    *,
    origin: tuple[float, float, float] | None = None,
) -> list[PropPart]:
    """Coping, recessed water, and a lawn cutout."""
    _ = material
    ox, oy, oz = origin or (0.0, 0.0, dims.height / 2.0)
    w = params.pool_width if origin else dims.width
    d = params.pool_depth if origin else dims.depth
    lawn = "rear_lawn" if origin else None
    water_snap = PartSnap(to=lawn, on="top") if lawn else None
    extras: list[PropPart] = []
    if lawn is None:
        extras.append(PropPart(
            name="pool_deck",
            size=(w + 0.36, d + 0.36, 0.08),
            location=(ox, oy, oz - 0.04),
            material="stone",
            family="masonry",
        ))
        lawn = "pool_deck"
        water_snap = PartSnap(to="pool_deck", on="top")
    return extras + [
        PropPart(
            name="pool_water",
            size=(w, d, 0.05),
            location=(ox, oy, oz),
            material="water",
            family="water",
            snap=water_snap,
        ),
        PropPart(
            name="pool_cut",
            size=(w - 0.04, d - 0.04, 0.10),
            location=(ox, oy, oz),
            material="water",
            bevel=False,
            snap=PartSnap(to=lawn, on="top", embed=0.04),
            cutout=PartCutout(target=lawn),
        ),
        PropPart(
            name="pool_coping",
            size=(w + 0.24, d + 0.22, 0.06),
            location=(ox, oy, oz),
            material="stone",
            family="masonry",
            component="rail",
            snap=water_snap,
        ),
        PropPart(
            name="pool_step",
            size=(0.36, 0.16, 0.04),
            location=(ox, oy - d / 2.0 - 0.08, oz),
            material="stone",
            family="masonry",
            snap=(
                PartSnap(to=lawn, on="top") if lawn else None
            ),
        ),
    ]


def estate_parts(
    dims: Dimensions3D,
    params: RecipeParams,
    material: str,
) -> list[PropPart]:
    """Lot, house, formal garden, rear pool, and corner trees."""
    w, d, _h = dims.width, dims.depth, dims.height
    stone = material or "stone"
    parts: list[PropPart] = [
        PropPart(
            name="lot",
            size=(w, d, 0.06),
            location=(0.0, 0.0, 0.03),
            material="path",
            family="masonry",
        ),
        PropPart(
            name="front_lawn",
            size=(w - 0.20, 1.55, 0.05),
            location=(0.0, -1.82, 0.2),
            material="lawn",
            family="lawn",
            snap=PartSnap(to="lot", on="top"),
        ),
        PropPart(
            name="rear_lawn",
            size=(w - 0.20, 1.72, 0.05),
            location=(0.0, 1.74, 0.2),
            material="lawn",
            family="lawn",
            snap=PartSnap(to="lot", on="top"),
        ),
    ]
    house = house_parts(
        Dimensions3D(width=3.28, depth=1.58, height=2.0),
        params,
        stone,
    )
    shifted: list[PropPart] = []
    for part in house:
        if part.name == "plinth":
            shifted.append(part.model_copy(update={
                "snap": PartSnap(to="lot", on="top"),
                "location": (0.0, -0.18, 0.3),
            }))
        else:
            loc = list(part.location)
            loc[1] += -0.18
            shifted.append(part.model_copy(update={
                "location": (loc[0], loc[1], loc[2]),
            }))
    parts.extend(shifted)
    parts.extend([
        PropPart(
            name="path",
            size=(0.38, 1.28, 0.03),
            location=(0.0, -1.92, 0.2),
            material="path",
            family="masonry",
            snap=PartSnap(to="front_lawn", on="top"),
        ),
        PropPart(
            name="hedge_side",
            size=(0.16, 1.42, 0.32),
            location=(-1.88, -1.78, 0.4),
            material="hedge",
            family="foliage",
            snap=PartSnap(to="front_lawn", on="top"),
            mirror="x",
        ),
        PropPart(
            name="parterre",
            size=(0.58, 0.42, 0.10),
            location=(-0.92, -1.72, 0.3),
            material="hedge",
            family="foliage",
            snap=PartSnap(to="front_lawn", on="top"),
            mirror="x",
        ),
        PropPart(
            name="topiary_stem",
            shape="cylinder",
            size=(0.07, 0.07, 0.22),
            location=(-1.48, -2.22, 0.4),
            material="wood",
            family="varnished_wood",
            snap=PartSnap(to="front_lawn", on="top"),
            mirror="x",
        ),
        PropPart(
            name="topiary_ball",
            shape="sphere",
            size=(0.28, 0.28, 0.28),
            location=(-1.48, -2.22, 0.7),
            material="hedge",
            family="foliage",
            snap=PartSnap(to="topiary_stem", on="top"),
            mirror="x",
        ),
        PropPart(
            name="fountain_base",
            shape="cylinder",
            size=(0.42, 0.42, 0.08),
            location=(0.0, -2.28, 0.3),
            material="stone",
            family="masonry",
            snap=PartSnap(to="front_lawn", on="top"),
        ),
        PropPart(
            name="fountain_bowl",
            shape="torus",
            size=(0.28, 0.28, 0.08),
            location=(0.0, -2.28, 0.4),
            material="stone",
            family="masonry",
            snap=PartSnap(to="fountain_base", on="top"),
        ),
        PropPart(
            name="fountain_jet",
            shape="cylinder",
            size=(0.04, 0.04, 0.16),
            location=(0.0, -2.28, 0.5),
            material="cream",
            family="masonry",
            snap=PartSnap(to="fountain_base", on="top"),
        ),
        PropPart(
            name="rear_hedge",
            size=(w - 0.40, 0.18, 0.48),
            location=(0.0, 2.48, 0.5),
            material="hedge",
            family="foliage",
            snap=PartSnap(to="rear_lawn", on="top"),
        ),
    ])
    parts.extend(pool_parts(
        dims, params, stone, origin=(0.0, 1.78, 0.3),
    ))
    parts.extend(tree_parts(
        dims, params, stone,
        origin=(-1.72, 2.12, 0.2),
        prefix="tree",
        snap_ground="rear_lawn",
    ))
    parts.extend(tree_parts(
        dims, params, stone,
        origin=(1.72, 2.12, 0.2),
        prefix="tree_r",
        snap_ground="rear_lawn",
    ))
    return parts
