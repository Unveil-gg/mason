"""Material variant parsing and fan-out."""

from __future__ import annotations

from mason.core.assets import StaticPropSpec, parse_asset_spec
from mason.pipelines.dispatch import _variant_specs


def _cart_spec() -> StaticPropSpec:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "cart",
        "name": "Cart",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {"recipe": "crate"},
        "materials": {
            "primary": "steel",
            "palette_overrides": {"steel": "#111111"},
        },
        "variants": [
            {
                "suffix": "black",
                "palette_overrides": {"steel": "#2B2E31"},
            },
            {"suffix": "brass", "primary": "brass"},
        ],
    })
    assert isinstance(spec, StaticPropSpec)
    return spec


def test_variants_parse() -> None:
    spec = _cart_spec()
    assert [v.suffix for v in spec.variants] == ["black", "brass"]
    assert spec.materials.palette_overrides == {"steel": "#111111"}


def test_variant_specs_merge_palette_overrides() -> None:
    spec = _cart_spec()
    children = _variant_specs(spec)
    assert [c.id for c in children] == ["cart_black", "cart_brass"]

    black = children[0]
    assert black.name == "Cart (black)"
    assert black.variants == []
    # Parent override stays; variant override is layered on top.
    assert black.materials.palette_overrides == {"steel": "#2B2E31"}
    assert black.materials.primary == "steel"

    brass = children[1]
    assert brass.materials.primary == "brass"
    assert brass.materials.palette_overrides == {"steel": "#111111"}


def test_variant_specs_keep_recipe_unexpanded() -> None:
    # Variants are snapshotted before recipe expansion, so a rebuild
    # of the sibling spec re-expands from the recipe, not a frozen
    # part list.
    spec = _cart_spec()
    children = _variant_specs(spec)
    assert children[0].geometry.recipe == "crate"
    assert children[0].geometry.parts == []


def test_no_variants_returns_empty() -> None:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "plain",
        "name": "Plain",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {"recipe": "crate"},
    })
    assert isinstance(spec, StaticPropSpec)
    assert _variant_specs(spec) == []
