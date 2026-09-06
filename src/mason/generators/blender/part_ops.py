"""Expand inset, array, and mirror on parts before Blender sees them."""

from __future__ import annotations

import math

from mason.core.parts import PartArray, PropPart


def expand_part_ops(parts: list[PropPart]) -> list[PropPart]:
    """Apply inset, linear/radial arrays, and mirror copies."""
    expanded: list[PropPart] = []
    for part in parts:
        size = _inset_size(part.size, part.inset)
        base = part.model_copy(update={
            "size": size,
            "inset": 0.0,
            "array": None,
            "mirror": None,
        })
        copies = _array_copies(base, part)
        for copy in copies:
            expanded.append(copy)
            if part.mirror:
                expanded.append(_mirrored(copy, part.mirror))
    return expanded


def _array_copies(base: PropPart, part: PropPart) -> list[PropPart]:
    if part.array is None:
        return [base]
    if part.array.radial is not None:
        return _radial_copies(base, part.array)
    copies: list[PropPart] = []
    for i in range(part.array.count):
        loc = (
            part.location[0] + part.array.offset[0] * i,
            part.location[1] + part.array.offset[1] * i,
            part.location[2] + part.array.offset[2] * i,
        )
        name = part.name if i == 0 else f"{part.name}_{i + 1}"
        copies.append(base.model_copy(update={"name": name, "location": loc}))
    return copies


def _radial_copies(base: PropPart, array: PartArray) -> list[PropPart]:
    radial = array.radial
    assert radial is not None
    cx, cy, cz = base.location
    copies: list[PropPart] = []
    for i in range(array.count):
        angle = radial.start_angle + (2.0 * math.pi * i / array.count)
        loc = [cx, cy, cz]
        rot = list(base.rotation)
        if radial.axis == "z":
            loc[0] = cx + radial.radius * math.cos(angle)
            loc[1] = cy + radial.radius * math.sin(angle)
            rot[2] = base.rotation[2] + angle
        elif radial.axis == "y":
            loc[0] = cx + radial.radius * math.cos(angle)
            loc[2] = cz + radial.radius * math.sin(angle)
            rot[1] = base.rotation[1] + angle
        else:
            loc[1] = cy + radial.radius * math.cos(angle)
            loc[2] = cz + radial.radius * math.sin(angle)
            rot[0] = base.rotation[0] + angle
        name = base.name if i == 0 else f"{base.name}_{i + 1}"
        copies.append(base.model_copy(update={
            "name": name,
            "location": (loc[0], loc[1], loc[2]),
            "rotation": (rot[0], rot[1], rot[2]),
        }))
    return copies


def _mirrored(part: PropPart, axis: str) -> PropPart:
    loc = list(part.location)
    rot = list(part.rotation)
    if axis == "x":
        loc[0] = -loc[0]
        rot[1] = -rot[1]
        rot[2] = -rot[2]
    elif axis == "y":
        loc[1] = -loc[1]
        rot[0] = -rot[0]
        rot[2] = -rot[2]
    else:
        loc[2] = -loc[2]
        rot[0] = -rot[0]
        rot[1] = -rot[1]
    return part.model_copy(update={
        "name": f"{part.name}_m",
        "location": (loc[0], loc[1], loc[2]),
        "rotation": (rot[0], rot[1], rot[2]),
    })


def _inset_size(
    size: tuple[float, float, float],
    inset: float,
) -> tuple[float, float, float]:
    if inset <= 0:
        return size
    return tuple(max(0.001, s - 2.0 * inset) for s in size)
