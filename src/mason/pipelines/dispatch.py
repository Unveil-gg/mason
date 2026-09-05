"""Route build/rebuild/preview by asset type."""

from __future__ import annotations

from pathlib import Path

from mason.core.assets import (
    AssetSpec,
    ImageProcessSpec,
    LayeredRasterSpec,
    SpriteSheetSpec,
    StaticPropSpec,
    load_asset_spec,
)
from mason.core.jobs import AssetJob, require_job
from mason.core.results import BuildResult
from mason.pipelines.common import (
    load_spec_for_rebuild,
    project_context,
    resolve_job_style,
)
from mason.pipelines.image_process import build_image_process
from mason.pipelines.layered_raster import build_layered_raster
from mason.pipelines.sprite_sheet import build_sprite_sheet
from mason.pipelines.static_prop import build_static_prop, rel_source


def run_build(spec_path: Path, *, mode: str = "all") -> BuildResult:
    """Build from a spec file in the current project."""
    root, project = project_context()
    spec = load_asset_spec(spec_path)
    style = resolve_job_style(root, spec, project.default_style)
    job = AssetJob(root, spec.id)
    source = rel_source(root, spec_path)
    return _run(spec, style, job, source, mode)


def run_rebuild(asset_id: str, *, mode: str = "all") -> BuildResult:
    """Rebuild an existing job."""
    root, project = project_context()
    job = require_job(root, asset_id)
    spec, original = load_spec_for_rebuild(job)
    style = resolve_job_style(root, spec, project.default_style)
    source = rel_source(root, original) if original else None
    if source is None:
        meta = job.load_meta()
        source = meta.source_spec if meta else None
    return _run(spec, style, job, source, mode)


def _run(
    spec: AssetSpec,
    style,
    job: AssetJob,
    source: str | None,
    mode: str,
) -> BuildResult:
    if isinstance(spec, StaticPropSpec):
        return build_static_prop(spec, style, job, source, mode=mode)
    if isinstance(spec, LayeredRasterSpec):
        return build_layered_raster(spec, style, job, source, mode=mode)
    if isinstance(spec, ImageProcessSpec):
        return build_image_process(spec, style, job, source, mode=mode)
    if isinstance(spec, SpriteSheetSpec):
        return build_sprite_sheet(spec, style, job, source, mode=mode)
    raise TypeError(f"Unsupported spec {type(spec)}")
