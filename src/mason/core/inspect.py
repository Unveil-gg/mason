"""Assemble mason inspect --json for an existing job."""

from __future__ import annotations

from typing import Any

from mason.core.jobs import AssetJob
from mason.core.styles import QualityGuidance, StyleProfile, load_style


def inspect_payload(job: AssetJob) -> dict[str, Any]:
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
    return {
        "asset_id": spec.id,
        "name": spec.name,
        "type": spec.type,
        "style": spec.style,
        "source_spec": meta.source_spec if meta else None,
        "tool": result.tool if result else None,
        "tool_version": result.tool_version if result else None,
        "outputs": result.outputs if result else {},
        "previews": result.previews if result else {},
        "validation": report.model_dump() if report else None,
        "built_at": result.built_at if result else None,
        "spec": spec.model_dump(mode="json", exclude_none=True),
        "art_direction": (
            direction.model_dump(mode="json") if direction else None
        ),
        "construction_plan": (
            spec.construction_plan.model_dump(mode="json")
            if spec.construction_plan else None
        ),
        "art_analysis": (
            spec.art_analysis.model_dump(mode="json")
            if spec.art_analysis else None
        ),
        "references": (
            [ref.model_dump(mode="json") for ref in direction.references]
            if direction else []
        ),
        "depends_on": list(spec.depends_on),
        "usage": usage.model_dump(mode="json") if usage else None,
        "detail_density": direction.detail_density if direction else None,
        "quality": quality.model_dump(mode="json") if quality else None,
        "iteration": latest_iter,
        "evaluation": (
            latest_eval.model_dump(mode="json") if latest_eval else None
        ),
        "evaluations": evaluations,
    }


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
