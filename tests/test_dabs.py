"""Stroke dabs and the paintop window guard."""

from __future__ import annotations

from pathlib import Path

from mason.core.assets import parse_asset_spec
from mason.core.styles import load_style
from mason.errors import MasonError
from mason.generators.raster.dabs import bake_strokes
from mason.pipelines.layered_raster import (
    _paintop_guard,
    write_raster_silhouette,
)


def test_bake_strokes_writes_png(project: Path) -> None:
    spec = parse_asset_spec({
        "type": "layered_raster",
        "id": "wash",
        "name": "Wash",
        "dimensions": {"width": 32, "height": 16},
        "layers": [{
            "name": "crest",
            "fill": "ink",
            "stroke": {
                "points": [[2, 8], [28, 8]],
                "radius": 3,
                "spacing": 0.5,
            },
        }],
    })
    style = load_style(project / "styles" / "default.yaml")
    dest = project / "strokes"
    baked = bake_strokes(spec, style, dest, 32, 16)
    assert baked.layers[0].stroke is None
    assert baked.layers[0].image is not None
    assert Path(baked.layers[0].image).is_file()


def test_paintop_stops_without_a_window() -> None:
    spec = parse_asset_spec({
        "type": "layered_raster",
        "id": "brush",
        "name": "Brush",
        "metadata": {"krita_paintop": "1"},
        "layers": [{"name": "paper", "fill": "cream"}],
    })
    try:
        _paintop_guard(spec, False)
    except MasonError as exc:
        assert exc.code == "needs_window"
    else:
        raise AssertionError("expected needs_window")
    try:
        _paintop_guard(spec, True)
    except MasonError as exc:
        assert exc.code == "paintop_unwired"
    else:
        raise AssertionError("expected paintop_unwired")


def test_raster_silhouette(tmp_path: Path) -> None:
    from PIL import Image

    src = tmp_path / "full.png"
    Image.new("RGB", (8, 4), (20, 20, 20)).save(src)
    dest = tmp_path / "silhouette.png"
    write_raster_silhouette(src, dest)
    assert dest.is_file()
    assert Image.open(dest).getpixel((0, 0)) == 0
