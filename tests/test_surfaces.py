"""Palette swatches, atlas cells, and surface strategy."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from mason.core.assets import parse_asset_spec
from mason.core.jobs import AssetJob
from mason.core.styles import load_style
from mason.core.surfaces import (
    AtlasResource,
    atlas_cell_rect,
    cell_uv_rect,
    load_atlas,
    palette_keys,
    prepare_surface_maps,
    swatch_rects_for,
    swatch_uv_rect,
    write_palette_png,
)
from mason.errors import MasonError
from mason.generators.blender.script_builder import build_blender_script
from mason.pipelines.static_prop import apply_style_defaults, resolved_parts


def test_swatch_rects_do_not_overlap() -> None:
    palette = {
        "wood_dark": "#654936",
        "wood_light": "#A77C54",
        "steel": "#8A9196",
    }
    rects = swatch_rects_for(palette)
    keys = palette_keys(palette)
    assert keys[0] == "steel"
    first = rects["steel"]
    second = rects["wood_dark"]
    assert first[2] <= second[0] + 1e-9
    for rect in rects.values():
        u0, v0, u1, v1 = rect
        assert 0 < u0 < u1 < 1
        assert 0 < v0 < v1 < 1
        assert (u1 - u0) < 0.25
        assert (v1 - v0) < 0.25


def test_write_palette_png(tmp_path: Path) -> None:
    palette = {"a": "#FF0000", "b": "#00FF00"}
    dest = tmp_path / "palette.png"
    write_palette_png(palette, dest)
    with Image.open(dest) as img:
        assert img.size == (64, 64)
        assert img.getpixel((4, 4)) == (255, 0, 0)
        assert img.getpixel((20, 4)) == (0, 255, 0)


def test_atlas_index_to_rect() -> None:
    atlas = AtlasResource.model_validate({
        "id": "test_labels",
        "grid": {"columns": 2, "rows": 2},
        "entries": {"alpha": 0, "beta": 1},
    })
    alpha = atlas_cell_rect(atlas, "alpha")
    beta = atlas_cell_rect(atlas, "beta")
    assert alpha[2] <= 0.5
    assert beta[0] >= 0.5
    with pytest.raises(MasonError) as exc:
        atlas_cell_rect(atlas, "missing")
    assert exc.value.code == "unknown_atlas_entry"


def test_cell_uv_inset_inside_cell() -> None:
    u0, v0, u1, v1 = cell_uv_rect(0, 2, 2)
    assert u0 > 0
    assert u1 < 0.5
    assert v1 < 1.0
    assert v0 > 0.5


def test_swatch_uv_matches_grid() -> None:
    assert swatch_uv_rect(0)[0] < swatch_uv_rect(1)[0]


def test_materials_strategy_default() -> None:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "crate",
        "name": "Crate",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {"recipe": "crate"},
    })
    assert spec.materials.strategy == "family"


def test_materials_strategy_palette_roundtrip() -> None:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "block",
        "name": "Block",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {"recipe": "crate"},
        "materials": {"strategy": "palette", "primary": "wood_dark"},
    })
    assert spec.materials.strategy == "palette"


def test_atlas_strategy_requires_ids() -> None:
    with pytest.raises(MasonError):
        parse_asset_spec({
            "type": "static_prop",
            "id": "label",
            "name": "Label",
            "dimensions": {"width": 1, "depth": 1, "height": 1},
            "geometry": {"recipe": "crate"},
            "materials": {"strategy": "atlas"},
        })


def _write_test_atlas(project: Path) -> None:
    dest = project / "atlases" / "test_labels.yaml"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        "id: test_labels\n"
        "grid: {columns: 2, rows: 2}\n"
        "entries:\n  alpha: 0\n  beta: 1\n",
        encoding="utf-8",
    )


def test_load_atlas_from_project(project: Path) -> None:
    _write_test_atlas(project)
    atlas = load_atlas(project, "test_labels")
    assert atlas.id == "test_labels"
    assert atlas.entries["alpha"] == 0


def test_palette_script_uses_shared_material(
    project: Path,
) -> None:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "block",
        "name": "Block",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {
            "parts": [
                {
                    "name": "body",
                    "size": [1, 1, 0.8],
                    "location": [0, 0, 0.4],
                    "material": "wood_dark",
                },
                {
                    "name": "trim",
                    "size": [1, 1, 0.2],
                    "location": [0, 0, 0.9],
                    "material": "wood_light",
                },
            ],
        },
        "materials": {"strategy": "palette", "primary": "wood_dark"},
    })
    style = load_style(project / "styles" / "default.yaml")
    parts = resolved_parts(spec)
    bw, bs, r, m = apply_style_defaults(spec, style)
    job = AssetJob(project, spec.id)
    job.prepare()
    surface = prepare_surface_maps(job, spec, style)
    script = build_blender_script(
        spec, style, parts, job.dir,
        bevel_width=bw, bevel_segments=bs, roughness=r, metallic=m,
        **surface,
    )
    assert script.count('"mason_palette"') == 1
    assert "unwrap_swatch" in script
    assert (job.dir / "palette.png").is_file()


def test_atlas_script_uses_shared_material(project: Path) -> None:
    _write_test_atlas(project)
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "label",
        "name": "Label",
        "dimensions": {"width": 0.5, "depth": 0.02, "height": 0.5},
        "geometry": {
            "parts": [{
                "name": "board",
                "shape": "plane",
                "size": [0.5, 0.5, 0.0],
                "location": [0, 0, 0.25],
                "bevel": False,
            }],
        },
        "materials": {
            "strategy": "atlas",
            "atlas": "test_labels",
            "entry": "alpha",
        },
    })
    style = load_style(project / "styles" / "default.yaml")
    parts = resolved_parts(spec)
    bw, bs, r, m = apply_style_defaults(spec, style)
    job = AssetJob(project, spec.id)
    job.prepare()
    surface = prepare_surface_maps(job, spec, style)
    script = build_blender_script(
        spec, style, parts, job.dir,
        bevel_width=bw, bevel_segments=bs, roughness=r, metallic=m,
        **surface,
    )
    assert script.count('"mason_atlas"') == 1
    assert "unwrap_swatch" in script
