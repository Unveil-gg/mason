"""Sandboxed raster expressions."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from mason.core.assets import RasterLayer, parse_asset_spec
from mason.core.jobs import AssetJob
from mason.core.styles import load_style
from mason.errors import MasonError
from mason.generators.raster.expression import (
    _eval_formula,
    materialize_expressions,
    render_expression,
)
from mason.pipelines.text_fit import fit_text_layers


def test_formula_rejects_attribute() -> None:
    ctx = {"x": np.float32(1), "y": np.float32(1)}
    with pytest.raises(MasonError, match="Unsupported"):
        _eval_formula("__import__('os').name", ctx)


def test_formula_dusk_ramp() -> None:
    w, h = 8, 4
    yy, xx = np.mgrid[0:h, 0:w]
    ctx = {
        "x": xx.astype(np.float32),
        "y": yy.astype(np.float32),
        "u": (xx / 7).astype(np.float32),
        "v": (yy / 3).astype(np.float32),
        "w": np.float32(w),
        "h": np.float32(h),
        "seed": np.float32(0),
    }
    out = _eval_formula("1 - v", ctx)
    assert out[0, 0] > out[-1, 0]


def test_render_alpha_png(tmp_path: Path) -> None:
    style = load_style(Path("styles/default.yaml"))
    layer = RasterLayer.model_validate({
        "name": "dusk",
        "fill": "accent",
        "rect": {"x": 0, "y": 0, "width": 16, "height": 8},
        "expression": {"formula": "1 - v", "mode": "alpha"},
    })
    dest = tmp_path / "dusk.png"
    render_expression(layer, style, dest)
    with Image.open(dest) as img:
        assert img.size == (16, 8)
        assert img.mode == "RGBA"
        top = img.getpixel((8, 0))[3]
        bot = img.getpixel((8, 7))[3]
        assert top > bot


def test_render_height_is_gray(tmp_path: Path) -> None:
    style = load_style(Path("styles/default.yaml"))
    layer = RasterLayer.model_validate({
        "name": "weave",
        "fill": "cream",
        "rect": {"x": 0, "y": 0, "width": 8, "height": 8},
        "expression": {"formula": "u", "mode": "height"},
    })
    dest = tmp_path / "h.png"
    render_expression(layer, style, dest)
    with Image.open(dest) as img:
        left = img.getpixel((0, 4))
        right = img.getpixel((7, 4))
        assert left[0] == left[1] == left[2]
        assert right[0] > left[0]


def test_expression_color_needs_to() -> None:
    with pytest.raises(Exception, match="to"):
        parse_asset_spec({
            "type": "layered_raster",
            "id": "p",
            "name": "P",
            "layers": [{
                "name": "g",
                "fill": "cream",
                "rect": {"x": 0, "y": 0, "width": 8, "height": 8},
                "expression": {"formula": "u", "mode": "color"},
            }],
        })


def test_materialize_sets_image(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    (root / "styles").mkdir(parents=True)
    (root / "styles" / "default.yaml").write_text(
        Path("styles/default.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    spec = parse_asset_spec({
        "type": "layered_raster",
        "id": "panel",
        "name": "Panel",
        "layers": [{
            "name": "dusk",
            "fill": "accent",
            "rect": {"x": 0, "y": 0, "width": 8, "height": 8},
            "expression": {"formula": "u * v", "mode": "alpha"},
        }],
    })
    job = AssetJob(root, "panel")
    job.prepare()
    style = load_style(root / "styles" / "default.yaml")
    baked = materialize_expressions(spec, style, job)
    assert baked.layers[0].image is not None
    assert Path(baked.layers[0].image).is_file()


def test_text_fit_shrinks_long_title() -> None:
    spec = parse_asset_spec({
        "type": "layered_raster",
        "id": "card",
        "name": "Card",
        "layers": [{
            "name": "title",
            "role": "text",
            "text": "Harvest Hollow Harvest Hollow",
            "fill": "cream",
            "font_size": 120,
            "rect": {"x": 0, "y": 0, "width": 200, "height": 40},
        }],
    })
    fitted = fit_text_layers(spec)
    assert fitted.layers[0].font_size < 120
