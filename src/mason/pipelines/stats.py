"""Triangle and mesh counts from stored job metadata."""

from __future__ import annotations

from typing import Any

from mason.core.jobs import AssetJob, list_jobs, require_job
from mason.core.workspace import find_project_root
from mason.errors import MasonError


def run_stats(asset_id: str | None = None) -> dict[str, Any]:
    """Return poly counts for one job, or every job with metrics."""
    root = find_project_root()
    if asset_id:
        return job_stats(require_job(root, asset_id))
    assets = []
    for job in list_jobs(root):
        try:
            assets.append(job_stats(job))
        except MasonError:
            continue
    return {"assets": assets}


def job_stats(job: AssetJob) -> dict[str, Any]:
    """Read triangles/meshes/materials from a built job."""
    spec = job.load_spec()
    report = job.load_validation()
    metrics = dict(report.metrics) if report else {}
    result = job.load_result()
    validation = result.validation if result else {}
    triangles = metrics.get("triangles")
    if triangles is None:
        triangles = validation.get("triangles")
    if triangles is None:
        raise MasonError(
            f"No triangle count for '{job.asset_id}'.",
            code="no_stats",
            hint="Build a static_prop first.",
            context={"asset_id": job.asset_id},
        )
    return {
        "asset_id": job.asset_id,
        "type": spec.type,
        "triangles": int(triangles),
        "meshes": int(
            metrics.get("mesh_count")
            or validation.get("mesh_count")
            or 0
        ),
        "materials": int(
            metrics.get("materials")
            or validation.get("materials")
            or 0
        ),
    }
