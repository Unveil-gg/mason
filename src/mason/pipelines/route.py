"""Classify a brief or job and return a workflow card."""

from __future__ import annotations

from typing import Any

from mason.core.jobs import AssetJob
from mason.core.masters import discover_approved_jobs
from mason.core.workflow import infer_workflow, route_card
from mason.core.workspace import find_project_root


def run_route(query: str) -> dict[str, Any]:
    """Route a subject string or existing asset id."""
    root = find_project_root()
    spec = None
    subject = query
    job = AssetJob(root, query)
    if job.exists():
        spec = job.load_spec()
        if spec.art_direction and spec.art_direction.subject:
            subject = spec.art_direction.subject
        else:
            subject = spec.name
    workflow = infer_workflow(subject, spec)
    masters = discover_approved_jobs(root, workflow)
    card = route_card(subject, spec, masters=masters)
    payload = card.model_dump(mode="json")
    payload["query"] = query
    payload["from_job"] = spec.id if spec is not None else None
    if spec is not None and spec.geometric_plan:
        primaries = [
            row for row in spec.geometric_plan.masses
            if row.role == "primary"
        ]
        if card.decompose and len(primaries) > 2:
            payload["decompose_required"] = True
    return payload
