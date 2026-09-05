"""Persistent job directories under .mason/jobs/<asset-id>/."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from mason.core.assets import AssetSpec, dump_asset_spec, load_asset_spec
from mason.core.results import BuildResult, ValidationReport
from mason.core.styles import StyleProfile
from mason.errors import MasonError


class JobMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str
    source_spec: str | None = None
    created_at: str = ""
    updated_at: str = ""


class AssetJob:
    """Filesystem layout for one asset build."""

    def __init__(self, root: Path, asset_id: str) -> None:
        self.project_root = root
        self.asset_id = asset_id
        self.dir = root / ".mason" / "jobs" / asset_id
        self.output = self.dir / "output"
        self.previews = self.dir / "previews"

    @property
    def asset_yaml(self) -> Path:
        return self.dir / "asset.yaml"

    @property
    def style_yaml(self) -> Path:
        return self.dir / "resolved_style.yaml"

    @property
    def build_py(self) -> Path:
        return self.dir / "build.py"

    @property
    def stdout_log(self) -> Path:
        return self.dir / "stdout.log"

    @property
    def stderr_log(self) -> Path:
        return self.dir / "stderr.log"

    @property
    def validation_json(self) -> Path:
        return self.dir / "validation.json"

    @property
    def result_json(self) -> Path:
        return self.dir / "result.json"

    @property
    def meta_yaml(self) -> Path:
        return self.dir / "job.yaml"

    def exists(self) -> bool:
        return self.dir.is_dir() and self.asset_yaml.is_file()

    def prepare(self) -> None:
        """Create job directories. Does not delete unrelated files."""
        self.output.mkdir(parents=True, exist_ok=True)
        self.previews.mkdir(parents=True, exist_ok=True)

    def write_spec(self, spec: AssetSpec) -> None:
        dump_asset_spec(spec, self.asset_yaml)

    def load_spec(self) -> AssetSpec:
        return load_asset_spec(self.asset_yaml)

    def write_style(self, style: StyleProfile) -> None:
        self.style_yaml.write_text(
            yaml.safe_dump(style.model_dump(mode="json"), sort_keys=False),
            encoding="utf-8",
        )

    def write_meta(self, source_spec: str | None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        existing = self.load_meta()
        created = existing.created_at if existing else now
        meta = JobMeta(
            asset_id=self.asset_id,
            source_spec=source_spec,
            created_at=created,
            updated_at=now,
        )
        self.meta_yaml.write_text(
            yaml.safe_dump(meta.model_dump(), sort_keys=False),
            encoding="utf-8",
        )

    def load_meta(self) -> JobMeta | None:
        if not self.meta_yaml.is_file():
            return None
        data = yaml.safe_load(self.meta_yaml.read_text(encoding="utf-8"))
        return JobMeta.model_validate(data)

    def write_validation(self, report: ValidationReport) -> None:
        self.validation_json.write_text(
            report.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def load_validation(self) -> ValidationReport | None:
        if not self.validation_json.is_file():
            return None
        return ValidationReport.model_validate_json(
            self.validation_json.read_text(encoding="utf-8"),
        )

    def write_result(self, result: BuildResult) -> None:
        self.result_json.write_text(
            result.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def load_result(self) -> BuildResult | None:
        if not self.result_json.is_file():
            return None
        return BuildResult.model_validate_json(
            self.result_json.read_text(encoding="utf-8"),
        )

    def rel(self, path: Path) -> str:
        """Project-relative POSIX path if possible."""
        try:
            return path.resolve().relative_to(
                self.project_root.resolve(),
            ).as_posix()
        except ValueError:
            return path.resolve().as_posix()


def require_job(root: Path, asset_id: str) -> AssetJob:
    """Return an existing job or raise."""
    job = AssetJob(root, asset_id)
    if not job.exists():
        raise MasonError(
            f"No job found for asset '{asset_id}'.",
            code="job_not_found",
            hint="Run mason build <spec.yaml> first.",
            context={"asset_id": asset_id},
        )
    return job


def list_jobs(root: Path) -> list[AssetJob]:
    """List job directories that have an asset.yaml."""
    jobs_root = root / ".mason" / "jobs"
    if not jobs_root.is_dir():
        return []
    jobs: list[AssetJob] = []
    for child in sorted(jobs_root.iterdir()):
        if child.is_dir() and (child / "asset.yaml").is_file():
            jobs.append(AssetJob(root, child.name))
    return jobs
