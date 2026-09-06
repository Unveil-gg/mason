"""AABB snap moves parts so named faces meet."""

from __future__ import annotations

import pytest

from mason.core.parts import PartSnap, PropPart
from mason.errors import MasonError
from mason.generators.blender.snap import apply_snaps, snaps_touch


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
