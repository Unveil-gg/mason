"""Raster layer stamp expansion."""

from __future__ import annotations

from mason.core.assets import LayerRect, RasterLayer, parse_asset_spec
from mason.generators.krita.stamps import expand_stamps


def test_l_corner_two_rects() -> None:
    layers = expand_stamps([
        RasterLayer(
            name="c",
            fill="gold",
            stamp="l_corner",
            stamp_corner="tl",
            rect=LayerRect(x=16, y=16, width=18, height=18),
        ),
    ])
    assert [ly.name for ly in layers] == ["c_h", "c_v"]
    assert layers[0].rect is not None
    assert layers[0].rect.height < layers[1].rect.height


def test_gem_three_layers() -> None:
    layers = expand_stamps([
        RasterLayer(
            name="pip",
            fill="gold",
            stamp="gem",
            stamp_inner="gem",
            rect=LayerRect(x=32, y=32, width=30, height=30),
        ),
    ])
    assert [ly.name for ly in layers] == [
        "pip_bezel", "pip_stone", "pip_shine",
    ]
    assert layers[1].fill == "gem"


def test_rule_has_end_caps() -> None:
    layers = expand_stamps([
        RasterLayer(
            name="rule",
            fill="gold",
            stamp="rule",
            rect=LayerRect(x=20, y=18, width=600, height=3),
        ),
    ])
    assert len(layers) == 3
    assert layers[0].name == "rule_bar"


def test_stamp_spec_parses() -> None:
    spec = parse_asset_spec({
        "type": "layered_raster",
        "id": "row",
        "name": "Row",
        "dimensions": {"width": 64, "height": 32},
        "layers": [{
            "name": "c",
            "fill": "gold",
            "stamp": "l_corner",
            "stamp_corner": "br",
            "rect": {"x": 0, "y": 0, "width": 12, "height": 12},
        }],
    })
    assert spec.layers[0].stamp == "l_corner"
    assert spec.layers[0].stamp_corner == "br"
