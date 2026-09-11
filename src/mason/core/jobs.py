"""Persistent job directories under .mason/jobs/<asset-id>/."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from mason.core.art import VisualEvaluation
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
    iteration: int = 0
    current_best: int | None = None


class AssetJob:
    """Filesystem layout for one asset build."""

    def __init__(self, root: Path, asset_id: str) -> None:
        self.project_root = root
        self.asset_id = asset_id
        self.dir = root / ".mason" / "jobs" / asset_id
        self.output = self.dir / "output"
        self.previews = self.dir / "previews"
        self.iterations = self.dir / "iterations"
        self.evaluations = self.dir / "evaluations"

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
    def build_lua(self) -> Path:
        return self.dir / "build.lua"

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

    @property
    def art_direction_yaml(self) -> Path:
        return self.dir / "art_direction.yaml"

    @property
    def construction_plan_yaml(self) -> Path:
        return self.dir / "construction_plan.yaml"

    @property
    def art_analysis_yaml(self) -> Path:
        return self.dir / "art_analysis.yaml"

    @property
    def geometric_plan_yaml(self) -> Path:
        return self.dir / "geometric_plan.yaml"

    @property
    def reference_analysis_yaml(self) -> Path:
        return self.dir / "reference_analysis.yaml"

    @property
    def decomposition_yaml(self) -> Path:
        return self.dir / "decomposition.yaml"

    @property
    def run_json(self) -> Path:
        return self.dir / "run.json"

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

    def write_meta(
        self,
        source_spec: str | None,
        *,
        iteration: int | None = None,
        current_best: int | None = None,
        set_best: bool = False,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        existing = self.load_meta()
        created = existing.created_at if existing else now
        if iteration is None:
            iteration = existing.iteration if existing else 0
        if not set_best:
            current_best = existing.current_best if existing else None
        meta = JobMeta(
            asset_id=self.asset_id,
            source_spec=source_spec,
            created_at=created,
            updated_at=now,
            iteration=iteration,
            current_best=current_best,
        )
        self.meta_yaml.write_text(
            yaml.safe_dump(meta.model_dump(), sort_keys=False),
            encoding="utf-8",
        )

    def set_current_best(self, iteration: int | None) -> None:
        """Record the highest-quality snapshot. Does not bump."""
        existing = self.load_meta()
        self.write_meta(
            existing.source_spec if existing else None,
            iteration=existing.iteration if existing else 0,
            current_best=iteration,
            set_best=True,
        )

    def bump_iteration(self) -> int:
        """Increment the stored iteration and return the new value."""
        existing = self.load_meta()
        nxt = (existing.iteration if existing else 0) + 1
        source = existing.source_spec if existing else None
        self.write_meta(source, iteration=nxt)
        return nxt

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

    def write_art_sidecars(self, spec: AssetSpec) -> None:
        """Persist art-loop YAML next to asset.yaml when present."""
        mapping = (
            (spec.art_direction, self.art_direction_yaml),
            (spec.construction_plan, self.construction_plan_yaml),
            (spec.geometric_plan, self.geometric_plan_yaml),
            (spec.art_analysis, self.art_analysis_yaml),
            (spec.reference_analysis, self.reference_analysis_yaml),
            (spec.decomposition, self.decomposition_yaml),
        )
        for value, dest in mapping:
            if value is None:
                continue
            dest.write_text(
                yaml.safe_dump(
                    value.model_dump(mode="json"),
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

    def evaluation_path(self, iteration: int) -> Path:
        return self.evaluations / f"iteration_{iteration:03d}.json"

    def write_evaluation(self, evaluation: VisualEvaluation) -> Path:
        """Store a critic evaluation for the given iteration."""
        self.evaluations.mkdir(parents=True, exist_ok=True)
        path = self.evaluation_path(int(evaluation.iteration or 1))
        path.write_text(
            evaluation.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return path

    def load_evaluation(self, iteration: int) -> VisualEvaluation | None:
        path = self.evaluation_path(iteration)
        if not path.is_file():
            return None
        return VisualEvaluation.model_validate_json(
            path.read_text(encoding="utf-8"),
        )

    def list_evaluations(self) -> list[tuple[int, Path]]:
        if not self.evaluations.is_dir():
            return []
        found: list[tuple[int, Path]] = []
        for path in sorted(self.evaluations.glob("iteration_*.json")):
            stem = path.stem.replace("iteration_", "", 1)
            if stem.isdigit():
                found.append((int(stem), path))
        return found

    def snapshot_iteration(self, iteration: int) -> Path:
        """Copy previews, spec, outputs, and validation into iterations/NNN."""
        dest = self.iterations / f"{iteration:03d}"
        dest.mkdir(parents=True, exist_ok=True)
        preview_dest = dest / "previews"
        preview_dest.mkdir(parents=True, exist_ok=True)
        if self.previews.is_dir():
            for src in self.previews.iterdir():
                if src.is_file():
                    (preview_dest / src.name).write_bytes(src.read_bytes())
        for src in (
            self.asset_yaml,
            self.validation_json,
            self.art_direction_yaml,
            self.construction_plan_yaml,
            self.geometric_plan_yaml,
            self.art_analysis_yaml,
            self.reference_analysis_yaml,
            self.decomposition_yaml,
            self.run_json,
            self.result_json,
            self.dir / "silhouette_metrics.json",
        ):
            if src.is_file():
                (dest / src.name).write_bytes(src.read_bytes())
        if self.output.is_dir():
            out_dest = dest / "output"
            out_dest.mkdir(parents=True, exist_ok=True)
            for src in self.output.iterdir():
                if src.is_file():
                    (out_dest / src.name).write_bytes(src.read_bytes())
        return dest

    def list_iterations(self) -> list[int]:
        if not self.iterations.is_dir():
            return []
        nums: list[int] = []
        for child in self.iterations.iterdir():
            if child.is_dir() and child.name.isdigit():
                nums.append(int(child.name))
        return sorted(nums)

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


def clean_jobs(root: Path, asset_id: str | None = None) -> list[str]:
    """Delete job directories. Returns removed asset ids."""
    jobs_root = root / ".mason" / "jobs"
    if asset_id:
        path = jobs_root / asset_id
        if not path.is_dir():
            raise MasonError(
                f"No job found for asset '{asset_id}'.",
                code="job_not_found",
                hint="Run mason build <spec.yaml> first.",
                context={"asset_id": asset_id},
            )
        shutil.rmtree(path)
        return [asset_id]
    removed: list[str] = []
    if not jobs_root.is_dir():
        return removed
    for child in sorted(jobs_root.iterdir()):
        if child.is_dir():
            shutil.rmtree(child)
            removed.append(child.name)
    return removed
