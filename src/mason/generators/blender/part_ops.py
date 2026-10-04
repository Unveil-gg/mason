"""Expand inset, array, mirror, and construction vary."""

from __future__ import annotations

import math

from mason.core.entropy import PartVary, signed, unit
from mason.core.parts import PartArray, PropPart
from mason.core.styles import StyleProcess

_AXIS = {"x": 0, "y": 1, "z": 2}
_CHIP_SHAPES = ("box", "tapered_box", "cylinder", "sphere", "cone")


def expand_part_ops(
    parts: list[PropPart],
    *,
    seed: int = 0,
    process: StyleProcess | None = None,
    bevel_width: float = 0.02,
    breakup: bool = True,
) -> list[PropPart]:
    """Apply inset, arrays, mirror, and vary.

    seed and process drive opt-in vary. breakup False leaves vary
    set so a later place_breakup can sit flecks after snap.
    Returns concrete parts.
    """
    hand = process if process is not None else StyleProcess()
    expanded: list[PropPart] = []
    for part in parts:
        if part.shape == "instance":
            expanded.append(part)
            continue
        size = _inset_size(part.size, part.inset)
        base = part.model_copy(update={
            "size": size,
            "inset": 0.0,
            "array": None,
            "mirror": None,
        })
        copies = _array_copies(base, part, seed, hand)
        for copy in copies:
            expanded.append(_apply_vary(
                copy, part, seed, hand, bevel_width,
            ))
            if part.mirror:
                expanded.append(_mirrored(expanded[-1], part.mirror))
    if breakup:
        return place_breakup(expanded, seed=seed, process=hand)
    return expanded


def place_breakup(
    parts: list[PropPart],
    *,
    seed: int,
    process: StyleProcess | None = None,
) -> list[PropPart]:
    """Append face flecks and clear vary. seed keys each fleck."""
    hand = process if process is not None else StyleProcess()
    out: list[PropPart] = []
    for part in parts:
        if part.vary is None:
            out.append(part)
            continue
        chips = _chips(part, seed, hand)
        out.append(part.model_copy(update={"vary": None}))
        out.extend(chips)
    return out


def _array_copies(
    base: PropPart,
    part: PropPart,
    seed: int,
    process: StyleProcess,
) -> list[PropPart]:
    if part.array is None:
        return [base]
    amounts = _amounts(part.vary, process)
    if part.array.radial is not None:
        return _radial_copies(base, part, seed, amounts["spacing"])
    return _linear_copies(base, part, seed, amounts["spacing"])


def _linear_copies(
    base: PropPart,
    part: PropPart,
    seed: int,
    spacing: float,
) -> list[PropPart]:
    assert part.array is not None
    offset = part.array.offset
    copies: list[PropPart] = []
    loc = list(part.location)
    for i in range(part.array.count):
        if spacing == 0.0:
            placed = (
                part.location[0] + offset[0] * i,
                part.location[1] + offset[1] * i,
                part.location[2] + offset[2] * i,
            )
        else:
            if i:
                wobble = 1.0 + signed(seed, part.name, i, 5) * spacing
                loc = [
                    loc[0] + offset[0] * wobble,
                    loc[1] + offset[1] * wobble,
                    loc[2] + offset[2] * wobble,
                ]
            placed = (loc[0], loc[1], loc[2])
        copies.append(base.model_copy(update={
            "name": _copy_name(part.name, i),
            "location": placed,
        }))
    return copies


def _radial_copies(
    base: PropPart,
    part: PropPart,
    seed: int,
    spacing: float,
) -> list[PropPart]:
    assert part.array is not None
    array = part.array
    radial = array.radial
    assert radial is not None
    cx, cy, cz = base.location
    copies: list[PropPart] = []
    for i in range(array.count):
        angle = radial.start_angle + (2.0 * math.pi * i / array.count)
        if spacing:
            step = 2.0 * math.pi / array.count
            angle += signed(seed, part.name, i, 5) * spacing * step
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
        copies.append(base.model_copy(update={
            "name": _copy_name(part.name, i),
            "location": (loc[0], loc[1], loc[2]),
            "rotation": (rot[0], rot[1], rot[2]),
        }))
    return copies


def _apply_vary(
    copy: PropPart,
    source: PropPart,
    seed: int,
    process: StyleProcess,
    bevel_width: float,
) -> PropPart:
    """Scale, rotate, bevel, and material. Leaves vary for breakup."""
    if source.vary is None:
        return copy
    amounts = _amounts(source.vary, process)
    updates: dict = {}
    index = _index_of(copy.name, source.name)
    if amounts["scale"] or amounts["silhouette"]:
        updates["size"] = _scaled(
            copy.size, source.name, index, seed,
            amounts["scale"], amounts["silhouette"], source.vary.axis,
        )
    if amounts["rotation"]:
        rot = list(copy.rotation)
        axis = _AXIS[source.vary.axis]
        rot[axis] += signed(seed, source.name, index, 4) * amounts["rotation"]
        updates["rotation"] = (rot[0], rot[1], rot[2])
    if amounts["bevel"]:
        wobble = signed(seed, source.name, index, 8)
        width = bevel_width * (1.0 + wobble * amounts["bevel"])
        updates["bevel_width"] = max(0.0, width)
    if amounts["material"]:
        updates["color_bias"] = unit(
            seed, source.name, index, 6,
        ) * amounts["material"]
        updates["roughness_bias"] = signed(
            seed, source.name, index, 7,
        ) * amounts["material"] * 0.15
    if not updates:
        return copy
    return copy.model_copy(update=updates)


