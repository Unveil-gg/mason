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


_POSE_ALIASES = {
    "stand": "neutral",
    "walk": "arms_forward",
    "sit": "crouch",
    "reach": "arms_spread",
}
_POSE_PEN_LIMIT = 0.25


def _garment_pipeline(spec: StaticPropSpec) -> str:
    """stylized second-skin (default) or later drape."""
    garment = spec.geometry.garment
    if garment is None:
        return "stylized"
    raw = getattr(garment, "pipeline", "stylized") or "stylized"
    return "drape" if raw == "drape" else "stylized"


def _pose_tests_ok(fit: dict) -> tuple[bool, str]:
    """Fail obvious clipping on stand/walk/sit/reach poses."""
    scores = fit.get("pose_scores") or {}
    if not scores:
        return True, "no pose_scores"
    failed: list[str] = []
    for alias, canonical in _POSE_ALIASES.items():
        row = scores.get(alias) or scores.get(canonical) or {}
        pen = float(row.get("penetration") or 0.0)
        if pen > _POSE_PEN_LIMIT:
            failed.append(f"{alias}={pen:.3f}")
    return (not failed, ",".join(failed) if failed else "ok")


def validate_static_prop(
    job: AssetJob,
    spec: StaticPropSpec,
    exit_code: int,
    touch: tuple[bool, str] | None = None,
    facade: tuple[bool, str] | None = None,
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
    if spec.geometry.garment:
        worn = job.previews / "worn.png"
        worn_ok = worn.is_file() and worn.stat().st_size > 0
        if worn_ok:
            try:
                with Image.open(worn) as img:
                    img.verify()
            except OSError:
                worn_ok = False
        checks.append(_check(
            "preview_worn", worn_ok, None if worn_ok else "missing",
        ))
        sheet_w = job.previews / "worn_sheet.png"
        sheet_ok = sheet_w.is_file() and sheet_w.stat().st_size > 0
        checks.append(_check(
            "preview_worn_sheet",
            sheet_ok,
            None if sheet_ok else "missing",
        ))
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
        if data.get("attachments"):
            metrics["attachments"] = data["attachments"]
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

    if spec.geometry.garment:
        fit = data.get("fit") or {}
        pen = float(fit.get("penetration") or 0.0)
        gap = float(fit.get("clearance_min") or 0.0)
        neck = float(fit.get("opening_neck") or 0.0)
        cuffs = float(fit.get("opening_cuffs") or 0.0)
        sleeves = fit.get("sleeves") or {}
        ratios = [
            float((sleeves.get(s) or {}).get("ratio") or 0.0)
            for s in ("l", "r")
        ]
        alongs = [
            float((sleeves.get(s) or {}).get("along") or 0.0)
            for s in ("l", "r")
        ]
        fats = [
            float((sleeves.get(s) or {}).get("fat") or 0.0)
            for s in ("l", "r")
        ]
        flaps = [
            int((sleeves.get(s) or {}).get("off_axis") or 0)
            for s in ("l", "r")
        ]
        off_maxs = [
            float((sleeves.get(s) or {}).get("off_max") or 0.0)
            for s in ("l", "r")
        ]
        side_spans = [
            float((sleeves.get(s) or {}).get("side_span") or 0.0)
            for s in ("l", "r")
        ]
        wide = [r for r in ratios if r > 2.2]
        baggy = [f for f in fats if f > 2.4]
        flare = float(fit.get("underarm_flare") or 0.0)
        brim = float(fit.get("neck_brim") or 0.0)
        asym = float(fit.get("sleeve_asymmetry") or 0.0)
        clips = fit.get("clip_regions") or {}
        want_btn = "buttons" in (
            spec.geometry.garment.details
            + spec.geometry.garment.surface_details
        )
        n_btn = int(fit.get("buttons") or 0)
        stylized = _garment_pipeline(spec) == "stylized"
        ok = pen < 0.12 and gap > -0.008
        if not stylized:
            ok = ok and neck > 0.008
        body_h = float(fit.get("body_height") or 0.0)
        cuff_cap = body_h * 0.42 if body_h > 1e-6 else 0.05
        tubes = fit.get("sleeve_tubes") or []
        tube_ok = (
            len(tubes) >= 2
            and all(float(t.get("length") or 0) > body_h * 0.06 for t in tubes)
        ) if body_h > 1e-6 else len(tubes) >= 2
        flap_cap = body_h * 0.12 if body_h > 1e-6 else 0.02
        span_cap = body_h * 0.14 if body_h > 1e-6 else 0.05
        if (
            spec.geometry.garment.sleeve in ("short", "long")
            and not stylized
        ):
            ok = ok and cuffs > 0.005 and cuffs < cuff_cap
            ok = ok and not wide and not baggy
            ok = ok and all(a > 0.16 for a in alongs)
            ok = ok and flare < 1.65
            ok = ok and tube_ok
            ok = ok and all(o <= flap_cap for o in off_maxs)
            ok = ok and all(s <= span_cap for s in side_spans)
            ok = ok and max(flaps) <= 24
            ok = ok and asym < 0.35
        ok = ok and brim < (5.5 if stylized else 1.75)
        if (
            spec.geometry.garment.sleeve == "long"
            and not stylized
        ):
            ok = ok and all(a > 0.70 for a in alongs)
        if want_btn:
            ok = ok and n_btn >= 3
        clip_s = ",".join(
            f"{k}:{v.get('count', 0)}" for k, v in sorted(clips.items())
        )
        checks.append(_check(
            "garment_fit",
            ok,
            (
                f"pen={pen:.3f} gap={gap:.4f} neck={neck:.3f} "
                f"cuffs={cuffs:.3f} sleeve={ratios} along={alongs} "
                f"fat={fats} flare={flare:.2f} brim={brim:.2f} "
                f"flap={flaps} off={off_maxs} span={side_spans} "
                f"asym={asym:.2f} buttons={n_btn} "
                f"tubes={len(tubes)} clip={clip_s or 'none'}"
            ),
        ))
        pose_ok, pose_detail = _pose_tests_ok(fit)
        checks.append(_check("garment_poses", pose_ok, pose_detail))
        if fit:
            metrics["fit"] = fit
    else:
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
        if facade is not None:
            checks.append(_check("facade_fit", facade[0], facade[1]))
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
