"""Generated scripts contain expected calls and palette colors."""

from __future__ import annotations

from pathlib import Path

from mason.core.assets import parse_asset_spec
from mason.core.styles import load_style
from mason.generators.blender.script_builder import build_blender_script
from mason.generators.krita.script_builder import build_krita_script
from mason.pipelines.static_prop import apply_style_defaults, resolved_parts


def test_blender_script_has_helpers(project: Path) -> None:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "crate",
        "name": "Crate",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {"recipe": "crate"},
        "materials": {"primary": "wood_dark"},
    })
    style = load_style(project / "styles" / "default.yaml")
    parts = resolved_parts(spec)
    bw, bs, r, m = apply_style_defaults(spec, style)
    script = build_blender_script(
        spec, style, parts, project / ".mason" / "jobs" / "crate",
        bevel_width=bw, bevel_segments=bs, roughness=r, metallic=m,
    )
    assert "def create_box" in script
    assert "def create_cylinder" in script
    assert "def create_plane" in script
    assert "def create_primitive" in script
    assert "def create_material" in script
    assert "def export_glb" in script
    assert "json.loads" in script
    assert "#654936" in script
    assert "BLENDER_EEVEE" in script
    assert "CYCLES" in script


def test_krita_script_has_document(project: Path) -> None:
    spec = parse_asset_spec({
        "type": "layered_raster",
        "id": "panel",
        "name": "Panel",
        "layers": [
            {"name": "background", "fill": "cream"},
            {"name": "accent", "fill": "accent"},
        ],
    })
    style = load_style(project / "styles" / "default.yaml")
    script = build_krita_script(spec, style, project / "job", 128, 256)
    assert "createDocument" in script
    assert "paint_text" in script
    assert "createFileLayer" in script
    assert "background" in script
    assert "#DDD0B4" in script
    assert "#8066A8" in script
