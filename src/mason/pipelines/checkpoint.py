"""Best-so-far checkpoints and cross-view regression checks."""

from __future__ import annotations

from pathlib import Path

from mason.core.art import CompareToBest, VisualEvaluation
from mason.core.assets import dump_asset_spec, load_asset_spec
from mason.core.form_plan import GeometricPlan, ViewWeight
from mason.core.jobs import AssetJob
from mason.errors import MasonError
from mason.pipelines.silhouette import iou_regressed, load_metrics

CRITICAL_DROP = 2
IMPROVE_DELTA = 1
IDENTITY_KEYS = ("target_identity", "primary_silhouette")
_SIDECARS = (
    "asset.yaml",
    "art_direction.yaml",
    "construction_plan.yaml",
    "geometric_plan.yaml",
    "art_analysis.yaml",
    "reference_analysis.yaml",
    "decomposition.yaml",
    "validation.json",
    "result.json",
    "silhouette_metrics.json",
)


def default_critical_views(recognition: str) -> list[ViewWeight]:
    """Views that matter most when the plan omits critical_views."""
    if recognition == "silhouette":
        return [
            ViewWeight(view="silhouette_side", weight=3.0),
            ViewWeight(view="side", weight=2.0),
            ViewWeight(view="silhouette_front", weight=1.0),
            ViewWeight(view="three_quarter", weight=1.0),
        ]
    if recognition == "proportion":
        return [
            ViewWeight(view="front", weight=2.0),
            ViewWeight(view="side", weight=2.0),
            ViewWeight(view="three_quarter", weight=1.5),
        ]
    return [
        ViewWeight(view="three_quarter", weight=2.0),
        ViewWeight(view="side", weight=1.0),
        ViewWeight(view="front", weight=1.0),
    ]


def critical_views_for(plan: GeometricPlan | None) -> list[ViewWeight]:
    """Plan-named views, or defaults from recognition."""
    if plan and plan.critical_views:
        return list(plan.critical_views)
    recognition = plan.recognition if plan else "mixed"
    return default_critical_views(recognition)


def view_score_map(evaluation: VisualEvaluation) -> dict[str, int]:
    """Map view name to score."""
    return {row.view: row.score for row in evaluation.view_scores}


def identity_regressed(
    candidate: VisualEvaluation,
    best: VisualEvaluation,
) -> list[str]:
    """Identity scores that fell versus current_best."""
    dropped: list[str] = []
    for key in IDENTITY_KEYS:
        cand = getattr(candidate.scores, key)
        prior = getattr(best.scores, key)
        if cand is None or prior is None:
            continue
        if cand < prior:
            dropped.append(key)
    return dropped


def critical_view_regressed(
    candidate: VisualEvaluation,
    best: VisualEvaluation,
    views: list[ViewWeight],
    *,
    drop: int = CRITICAL_DROP,
) -> list[str]:
    """Critical views where candidate fell by `drop` or more."""
    cmap = view_score_map(candidate)
    bmap = view_score_map(best)
    dropped: list[str] = []
    for view in views:
        if view.view not in cmap or view.view not in bmap:
            continue
        if cmap[view.view] <= bmap[view.view] - drop:
            dropped.append(view.view)
    return dropped


def weighted_view_score(
    evaluation: VisualEvaluation,
    views: list[ViewWeight],
) -> float | None:
    """Weight-average of overlapping view scores, or None."""
    scores = view_score_map(evaluation)
    total = 0.0
    weight = 0.0
    for view in views:
        if view.view not in scores:
            continue
        total += scores[view.view] * view.weight
        weight += view.weight
    if weight <= 0:
        return None
    return total / weight


def primary_metric(
    evaluation: VisualEvaluation,
    views: list[ViewWeight],
) -> float | None:
    """Single number used when the critic omits a verdict."""
    weighted = weighted_view_score(evaluation, views)
    if weighted is not None:
        return weighted
    scores = evaluation.scores
    for key in (
        "target_identity",
        "primary_silhouette",
        "overall_visual_quality",
        "silhouette",
    ):
        value = getattr(scores, key)
        if value is not None:
            return float(value)
    return None


