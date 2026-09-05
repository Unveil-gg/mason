"""Map image_process ops to magick argv (no shell)."""

from __future__ import annotations

from pathlib import Path

from mason.core.assets import (
    CompositeOp,
    ConvertOp,
    CropOp,
    ImageOp,
    ImageProcessSpec,
    QuantizeOp,
    ResizeOp,
    TrimOp,
)
from mason.core.jobs import AssetJob
from mason.core.paths import resolve_project_path
from mason.core.styles import StyleProfile
from mason.errors import MasonError


def resolve_source(spec: ImageProcessSpec, job: AssetJob) -> Path:
    """Resolve the input image path inside the project."""
    src = spec.source
    if src.path:
        return resolve_project_path(job.project_root, src.path)
    assert src.asset and src.file
    base = job.project_root / ".mason" / "jobs" / src.asset
    return resolve_project_path(job.project_root, str(base / src.file))


def resolve_overlay(op: CompositeOp, job: AssetJob) -> Path:
    if op.path:
        return resolve_project_path(job.project_root, op.path)
    assert op.asset and op.file
    base = job.project_root / ".mason" / "jobs" / op.asset
    return resolve_project_path(job.project_root, str(base / op.file))


def write_palette_png(style: StyleProfile, dest: Path) -> Path:
    """Write a 1xN palette strip for -remap."""
    from PIL import Image

    colors = []
    for hex_color in style.palette.values():
        text = hex_color.strip().lstrip("#")
        colors.append((
            int(text[0:2], 16),
            int(text[2:4], 16),
            int(text[4:6], 16),
        ))
    if not colors:
        raise MasonError("Style palette is empty.", code="empty_palette")
    img = Image.new("RGB", (len(colors), 1))
    img.putdata(colors)
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest)
    return dest


def op_args(
    op: ImageOp,
    job: AssetJob,
    style: StyleProfile,
) -> list[str]:
    """Return magick args for one operation (no executable, no files)."""
    if isinstance(op, ResizeOp):
        geom = f"{op.width}x{op.height}"
        if op.fit == "contain":
            return ["-resize", geom]
        if op.fit == "cover":
            return ["-resize", f"{geom}^", "-gravity", "center", "-extent", geom]
        return ["-resize", f"{geom}!"]
    if isinstance(op, CropOp):
        return ["-crop", f"{op.width}x{op.height}+{op.x}+{op.y}", "+repage"]
    if isinstance(op, TrimOp):
        args = []
        if op.fuzz:
            args.extend(["-fuzz", f"{op.fuzz}%"])
        args.append("-trim")
        args.append("+repage")
        return args
    if isinstance(op, CompositeOp):
        overlay = resolve_overlay(op, job)
        return [
            overlay.as_posix(),
            "-gravity",
            op.gravity,
            "-geometry",
            f"+{op.offset_x}+{op.offset_y}",
            "-composite",
        ]
    if isinstance(op, QuantizeOp):
        args: list[str] = []
        if op.dither:
            args.extend(["-dither", "FloydSteinberg"])
        else:
            args.append("+dither")
        if op.palette == "style":
            palette = write_palette_png(
                style,
                job.dir / "palette.png",
            )
            args.extend(["-remap", palette.as_posix()])
        elif op.colors:
            args.extend(["-colors", str(op.colors)])
        return args
    if isinstance(op, ConvertOp):
        return []
    raise MasonError(f"Unknown op {op}", code="unknown_op")


def last_format(spec: ImageProcessSpec) -> str:
    fmt = spec.export.format
    for op in spec.operations:
        if isinstance(op, ConvertOp):
            fmt = op.format
    return fmt


def build_magick_args(
    spec: ImageProcessSpec,
    style: StyleProfile,
    job: AssetJob,
    source: Path,
    dest: Path,
) -> list[str]:
    """Full argv after the magick executable."""
    args: list[str] = [source.as_posix()]
    for op in spec.operations:
        args.extend(op_args(op, job, style))
    args.append(dest.as_posix())
    return args


def expected_size(spec: ImageProcessSpec) -> tuple[int, int] | None:
    """Pixel size after the last resize or crop, if any."""
    size = None
    for op in spec.operations:
        if isinstance(op, ResizeOp):
            size = (op.width, op.height)
        elif isinstance(op, CropOp):
            size = (op.width, op.height)
    return size
