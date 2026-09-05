"""Shared pipeline helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from mason.core.assets import AssetSpec, load_asset_spec
from mason.core.config import load_project_config
from mason.core.jobs import AssetJob
from mason.core.results import BuildResult, ValidationReport
from mason.core.styles import StyleProfile, resolve_style
from mason.core.workspace import find_project_root
from mason.errors import MasonError


def project_context(start: Path | None = None):
    """Return (root, project config)."""
    root = find_project_root(start)
    return root, load_project_config(root)


def load_spec_for_rebuild(job: AssetJob) -> tuple[AssetSpec, Path | None]:
    """Prefer the original spec file if it still exists."""
    meta = job.load_meta()
    if meta and meta.source_spec:
        original = job.project_root / meta.source_spec
        if original.is_file():
            return load_asset_spec(original), original
    return job.load_spec(), None


def resolve_job_style(
    root: Path,
    spec: AssetSpec,
    default_style: str,
) -> StyleProfile:
    return resolve_style(root, spec.style, default_style)


def finish_result(
    job: AssetJob,
    spec: AssetSpec,
    *,
    tool: str,
    version: str | None,
    outputs: dict[str, str],
    previews: dict[str, str],
    report: ValidationReport,
    source_spec: str | None,
) -> BuildResult:
    result = BuildResult(
        success=report.passed,
        asset_id=spec.id,
        asset_type=spec.type,
        tool=tool,
        tool_version=version,
        outputs=outputs,
        previews=previews,
        validation={
            "passed": report.passed,
            **report.metrics,
        },
        job_dir=job.rel(job.dir),
        built_at=datetime.now(timezone.utc).isoformat(),
        source_spec=source_spec,
        style=spec.style,
    )
    job.write_validation(report)
    job.write_result(result)
    return result


def tool_failed(
    job: AssetJob,
    command: list[str],
    exit_code: int,
    tool: str,
) -> MasonError:
    return MasonError(
        f"{tool} process failed with exit code {exit_code}.",
        code=f"{tool}_failed",
        hint="Inspect stdout.log and stderr.log in the job directory.",
        context={
            "command": command,
            "exit_code": exit_code,
            "stdout_log": job.rel(job.stdout_log),
            "stderr_log": job.rel(job.stderr_log),
            "job_dir": job.rel(job.dir),
        },
    )
