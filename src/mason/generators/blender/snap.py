"""AABB snap: move a part so it meets a named face of another."""

from __future__ import annotations

from mason.core.forms import BodySpec, member_to_body, part_local_bounds
from mason.core.parts import PropPart
from mason.errors import MasonError

# axis index, sign of the target face (+1 = max, -1 = min)
_FACES = {
    "top": (2, 1),
    "bottom": (2, -1),
    "back": (1, 1),
    "front": (1, -1),
    "right": (0, 1),
    "left": (0, -1),
}


def aabb(part: PropPart) -> tuple[list[float], list[float]]:
    """Axis-aligned min/max. Skin/curve/outline use local origin."""
    loc = list(part.location)
    local = part_local_bounds(part)
    if local is not None:
        lo, hi = local
        return (
            [loc[i] + lo[i] for i in range(3)],
            [loc[i] + hi[i] for i in range(3)],
        )
    dims = part.size or (0.001, 0.001, 0.001)
    half = [s / 2.0 for s in dims]
    return (
        [loc[i] - half[i] for i in range(3)],
        [loc[i] + half[i] for i in range(3)],
    )


def union_aabb(
    parts: list[PropPart],
) -> tuple[list[float], list[float]]:
    """Union AABB of several parts. Returns (min, max)."""
    lo, hi = aabb(parts[0])
    for part in parts[1:]:
        a, b = aabb(part)
        lo = [min(lo[i], a[i]) for i in range(3)]
        hi = [max(hi[i], b[i]) for i in range(3)]
    return lo, hi


def apply_snaps(parts: list[PropPart]) -> list[PropPart]:
    """Move snapped parts so opposite faces meet. One pass, list order."""
    return _apply_meets(parts, "snap")


def apply_flushes(parts: list[PropPart]) -> list[PropPart]:
    """Second-axis meet after snap. Portico on a pad against a wall."""
    return _apply_meets(parts, "flush")


def apply_seats(parts: list[PropPart]) -> list[PropPart]:
    """Snap, then flush. Use this before Blender sees locations."""
    return apply_flushes(apply_snaps(parts))


def _apply_meets(
    parts: list[PropPart],
    field: str,
) -> list[PropPart]:
    """Move parts that declare snap or flush. Returns a new list."""
    by_name = {part.name: part for part in parts}
    out: list[PropPart] = []
    for part in parts:
        meet = getattr(part, field, None)
        if meet is None:
            out.append(part)
            continue
        current = list(by_name.values())
        targets = _lookup(
            current, by_name, _snap_target(part.name, meet.to),
        )
        target_lo, target_hi = union_aabb(targets)
        loc = _snapped_location(
            part, target_lo, target_hi, meet.on, meet.embed,
        )
        moved = part.model_copy(update={"location": loc})
        by_name[part.name] = moved
        out.append(moved)
    return out


def snaps_touch(
    parts: list[PropPart],
    tol: float = 0.05,
) -> tuple[bool, str]:
    """Whether every snapped part's AABB meets its target. Returns
    (ok, detail)."""
    return _meets_touch(parts, "snap", tol)


def flushes_touch(
    parts: list[PropPart],
    tol: float = 0.05,
) -> tuple[bool, str]:
    """Whether every flushed part's AABB meets its host. Returns
    (ok, detail)."""
    return _meets_touch(parts, "flush", tol)


def _meets_touch(
    parts: list[PropPart],
    field: str,
    tol: float,
) -> tuple[bool, str]:
    """Shared snap/flush contact test."""
    by_name = {part.name: part for part in parts}
    details: list[str] = []
    ok = True
    for part in parts:
        meet = getattr(part, field, None)
        if meet is None:
            continue
        try:
            targets = _lookup(
                parts, by_name, _snap_target(part.name, meet.to),
            )
        except MasonError as exc:
            ok = False
            details.append(str(exc.message))
            continue
        if not aabbs_touch(aabb(part), union_aabb(targets), tol):
            ok = False
            details.append(f"{part.name}->{meet.to}")
    return ok, ", ".join(details) if details else "ok"


_WALL = frozenset({"front", "back", "left", "right"})


def facades_fit(
    parts: list[PropPart],
    tol: float = 0.05,
    min_overlap: float = 0.25,
) -> tuple[bool, str]:
    """Wall snap/flush parts must meet the host and share the face.

    A portico that only kisses a corner fails. Returns (ok, detail).
    """
    touch_ok, touch_detail = flushes_touch(parts, tol)
    by_name = {part.name: part for part in parts}
    details: list[str] = []
    ok = touch_ok
    if not touch_ok and touch_detail != "ok":
        details.append(touch_detail)
    for part in parts:
        meets = [part.flush]
        for meet in meets:
            if meet is None or meet.on not in _WALL:
                continue
            try:
                targets = _lookup(
                    parts, by_name, _snap_target(part.name, meet.to),
                )
            except MasonError as exc:
                ok = False
                details.append(str(exc.message))
                continue
            host = union_aabb(targets)
            child = aabb(part)
            if not aabbs_touch(child, host, tol):
                ok = False
                details.append(f"{part.name}->{meet.to}")
                continue
            if not _face_overlap(child, host, meet.on, min_overlap):
                ok = False
                details.append(f"{part.name}@{meet.on}")
    return ok, ", ".join(details) if details else "ok"


