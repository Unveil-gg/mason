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


def _box_with_decal(face: str) -> list[PropPart]:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "box",
        "name": "Box",
        "dimensions": {"width": 0.3, "depth": 0.3, "height": 0.075},
        "geometry": {
            "parts": [{
                "name": "body",
                "size": [0.3, 0.3, 0.075],
                "location": [0, 0, 0.0375],
            }],
        },
        "decals": [{
            "name": "label",
            "image": {"path": "examples/ref/x.png"},
            "face": face,
        }],
    })
    return resolved_parts(spec)


def test_decal_face_top_derives_placement() -> None:
    label = next(p for p in _box_with_decal("top") if p.name == "label")
    assert label.rotation == (0.0, 0.0, 0.0)
    assert label.size[:2] == (0.3, 0.3)
    assert label.location[2] > 0.075


def test_decal_face_right_keeps_full_size_unswapped() -> None:
    # Regression: a naive rotation-about-Y for the right/left faces
    # swaps which world axis gets the width vs. height extent
    # (create_plane's local X/Y map to world Z/Y under a Y rotation).
    # `face: right` must resolve to (depth, height), not (width,
    # height), so the plane's world footprint is not oversized.
    label = next(p for p in _box_with_decal("right") if p.name == "label")
    assert label.size[:2] == (0.3, 0.075)
    assert label.location[0] > 0.15


def test_decal_face_left_mirrors_x() -> None:
    right = next(p for p in _box_with_decal("right") if p.name == "label")
    left = next(p for p in _box_with_decal("left") if p.name == "label")
    assert left.location[0] == -right.location[0]
    assert left.rotation[2] == -right.rotation[2]


def test_decal_face_exclusive_with_manual_fields() -> None:
    with pytest.raises(Exception, match="exclusive"):
        parse_asset_spec({
            "type": "static_prop",
            "id": "box",
            "name": "Box",
            "dimensions": {"width": 1, "depth": 1, "height": 1},
            "geometry": {
                "parts": [{
                    "name": "body", "size": [1, 1, 1],
                    "location": [0, 0, 0.5],
                }],
            },
            "decals": [{
                "name": "label",
                "image": {"path": "examples/ref/x.png"},
                "face": "top",
                "location": [0, 0, 1],
                "size": [0.4, 0.2],
            }],
        })


def test_decal_needs_face_or_manual_fields() -> None:
    with pytest.raises(Exception, match="face"):
        parse_asset_spec({
            "type": "static_prop",
            "id": "box",
            "name": "Box",
            "dimensions": {"width": 1, "depth": 1, "height": 1},
            "geometry": {
                "parts": [{
                    "name": "body", "size": [1, 1, 1],
                    "location": [0, 0, 0.5],
                }],
            },
            "decals": [{
                "name": "label",
                "image": {"path": "examples/ref/x.png"},
            }],
        })


def test_x_brace_two_diagonals() -> None:
    parts = expand_components([
        PropPart(
            name="brace",
            component="x_brace",
            size=(1.0, 0.04, 0.8),
            location=(0.0, -0.5, 1.0),
        ),
    ])
    assert [p.name for p in parts] == ["brace_a", "brace_b"]
    assert parts[0].rotation[1] > 0
    assert parts[1].rotation[1] < 0


def test_rail_four_sides() -> None:
    parts = expand_components([
        PropPart(
            name="rim",
            component="rail",
            size=(0.56, 0.42, 0.012),
            location=(0.0, 0.0, 0.6),
        ),
    ])
    assert [p.name for p in parts] == [
        "rim_s", "rim_n", "rim_w", "rim_e",
    ]


def test_wire_wall_count() -> None:
    parts = expand_components([
        PropPart(
            name="side",
            component="wire_wall",
            size=(0.01, 0.4, 0.4),
            location=(-0.2, 0.0, 0.4),
            component_params={"count": 5},
        ),
    ])
    assert len(parts) == 5
    assert parts[0].name == "side_1"
    assert parts[-1].name == "side_5"


def test_rivet_strip_linear_bolts() -> None:
    parts = expand_components([
        PropPart(
            name="rivets",
            component="rivet_strip",
            size=(0.4, 0.02, 0.02),
            location=(0.0, 0.0, 0.1),
            component_params={"count": 3},
        ),
    ])
    assert len(parts) == 6
    assert parts[0].name == "rivets_1_head"
    assert parts[1].shape == "cylinder"


def test_cornice_steps() -> None:
    parts = expand_components([
        PropPart(
            name="lip",
            component="cornice",
            size=(0.4, 0.1, 0.06),
            location=(0.0, 0.0, 0.5),
            component_params={"steps": 3},
        ),
    ])
    assert len(parts) == 3
    assert parts[-1].size[0] > parts[0].size[0]


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