def apply_checkpoint(
    job: AssetJob,
    evaluation: VisualEvaluation,
) -> dict:
    """Promote or keep current_best. Newest is never auto-best."""
    meta = job.load_meta()
    candidate = evaluation.iteration or (meta.iteration if meta else 1)
    best_n = meta.current_best if meta else None
    plan = None
    try:
        plan = job.load_spec().geometric_plan
    except Exception:
        plan = None
    views = critical_views_for(plan)
    best_eval = job.load_evaluation(best_n) if best_n else None
    dropped = []
    if best_eval is not None:
        dropped = critical_view_regressed(evaluation, best_eval, views)
        dropped.extend(identity_regressed(evaluation, best_eval))
    compare = evaluation.compare
    verdict = compare.verdict if compare else None
    reason = compare.reason if compare else ""
    if evaluation.represents_object is False:
        verdict = "reject"
        why = "does not represent the object"
        reason = f"{why}. {reason}" if reason else why
    critical = [
        row for row in evaluation.discrepancies if row.rank == "critical"
    ]
    if evaluation.ship and critical:
        evaluation.ship = False
        verdict = "reject"
        why = "ship blocked: critical discrepancies remain"
        reason = f"{why}. {reason}" if reason else why
    lock_hits = _locked_region_hits(job, evaluation)
    if lock_hits:
        verdict = "reject"
        why = "locked region(s) changed: " + ", ".join(lock_hits)
        reason = f"{why}. {reason}" if reason else why
    iou_dropped = []
    if best_n and best_n != candidate:
        iou_dropped = iou_regressed(
            load_metrics(job, candidate),
            load_metrics(job, best_n),
            [row.view for row in views],
        )
        dropped = list(dict.fromkeys([*dropped, *iou_dropped]))
    if dropped:
        verdict = "reject"
        names = ", ".join(dropped)
        auto = f"critical view(s) dropped: {names}"
        reason = f"{auto}. {reason}" if reason else auto
    elif verdict is None:
        if best_n is None or best_eval is None:
            verdict = "accept"
            reason = reason or "first checkpoint"
        else:
            cand_m = primary_metric(evaluation, views)
            best_m = primary_metric(best_eval, views)
            if (
                cand_m is not None
                and best_m is not None
                and cand_m >= best_m + IMPROVE_DELTA
            ):
                verdict = "accept"
                reason = reason or "meaningfully better than current_best"
            else:
                verdict = "reject"
                reason = reason or "not better than current_best"
    accepted = verdict == "accept"
    new_best = candidate if accepted else best_n
    preserved = not bool(lock_hits)
    if accepted:
        job.set_current_best(candidate)
        if evaluation.approved:
            from mason.core.approvals import merge_approved
            merge_approved(job, evaluation.approved, candidate)
        _record_first_accept(job, evaluation, candidate, preserved)
    compared = evaluation.compare or CompareToBest()
    compared.verdict = verdict
    compared.reason = reason
    if compared.best_iteration is None:
        compared.best_iteration = best_n
    evaluation.compare = compared
    job.write_evaluation(evaluation)
    return {
        "current_best": new_best,
        "candidate": candidate,
        "accepted": accepted,
        "verdict": verdict,
        "reason": reason,
        "regressed_views": dropped,
        "critical_views": [row.view for row in views],
        "approved_preserved": preserved,
        "locked_changed": lock_hits,
    }


def checkpoint_status(job: AssetJob) -> dict:
    """Inspect-facing checkpoint fields."""
    meta = job.load_meta()
    current_best = meta.current_best if meta else None
    iteration = meta.iteration if meta else None
    latest = job.load_evaluation(iteration) if iteration else None
    compare = latest.compare if latest else None
    return {
        "current_best": current_best,
        "iteration": iteration,
        "accepted": (
            current_best == iteration if current_best and iteration else None
        ),
        "verdict": compare.verdict if compare else None,
        "reason": compare.reason if compare else "",
    }


