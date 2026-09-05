"""Blender static_prop build pipeline."""

from __future__ import annotations

from pathlib import Path

from mason.core.assets import StaticPropSpec
from mason.core.jobs import AssetJob
from mason.core.results import BuildResult
from mason.core.styles import StyleProfile
from mason.core.workspace import find_project_root
from mason.generators.blender.recipes import expand_recipe
from mason.generators.blender.script_builder import build_blender_script
from mason.pipelines.common import finish_result, tool_failed
from mason.tools.blender.commands import headless_python, preview_from_blend
from mason.tools.blender.preview import PREVIEW_VIEWS
from mason.tools.blender.validation import validate_static_prop
from mason.tools.registry import require_tool


def resolved_parts(spec: StaticPropSpec):
    """Return parts, using a recipe expander when needed."""
    if spec.geometry.parts:
        return list(spec.geometry.parts)
    assert spec.geometry.recipe is not None
    return expand_recipe(
        spec.geometry.recipe,
        spec.dimensions,
        spec.geometry.recipe_params,
        spec.materials.primary,
    )


def apply_style_defaults(spec: StaticPropSpec, style: StyleProfile):
    """Merge style geometry/material defaults. Returns tuples."""
    geo = spec.geometry
    bevel_width = (
        geo.bevel_width
        if geo.bevel_width is not None
        else style.geometry.bevel_width
    )
    bevel_segments = (
        geo.bevel_segments
        if geo.bevel_segments is not None
        else style.geometry.bevel_segments
    )
    roughness = (
        spec.materials.roughness
        if spec.materials.roughness is not None
        else style.materials.roughness
    )
    metallic = (
        spec.materials.metallic
        if spec.materials.metallic is not None
        else style.materials.metallic
    )
    return bevel_width, bevel_segments, roughness, metallic


def build_static_prop(
    spec: StaticPropSpec,
    style: StyleProfile,
    job: AssetJob,
    source_spec: str | None,
    *,
    mode: str = "all",
) -> BuildResult:
    """Generate script, run Blender, validate, write result.json."""
    info = require_tool("blender")
    parts = resolved_parts(spec)
    spec.geometry.parts = parts
    job.prepare()
    job.write_spec(spec)
    job.write_style(style)
    job.write_meta(source_spec)

    bw, bs, rough, metal = apply_style_defaults(spec, style)
    script = build_blender_script(
        spec,
        style,
        parts,
        job.dir,
        bevel_width=bw,
        bevel_segments=bs,
        roughness=rough,
        metallic=metal,
    )
    job.build_py.write_text(script, encoding="utf-8")

    extra = ["--mode", mode, "--job-dir", str(job.dir)]
    if mode == "preview" and (job.output / "asset.blend").is_file():
        args = preview_from_blend(
            job.output / "asset.blend",
            job.build_py,
            extra,
        )
    else:
        args = headless_python(job.build_py, extra)

    from mason.tools.blender.adapter import BlenderAdapter

    adapter = BlenderAdapter()
    exe = Path(info.path) if info.path else None
    result = adapter.execute(
        args,
        cwd=job.dir,
        timeout=900,
        executable=exe,
        stdout_path=job.stdout_log,
        stderr_path=job.stderr_log,
    )
    if not result.success or _script_failed(job.stderr_log):
        raise tool_failed(job, result.command, result.exit_code, "blender")

    report = validate_static_prop(job, spec, result.exit_code)
    outputs = {}
    glb = job.output / "asset.glb"
    if glb.is_file():
        outputs["glb"] = job.rel(glb)
    blend = job.output / "asset.blend"
    if blend.is_file():
        outputs["blend"] = job.rel(blend)
    previews = {
        view: job.rel(job.previews / f"{view}.png")
        for view in PREVIEW_VIEWS
        if (job.previews / f"{view}.png").is_file()
    }
    return finish_result(
        job,
        spec,
        tool="blender",
        version=info.version,
        outputs=outputs,
        previews=previews,
        report=report,
        source_spec=source_spec,
    )


def _script_failed(stderr_path: Path) -> bool:
    """Blender often exits 0 after a Python traceback."""
    if not stderr_path.is_file():
        return False
    text = stderr_path.read_text(encoding="utf-8", errors="replace")
    return "Traceback (most recent call last)" in text


def rel_source(project_root: Path, spec_path: Path | None) -> str | None:
    if spec_path is None:
        return None
    try:
        return spec_path.resolve().relative_to(
            project_root.resolve(),
        ).as_posix()
    except ValueError:
        return str(spec_path.resolve())


def project_root_of(job: AssetJob) -> Path:
    return find_project_root(job.project_root)
