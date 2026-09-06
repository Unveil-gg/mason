"""AABB snap: move a part so it meets a named face of another."""

from __future__ import annotations

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
    """Axis-aligned min/max from location and size. Returns (min, max)."""
    loc = list(part.location)
    half = [s / 2.0 for s in part.size]
    lo = [loc[i] - half[i] for i in range(3)]
    hi = [loc[i] + half[i] for i in range(3)]
    return lo, hi


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
    by_name = {part.name: part for part in parts}
    out: list[PropPart] = []
    for part in parts:
        if part.snap is None:
            out.append(part)
            continue
        current = list(by_name.values())
        targets = _lookup(
            current, by_name, _snap_target(part.name, part.snap.to),
        )
        target_lo, target_hi = union_aabb(targets)
        loc = _snapped_location(
            part, target_lo, target_hi, part.snap.on, part.snap.embed,
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
    by_name = {part.name: part for part in parts}
    details: list[str] = []
    ok = True
    for part in parts:
        if part.snap is None:
            continue
        try:
            targets = _lookup(
                parts, by_name, _snap_target(part.name, part.snap.to),
            )
        except MasonError as exc:
            ok = False
            details.append(str(exc.message))
            continue
        if not aabbs_touch(aabb(part), union_aabb(targets), tol):
            ok = False
            details.append(f"{part.name}->{part.snap.to}")
    return ok, ", ".join(details) if details else "ok"


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
) -> tuple[bool, str]:
    """Whether each parented part meets its parent AABB. Returns
    (ok, detail)."""
    details: list[str] = []
    ok = True
    for part in parts:
        if not part.parent:
            continue
        child = _bounds_named(object_bounds, part.name)
        parent = _bounds_named(object_bounds, part.parent)
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
