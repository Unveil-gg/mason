"""Per-run job metadata (timings, prompt, optional agent notes)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from mason.core.assets import AssetSpec
from mason.core.jobs import AssetJob
from mason.core.results import BuildResult
from mason.errors import MasonError


class RunContext:
    """Set on AssetJob for the duration of one pipeline call."""

    def __init__(
        self,
        started_at: datetime,
        command: str,
        prompt: str | None = None,
    ) -> None:
        self.started_at = started_at
        self.command = command
        self.prompt = prompt


class JobRun(BaseModel):
    """One build/rebuild/preview/ingest. tokens/model stay null
    unless an agent writes them -- Mason cannot see Cursor's meter."""

    model_config = ConfigDict(extra="forbid")

    asset_id: str
    iteration: int | None = None
    command: str = "build"
    started_at: str = ""
    ended_at: str = ""
    duration_ms: int = 0
    prompt: str | None = None
    triangles: int | None = None
    tool: str | None = None
    style: str | None = None
    model: str | None = None
    tokens: int | None = None


def prompt_from_spec(
    spec: AssetSpec,
    override: str | None = None,
) -> str | None:
    """CLI --prompt wins; else art_direction.subject."""
    if override:
        return override
    direction = spec.art_direction
    if direction is None:
        return None
    subject = (direction.subject or "").strip()
    return subject or None


def triangles_from_result(result: BuildResult) -> int | None:
    """Prefer validation.triangles when the tool wrote a count."""
    raw = result.validation.get("triangles")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def write_run(job: AssetJob, run: JobRun) -> Path:
    """Write job-level run.json."""
    path = job.run_json
    path.write_text(run.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_run(job: AssetJob) -> JobRun | None:
    if not job.run_json.is_file():
        return None
    return JobRun.model_validate_json(
        job.run_json.read_text(encoding="utf-8"),
    )


def record_build_run(
    job: AssetJob,
    result: BuildResult,
    iteration: int,
) -> JobRun | None:
    """Write run.json after a successful or failed finish_result."""
    ctx = getattr(job, "run_ctx", None)
    if ctx is None:
        return None
    ended = datetime.now(timezone.utc)
    started = ctx.started_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    duration = max(int((ended - started).total_seconds() * 1000), 0)
    existing = load_run(job)
    run = JobRun(
        asset_id=job.asset_id,
        iteration=iteration,
        command=ctx.command,
        started_at=started.isoformat(),
        ended_at=ended.isoformat(),
        duration_ms=duration,
        prompt=ctx.prompt,
        triangles=triangles_from_result(result),
        tool=result.tool,
        style=result.style,
        model=existing.model if existing else None,
        tokens=existing.tokens if existing else None,
    )
    write_run(job, run)
    return run


def record_ingest_run(
    job: AssetJob,
    *,
    source: str,
    started_at: datetime,
) -> JobRun:
    """Write a run.json for mason ingest (no triangle count)."""
    ended = datetime.now(timezone.utc)
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    duration = max(int((ended - started_at).total_seconds() * 1000), 0)
    run = JobRun(
        asset_id=job.asset_id,
        command="ingest",
        started_at=started_at.isoformat(),
        ended_at=ended.isoformat(),
        duration_ms=duration,
        prompt=source,
        tool="opencv",
    )
    write_run(job, run)
    return run


def patch_run(job: AssetJob, **updates: Any) -> JobRun:
    """Merge agent-supplied notes into the latest run.json.

    Only `model`, `tokens`, and `prompt` are accepted. tokens stay
    null unless the caller measured them.
    """
    run = load_run(job)
    if run is None:
        raise MasonError(
            f"No run.json for asset '{job.asset_id}'.",
            code="run_not_found",
            hint="Run mason build first, then mason note.",
            context={"asset_id": job.asset_id},
        )
    allowed = {"model", "tokens", "prompt"}
    data = run.model_dump()
    for key, value in updates.items():
        if key not in allowed:
            continue
        if value is not None:
            data[key] = value
    patched = JobRun.model_validate(data)
    write_run(job, patched)
    _copy_run_into_iteration(job, patched)
    return patched


def _copy_run_into_iteration(job: AssetJob, run: JobRun) -> None:
    meta = job.load_meta()
    if meta is None or not meta.iteration:
        return
    dest = job.iterations / f"{meta.iteration:03d}" / "run.json"
    if dest.parent.is_dir():
        dest.write_text(
            run.model_dump_json(indent=2),
            encoding="utf-8",
        )
