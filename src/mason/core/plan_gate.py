"""Art-direction completeness critic. Does not generate geometry."""

from __future__ import annotations

from typing import Any

from mason.core.assets import AssetSpec
from mason.core.workflow import infer_workflow


def plan_payload(spec: AssetSpec) -> dict[str, Any]:
    """Return missing required fields for the declared workflow."""
    workflow = infer_workflow(
        (spec.art_direction.subject if spec.art_direction else "")
        or spec.name,
        spec,
    )
    missing = _missing_for(spec, workflow)
    return {
        "asset_id": spec.id,
        "workflow": workflow,
        "passed": not missing,
        "missing": missing,
    }


def _missing_for(spec: AssetSpec, workflow: str) -> list[str]:
    direction = spec.art_direction
    missing: list[str] = []
    if direction is None or not (direction.subject or "").strip():
        missing.append("art_direction.subject")
    if workflow == "turned":
        missing.extend(_need_silhouette(direction, "side"))
    if workflow in ("clothing_fitted", "clothing_loose"):
        garment = getattr(getattr(spec, "geometry", None), "garment", None)
        if garment is None:
            missing.append("geometry.garment")
        elif garment.body is None:
            missing.append("geometry.garment.body")
        if garment is not None and not garment.fit:
            missing.append("geometry.garment.fit")
    if workflow == "pixel":
        if not getattr(spec, "canvas", None):
            missing.append("canvas")
        if direction is None or not direction.focal_point:
            missing.append("art_direction.focal_point")
        anims = getattr(spec, "animations", None) or []
        master = getattr(spec, "master_frame", None)
        if len(anims) > 1 and not master:
            missing.append("master_frame")
    if workflow in ("illustrated", "texture"):
        if direction is None or not direction.focal_point:
            missing.append("art_direction.focal_point")
        if direction is None or not direction.value_hierarchy:
            missing.append("art_direction.value_hierarchy")
        dims = getattr(spec, "dimensions", None) or getattr(
            spec, "canvas", None,
        )
        if dims is None:
            missing.append("dimensions")
    if workflow in ("sculptural", "building"):
        plan = spec.geometric_plan
        masses = [
            row for row in (plan.masses if plan else [])
            if row.role == "primary"
        ]
        if len(masses) > 2 and spec.decomposition is None:
            missing.append("decomposition")
    if direction and not direction.focal_point and workflow in (
        "character", "clothing_fitted", "clothing_loose",
    ):
        missing.append("art_direction.focal_point")
    if direction and not direction.gameplay.must_read and workflow in (
        "character", "clothing_fitted",
    ):
        missing.append("art_direction.gameplay.must_read")
    return missing


def _need_silhouette(direction, view: str) -> list[str]:
    if direction is None or not direction.silhouette:
        return ["art_direction.silhouette"]
    refs = direction.references or []
    if not any(
        row.view == view or row.purpose == "silhouette" for row in refs
    ):
        return [f"art_direction.references[{view}]"]
    return []
