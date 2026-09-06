"""Route build/rebuild/preview by asset type."""

from __future__ import annotations

from pathlib import Path

from mason.core.assets import (
    AssetSpec,
    ImageProcessSpec,
    LayeredRasterSpec,
    SpriteSheetSpec,
    StaticPropSpec,
    dump_asset_spec,
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
    # Snapshot variant specs before the primary build mutates
    # spec.geometry.parts (recipe expansion writes the flattened
    # part list back onto the spec in place).
    variants = (
        _variant_specs(spec) if isinstance(spec, StaticPropSpec) else []
    )
    style = resolve_job_style(root, spec, project.default_style)
    job = AssetJob(root, spec.id)
    source = rel_source(root, spec_path)
    result = _run(spec, style, job, source, mode)
    if result.success and variants:
        result = _build_variants(variants, spec_path, result)
    return result


def _variant_specs(spec: StaticPropSpec) -> list[StaticPropSpec]:
    """One sibling spec per materials.variants entry. Suffix names
    and merges palette_overrides on top of the parent's."""
    children = []
    for variant in spec.variants:
        materials = spec.materials.model_copy(update={
            "primary": variant.primary or spec.materials.primary,
            "palette_overrides": {
                **spec.materials.palette_overrides,
                **variant.palette_overrides,
            },
        })
        children.append(spec.model_copy(deep=True, update={
            "id": f"{spec.id}_{variant.suffix}",
            "name": f"{spec.name} ({variant.suffix})",
            "variants": [],
            "materials": materials,
        }))
    return children


def _build_variants(
    variants: list[StaticPropSpec],
    spec_path: Path,
    result: BuildResult,
) -> BuildResult:
    """Write + build each variant sibling. Returns result with a
    variants summary attached; each variant is its own stored job."""
    entries = []
    for child in variants:
        child_path = spec_path.with_name(f"{child.id}.yaml")
        dump_asset_spec(child, child_path)
        child_result = run_build(child_path)
        entries.append({
            "asset_id": child.id,
            "success": child_result.success,
            "outputs": child_result.outputs,
            "previews": child_result.previews,
        })
    return result.model_copy(update={"variants": entries})


def run_rebuild(
    asset_id: str, *, mode: str = "all", demo_lighting: bool = False,
) -> BuildResult:
    """Rebuild an existing job. `demo_lighting` (preview mode only)
    swaps in a nicer one-off light rig without touching the stored
    spec/style."""
    root, project = project_context()
    job = require_job(root, asset_id)
    spec, original = load_spec_for_rebuild(job)
    style = resolve_job_style(root, spec, project.default_style)
    source = rel_source(root, original) if original else None
    if source is None:
        meta = job.load_meta()
        source = meta.source_spec if meta else None
    return _run(spec, style, job, source, mode, demo_lighting=demo_lighting)


def _run(
    spec: AssetSpec,
    style,
    job: AssetJob,
    source: str | None,
    mode: str,
    *,
    demo_lighting: bool = False,
) -> BuildResult:
    if isinstance(spec, StaticPropSpec):
        return build_static_prop(
            spec, style, job, source, mode=mode, demo_lighting=demo_lighting,
        )
    if isinstance(spec, LayeredRasterSpec):
        return build_layered_raster(spec, style, job, source, mode=mode)
    if isinstance(spec, ImageProcessSpec):
        return build_image_process(spec, style, job, source, mode=mode)
    if isinstance(spec, SpriteSheetSpec):
        return build_sprite_sheet(spec, style, job, source, mode=mode)
    raise TypeError(f"Unsupported spec {type(spec)}")
