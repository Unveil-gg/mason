"""Expand named hardware components into primitive parts."""

from __future__ import annotations

from mason.core.parts import PropPart
from mason.errors import MasonError

_COMPONENTS = frozenset({
    "bolt", "hinge", "handle", "caster", "bracket", "trim",
})


def expand_components(parts: list[PropPart]) -> list[PropPart]:
    """Replace component instances with primitive clusters."""
    expanded: list[PropPart] = []
    for part in parts:
        if not part.component:
            expanded.append(part)
            continue
        if part.component not in _COMPONENTS:
            raise MasonError(
                f"Unknown component '{part.component}'.",
                code="unknown_component",
            )
        expanded.extend(_expand_one(part))
    return expanded


def _expand_one(part: PropPart) -> list[PropPart]:
    dispatch = {
        "bolt": _bolt,
        "hinge": _hinge,
        "handle": _handle,
        "caster": _caster,
        "bracket": _bracket,
        "trim": _trim,
    }
    return dispatch[part.component](part)


def _params(part: PropPart) -> dict[str, float]:
    return dict(part.component_params)


def _child(
    part: PropPart,
    suffix: str,
    *,
    shape: str,
    size: tuple[float, float, float],
    location: tuple[float, float, float],
    rotation: tuple[float, float, float] | None = None,
) -> PropPart:
    return PropPart(
        name=f"{part.name}_{suffix}",
        shape=shape,  # type: ignore[arg-type]
        size=size,
        location=location,
        rotation=rotation or part.rotation,
        material=part.material,
        family=part.family,
        wear=part.wear,
        parent=part.parent,
        bevel=part.bevel,
    )


def _bolt(part: PropPart) -> list[PropPart]:
    p = _params(part)
    radius = p.get("radius") or max(part.size[0] / 2.0, 0.004)
    depth = p.get("depth") or max(part.size[2], 0.008)
    head_h = max(depth * 0.35, 0.003)
    shank_h = max(depth - head_h, 0.003)
    x, y, z = part.location
    return [
        _child(
            part, "head", shape="box",
            size=(radius * 2.2, radius * 2.2, head_h),
            location=(x, y, z + shank_h * 0.5),
        ),
        _child(
            part, "shank", shape="cylinder",
            size=(radius * 2.0, radius * 2.0, shank_h),
            location=(x, y, z - head_h * 0.25),
        ),
    ]


def _hinge(part: PropPart) -> list[PropPart]:
    w, d, h = part.size
    x, y, z = part.location
    knuckle = min(w, d, h) * 0.45
    return [
        _child(
            part, "knuckle_a", shape="cylinder",
            size=(knuckle, knuckle, h),
            location=(x - w * 0.2, y, z),
        ),
        _child(
            part, "knuckle_b", shape="cylinder",
            size=(knuckle, knuckle, h),
            location=(x + w * 0.2, y, z),
        ),
        _child(
            part, "pin", shape="cylinder",
            size=(knuckle * 0.45, knuckle * 0.45, h * 1.15),
            location=(x, y, z),
        ),
    ]


def _handle(part: PropPart) -> list[PropPart]:
    w, _d, h = part.size
    x, y, z = part.location
    post = min(w, h) * 0.12
    return [
        _child(
            part, "post_l", shape="cylinder",
            size=(post, post, h),
            location=(x - w * 0.4, y, z),
        ),
        _child(
            part, "post_r", shape="cylinder",
            size=(post, post, h),
            location=(x + w * 0.4, y, z),
        ),
        _child(
            part, "bar", shape="cylinder",
            size=(post * 1.1, post * 1.1, w * 0.85),
            location=(x, y, z + h * 0.42),
            rotation=(0.0, 1.5708, 0.0),
        ),
    ]


def _caster(part: PropPart) -> list[PropPart]:
    w, d, h = part.size
    x, y, z = part.location
    return [
        _child(
            part, "wheel", shape="cylinder",
            size=(h, h, d),
            location=(x, y, z),
            rotation=(1.5708, 0.0, 1.5708),
        ),
        _child(
            part, "fork", shape="box",
            size=(w * 0.25, d * 0.8, h * 0.55),
            location=(x, y, z + h * 0.35),
        ),
    ]


def _bracket(part: PropPart) -> list[PropPart]:
    w, d, h = part.size
    x, y, z = part.location
    t = min(w, d, h) * 0.22
    return [
        _child(
            part, "vert", shape="box",
            size=(t, d, h),
            location=(x - w * 0.4, y, z),
        ),
        _child(
            part, "horiz", shape="box",
            size=(w, d, t),
            location=(x, y, z - h * 0.4),
        ),
    ]


def _trim(part: PropPart) -> list[PropPart]:
    slim = (
        part.size[0],
        part.size[1],
        max(part.size[2] * 0.35, 0.004),
    )
    return [
        _child(
            part, "strip", shape="box",
            size=slim,
            location=part.location,
        ),
    ]
