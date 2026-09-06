"""Blender static_prop build pipeline."""

from __future__ import annotations

from pathlib import Path

from mason.core.assets import StaticPropSpec
from mason.core.jobs import AssetJob
from mason.core.parts import PropPart
from mason.core.paths import resolve_image_source
from mason.core.results import BuildResult
from mason.core.styles import StyleProfile
from mason.core.surfaces import prepare_surface_maps
from mason.core.workspace import find_project_root
from mason.errors import MasonError
from mason.generators.blender.components import expand_components
from mason.generators.blender.part_ops import expand_part_ops
from mason.generators.blender.recipes import expand_recipe
from mason.generators.blender.snap import apply_snaps, snaps_touch
from mason.generators.blender.script_builder import build_blender_script
from mason.pipelines.compare import write_compare_plate
from mason.pipelines.contact_sheet import write_contact_sheet
from mason.pipelines.common import finish_result, tool_failed
from mason.pipelines.ingest import ensure_reference_silhouette
from mason.tools.blender.commands import headless_python, preview_from_blend
from mason.tools.blender.preview import ALL_PREVIEW_FILES
from mason.tools.blender.validation import validate_static_prop
from mason.tools.registry import require_tool


def resolved_parts(spec: StaticPropSpec):
    """Return parts, using a recipe expander when needed."""
    if spec.geometry.parts:
        parts = list(spec.geometry.parts)
    else:
        assert spec.geometry.recipe is not None
        parts = expand_recipe(
            spec.geometry.recipe,
            spec.dimensions,
            spec.geometry.recipe_params,
            spec.materials.primary,
        )
    parts = parts + _decal_parts(spec)
    after_ops = expand_part_ops(parts)
    after_snap = apply_snaps(after_ops)
    return expand_components(after_snap)


def snap_touch_report(spec: StaticPropSpec) -> tuple[bool, str]:
    """Re-expand through snap and report whether snapped faces meet."""
    if spec.geometry.parts:
        parts = list(spec.geometry.parts)
    elif spec.geometry.recipe is not None:
        parts = expand_recipe(
            spec.geometry.recipe,
            spec.dimensions,
            spec.geometry.recipe_params,
            spec.materials.primary,
        )
    else:
        return True, "ok"
    after_snap = apply_snaps(expand_part_ops(parts + _decal_parts(spec)))
    if not any(part.snap for part in after_snap):
        return True, "ok"
    return snaps_touch(after_snap)


def _decal_parts(spec: StaticPropSpec) -> list[PropPart]:
    """Expand spec.decals into textured planes."""
    planes: list[PropPart] = []
    for decal in spec.decals:
        width, height = decal.size
        planes.append(PropPart(
            name=decal.name,
            shape="plane",
            size=(width, height, 0.0),
            location=decal.location,
            rotation=decal.rotation,
            parent=decal.parent,
            material=decal.material,
            texture=decal.image,
            bevel=False,
        ))
    return planes


def assert_known_families(
    parts: list[PropPart],
    style: StyleProfile,
) -> None:
    """Raise if a part names a family the style does not define."""
    known = set(style.materials.families)
    for part in parts:
        if part.family and part.family not in known:
            raise MasonError(
                f"Unknown material family '{part.family}'.",
                code="unknown_family",
                hint="Use a family from the style profile.",
                context={
                    "family": part.family,
                    "available": sorted(known),
                },
            )


def resolve_part_textures(
    job: AssetJob,
    parts: list[PropPart],
    style: StyleProfile | None = None,
) -> dict[str, str]:
    """Map each textured part's name to its resolved PNG path."""
    textures, _rough = resolve_part_maps(job, parts, style)
    return textures


def resolve_part_maps(
    job: AssetJob,
    parts: list[PropPart],
    style: StyleProfile | None = None,
) -> tuple[dict[str, str], dict[str, str]]:
    """Resolve albedo and optional roughness maps. Explicit
    part.texture is required if named; family albedo is used only
    when the file already exists."""
    textures: dict[str, str] = {}
    roughness: dict[str, str] = {}
    families = style.materials.families if style else {}
    for part in parts:
        if part.texture:
            path = resolve_image_source(part.texture, job.project_root)
            if not path.is_file():
                raise MasonError(
                    f"Texture for part '{part.name}' not found: {path}",
                    code="texture_missing",
                    hint="Build the referenced texture asset first.",
                    context={"part": part.name, "path": str(path)},
                )
            textures[part.name] = str(path)
            continue
        fam = families.get(part.family or "")
        if fam is None:
            continue
        if fam.albedo:
            path = resolve_image_source(fam.albedo, job.project_root)
            if path.is_file():
                textures[part.name] = str(path)
        if fam.roughness_map:
            path = resolve_image_source(
                fam.roughness_map, job.project_root,
            )
            if path.is_file():
                roughness[part.name] = str(path)
    return textures, roughness


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
    demo_lighting: bool = False,
) -> BuildResult:
    """Generate script, run Blender, validate, write result.json.

    `demo_lighting` swaps in a nicer preview-only light rig (opt-in,
    default off); it never touches the stored spec/style.
    """
    info = require_tool("blender")
    if spec.materials.palette_overrides:
        style = style.model_copy(update={
            "palette": {
                **style.palette,
                **spec.materials.palette_overrides,
            },
        })
    touch = snap_touch_report(spec)
    parts = resolved_parts(spec)
    assert_known_families(parts, style)
    spec.geometry.parts = parts
    job.prepare()
    ensure_reference_silhouette(job, spec)
    job.write_spec(spec)
    job.write_style(style)
    job.write_meta(source_spec)

    bw, bs, rough, metal = apply_style_defaults(spec, style)
    part_textures, part_roughness = resolve_part_maps(job, parts, style)
    surface = prepare_surface_maps(job, spec, style)
    script = build_blender_script(
        spec,
        style,
        parts,
        job.dir,
        bevel_width=bw,
        bevel_segments=bs,
        roughness=rough,
        metallic=metal,
        part_textures=part_textures,
        part_roughness=part_roughness,
        demo_lighting=demo_lighting,
        **surface,
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

    write_contact_sheet(job.previews)
    write_compare_plate(job)
    report = validate_static_prop(
        job, spec, result.exit_code, touch=touch,
    )
    outputs = {}
    glb = job.output / "asset.glb"
    if glb.is_file():
        outputs["glb"] = job.rel(glb)
    blend = job.output / "asset.blend"
    if blend.is_file():
        outputs["blend"] = job.rel(blend)
    previews = {
        view: job.rel(job.previews / f"{view}.png")
        for view in ALL_PREVIEW_FILES
        if (job.previews / f"{view}.png").is_file()
    }
    sheet = job.previews / "contact_sheet.png"
    if sheet.is_file():
        previews["contact_sheet"] = job.rel(sheet)
    compare = job.previews / "compare.png"
    if compare.is_file():
        previews["compare"] = job.rel(compare)
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
