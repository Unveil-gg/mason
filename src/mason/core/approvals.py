"""Approved-region locks so later edits cannot undo accepted work."""

from __future__ import annotations

from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from mason.core.assets import AssetSpec
from mason.core.jobs import AssetJob


class ApprovalLock(BaseModel):
    """One locked part, param, landmark, or quality."""

    model_config = ConfigDict(extra="forbid")

    path: str
    iteration_approved: int
    locked: bool = True


class JobApprovals(BaseModel):
    """Persisted locks for one job."""

    model_config = ConfigDict(extra="forbid")

    locks: list[ApprovalLock] = Field(default_factory=list)


def approvals_path(job: AssetJob):
    return job.dir / "approvals.yaml"


def load_approvals(job: AssetJob) -> JobApprovals:
    """Read locks, or an empty set."""
    path = approvals_path(job)
    if not path.is_file():
        return JobApprovals()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return JobApprovals.model_validate(data)


def write_approvals(job: AssetJob, approvals: JobApprovals) -> None:
    """Persist locks next to asset.yaml."""
    approvals_path(job).write_text(
        yaml.safe_dump(approvals.model_dump(mode="json"), sort_keys=False),
        encoding="utf-8",
    )


def merge_approved(
    job: AssetJob,
    names: list[str],
    iteration: int,
) -> JobApprovals:
    """Lock named regions from an accepted evaluation."""
    approvals = load_approvals(job)
    known = {row.path: row for row in approvals.locks}
    for name in names:
        known[name] = ApprovalLock(
            path=name,
            iteration_approved=iteration,
            locked=True,
        )
    approvals.locks = list(known.values())
    write_approvals(job, approvals)
    return approvals


def spec_path_value(spec: AssetSpec, path: str) -> Any:
    """Read a dotted lock path from a spec. Unknown paths are None."""
    kind, _, rest = path.partition(".")
    if kind == "part" and hasattr(spec, "geometry"):
        for part in spec.geometry.parts or []:
            if part.name == rest:
                return part.model_dump(mode="json")
        return None
    if kind == "garment" and hasattr(spec, "geometry"):
        garment = spec.geometry.garment
        if garment is None:
            return None
        if rest == "ease_offset":
            rest = "clearance"
        return getattr(garment, rest, None)
    if kind == "layer" and hasattr(spec, "layers"):
        for layer in spec.layers:
            if layer.name == rest:
                return layer.model_dump(mode="json")
        return None
    if kind == "landmark" and spec.geometric_plan:
        for row in spec.geometric_plan.landmarks:
            if row.id == rest:
                return row.model_dump(mode="json")
        return None
    if kind == "quality":
        return rest
    return None


def locked_paths_changed(
    live: AssetSpec,
    best: AssetSpec,
    approvals: JobApprovals,
) -> list[str]:
    """Locked paths whose live values differ from current_best."""
    changed: list[str] = []
    for lock in approvals.locks:
        if not lock.locked:
            continue
        if spec_path_value(live, lock.path) != spec_path_value(
            best, lock.path,
        ):
            changed.append(lock.path)
    return changed
