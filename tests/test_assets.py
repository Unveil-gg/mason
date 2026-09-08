"""AssetSpec parsing tests."""

from __future__ import annotations

import pytest

from mason.core.assets import (
    ImageProcessSpec,
    LayeredRasterSpec,
    SpriteSheetSpec,
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


def test_cylinder_and_parent() -> None:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "sign",
        "name": "Sign",
        "dimensions": {"width": 1, "depth": 0.2, "height": 1.5},
        "geometry": {
            "parts": [
                {
                    "name": "post",
                    "shape": "cylinder",
                    "size": [0.1, 0.1, 1.5],
                    "location": [0, 0, 0.75],
                },
                {
                    "name": "board",
                    "shape": "plane",
                    "size": [0.6, 0.4, 0.0],
                    "location": [0, 0.05, 1.2],
                    "parent": "post",
                    "material": "cream",
                },
            ],
        },
    })
    assert spec.geometry.parts[0].shape == "cylinder"
    assert spec.geometry.parts[1].parent == "post"


def test_part_texture_asset_file() -> None:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "crate",
        "name": "Crate",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {
            "parts": [{
                "name": "box",
                "size": [1, 1, 1],
                "location": [0, 0, 0.5],
                "texture": {"asset": "plank_texture", "file": "output/asset.png"},
            }],
        },
    })
    part = spec.geometry.parts[0]
    assert part.texture.asset == "plank_texture"
    assert part.texture.file == "output/asset.png"


def test_part_texture_rejects_path_and_asset() -> None:
    with pytest.raises(MasonError):
        parse_asset_spec({
            "type": "static_prop",
            "id": "crate",
            "name": "Crate",
            "dimensions": {"width": 1, "depth": 1, "height": 1},
            "geometry": {
                "parts": [{
                    "name": "box",
                    "size": [1, 1, 1],
                    "location": [0, 0, 0.5],
                    "texture": {"asset": "a", "file": "f", "path": "p"},
                }],
            },
        })


def test_text_layer_without_fill() -> None:
    spec = parse_asset_spec({
        "type": "layered_raster",
        "id": "card",
        "name": "Card",
        "layers": [{"name": "title", "role": "text", "text": "Hello"}],
    })
    assert spec.layers[0].text == "Hello"


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


def test_sprite_sheet_pixels() -> None:
    spec = parse_asset_spec({
        "type": "sprite_sheet",
        "id": "hero",
        "name": "Hero",
        "canvas": {"width": 8, "height": 8},
        "animations": [{
            "name": "idle",
            "frames": [{
                "duration_ms": 200,
                "layers": [{
                    "name": "body",
                    "pixels": ["..HH..", ".HSSH."],
                    "keys": {"H": "hair", "S": "skin"},
                }],
            }],
        }],
    })
    assert isinstance(spec, SpriteSheetSpec)
    assert spec.animations[0].frames[0].layers[0].keys["H"] == "hair"


def test_sprite_sheet_rejects_unknown_pixel_key() -> None:
    with pytest.raises(MasonError):
        parse_asset_spec({
            "type": "sprite_sheet",
            "id": "hero",
            "name": "Hero",
            "canvas": {"width": 8, "height": 8},
            "animations": [{
                "name": "idle",
                "frames": [{
                    "layers": [{
                        "name": "body",
                        "pixels": ["X."],
                        "keys": {"H": "hair"},
                    }],
                }],
            }],
        })


def test_lathe_derives_size() -> None:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "vase",
        "name": "Vase",
        "dimensions": {"width": 0.2, "depth": 0.2, "height": 0.3},
        "geometry": {
            "parts": [{
                "name": "body",
                "shape": "lathe",
                "location": [0, 0, 0.15],
                "profile": [[0.05, 0.0], [0.03, 0.3]],
                "bend": {"axis": "x", "angle": 0.4, "origin": "base"},
            }],
        },
    })
    part = spec.geometry.parts[0]
    assert part.shape == "lathe"
    assert part.size == (0.1, 0.1, 0.3)
    assert part.bend is not None
    assert part.bend.origin == "base"


def test_lathe_requires_profile() -> None:
    with pytest.raises(MasonError):
        parse_asset_spec({
            "type": "static_prop",
            "id": "vase",
            "name": "Vase",
            "dimensions": {"width": 1, "depth": 1, "height": 1},
            "geometry": {
                "parts": [{
                    "name": "body",
                    "shape": "lathe",
                    "location": [0, 0, 0.5],
                }],
            },
        })


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
