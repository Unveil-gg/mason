"""ImageMagick argv construction."""

from __future__ import annotations

from pathlib import Path

from mason.core.assets import parse_asset_spec
from mason.core.jobs import AssetJob
from mason.core.paths import resolve_project_path
from mason.core.styles import load_style
from mason.errors import MasonError
from mason.generators.imagemagick.commands import build_magick_args, op_args
import pytest


def test_resize_argv(project: Path) -> None:
    spec = parse_asset_spec({
        "type": "image_process",
        "id": "r",
        "name": "R",
        "source": {"path": "in.png"},
        "operations": [{
            "op": "resize",
            "width": 64,
            "height": 32,
            "fit": "stretch",
        }],
    })
    style = load_style(project / "styles" / "default.yaml")
    job = AssetJob(project, "r")
    src = project / "in.png"
    src.write_bytes(b"x")
    dest = job.output / "asset.png"
    args = build_magick_args(spec, style, job, src, dest)
    assert args[0].endswith("in.png")
    assert "-resize" in args
    assert "64x32!" in args


def test_path_escape(project: Path) -> None:
    with pytest.raises(MasonError) as exc:
        resolve_project_path(project, "../outside.png")
    assert exc.value.code == "path_escape"


def test_quantize_writes_palette(project: Path) -> None:
    from mason.core.assets import QuantizeOp

    style = load_style(project / "styles" / "default.yaml")
    job = AssetJob(project, "q")
    job.prepare()
    args = op_args(QuantizeOp(op="quantize", palette="style"), job, style)
    assert "-remap" in args
    assert (job.dir / "palette.png").is_file()
