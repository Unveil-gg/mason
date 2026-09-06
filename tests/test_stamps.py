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


def test_bond_staggers_tabs() -> None:
    layers = expand_stamps([
        RasterLayer(
            name="tabs",
            fill="ink",
            stamp="bond",
            rect=LayerRect(x=0, y=0, width=64, height=64),
        ),
    ])
    names = [ly.name for ly in layers]
    assert any(n.startswith("tabs_h") for n in names)
    assert any(n.startswith("tabs_v") for n in names)
    assert len(layers) > 16


def test_dapple_uses_ellipses() -> None:
    layers = expand_stamps([
        RasterLayer(
            name="leaf",
            fill="lawn",
            stamp="dapple",
            rect=LayerRect(x=0, y=0, width=64, height=64),
        ),
    ])
    assert len(layers) > 8
    assert all(ly.shape == "ellipse" for ly in layers)


def test_vignette_has_rings() -> None:
    layers = expand_stamps([
        RasterLayer(
            name="edge",
            fill="ink",
            stamp="vignette",
            rect=LayerRect(x=0, y=0, width=200, height=100),
        ),
    ])
    assert len(layers) == 12
    assert layers[0].name.startswith("edge_r0")
    assert layers[0].opacity < 1.0


def test_speckle_varies_opacity() -> None:
    layers = expand_stamps([
        RasterLayer(
            name="grain",
            fill="wood",
            stamp="speckle",
            stamp_inner="cream",
            stamp_seed=9,
            rect=LayerRect(x=0, y=0, width=64, height=64),
        ),
    ])
    assert len(layers) > 20
    assert any(ly.opacity < 0.5 for ly in layers)


def test_figure_has_coat() -> None:
    layers = expand_stamps([
        RasterLayer(
            name="hero",
            fill="ink",
            stamp="figure",
            rect=LayerRect(x=10, y=10, width=80, height=160),
        ),
    ])
    names = [ly.name for ly in layers]
    assert "hero_hat" in names
    assert "hero_coat" in names
    assert "hero_flare" in names
