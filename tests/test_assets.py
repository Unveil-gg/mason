"""AssetSpec parsing tests."""

from __future__ import annotations

import pytest

from mason.core.assets import (
    ImageProcessSpec,
    LayeredRasterSpec,
    StaticPropSpec,
    parse_asset_spec,
)
from mason.errors import MasonError


def test_static_prop_recipe() -> None:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "crate",
        "name": "Crate",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {"recipe": "crate"},
    })
    assert isinstance(spec, StaticPropSpec)
    assert spec.geometry.recipe == "crate"


def test_static_prop_requires_parts_or_recipe() -> None:
    with pytest.raises(MasonError):
        parse_asset_spec({
            "type": "static_prop",
            "id": "x",
            "name": "X",
            "dimensions": {"width": 1, "depth": 1, "height": 1},
            "geometry": {},
        })


def test_layered_raster() -> None:
    spec = parse_asset_spec({
        "type": "layered_raster",
        "id": "panel",
        "name": "Panel",
        "dimensions": {"width": 64, "height": 64},
        "layers": [{"name": "bg", "fill": "cream"}],
    })
    assert isinstance(spec, LayeredRasterSpec)
    assert spec.layers[0].fill == "cream"


def test_image_process_source() -> None:
    spec = parse_asset_spec({
        "type": "image_process",
        "id": "p",
        "name": "P",
        "source": {"path": "examples/ref/swatch.png"},
        "operations": [{"op": "resize", "width": 32, "height": 32}],
    })
    assert isinstance(spec, ImageProcessSpec)


def test_rejects_unknown_type() -> None:
    with pytest.raises(MasonError):
        parse_asset_spec({"type": "spaceship", "id": "a", "name": "A"})


def test_rejects_extra_fields() -> None:
    with pytest.raises(MasonError):
        parse_asset_spec({
            "type": "static_prop",
            "id": "c",
            "name": "C",
            "dimensions": {"width": 1, "depth": 1, "height": 1},
            "geometry": {"recipe": "crate"},
            "nope": True,
        })