def restore_checkpoint(
    job: AssetJob,
    iteration: int | None = None,
) -> dict:
    """Copy a snapshot back to the job and source spec."""
    meta = job.load_meta()
    target = iteration
    if target is None:
        target = meta.current_best if meta else None
    if not target:
        raise MasonError(
            "No current_best checkpoint to restore.",
            code="no_checkpoint",
            hint="Evaluate a passing candidate or mason checkpoint.",
        )
    snap = job.iterations / f"{target:03d}"
    spec_path = snap / "asset.yaml"
    if not spec_path.is_file():
        raise MasonError(
            f"No snapshot for iteration {target:03d}.",
            code="snapshot_not_found",
            context={"iteration": target},
        )
    live = None
    if meta and meta.source_spec:
        src = job.project_root / meta.source_spec
        if src.is_file():
            try:
                live = load_asset_spec(src)
            except MasonError:
                live = None
    spec = load_asset_spec(spec_path)
    if live is not None:
        if spec.geometric_plan is None and live.geometric_plan:
            spec.geometric_plan = live.geometric_plan
        if spec.construction_plan is None and live.construction_plan:
            spec.construction_plan = live.construction_plan
        if spec.art_direction is None and live.art_direction:
            spec.art_direction = live.art_direction
        if spec.decomposition is None and live.decomposition:
            spec.decomposition = live.decomposition
    job.write_spec(spec)
    job.write_art_sidecars(spec)
    for name in _SIDECARS:
        if name == "asset.yaml":
            continue
        src = snap / name
        dest = job.dir / name
        if src.is_file():
            dest.write_bytes(src.read_bytes())
    _copy_previews(snap / "previews", job.previews)
    outputs_restored = _copy_dir(snap / "output", job.output)
    source_spec = None
    if meta and meta.source_spec:
        dest = job.project_root / meta.source_spec
        dest.parent.mkdir(parents=True, exist_ok=True)
        dump_asset_spec(spec, dest)
        source_spec = meta.source_spec
    return {
        "restored": target,
        "source_spec": source_spec,
        "current_best": meta.current_best if meta else target,
        "outputs_restored": outputs_restored,
    }


def promote_checkpoint(job: AssetJob, iteration: int | None = None) -> dict:
    """Mark an existing snapshot as current_best without evaluating."""
    meta = job.load_meta()
    target = iteration if iteration is not None else (
        meta.iteration if meta else None
    )
    if not target:
        raise MasonError(
            "No iteration to promote.",
            code="no_checkpoint",
        )
    snap = job.iterations / f"{target:03d}" / "asset.yaml"
    if not snap.is_file():
        raise MasonError(
            f"No snapshot for iteration {target:03d}.",
            code="snapshot_not_found",
            context={"iteration": target},
        )
    job.set_current_best(target)
    return {
        "current_best": target,
        "candidate": target,
        "accepted": True,
        "verdict": "accept",
        "reason": "manual checkpoint",
    }


def restart_parts(
    job: AssetJob,
    *,
    keep: list[str],
    rebuild: list[str],
) -> dict:
    """Copy keep names from current_best; drop rebuild names.

    Supports static_prop parts, garment fields, and raster layers.
    """
    meta = job.load_meta()
    best = meta.current_best if meta else None
    if not best:
        raise MasonError(
            "No current_best to restart from.",
            code="no_checkpoint",
        )
    snap = job.iterations / f"{best:03d}" / "asset.yaml"
    if not snap.is_file():
        raise MasonError(
            f"No snapshot for iteration {best:03d}.",
            code="snapshot_not_found",
        )
    best_spec = load_asset_spec(snap)
    live = job.load_spec()
    keep_set = set(keep)
    rebuild_set = set(rebuild)
    kept: list[str] = []
    if live.type == "layered_raster" and best_spec.type == "layered_raster":
        kept_layers = [p for p in best_spec.layers if p.name in keep_set]
        others = [
            p for p in live.layers
            if p.name not in keep_set and p.name not in rebuild_set
        ]
        live.layers = kept_layers + others
        kept = [p.name for p in kept_layers]
    elif live.type == "static_prop" and best_spec.type == "static_prop":
        if live.geometry.garment and best_spec.geometry.garment:
            kept = _restart_garment(
                live, best_spec, keep_set, rebuild_set,
            )
        else:
            kept_parts = [
                p for p in best_spec.geometry.parts if p.name in keep_set
            ]
            others = [
                p for p in live.geometry.parts
                if p.name not in keep_set and p.name not in rebuild_set
            ]
            live.geometry.parts = kept_parts + others
            kept = [p.name for p in kept_parts]
    else:
        raise MasonError(
            "restart applies to static_prop or layered_raster.",
            code="restart_not_supported",
        )
    if live.construction_plan is None:
        from mason.core.art import ConstructionPlan
        live.construction_plan = ConstructionPlan()
    live.construction_plan.keep_parts = list(keep)
    live.construction_plan.rebuild_parts = list(rebuild)
    job.write_spec(live)
    job.write_art_sidecars(live)
    if meta.source_spec:
        dest = job.project_root / meta.source_spec
        dest.parent.mkdir(parents=True, exist_ok=True)
        dump_asset_spec(live, dest)
    return {
        "kept": kept,
        "removed": list(rebuild_set),
        "from_iteration": best,
    }


