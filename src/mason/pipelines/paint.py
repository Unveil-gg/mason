"""Krita painting desk: locked underlay plus editable paint layers."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Literal

from mason.core.assets import (
    LayeredRasterSpec,
    PixelDimensions,
    RasterLayer,
    dump_asset_spec,
)
from mason.core.jobs import AssetJob, require_job
from mason.core.workspace import find_project_root
from mason.errors import MasonError

PaintFrom = Literal["render", "uv", "raster"]


def run_paint(
    asset_id: str,
    *,
    source: PaintFrom = "render",
    view: str | None = None,
    component: str | None = None,
) -> dict[str, Any]:
    """Prepare a paint document for the parent job.

    Writes paint.yaml and copies the underlay PNG. Runs Krita when
    kritarunner is available; otherwise leaves the spec for a later
    mason build.
    """
    root = find_project_root()
    job = require_job(root, asset_id)
    underlay = _resolve_underlay(job, source, view)
    if underlay is None or not underlay.is_file():
        raise MasonError(
            f"No {source} underlay for '{asset_id}'.",
            code="paint_underlay_missing",
            hint="Build the asset or pass a render/UV/raster PNG.",
            context={"asset_id": asset_id, "from": source},
        )
    paint_id = _paint_id(asset_id, source, view, component)
    dest = AssetJob(root, paint_id)
    dest.prepare()
    refs = dest.dir / "refs"
    refs.mkdir(parents=True, exist_ok=True)
    underlay_copy = refs / "underlay.png"
    shutil.copy2(underlay, underlay_copy)
    width, height = _image_size(underlay_copy)
    spec = LayeredRasterSpec(
        type="layered_raster",
        id=paint_id,
        name=f"{asset_id} paint",
        workflow="illustrated" if source != "uv" else "texture",
        dimensions=PixelDimensions(width=width, height=height),
        layers=[
            RasterLayer(
                name="underlay",
                role="underlay",
                image=dest.rel(underlay_copy),
            ),
            RasterLayer(name="paint", role="paint"),
            RasterLayer(name="mask", role="mask"),
            RasterLayer(name="lettering", role="lettering"),
        ],
        metadata={
            "parent": asset_id,
            "paint_from": source,
            "view": view or "",
            "component": component or "",
        },
    )
    dump_asset_spec(spec, dest.asset_yaml)
    dest.write_spec(spec)
    dest.write_meta(dest.rel(dest.asset_yaml))
    built = _try_build(dest, spec)
    return {
        "asset_id": paint_id,
        "parent": asset_id,
        "from": source,
        "view": view,
        "component": component,
        "underlay": dest.rel(underlay_copy),
        "spec": dest.rel(dest.asset_yaml),
        "kra": dest.rel(dest.output / "asset.kra")
        if (dest.output / "asset.kra").is_file() else None,
        "png": dest.rel(dest.output / "asset.png")
        if (dest.output / "asset.png").is_file() else None,
        "built": built,
    }


def _paint_id(
    asset_id: str,
    source: str,
    view: str | None,
    component: str | None,
) -> str:
    parts = [asset_id, "paint", source]
    if view:
        parts.append(view)
    if component:
        parts.append(component)
    return "__".join(parts)


def _resolve_underlay(
    job: AssetJob,
    source: str,
    view: str | None,
) -> Path | None:
    if source == "uv":
        for name in ("uv_layout.png", "albedo.png"):
            path = job.output / name
            if path.is_file():
                return path
        return None
    if source == "raster":
        full = job.previews / "full.png"
        if full.is_file():
            return full
        png = job.output / "asset.png"
        return png if png.is_file() else None
    names = []
    if view:
        names.append(f"{view}.png")
    names.extend((
        "gameplay.png", "three_quarter.png", "worn.png", "front.png",
        "full.png",
    ))
    for name in names:
        path = job.previews / name
        if path.is_file():
            return path
    return None


def _image_size(path: Path) -> tuple[int, int]:
    from PIL import Image
    with Image.open(path) as img:
        return img.size


def _try_build(job: AssetJob, spec: LayeredRasterSpec) -> bool:
    """Build the paint job when Krita is installed."""
    from mason.tools.registry import detect_all
    tools = detect_all()
    info = tools.get("krita")
    if info is None or not info.available:
        return False
    from mason.core.styles import resolve_style
    from mason.pipelines.layered_raster import build_layered_raster
    root = job.project_root
    from mason.core.config import load_project_config
    project = load_project_config(root)
    style = resolve_style(root, spec.style, project.default_style)
    result = build_layered_raster(
        spec, style, job, job.rel(job.asset_yaml),
    )
    return bool(result.success)
