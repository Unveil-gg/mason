"""Approved visual masters. Not recipes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

from mason.core.jobs import AssetJob, list_jobs
from mason.core.workflow import infer_workflow
from mason.errors import MasonError


class MasterRecord(BaseModel):
    """Pointer at an approved job snapshot."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    workflow: str
    style: str = "default"
    source_job: str
    iteration: int | None = None
    scale: str = ""


def masters_dir(root: Path) -> Path:
    return root / "masters"


def load_master(root: Path, asset_id: str) -> MasterRecord | None:
    path = masters_dir(root) / f"{asset_id}.yaml"
    if not path.is_file():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return MasterRecord.model_validate(data)


def list_masters(root: Path, workflow: str | None = None) -> list[str]:
    """Approved master ids, optionally filtered by workflow."""
    folder = masters_dir(root)
    if not folder.is_dir():
        return []
    found: list[str] = []
    for path in sorted(folder.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if workflow and data.get("workflow") != workflow:
            continue
        found.append(str(data.get("id") or path.stem))
    return found


def approve_master(job: AssetJob) -> dict[str, Any]:
    """Mark the job as an approved master and write masters/<id>.yaml."""
    spec = job.load_spec()
    meta = job.load_meta()
    workflow = infer_workflow(
        (spec.art_direction.subject if spec.art_direction else "")
        or spec.name,
        spec,
    )
    if meta is None or meta.current_best is None:
        raise MasonError(
            f"'{job.asset_id}' has no current_best to approve.",
            code="no_checkpoint",
            hint="Accept an evaluation or mason checkpoint first.",
        )
    record = MasterRecord(
        id=spec.id,
        name=spec.name,
        workflow=workflow,
        style=spec.style,
        source_job=spec.id,
        iteration=meta.current_best,
    )
    folder = masters_dir(job.project_root)
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / f"{spec.id}.yaml"
    dest.write_text(
        yaml.safe_dump(record.model_dump(mode="json"), sort_keys=False),
        encoding="utf-8",
    )
    job.set_approved_master(True, workflow=workflow)
    return record.model_dump(mode="json")


def discover_approved_jobs(root: Path, workflow: str | None = None) -> list[str]:
    """Masters on disk plus jobs flagged approved_master."""
    names = set(list_masters(root, workflow))
    for job in list_jobs(root):
        meta = job.load_meta()
        if not meta or not meta.approved_master:
            continue
        if workflow and meta.workflow and meta.workflow != workflow:
            continue
        names.add(job.asset_id)
    return sorted(names)
