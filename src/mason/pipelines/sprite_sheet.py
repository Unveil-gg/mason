"""Aseprite sprite_sheet build pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from mason.core.assets import SpriteSheetSpec
from mason.core.jobs import AssetJob
from mason.core.results import ValidationCheck, ValidationReport
from mason.core.styles import StyleProfile
from mason.errors import MasonError
from mason.generators.aseprite.script_builder import (
    build_aseprite_script,
    sheet_layout,
)
from mason.pipelines.common import finish_result, tool_failed
from mason.tools.aseprite.adapter import AsepriteAdapter
from mason.tools.registry import require_tool


def _write_preview(src: Path, dest: Path, scale: int = 4) -> None:
    """Nearest-neighbor enlarge so agents can inspect NES-scale pixels."""
    with Image.open(src) as img:
        if scale <= 1:
            img.save(dest)
            return
        img.resize(
            (img.width * scale, img.height * scale),
            Image.Resampling.NEAREST,
        ).save(dest)


def write_frames_json(job: AssetJob, spec: SpriteSheetSpec) -> Path:
    """Write the engine-bridge frames contract (item 5). Returns path."""
    payload = sheet_layout(spec)
    dest = job.output / "frames.json"
    dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return dest


def build_sprite_sheet(
    spec: SpriteSheetSpec,
    style: StyleProfile,
    job: AssetJob,
    source_spec: str | None,
    *,
    mode: str = "all",
):
    """Generate Lua, run Aseprite headless, write frames.json, validate."""
    info = require_tool("aseprite")
    job.prepare()
    job.write_spec(spec)
    job.write_style(style)
    job.write_meta(source_spec)
    layout = sheet_layout(spec)
    script_path = job.build_lua
    script_path.write_text(
        build_aseprite_script(spec, style, job.dir),
        encoding="utf-8",
    )

    adapter = AsepriteAdapter()
    exe = Path(info.path) if info.path else None
    dest = job.output / "asset.png"
    preview = job.previews / "full.png"

    if mode == "preview":
        if not dest.is_file():
            raise MasonError(
                "No sprite sheet to preview; run mason build first.",
                code="missing_png",
            )
        exit_code = 0
    else:
        result = adapter.execute(
            ["-b", "--script", str(script_path.resolve())],
            cwd=job.dir,
            executable=exe,
            stdout_path=job.stdout_log,
            stderr_path=job.stderr_log,
        )
        if not result.success:
            raise tool_failed(job, result.command, result.exit_code, "aseprite")
        exit_code = result.exit_code

    if dest.is_file():
        _write_preview(dest, preview)
    frames_path = write_frames_json(job, spec)
    report = validate_sprite_sheet(
        job, spec, layout, dest, preview, frames_path, exit_code,
    )
    outputs: dict[str, str] = {}
    if dest.is_file():
        outputs["png"] = job.rel(dest)
    if spec.export.frames:
        outputs["frames"] = job.rel(frames_path)
    ase = job.output / "asset.aseprite"
    if ase.is_file():
        outputs["aseprite"] = job.rel(ase)
    previews = {"full": job.rel(preview)} if preview.is_file() else {}
    return finish_result(
        job,
        spec,
        tool="aseprite",
        version=info.version,
        outputs=outputs,
        previews=previews,
        report=report,
        source_spec=source_spec,
    )


def validate_sprite_sheet(
    job: AssetJob,
    spec: SpriteSheetSpec,
    layout: dict,
    dest: Path,
    preview: Path,
    frames_path: Path,
    exit_code: int,
) -> ValidationReport:
    """Check outputs, sheet size, and animation metadata. Returns report."""
    sheet = layout["sheet"]
    expect = (sheet["width"], sheet["height"])
    checks = [
        ValidationCheck(
            name="exit_code", passed=exit_code == 0, detail=str(exit_code),
        ),
    ]
    if spec.export.aseprite:
        ase = job.output / "asset.aseprite"
        checks.append(ValidationCheck(
            name="aseprite_exists",
            passed=ase.is_file() and ase.stat().st_size > 0,
        ))
    size = (0, 0)
    ok = False
    if dest.is_file() and dest.stat().st_size > 0:
        try:
            with Image.open(dest) as img:
                size = img.size
                img.verify()
            ok = True
        except OSError as exc:
            checks.append(
                ValidationCheck(name="image_valid", passed=False, detail=str(exc)),
            )
    checks.append(ValidationCheck(
        name="png_exists",
        passed=ok,
        detail=f"{size[0]}x{size[1]}" if ok else "missing",
    ))
    if ok:
        checks.append(ValidationCheck(
            name="sheet_size",
            passed=size == expect,
            detail=f"{size[0]}x{size[1]} vs {expect[0]}x{expect[1]}",
        ))
    checks.append(ValidationCheck(
        name="preview_full",
        passed=preview.is_file() and preview.stat().st_size > 0,
    ))
    if spec.export.frames:
        frames_ok = frames_path.is_file() and frames_path.stat().st_size > 0
        checks.append(ValidationCheck(name="frames_json", passed=frames_ok))
        if frames_ok:
            data = json.loads(frames_path.read_text(encoding="utf-8"))
            names = [a["name"] for a in data.get("animations", [])]
            expect_names = [a.name for a in spec.animations]
            checks.append(ValidationCheck(
                name="animation_names",
                passed=names == expect_names,
                detail=",".join(names),
            ))
    total = sum(len(a.frames) for a in spec.animations)
    metrics = {
        "width": size[0],
        "height": size[1],
        "frame_size": layout["frame_size"],
        "frame_count": total,
        "animations": [
            {
                "name": anim.name,
                "frame_count": len(anim.frames),
                "loop": anim.loop,
            }
            for anim in spec.animations
        ],
    }
    return ValidationReport(
        passed=all(c.passed for c in checks),
        checks=checks,
        metrics=metrics,
    )
