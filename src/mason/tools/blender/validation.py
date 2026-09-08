"""Validate Blender job outputs and metadata."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from mason.core.assets import StaticPropSpec
from mason.core.jobs import AssetJob
from mason.core.results import ValidationCheck, ValidationReport
from mason.generators.blender.snap import parents_touch_bounds
from mason.tools.blender.preview import ALL_PREVIEW_FILES


def _check(name: str, passed: bool, detail: str | None = None) -> ValidationCheck:
    return ValidationCheck(name=name, passed=passed, detail=detail)


def validate_static_prop(
    job: AssetJob,
    spec: StaticPropSpec,
    exit_code: int,
    touch: tuple[bool, str] | None = None,
) -> ValidationReport:
    """Run deterministic checks on a static_prop job."""
    checks: list[ValidationCheck] = []
    metrics: dict = {}
    checks.append(_check("exit_code", exit_code == 0, str(exit_code)))

    glb = job.output / "asset.glb"
    checks.append(_check("glb_exists", glb.is_file() and glb.stat().st_size > 0))
    if spec.export.save_blend:
        blend = job.output / "asset.blend"
        checks.append(
            _check("blend_exists", blend.is_file() and blend.stat().st_size > 0),
        )

    for view in ALL_PREVIEW_FILES:
        path = job.previews / f"{view}.png"
        ok = False
        detail = "missing"
        if path.is_file() and path.stat().st_size > 0:
            try:
                with Image.open(path) as img:
                    img.verify()
                ok = True
                detail = None
            except OSError as exc:
                detail = str(exc)
        checks.append(_check(f"preview_{view}", ok, detail))
    sheet = job.previews / "contact_sheet.png"
    if sheet.is_file() and sheet.stat().st_size > 0:
        checks.append(_check("preview_contact_sheet", True))
    else:
        checks.append(_check("preview_contact_sheet", False, "missing"))

    meta_path = job.output / "metadata.json"
    bounds = None
    data: dict = {}
    if meta_path.is_file():
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        metrics["triangles"] = data.get("triangles")
        metrics["materials"] = data.get("material_count")
        metrics["mesh_count"] = data.get("mesh_count")
        metrics["objects"] = data.get("objects")
        checks.append(_check(
            "mesh_count",
            int(data.get("mesh_count") or 0) > 0,
        ))
        checks.append(_check(
            "object_names",
            bool(data.get("objects")),
        ))
        scales = data.get("scales") or {}
        sensible = all(
            all(0.001 <= abs(v) <= 1000 for v in scale)
            for scale in scales.values()
        ) if scales else True
        checks.append(_check("scale_sensible", sensible))
        bounds = data.get("bounds")
        if data.get("preview_engine"):
            metrics["preview_engine"] = data["preview_engine"]
        if data.get("object_bounds"):
            metrics["object_bounds_count"] = len(data["object_bounds"])
    else:
        checks.append(_check("metadata", False, "metadata.json missing"))

    if bounds:
        dims = spec.dimensions
        expected = {"x": dims.width, "y": dims.depth, "z": dims.height}
        ok = True
        detail_parts = []
        for axis, want in expected.items():
            got = float(bounds.get(axis) or 0)
            if got <= 0 or not _near(got, want):
                ok = False
            detail_parts.append(f"{axis}={got:.4f}/{want:.4f}")
        checks.append(_check("dimensions", ok, ", ".join(detail_parts)))
        metrics["bounds"] = bounds

    snap_ok, snap_detail = touch if touch else (True, "ok")
    parent_ok, parent_detail = True, "ok"
    if data.get("object_bounds"):
        parent_ok, parent_detail = parents_touch_bounds(
            spec.geometry.parts,
            data["object_bounds"],
            bodies=spec.geometry.bodies,
        )
    touch_ok = snap_ok and parent_ok
    if not snap_ok:
        touch_detail = snap_detail
    elif not parent_ok:
        touch_detail = parent_detail
    else:
        touch_detail = "ok"
    checks.append(_check("parts_touch", touch_ok, touch_detail))
    if spec.geometry.bodies:
        from mason.pipelines.continuity import preview_continuity
        for name in (
            "silhouette_side",
            "silhouette_front",
            "silhouette_three_quarter",
        ):
            path = job.previews / f"{name}.png"
            if not path.is_file():
                continue
            solid = preview_continuity(path)
            checks.append(_check(
                f"solid_{name}",
                solid["holes"] == 0,
                (
                    f"holes={solid['holes']} "
                    f"islands={solid['islands']}"
                ),
            ))

    return ValidationReport(
        passed=all(c.passed for c in checks),
        checks=checks,
        metrics=metrics,
    )


def _near(got: float, want: float, rel: float = 0.10, abs_tol: float = 0.05) -> bool:
    return abs(got - want) <= max(abs_tol, abs(want) * rel)
