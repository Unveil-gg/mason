"""Assemble mason inspect --json for an existing job."""

from __future__ import annotations

from typing import Any

from mason.core.jobs import AssetJob
from mason.core.results import SLIM_METRICS_KEYS
from mason.core.styles import QualityGuidance, StyleProfile, load_style
from mason.core.preview_roles import preview_roles_for
from mason.pipelines.checkpoint import checkpoint_status
from mason.pipelines.compare import reference_iou, silhouette_regressed


def inspect_payload(job: AssetJob, *, full: bool = False) -> dict[str, Any]:
    """Return the agent context payload for one job."""
    spec = job.load_spec()
    result = job.load_result()
    report = job.load_validation()
    meta = job.load_meta()
    style = _load_job_style(job)
    direction = spec.art_direction
    usage = direction.usage if direction else None
    quality = _quality_for(style, usage.importance if usage else None)
    latest_iter = meta.iteration if meta else 0
    latest_eval = (
        job.load_evaluation(latest_iter) if latest_iter else None
    )
    evaluations = []
    for number, path in job.list_evaluations():
        record = job.load_evaluation(number)
        evaluations.append({
            "iteration": number,
            "path": job.rel(path),
            "ship": record.ship if record else None,
            "passed": record.passed if record else None,
        })
    payload = {
        "asset_id": spec.id,
        "name": spec.name,
        "type": spec.type,
        "style": spec.style,
        "source_spec": meta.source_spec if meta else None,
        "tool": result.tool if result else None,
        "tool_version": result.tool_version if result else None,
        "outputs": result.outputs if result else {},
        "previews": result.previews if result else {},
        "validation": _slim_validation(report),
        "built_at": result.built_at if result else None,
        "art_direction": (
            {
                "subject": direction.subject,
                "usage": direction.usage.model_dump(mode="json"),
                "detail_density": direction.detail_density,
            } if direction else None
        ),
        "depends_on": list(spec.depends_on),
        "iteration": latest_iter,
        "current_best": meta.current_best if meta else None,
        "checkpoint": checkpoint_status(job),
        "evaluation": (
            latest_eval.model_dump(mode="json") if latest_eval else None
        ),
        "evaluations": evaluations,
        "compare": _compare_path(job, result),
        "silhouette_regressed": _silhouette_regressed(job),
        "preview_roles": preview_roles_for(spec.type),
    }
    if spec.geometric_plan:
        payload["stage"] = spec.geometric_plan.stage
        payload["recognition"] = spec.geometric_plan.recognition
    iou = _silhouette_iou(job)
    if iou is not None:
        payload["silhouette_iou"] = iou
    if full:
        payload["validation"] = (
            _full_validation(report) if report else None
        )
        payload["spec"] = spec.model_dump(mode="json", exclude_none=True)
        payload["construction_plan"] = (
            spec.construction_plan.model_dump(mode="json")
            if spec.construction_plan else None
        )
        payload["geometric_plan"] = (
            spec.geometric_plan.model_dump(mode="json")
            if spec.geometric_plan else None
        )
        payload["art_analysis"] = (
            spec.art_analysis.model_dump(mode="json")
            if spec.art_analysis else None
        )
        payload["references"] = (
            [ref.model_dump(mode="json") for ref in direction.references]
            if direction else []
        )
        payload["usage"] = usage.model_dump(mode="json") if usage else None
        payload["detail_density"] = (
            direction.detail_density if direction else None
        )
        payload["quality"] = (
            quality.model_dump(mode="json") if quality else None
        )
        payload["art_direction"] = (
            direction.model_dump(mode="json") if direction else None
        )
    return payload


def _slim_validation(report) -> dict[str, Any] | None:
    if report is None:
        return None
    metrics = dict(report.metrics)
    metrics.pop("objects", None)
    return {
        "passed": report.passed,
        "failed_checks": [
            c.name for c in report.checks if not c.passed
        ],
        **{
            key: metrics[key]
            for key in SLIM_METRICS_KEYS if key in metrics
        },
    }


def _full_validation(report) -> dict[str, Any]:
    data = report.model_dump()
    metrics = dict(data.get("metrics") or {})
    metrics.pop("objects", None)
    data["metrics"] = metrics
    return data


def _load_job_style(job: AssetJob) -> StyleProfile | None:
    if job.style_yaml.is_file():
        return load_style(job.style_yaml)
    return None


def _quality_for(
    style: StyleProfile | None,
    importance: str | None,
) -> QualityGuidance | None:
    if style is None or not importance:
        return None
    return style.quality.get(importance)


def _compare_path(job: AssetJob, result) -> str | None:
    path = job.previews / "compare.png"
    if path.is_file():
        return job.rel(path)
    if result and result.previews.get("compare"):
        return result.previews["compare"]
    return None


def _silhouette_regressed(job: AssetJob) -> bool:
    return silhouette_regressed(job)


def _silhouette_iou(job: AssetJob) -> float | None:
    return reference_iou(job)
