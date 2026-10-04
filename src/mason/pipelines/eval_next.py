"""Action packet a critic evaluation hands to the next edit."""

from __future__ import annotations

import json

from mason.core.art import CorrectionTarget, VisualEvaluation
from mason.core.jobs import AssetJob
from mason.pipelines.silhouette import load_metrics


def next_packet(job: AssetJob, evaluation: VisualEvaluation) -> dict:
    """Failure, targets, unresolved names, preview, and measures.

    job: asset job holding the spec, validation, and previews.
    evaluation: stored critic record for one iteration.
    Returns the packet. Unresolved names are advisory.
    """
    landmarks, parts, layers = _controls(job)
    targets = [
        target.model_dump(mode="json")
        for target in evaluation.correction_targets
    ]
    unresolved = _unresolved_names(
        evaluation.correction_targets, landmarks, parts, layers,
    )
    iteration = evaluation.iteration or 1
    best = None
    verdict = None
    if evaluation.compare:
        verdict = evaluation.compare.verdict
        best = evaluation.compare.best_iteration
    return {
        "primary_failure": evaluation.primary_failure,
        "correction_targets": targets,
        "unresolved": unresolved,
        "verdict": verdict,
        "primary_preview": iteration_preview(job, iteration),
        "measured": _measured(job, iteration, best),
    }


def iteration_preview(job: AssetJob, iteration: int) -> str | None:
    """Primary preview path for one snapshot."""
    result = job.load_result()
    primary_key = "full"
    if result and result.preview_roles.get("primary"):
        primary_key = result.preview_roles["primary"]
    snap = job.iterations / f"{iteration:03d}" / "previews"
    previews = {}
    if snap.is_dir():
        for png in sorted(snap.glob("*.png")):
            previews[png.stem] = job.rel(png)
    return primary_preview(previews, primary_key)


def primary_preview(
    previews: dict[str, str],
    primary_key: str,
) -> str | None:
    """Pick the preview path a summary row should open."""
    if primary_key in previews:
        return previews[primary_key]
    for key in ("three_quarter", "full", "front"):
        if key in previews:
            return previews[key]
    if previews:
        return next(iter(previews.values()))
    return None


def _controls(job: AssetJob) -> tuple[set[str], set[str], set[str]]:
    """Landmark ids, part names, and layer names on the live spec."""
    spec = job.load_spec()
    landmarks: set[str] = set()
    parts: set[str] = set()
    layers: set[str] = set()
    plan = spec.geometric_plan
    if plan:
        for mark in plan.landmarks:
            landmarks.add(mark.id)
            if mark.part:
                parts.add(mark.part)
    geom = getattr(spec, "geometry", None)
    if geom is not None:
        for part in geom.parts or []:
            parts.add(part.name)
        for body in geom.bodies or []:
            parts.add(body.name)
    for layer in getattr(spec, "layers", None) or []:
        layers.add(layer.name)
    for anim in getattr(spec, "animations", None) or []:
        for frame in anim.frames:
            for layer in frame.layers:
                layers.add(layer.name)
    return landmarks, parts, layers


def _unresolved_names(
    targets: list[CorrectionTarget],
    landmarks: set[str],
    parts: set[str],
    layers: set[str],
) -> list[str]:
    """Names on targets that are not a landmark, part, or layer."""
    known = parts | layers | landmarks
    missing: list[str] = []
    for target in targets:
        if target.part and target.part not in known:
            missing.append(target.part)
        if target.landmark and target.landmark not in landmarks:
            missing.append(target.landmark)
        if not target.part and not target.landmark:
            missing.append(target.param or "unnamed")
    return missing


def _measured(
    job: AssetJob,
    iteration: int,
    best: int | None,
) -> dict:
    """Validation and silhouette IoU already stored on the job."""
    measured: dict = {}
    passed = _validation_passed(job, iteration)
    if passed is not None:
        measured["validation_passed"] = passed
    cand = _iou_value(job, iteration)
    if cand is not None:
        measured["silhouette_iou"] = cand
    if best and best != iteration:
        prior = _iou_value(job, best)
        if cand is not None and prior is not None:
            measured["silhouette_iou_delta"] = round(cand - prior, 4)
    return measured


def _validation_passed(job: AssetJob, iteration: int) -> bool | None:
    """Return validation.passed for a snapshot, or None."""
    path = job.iterations / f"{iteration:03d}" / "validation.json"
    if not path.is_file():
        meta = job.load_meta()
        current = meta.iteration if meta and meta.iteration else None
        if current == iteration:
            path = job.validation_json
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if "passed" not in data:
        return None
    return bool(data["passed"])


def _iou_value(job: AssetJob, iteration: int) -> float | None:
    """Minimum silhouette IoU for a snapshot, or None."""
    metrics = load_metrics(job, iteration)
    if not metrics or metrics.get("iou") is None:
        return None
    return float(metrics["iou"])
