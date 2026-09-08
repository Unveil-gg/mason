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