_GARMENT_FIELDS = frozenset({
    "collar", "cuffs", "hem", "hood", "sleeve", "neck",
    "clearance", "ease_offset", "thickness", "fit",
    "pipeline",
})


def _restart_garment(
    live,
    best_spec,
    keep_set: set[str],
    rebuild_set: set[str],
) -> list[str]:
    """Copy named garment fields from current_best."""
    kept: list[str] = []
    aliases = {"ease_offset": "clearance", "collar": "neck"}
    for name in keep_set:
        field = aliases.get(name, name)
        if field not in _GARMENT_FIELDS and name not in _GARMENT_FIELDS:
            continue
        src = getattr(best_spec.geometry.garment, field, None)
        if src is None:
            continue
        setattr(live.geometry.garment, field, src)
        kept.append(name)
    details = list(best_spec.geometry.garment.details)
    if rebuild_set:
        live.geometry.garment.details = [
            row for row in details if row not in rebuild_set
        ]
    return kept


def _locked_region_hits(
    job: AssetJob,
    evaluation,
) -> list[str]:
    """Locked paths that differ from the current_best snapshot."""
    from mason.core.approvals import (
        load_approvals,
        locked_paths_changed,
    )
    meta = job.load_meta()
    if meta is None or meta.current_best is None:
        return []
    approvals = load_approvals(job)
    if not approvals.locks:
        return []
    snap = job.iterations / f"{meta.current_best:03d}" / "asset.yaml"
    if not snap.is_file():
        return []
    try:
        live = job.load_spec()
        best = load_asset_spec(snap)
    except Exception:
        return []
    return locked_paths_changed(live, best, approvals)


def _record_first_accept(
    job: AssetJob,
    evaluation,
    candidate: int,
    preserved: bool,
) -> None:
    """Write time-to-accept the first time a candidate is promoted."""
    from mason.core.runs import JobRun
    from mason.core.workflow import infer_workflow
    spec = None
    try:
        spec = job.load_spec()
    except Exception:
        spec = None
    workflow = None
    if spec is not None:
        workflow = infer_workflow(
            (spec.art_direction.subject if spec.art_direction else "")
            or spec.name,
            spec,
        )
    time_ms = 0
    for number in job.list_iterations():
        if number > candidate:
            continue
        path = job.iterations / f"{number:03d}" / "run.json"
        if not path.is_file():
            continue
        run = JobRun.model_validate_json(path.read_text(encoding="utf-8"))
        time_ms += int(run.duration_ms or 0)
    job.record_accept_metrics(
        workflow=workflow,
        iterations=candidate,
        time_ms=time_ms,
        visual_reasoning=evaluation.visual_reasoning,
        approved_preserved=preserved,
    )


def _copy_previews(src: Path, dest: Path) -> None:
    _copy_dir(src, dest)


def _copy_dir(src: Path, dest: Path) -> bool:
    if not src.is_dir():
        return False
    dest.mkdir(parents=True, exist_ok=True)
    copied = False
    for path in src.iterdir():
        if path.is_file():
            (dest / path.name).write_bytes(path.read_bytes())
            copied = True
    return copied
