"""AABB snap moves parts so named faces meet."""

from __future__ import annotations

import pytest

from mason.core.forms import BodySpec
from mason.core.parts import PartCutout, PartSnap, PropPart
from mason.generators.blender.snap import (
    apply_snaps,
    parents_touch_bounds,
    snaps_touch,
)
from mason.errors import MasonError


def test_snap_box_onto_top() -> None:
    base = PropPart(
        name="base",
        size=(1.0, 1.0, 0.2),
        location=(0.0, 0.0, 0.1),
    )
    lid = PropPart(
        name="lid",
        size=(1.0, 1.0, 0.2),
        location=(0.0, 0.0, 5.0),
        snap=PartSnap(to="base", on="top"),
    )
    out = apply_snaps([base, lid])
    assert out[1].location[2] == pytest.approx(0.3)
    ok, detail = snaps_touch(out)
    assert ok, detail


def test_mirrored_snap_prefers_twin() -> None:
    from mason.generators.blender.part_ops import expand_part_ops

    base = PropPart(
        name="wing",
        size=(0.4, 0.4, 0.4),
        location=(-1.0, 0.0, 0.2),
        mirror="x",
    )
    roof = PropPart(
        name="roof",
        size=(0.4, 0.4, 0.2),
        location=(-1.0, 0.0, 3.0),
        snap=PartSnap(to="wing", on="top"),
        mirror="x",
    )
    out = apply_snaps(expand_part_ops([base, roof]))
    by_name = {p.name: p for p in out}
    assert by_name["roof"].location[0] == pytest.approx(-1.0)
    assert by_name["roof_m"].location[0] == pytest.approx(1.0)
    assert by_name["roof"].location[2] == pytest.approx(0.5)
    assert by_name["roof_m"].location[2] == pytest.approx(0.5)
    ok, detail = snaps_touch(out)
    assert ok, detail


def test_snap_embed_pushes_into_target() -> None:
    base = PropPart(
        name="base",
        size=(1.0, 1.0, 0.2),
        location=(0.0, 0.0, 0.1),
    )
    post = PropPart(
        name="post",
        size=(0.2, 0.2, 0.4),
        location=(0.0, 0.0, 5.0),
        snap=PartSnap(to="base", on="top", embed=0.1),
    )
    out = apply_snaps([base, post])
    assert out[1].location[2] == pytest.approx(0.3)
    ok, _detail = snaps_touch(out)
    assert ok


def test_parents_touch_skips_cutout() -> None:
    cutter = PropPart(
        name="hole",
        size=(0.2, 0.2, 0.2),
        location=(0.0, 0.0, 0.5),
        parent="wall",
        cutout=PartCutout(target="wall"),
    )
    ok, detail = parents_touch_bounds(
        [cutter],
        {"wall": {"min": [0, 0, 0], "max": [1, 1, 1]}},
    )
    assert ok, detail


def test_parents_touch_skips_body_members() -> None:
    neck = PropPart(
        name="neck",
        size=(0.2, 0.2, 0.2),
        location=(0.0, 0.0, 0.5),
        parent="stem",
    )
    ok, detail = parents_touch_bounds(
        [neck],
        {"head": {"min": [0, 0, 0], "max": [1, 1, 1]}},
        bodies=[BodySpec(name="head", members=["neck"])],
    )
    assert ok, detail


def test_snap_skin_uses_node_origin() -> None:
    base = PropPart(
        name="base",
        size=(0.2, 0.2, 0.1),
        location=(0.0, 0.0, 0.05),
    )
    upper = PropPart(
        name="upper",
        shape="skin",
        location=(0.0, 0.0, 5.0),
        snap=PartSnap(to="base", on="top", embed=0.02),
        skin={
            "nodes": [
                {"id": "root", "at": [0.0, 0.0, 0.0], "radius": 0.05},
                {"id": "tip", "at": [0.0, 0.0, 0.2], "radius": 0.02},
            ],
            "edges": [["root", "tip"]],
        },
    )
    out = apply_snaps([base, upper])
    assert out[1].location[2] == pytest.approx(0.13)
    ok, detail = snaps_touch(out)
    assert ok, detail


def test_flush_second_axis() -> None:
    from mason.generators.blender.snap import apply_seats, facades_fit

    wall = PropPart(
        name="main",
        size=(2.0, 1.0, 1.4),
        location=(0.0, 0.0, 0.7),
    )
    pad = PropPart(
        name="portico",
        size=(1.2, 0.6, 0.1),
        location=(0.0, -2.0, 5.0),
        snap=PartSnap(to="plinth", on="top"),
        flush=PartSnap(to="main", on="front"),
    )
    plinth = PropPart(
        name="plinth",
        size=(2.2, 1.2, 0.14),
        location=(0.0, 0.0, 0.07),
    )
    out = apply_seats([plinth, wall, pad])
    by_name = {p.name: p for p in out}
    assert by_name["portico"].location[2] == pytest.approx(0.19)
    assert by_name["portico"].location[1] == pytest.approx(-0.8)
    ok, detail = facades_fit(out)
    assert ok, detail


def test_facade_fit_rejects_corner_kiss() -> None:
    from mason.generators.blender.snap import facades_fit

    wall = PropPart(
        name="main",
        size=(2.0, 1.0, 1.4),
        location=(0.0, 0.0, 0.7),
    )
    pad = PropPart(
        name="portico",
        size=(0.2, 0.2, 0.1),
        location=(1.08, -0.6, 0.05),
        flush=PartSnap(to="main", on="front"),
    )
    ok, detail = facades_fit([wall, pad])
    assert not ok
    assert "portico" in detail


def test_unknown_to_raises() -> None:
    part = PropPart(
        name="lid",
        size=(1.0, 1.0, 0.2),
        location=(0.0, 0.0, 1.0),
        snap=PartSnap(to="missing", on="top"),
    )
    with pytest.raises(MasonError) as exc:
        apply_snaps([part])
    assert exc.value.code == "snap_target_missing"