def _chips(
    part: PropPart,
    seed: int,
    process: StyleProcess,
) -> list[PropPart]:
    vary = part.vary
    if vary is None or part.size is None:
        return []
    if part.shape not in _CHIP_SHAPES or part.component or part.helper:
        return []
    amount = _amounts(vary, process)["breakup"]
    count = _chip_count(vary, amount)
    if count == 0:
        return []
    shortest = min(part.size)
    chip = max(0.001, amount * shortest)
    span_u, span_v = _face_span(part.size, vary.face)
    usable_u = max(span_u - chip, 0.001)
    usable_v = max(span_v - chip, 0.001)
    chips: list[PropPart] = []
    for i in range(count):
        u = (unit(seed, part.name, i, 1) - 0.5) * usable_u
        v = (unit(seed, part.name, i, 2) - 0.5) * usable_v
        local = _face_point(part.size, vary.face, u, v, chip * 0.25)
        world = _rotate(local, part.rotation)
        chips.append(PropPart(
            name=f"{part.name}_chip_{i + 1}",
            shape="box",
            size=_chip_size(chip, vary.face),
            location=(
                part.location[0] + world[0],
                part.location[1] + world[1],
                part.location[2] + world[2],
            ),
            rotation=part.rotation,
            material=part.material,
            family=part.family,
            bevel=False,
            color_bias=0.2 + 0.5 * unit(seed, part.name, i, 3),
        ))
    return chips


def _amounts(
    vary: PartVary | None,
    process: StyleProcess,
) -> dict[str, float]:
    """Explicit knob, else the style hand. No vary is all zeros."""
    if vary is None:
        return {
            "scale": 0.0,
            "rotation": 0.0,
            "spacing": 0.0,
            "bevel": 0.0,
            "silhouette": 0.0,
            "breakup": 0.0,
            "material": 0.0,
        }

    def pick(explicit: float | None, fallback: float) -> float:
        if explicit is not None:
            return explicit
        return fallback

    jitter = process.jitter
    return {
        "scale": pick(vary.scale, jitter),
        "rotation": pick(vary.rotation, min(0.5, jitter)),
        "spacing": pick(vary.spacing, jitter),
        "bevel": pick(vary.bevel, process.irregularity),
        "silhouette": pick(vary.silhouette, process.irregularity),
        "breakup": pick(vary.breakup, process.breakup),
        "material": pick(vary.material, process.variation),
    }


def _chip_count(vary: PartVary, amount: float) -> int:
    if amount <= 0:
        return 0
    if vary.breakup_count is not None:
        return vary.breakup_count
    return min(24, max(1, int(amount * 12)))


def _scaled(
    size: tuple[float, float, float] | None,
    name: str,
    index: int,
    seed: int,
    scale: float,
    silhouette: float,
    axis: str,
) -> tuple[float, float, float]:
    if size is None:
        return (0.001, 0.001, 0.001)
    skip = _AXIS[axis]
    out: list[float] = []
    for n, value in enumerate(size):
        factor = 1.0
        if scale:
            factor *= 1.0 + signed(seed, name, index, n) * scale
        if silhouette and n != skip:
            factor *= 1.0 + signed(seed, name, index, 10 + n) * silhouette
        out.append(max(0.001, value * factor))
    return (out[0], out[1], out[2])


def _copy_name(name: str, index: int) -> str:
    if index == 0:
        return name
    return f"{name}_{index + 1}"


def _index_of(copy_name: str, source_name: str) -> int:
    if copy_name == source_name:
        return 0
    prefix = f"{source_name}_"
    if copy_name.startswith(prefix) and copy_name[len(prefix):].isdigit():
        return int(copy_name[len(prefix):]) - 1
    return 0


def _face_span(
    size: tuple[float, float, float],
    face: str,
) -> tuple[float, float]:
    sx, sy, sz = size
    if face in ("top", "bottom"):
        return sx, sy
    if face in ("front", "back"):
        return sx, sz
    return sy, sz


def _face_point(
    size: tuple[float, float, float],
    face: str,
    u: float,
    v: float,
    embed: float,
) -> tuple[float, float, float]:
    hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
    if face == "top":
        return (u, v, hz - embed)
    if face == "bottom":
        return (u, v, -hz + embed)
    if face == "front":
        return (u, hy - embed, v)
    if face == "back":
        return (u, -hy + embed, v)
    if face == "right":
        return (hx - embed, u, v)
    return (-hx + embed, u, v)


def _chip_size(
    chip: float,
    face: str,
) -> tuple[float, float, float]:
    thin = chip * 0.45
    if face in ("top", "bottom"):
        return (chip, chip, thin)
    if face in ("front", "back"):
        return (chip, thin, chip)
    return (thin, chip, chip)


def _rotate(
    point: tuple[float, float, float],
    rotation: tuple[float, float, float],
) -> tuple[float, float, float]:
    """XYZ euler, matching Blender's default rotation order."""
    x, y, z = point
    rx, ry, rz = rotation
    cx, sx = math.cos(rx), math.sin(rx)
    y, z = y * cx - z * sx, y * sx + z * cx
    cy, sy = math.cos(ry), math.sin(ry)
    x, z = x * cy + z * sy, -x * sy + z * cy
    cz, sz = math.cos(rz), math.sin(rz)
    x, y = x * cz - y * sz, x * sz + y * cz
    return (x, y, z)


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
    size: tuple[float, float, float] | None,
    inset: float,
) -> tuple[float, float, float]:
    if size is None:
        return (0.001, 0.001, 0.001)
    if inset <= 0:
        return size
    return tuple(max(0.001, value - 2.0 * inset) for value in size)
