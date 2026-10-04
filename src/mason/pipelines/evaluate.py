"""Store an external visual evaluation on a job."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from mason.core.art import VisualEvaluation
from mason.core.jobs import AssetJob, require_job
from mason.core.runs import JobRun
from mason.core.workspace import find_project_root
from mason.errors import MasonError
from mason.pipelines.checkpoint import apply_checkpoint
from mason.pipelines.eval_next import next_packet, primary_preview


def run_evaluate(
    asset_id: str,
    evaluation_path: Path,
    *,
    iteration: int | None = None,
) -> VisualEvaluation:
    """Validate and persist a critic evaluation, then apply checkpoint."""
    payload = evaluate_payload(
        asset_id, evaluation_path, iteration=iteration, full=True,
    )
    payload.pop("checkpoint", None)
    payload.pop("next", None)
    return VisualEvaluation.model_validate(payload)


def evaluate_payload(
    asset_id: str,
    evaluation_path: Path,
    *,
    iteration: int | None = None,
    full: bool = False,
) -> dict:
    """Checkpoint plus next packet. `--full` adds the stored record."""
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
    _require_failure_packet(evaluation)
    root = find_project_root()
    job = require_job(root, asset_id)
    meta = job.load_meta()
    if iteration is None:
        iteration = meta.iteration if meta and meta.iteration else 1
    evaluation.iteration = iteration
    if not evaluation.created_at:
        evaluation.created_at = datetime.now(timezone.utc).isoformat()
    job.write_evaluation(evaluation)
    status = apply_checkpoint(job, evaluation)
    stored = job.load_evaluation(evaluation.iteration or iteration)
    record = stored or evaluation
    packet = next_packet(job, record)
    if not full:
        return {"next": packet, "checkpoint": status}
    payload = record.model_dump(mode="json")
    payload["checkpoint"] = status
    payload["next"] = packet
    return payload


def history_payload(asset_id: str, *, summary: bool = False) -> dict:
    """List iteration snapshots and any attached evaluations."""
    root = find_project_root()
    job = require_job(root, asset_id)
    result = job.load_result()
    primary_key = "full"
    if result and result.preview_roles.get("primary"):
        primary_key = result.preview_roles["primary"]
    meta = job.load_meta()
    current_best = meta.current_best if meta else None
    rows = []
    for number in job.list_iterations():
        evaluation = job.load_evaluation(number)
        snap = job.iterations / f"{number:03d}" / "previews"
        previews = {}
        if snap.is_dir():
            for png in sorted(snap.glob("*.png")):
                previews[png.stem] = job.rel(png)
        row: dict = {
            "iteration": number,
            "built_at": result.built_at if result else None,
            "is_best": number == current_best,
            "evaluation_ship": evaluation.ship if evaluation else None,
            "evaluation_passed": evaluation.passed if evaluation else None,
        }
        if evaluation:
            row["evaluation_mode"] = evaluation.mode
            row["stage"] = evaluation.stage
            row["represents_object"] = evaluation.represents_object
            row["represents_style"] = evaluation.represents_style
            row["critical_count"] = sum(
                1 for d in evaluation.discrepancies
                if d.rank == "critical"
            )
            if evaluation.compare:
                row["verdict"] = evaluation.compare.verdict
            if evaluation.candidate:
                row["candidate"] = evaluation.candidate
            if evaluation.actions_taken:
                row["actions_taken"] = evaluation.actions_taken
            if evaluation.acceptance_reason:
                row["acceptance_reason"] = evaluation.acceptance_reason
        run_path = job.iterations / f"{number:03d}" / "run.json"
        if run_path.is_file():
            run = JobRun.model_validate_json(
                run_path.read_text(encoding="utf-8"),
            )
            row["duration_ms"] = run.duration_ms
            row["triangles"] = run.triangles
            row["prompt"] = run.prompt
        preview = primary_preview(previews, primary_key)
        if summary:
            row = _summary_row(job, row, evaluation, preview)
        else:
            row["previews"] = previews
        rows.append(row)
    return {
        "asset_id": asset_id,
        "current_best": current_best,
        "iterations": rows,
    }


def _require_failure_packet(evaluation: VisualEvaluation) -> None:
    """Reject a failed review that omits the one next edit."""
    if evaluation.passed:
        return
    missing = []
    if not evaluation.primary_failure:
        missing.append("primary_failure")
    if not evaluation.correction_targets:
        missing.append("correction_targets")
    if not missing:
        return
    raise MasonError(
        "Failed evaluate needs " + " and ".join(missing) + ".",
        code="invalid_evaluation",
        hint=(
            "Set primary_failure and one correction_target "
            "naming a landmark, part, or layer."
        ),
    )


def _summary_row(
    job: AssetJob,
    row: dict,
    evaluation: VisualEvaluation | None,
    preview: str | None,
) -> dict:
    """Return only the next-edit packet for one iteration."""
    if evaluation is None:
        packet = {
            "primary_failure": "",
            "correction_targets": [],
            "verdict": None,
            "unresolved": [],
            "primary_preview": preview,
            "measured": {},
        }
    else:
        packet = next_packet(job, evaluation)
        if not packet["primary_preview"]:
            packet = {**packet, "primary_preview": preview}
    return {
        "iteration": row["iteration"],
        "primary_failure": packet["primary_failure"],
        "correction_targets": packet["correction_targets"],
        "verdict": packet["verdict"],
        "unresolved": packet["unresolved"],
        "primary_preview": packet["primary_preview"] or preview,
        "measured": packet["measured"],
    }
