"""Expand inset/array on parts before Blender sees them."""

from __future__ import annotations

from mason.core.parts import PropPart


def expand_part_ops(parts: list[PropPart]) -> list[PropPart]:
    """Apply inset and linear arrays. Parent names are left intact."""
    expanded: list[PropPart] = []
    for part in parts:
        size = _inset_size(part.size, part.inset)
        base = part.model_copy(update={"size": size, "inset": 0.0, "array": None})
        if part.array is None:
            expanded.append(base)
            continue
        for i in range(part.array.count):
            loc = (
                part.location[0] + part.array.offset[0] * i,
                part.location[1] + part.array.offset[1] * i,
                part.location[2] + part.array.offset[2] * i,
            )
            name = part.name if i == 0 else f"{part.name}_{i + 1}"
            expanded.append(base.model_copy(update={"name": name, "location": loc}))
    return expanded


def _inset_size(
    size: tuple[float, float, float],
    inset: float,
) -> tuple[float, float, float]:
    if inset <= 0:
        return size
    return tuple(max(0.001, s - 2.0 * inset) for s in size)
