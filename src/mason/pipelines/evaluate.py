"""Store an external visual evaluation on a job."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from mason.core.art import VisualEvaluation
from mason.core.jobs import require_job
from mason.core.workspace import find_project_root
from mason.errors import MasonError


def run_evaluate(asset_id: str, evaluation_path: Path) -> VisualEvaluation:
    """Validate and persist a critic evaluation for the current iteration."""
    if not evaluation_path.is_file():
        raise MasonError(
            f"Evaluation file not found: {evaluation_path}",
            code="evaluation_not_found",
            context={"path": str(evaluation_path)},
        )
    try:
        evaluation = VisualEvaluation.model_validate_json(
            evaluation_path.read_text(encoding="utf-8"),
        )
    except Exception as exc:
        raise MasonError(
            f"Invalid visual evaluation: {exc}",
            code="invalid_evaluation",
        ) from exc
    root = find_project_root()
    job = require_job(root, asset_id)
    meta = job.load_meta()
    iteration = meta.iteration if meta and meta.iteration else 1
    evaluation.iteration = iteration
    if not evaluation.created_at:
        evaluation.created_at = datetime.now(timezone.utc).isoformat()
    job.write_evaluation(evaluation)
    return evaluation


def history_payload(asset_id: str, *, summary: bool = False) -> dict:
    """List iteration snapshots and any attached evaluations."""
    root = find_project_root()
    job = require_job(root, asset_id)
    result = job.load_result()
    primary_key = "full"
    if result and result.preview_roles.get("primary"):
        primary_key = result.preview_roles["primary"]
    rows = []
    for number in job.list_iterations():
        evaluation = job.load_evaluation(number)
        snap = job.iterations / f"{number:03d}" / "previews"
        previews = {}
        if snap.is_dir():
            for png in sorted(snap.glob("*.png")):
                previews[png.stem] = job.rel(png)
        row = {
            "iteration": number,
            "built_at": result.built_at if result else None,
            "evaluation_ship": evaluation.ship if evaluation else None,
            "evaluation_passed": evaluation.passed if evaluation else None,
        }
        if summary:
            row["primary_preview"] = _primary_preview(previews, primary_key)
        else:
            row["previews"] = previews
        rows.append(row)
    return {"asset_id": asset_id, "iterations": rows}


def _primary_preview(previews: dict[str, str], primary_key: str) -> str | None:
    """Pick the best preview path for summary history rows."""
    if primary_key in previews:
        return previews[primary_key]
    for key in ("three_quarter", "full", "front"):
        if key in previews:
            return previews[key]
    if previews:
        return next(iter(previews.values()))
    return None
