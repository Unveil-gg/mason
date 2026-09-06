"""Part inset/array expansion."""

from __future__ import annotations

from mason.core.assets import parse_asset_spec
from mason.core.parts import PartArray, PropPart, RadialArray
from mason.generators.blender.part_ops import expand_part_ops
from mason.pipelines.static_prop import resolved_parts


def test_array_keeps_first_name() -> None:
    parts = expand_part_ops([
        PropPart(
            name="post",
            shape="cylinder",
            size=(0.1, 0.1, 1.0),
            location=(0.0, 0.0, 0.5),
            array=PartArray(count=3, offset=(0.4, 0.0, 0.0)),
        ),
    ])
    assert [p.name for p in parts] == ["post", "post_2", "post_3"]
    assert parts[2].location[0] == 0.8


def test_inset_shrinks_size() -> None:
    parts = expand_part_ops([
        PropPart(
            name="box",
            size=(1.0, 1.0, 1.0),
            location=(0.0, 0.0, 0.5),
            inset=0.1,
        ),
    ])
    assert parts[0].size == (0.8, 0.8, 0.8)
    assert parts[0].inset == 0.0


def test_resolved_parts_expands_array() -> None:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "fence",
        "name": "Fence",
        "dimensions": {"width": 1, "depth": 0.1, "height": 1},
        "geometry": {
            "parts": [{
                "name": "post",
                "shape": "cylinder",
                "size": [0.1, 0.1, 1],
                "location": [0, 0, 0.5],
                "array": {"count": 2, "offset": [0.5, 0, 0]},
            }],
        },
    })
    parts = resolved_parts(spec)
    assert len(parts) == 2


def test_radial_array_names() -> None:
    parts = expand_part_ops([
        PropPart(
            name="bolt",
            size=(0.02, 0.02, 0.02),
            location=(0.0, 0.0, 0.1),
            array=PartArray(
                count=4,
                radial=RadialArray(radius=0.1, axis="z"),
            ),
        ),
    ])
    assert [p.name for p in parts] == [
        "bolt", "bolt_2", "bolt_3", "bolt_4",
    ]
    assert abs(parts[0].location[0]) > 0.05


def test_mirror_x() -> None:
    parts = expand_part_ops([
        PropPart(
            name="ear",
            size=(0.1, 0.1, 0.1),
            location=(0.4, 0.0, 0.2),
            mirror="x",
        ),
    ])
    assert [p.name for p in parts] == ["ear", "ear_m"]
    assert parts[1].location[0] == -0.4
