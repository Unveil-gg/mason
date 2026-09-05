"""Krita layered_raster build pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

import os

from mason.core.assets import LayeredRasterSpec
from mason.core.jobs import AssetJob
from mason.core.results import BuildResult, ValidationCheck, ValidationReport
from mason.core.styles import StyleProfile
from mason.errors import MasonError
from mason.generators.krita.script_builder import build_krita_script
from mason.pipelines.common import finish_result, tool_failed
from mason.tools.krita.adapter import KritaAdapter
from mason.tools.registry import require_tool


def canvas_size(spec: LayeredRasterSpec, style: StyleProfile) -> tuple[int, int]:
    if spec.dimensions:
        return spec.dimensions.width, spec.dimensions.height
    return style.render.resolution.width, style.render.resolution.height


def build_layered_raster(
    spec: LayeredRasterSpec,
    style: StyleProfile,
    job: AssetJob,
    source_spec: str | None,
    *,
    mode: str = "all",
) -> BuildResult:
    """Generate Krita script, run kritarunner, validate."""
    info = require_tool("krita")
    runner = (info.extras or {}).get("kritarunner")
    if not runner:
        raise MasonError(
            "Krita was found but kritarunner is missing.",
            code="kritarunner_missing",
            hint="Install a full Krita package that includes kritarunner.",
            context={"krita": info.path},
        )
    width, height = canvas_size(spec, style)
    job.prepare()
    job.write_spec(spec)
    job.write_style(style)
    job.write_meta(source_spec)
    job.build_py.write_text(
        build_krita_script(
            spec,
            style,
            job.dir,
            width,
            height,
            project_root=job.project_root,
        ),
        encoding="utf-8",
    )

    adapter = KritaAdapter()
    if mode == "preview":
        kra = job.output / "asset.kra"
        if not kra.is_file():
            raise MasonError(
                "No .kra to preview; run mason build first.",
                code="missing_kra",
            )
        exe = Path(info.path) if info.path else None
        result = adapter.execute(
            [
                str(kra),
                "--nosplash",
                "--export",
                "--export-filename",
                str(job.previews / "full.png"),
            ],
            cwd=job.dir,
            executable=exe,
            stdout_path=job.stdout_log,
            stderr_path=job.stderr_log,
        )
    else:
        module = _install_krita_script(job)
        result = adapter.execute(
            ["-s", module, "-f", "__main__"],
            cwd=Path(runner).parent,
            executable=Path(runner),
            stdout_path=job.stdout_log,
            stderr_path=job.stderr_log,
            timeout=300,
        )
    if not result.success:
        raise tool_failed(job, result.command, result.exit_code, "krita")
    if not (job.previews / "full.png").is_file():
        raise tool_failed(job, result.command, result.exit_code, "krita")

    report = validate_raster(job, spec, width, height, result.exit_code)
    outputs = {}
    if (job.output / "asset.kra").is_file():
        outputs["kra"] = job.rel(job.output / "asset.kra")
    if (job.output / "asset.png").is_file():
        outputs["png"] = job.rel(job.output / "asset.png")
    previews = {}
    if (job.previews / "full.png").is_file():
        previews["full"] = job.rel(job.previews / "full.png")
    return finish_result(
        job,
        spec,
        tool="krita",
        version=info.version,
        outputs=outputs,
        previews=previews,
        report=report,
        source_spec=source_spec,
    )


def validate_raster(
    job: AssetJob,
    spec: LayeredRasterSpec,
    width: int,
    height: int,
    exit_code: int,
) -> ValidationReport:
    checks: list[ValidationCheck] = [
        ValidationCheck(name="exit_code", passed=exit_code == 0, detail=str(exit_code)),
    ]
    kra = job.output / "asset.kra"
    if spec.export.kra:
        checks.append(ValidationCheck(
            name="kra_exists",
            passed=kra.is_file() and kra.stat().st_size > 0,
        ))
    preview = job.previews / "full.png"
    preview_ok = False
    detail = "missing"
    if preview.is_file() and preview.stat().st_size > 0:
        try:
            with Image.open(preview) as img:
                size = img.size
                img.verify()
            preview_ok = True
            detail = f"{size[0]}x{size[1]}"
        except OSError as exc:
            detail = str(exc)
            size = (0, 0)
    else:
        size = (0, 0)
    checks.append(ValidationCheck(name="preview_full", passed=preview_ok, detail=detail))
    if preview_ok:
        checks.append(ValidationCheck(
            name="canvas_size",
            passed=size == (width, height),
            detail=f"{size[0]}x{size[1]} vs {width}x{height}",
        ))
    metrics: dict = {"width": width, "height": height, "layers": len(spec.layers)}
    meta = job.output / "metadata.json"
    if meta.is_file():
        data = json.loads(meta.read_text(encoding="utf-8"))
        checks.append(ValidationCheck(
            name="layer_count",
            passed=int(data.get("layer_count") or 0) == len(spec.layers),
        ))
        metrics["layer_names"] = data.get("layers")
    return ValidationReport(
        passed=all(c.passed for c in checks),
        checks=checks,
        metrics=metrics,
    )


def _install_krita_script(job: AssetJob) -> str:
    """Copy build.py where kritarunner can import it. Returns module name."""
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise MasonError("APPDATA is unset.", code="krita_script")
        dest_dir = Path(appdata) / "kritarunner"
    else:
        dest_dir = Path.home() / ".local" / "share" / "kritarunner"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "mason_job.py"
    dest.write_text(job.build_py.read_text(encoding="utf-8"), encoding="utf-8")
    return "mason_job"
