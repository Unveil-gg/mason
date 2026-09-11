"""Persist an agent-authored decomposition graph on a job."""

from __future__ import annotations

from pathlib import Path

import yaml

from mason.core.assets import dump_asset_spec
from mason.core.decompose import Decomposition
from mason.core.jobs import require_job
from mason.core.workspace import find_project_root
from mason.errors import MasonError


def run_decompose(asset_id: str, graph_path: Path) -> dict:
    """Validate a decomposition file and write it onto the job."""
    return decompose_payload(asset_id, graph_path)


def decompose_payload(asset_id: str, graph_path: Path) -> dict:
    """Load, validate, persist. Returns the stored graph dump."""
    graph = load_decomposition(graph_path)
    root = find_project_root()
    job = require_job(root, asset_id)
    spec = job.load_spec()
    spec.decomposition = graph
    if graph.mode == "assets":
        deps = list(dict.fromkeys([*spec.depends_on, *graph.asset_ids()]))
        spec.depends_on = deps
    job.write_spec(spec)
    job.write_art_sidecars(spec)
    meta = job.load_meta()
    if meta and meta.source_spec:
        dest = root / meta.source_spec
        if dest.is_file():
            dump_asset_spec(spec, dest)
    payload = graph.model_dump(mode="json")
    payload["asset_id"] = asset_id
    payload["path"] = job.rel(job.decomposition_yaml)
    return payload


def load_decomposition(path: Path) -> Decomposition:
    """Parse YAML or JSON as a Decomposition. Returns the graph."""
    if not path.is_file():
        raise MasonError(
            f"Decomposition file not found: {path}",
            code="decomposition_not_found",
            context={"path": str(path)},
        )
    text = path.read_text(encoding="utf-8")
    try:
        if path.suffix.lower() == ".json":
            graph = Decomposition.model_validate_json(text)
        else:
            data = yaml.safe_load(text) or {}
            if isinstance(data, dict) and "decomposition" in data:
                data = data["decomposition"]
            graph = Decomposition.model_validate(data)
    except MasonError:
        raise
    except Exception as exc:
        raise MasonError(
            f"Invalid decomposition: {exc}",
            code="invalid_decomposition",
        ) from exc
    return graph
