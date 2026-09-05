"""Recipe expanders produce explicit parts."""

from __future__ import annotations

from mason.core.assets import Dimensions3D, RecipeParams
from mason.generators.blender.recipes import expand_recipe


def test_crate_one_part() -> None:
    parts = expand_recipe(
        "crate",
        Dimensions3D(width=0.6, depth=0.6, height=0.6),
        RecipeParams(),
        "wood_dark",
    )
    assert len(parts) == 1
    assert parts[0].name == "crate"
    assert parts[0].size == (0.6, 0.6, 0.6)


def test_shelf_count() -> None:
    parts = expand_recipe(
        "shelf",
        Dimensions3D(width=1.2, depth=0.35, height=1.8),
        RecipeParams(shelf_count=4, side_panels=True, back_panel=False),
        "wood_dark",
    )
    names = [p.name for p in parts]
    assert names.count("left_side") == 1
    assert sum(1 for n in names if n.startswith("shelf_")) == 4


def test_table_has_legs() -> None:
    parts = expand_recipe(
        "table",
        Dimensions3D(width=1.2, depth=0.8, height=0.75),
        RecipeParams(),
        "wood_light",
    )
    assert any(p.name == "top" for p in parts)
    assert sum(1 for p in parts if p.name.startswith("leg_")) == 4


def test_explicit_parts_win() -> None:
    from mason.core.assets import parse_asset_spec
    from mason.pipelines.static_prop import resolved_parts

    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "bench",
        "name": "Bench",
        "dimensions": {"width": 1, "depth": 0.4, "height": 0.5},
        "geometry": {
            "recipe": "crate",
            "parts": [{
                "name": "seat",
                "size": [1, 0.4, 0.05],
                "location": [0, 0, 0.5],
            }],
        },
    })
    parts = resolved_parts(spec)
    assert [p.name for p in parts] == ["seat"]
