"""Component, decal, family, and hydrant recipe expansion."""

from __future__ import annotations

import pytest

from mason.core.assets import Dimensions3D, RecipeParams, parse_asset_spec
from mason.core.parts import PropPart
from mason.core.styles import load_style
from mason.errors import MasonError
from mason.generators.blender.components import expand_components
from mason.generators.blender.recipes import expand_recipe
from mason.pipelines.static_prop import (
    assert_known_families,
    resolved_parts,
)


def test_bolt_expands_to_head_and_shank() -> None:
    parts = expand_components([
        PropPart(
            name="bolt",
            component="bolt",
            size=(0.02, 0.02, 0.016),
            location=(0.0, 0.0, 0.1),
            material="steel",
        ),
    ])
    assert [p.name for p in parts] == ["bolt_head", "bolt_shank"]
    assert parts[0].shape == "box"
    assert parts[1].shape == "cylinder"


def test_hydrant_recipe_has_secondary_forms() -> None:
    parts = expand_recipe(
        "hydrant",
        Dimensions3D(width=0.56, depth=0.44, height=0.86),
        RecipeParams(bolt_count=6),
        "hydrant_red",
    )
    names = [p.name for p in parts]
    assert "barrel" in names
    assert "dome" in names
    assert "flange" in names
    assert "bolt" in names
    assert "pumper" in names


def test_hydrant_resolved_expands_bolts() -> None:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "fire_hydrant",
        "name": "Hydrant",
        "dimensions": {"width": 0.56, "depth": 0.44, "height": 0.86},
        "geometry": {"recipe": "hydrant"},
        "materials": {"primary": "hydrant_red"},
    })
    parts = resolved_parts(spec)
    bolts = [p for p in parts if p.name.startswith("bolt")]
    assert len(bolts) == 12


def test_decal_becomes_textured_plane() -> None:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "box",
        "name": "Box",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {
            "parts": [{
                "name": "body",
                "size": [1, 1, 1],
                "location": [0, 0, 0.5],
            }],
        },
        "decals": [{
            "name": "label",
            "image": {"path": "examples/ref/x.png"},
            "location": [0, -0.51, 0.5],
            "size": [0.4, 0.2],
        }],
    })
    parts = resolved_parts(spec)
    label = next(p for p in parts if p.name == "label")
    assert label.shape == "plane"
    assert label.texture is not None


def test_unknown_family(project, monkeypatch) -> None:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "box",
        "name": "Box",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {
            "parts": [{
                "name": "body",
                "size": [1, 1, 1],
                "location": [0, 0, 0.5],
                "family": "unobtainium",
            }],
        },
    })
    style = load_style(project / "styles" / "default.yaml")
    with pytest.raises(MasonError) as exc:
        assert_known_families(resolved_parts(spec), style)
    assert exc.value.code == "unknown_family"