def _face_overlap(
    child: tuple[list[float], list[float]],
    host: tuple[list[float], list[float]],
    on: str,
    min_frac: float,
) -> bool:
    """True if the child covers enough of the host on the wall face."""
    # front/back = Y; overlap X and Z. left/right = X; overlap Y and Z.
    axes = (0, 2) if on in ("front", "back") else (1, 2)
    c_lo, c_hi = child
    h_lo, h_hi = host
    for axis in axes:
        overlap = min(c_hi[axis], h_hi[axis]) - max(c_lo[axis], h_lo[axis])
        span = min(c_hi[axis] - c_lo[axis], h_hi[axis] - h_lo[axis])
        if span <= 1e-6:
            continue
        if overlap / span < min_frac:
            return False
    return True


def aabbs_touch(
    first: tuple[list[float], list[float]],
    second: tuple[list[float], list[float]],
    tol: float,
) -> bool:
    """True if AABBs overlap or the gap on every axis is <= tol."""
    a_lo, a_hi = first
    b_lo, b_hi = second
    for i in range(3):
        gap = max(a_lo[i] - b_hi[i], b_lo[i] - a_hi[i])
        if gap > tol:
            return False
    return True


def parents_touch_bounds(
    parts: list[PropPart],
    object_bounds: dict,
    tol: float = 0.05,
    bodies: list[BodySpec] | None = None,
) -> tuple[bool, str]:
    """Whether each parented part meets its parent AABB. Returns
    (ok, detail). Consumed body members are skipped."""
    details: list[str] = []
    ok = True
    body_of = member_to_body([p.name for p in parts], bodies or [])
    for part in parts:
        if not part.parent or part.cutout or part.helper:
            continue
        if part.name in body_of:
            continue
        parent_name = body_of.get(part.parent, part.parent)
        child = _bounds_named(object_bounds, part.name)
        parent = _bounds_named(object_bounds, parent_name)
        if child is None or parent is None:
            ok = False
            details.append(f"{part.name}->{part.parent}")
            continue
        if not aabbs_touch(child, parent, tol):
            ok = False
            details.append(f"{part.name}->{part.parent}")
    return ok, ", ".join(details) if details else "ok"


def _bounds_named(
    object_bounds: dict,
    name: str,
) -> tuple[list[float], list[float]] | None:
    if name in object_bounds:
        item = object_bounds[name]
        return list(item["min"]), list(item["max"])
    matches = [
        object_bounds[key] for key in object_bounds
        if key.startswith(name + "_")
    ]
    if not matches:
        return None
    lo = list(matches[0]["min"])
    hi = list(matches[0]["max"])
    for item in matches[1:]:
        lo = [min(lo[i], item["min"][i]) for i in range(3)]
        hi = [max(hi[i], item["max"][i]) for i in range(3)]
    return lo, hi


def _snap_target(part_name: str, target: str) -> str:
    """Prefer the mirrored twin when this part is a mirror copy."""
    if part_name.endswith("_m"):
        return f"{target}_m"
    return target


def _lookup(
    parts: list[PropPart],
    by_name: dict[str, PropPart],
    name: str,
) -> list[PropPart]:
    if name in by_name:
        return [by_name[name]]
    matches = [
        part for part in parts
        if part.name.startswith(name + "_")
    ]
    if not matches and name.endswith("_m"):
        return _lookup(parts, by_name, name[:-2])
    if not matches:
        raise MasonError(
            f"Snap target '{name}' not found.",
            code="snap_target_missing",
            hint="Use the name of another part in this spec.",
            context={"target": name},
        )
    return matches


def _snapped_location(
    part: PropPart,
    target_lo: list[float],
    target_hi: list[float],
    on: str,
    embed: float = 0.0,
) -> tuple[float, float, float]:
    axis, sign = _FACES[on]
    child_lo, child_hi = aabb(part)
    loc = list(part.location)
    if sign > 0:
        # child's min meets target max
        loc[axis] += target_hi[axis] - child_lo[axis]
    else:
        # child's max meets target min
        loc[axis] += target_lo[axis] - child_hi[axis]
    # Push into the target so sloped roofs get a through-joint.
    loc[axis] -= sign * embed
    return (loc[0], loc[1], loc[2])
