"""Curve, skin, outline, and body spec parsing."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from mason.core.assets import parse_asset_spec
from mason.core.forms import BodySpec, member_to_body
from mason.errors import MasonError


def _prop(geometry: dict) -> dict:
    return {
        "type": "static_prop",
        "id": "form",
        "name": "Form",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": geometry,
    }


def test_curve_derives_size() -> None:
    spec = parse_asset_spec(_prop({
        "parts": [{
            "name": "hose",
            "shape": "curve",
            "location": [0, 0, 0.1],
            "curve": {
                "points": [
                    {"at": [0, 0, 0], "radius": 1.0},
                    {"at": [0, 0, 0.2], "radius": 0.5},
                ],
                "bevel_depth": 0.02,
                "taper": 0.6,
            },
        }],
    }))
    part = spec.geometry.parts[0]
    assert part.shape == "curve"
    assert part.size[2] == pytest.approx(0.24)
    assert part.curve is not None
    assert part.curve.taper == 0.6


def test_skin_derives_size() -> None:
    spec = parse_asset_spec(_prop({
        "parts": [{
            "name": "limb",
            "shape": "skin",
            "location": [0, 0, 0],
            "skin": {
                "nodes": [
                    {"id": "root", "at": [0, 0, 0], "radius": 0.05},
                    {"id": "tip", "at": [0, 0, 0.2], "radius": 0.02},
                ],
                "edges": [["root", "tip"]],
            },
        }],
    }))
    part = spec.geometry.parts[0]
    assert part.size[2] == pytest.approx(0.27)
    assert part.skin is not None
    assert len(part.skin.nodes) == 2


def test_outline_derives_size() -> None:
    spec = parse_asset_spec(_prop({
        "parts": [{
            "name": "blade",
            "shape": "outline",
            "location": [0, 0, 0.2],
            "outline": {
                "points": [[0, 0], [0.04, 0.1], [0, 0.4]],
                "depth": 0.008,
            },
        }],
    }))
    part = spec.geometry.parts[0]
    assert part.size == pytest.approx((0.04, 0.008, 0.4))


def test_bodies_parse() -> None:
    spec = parse_asset_spec(_prop({
        "parts": [
            {
                "name": "a",
                "size": [0.1, 0.1, 0.1],
                "location": [0, 0, 0],
            },
            {
                "name": "b",
                "size": [0.1, 0.1, 0.1],
                "location": [0, 0, 0.05],
            },
        ],
        "bodies": [{
            "name": "joined",
            "members": ["a", "b"],
            "method": "remesh",
            "remesh": {"voxel_size": 0.01},
            "smooth": 2,
        }],
    }))
    assert spec.geometry.bodies[0].name == "joined"
    assert spec.geometry.bodies[0].remesh is not None
    assert spec.geometry.bodies[0].remesh.voxel_size == 0.01


def test_curve_field_rejected_on_box() -> None:
    with pytest.raises(MasonError):
        parse_asset_spec(_prop({
            "parts": [{
                "name": "box",
                "size": [1, 1, 1],
                "location": [0, 0, 0],
                "curve": {"points": [{"at": [0, 0, 0]}, {"at": [1, 0, 0]}]},
            }],
        }))


def test_skin_needs_nodes() -> None:
    with pytest.raises(MasonError):
        parse_asset_spec(_prop({
            "parts": [{
                "name": "limb",
                "shape": "skin",
                "location": [0, 0, 0],
            }],
        }))


def test_skin_unknown_edge() -> None:
    with pytest.raises(MasonError):
        parse_asset_spec(_prop({
            "parts": [{
                "name": "limb",
                "shape": "skin",
                "location": [0, 0, 0],
                "skin": {
                    "nodes": [
                        {"id": "a", "at": [0, 0, 0], "radius": 0.1},
                        {"id": "b", "at": [0, 0, 1], "radius": 0.1},
                    ],
                    "edges": [["a", "missing"]],
                },
            }],
        }))


def test_member_to_body_includes_mirror_copy() -> None:
    mapping = member_to_body(
        ["ear", "ear_m", "eye"],
        [BodySpec(name="head", members=["ear"])],
    )
    assert mapping["ear"] == "head"
    assert mapping["ear_m"] == "head"
    assert "eye" not in mapping


def test_knight_example_parses() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "examples" / "assets" / "chess_knight.yaml"
    )
    spec = parse_asset_spec(
        yaml.safe_load(path.read_text(encoding="utf-8")),
    )
    upper = next(p for p in spec.geometry.parts if p.name == "upper")
    assert upper.shape == "skin"
    assert spec.geometry.bodies[0].method == "remesh"
    kinds = [t.kind for t in spec.construction_plan.techniques]
    assert kinds == ["lathe", "skin", "remesh"]
    assert spec.geometric_plan is not None
    assert spec.geometric_plan.recognition == "silhouette"
    assert spec.geometric_plan.landmarks[0].node == "neck_base"
    assert spec.geometric_plan.critical_views[0].view == (
        "silhouette_side"
    )
