"""Generated scripts contain expected calls and palette colors."""

from __future__ import annotations

from pathlib import Path

from mason.core.assets import parse_asset_spec
from mason.core.styles import load_style
from mason.generators.aseprite.script_builder import (
    build_aseprite_script,
    sheet_layout,
)
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
    assert "def create_lathe" in script
    assert "def apply_bend" in script
    assert "def apply_drape" in script
    assert "def apply_bump_and_normal" in script
    assert "def apply_shader" in script
    assert "def create_attachments" in script
    assert "def create_curve" in script
    assert "def create_skin" in script
    assert "def create_blob" in script
    assert "def create_outline" in script
    assert "def import_instance" in script
    assert "def apply_bodies" in script
    assert "def apply_follow" in script
    assert "def finish_geometry" in script
    assert "def create_material" in script
    assert "def export_glb" in script
    assert "json.loads" in script
    assert "#654936" in script
    assert "BLENDER_EEVEE" in script
    assert "CYCLES" in script
    assert "def unwrap_cube" in script
    assert "def unwrap_stretch" in script
    assert "def unwrap_swatch" in script
    assert "def unwrap_world" in script
    assert "def apply_decimate" in script
    assert "def apply_clay_override" in script
    assert "0.74, 0.72, 0.68" in script
    assert "0.08, 0.08, 0.09" in script
    assert "def create_textured_material" in script
    assert 'path + "@"' in script


def test_blender_script_wires_part_textures(project: Path) -> None:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "textured_crate",
        "name": "Textured Crate",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {"recipe": "crate"},
        "materials": {"primary": "wood_dark"},
    })
    style = load_style(project / "styles" / "default.yaml")
    parts = resolved_parts(spec)
    bw, bs, r, m = apply_style_defaults(spec, style)
    script = build_blender_script(
        spec, style, parts, project / ".mason" / "jobs" / "textured_crate",
        bevel_width=bw, bevel_segments=bs, roughness=r, metallic=m,
        part_textures={"crate": "/abs/path/plank.png"},
    )
    assert '"part_textures"' in script
    assert "/abs/path/plank.png" in script
    assert '"tile_size": 1.0' in script
    assert '"wrap": "repeat"' in script


def test_blender_script_wires_demo_lighting(project: Path) -> None:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "crate",
        "name": "Crate",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {"recipe": "crate"},
    })
    style = load_style(project / "styles" / "default.yaml")
    parts = resolved_parts(spec)
    bw, bs, r, m = apply_style_defaults(spec, style)
    script = build_blender_script(
        spec, style, parts, project / ".mason" / "jobs" / "crate",
        bevel_width=bw, bevel_segments=bs, roughness=r, metallic=m,
        demo_lighting=True,
    )
    assert '"demo_lighting": true' in script
    assert "def setup_studio_lights" in script


def test_blender_script_stretches_textured_planes(project: Path) -> None:
    """A textured plane is a decal: unwrap_stretch, not cube_project."""
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "sign",
        "name": "Sign",
        "dimensions": {"width": 0.7, "depth": 0.1, "height": 1.5},
        "geometry": {
            "parts": [
                {
                    "name": "post", "shape": "cylinder",
                    "size": [0.1, 0.1, 1.5], "location": [0, 0, 0.75],
                },
                {
                    "name": "board", "shape": "plane",
                    "size": [0.6, 0.4, 0.0], "location": [0, 0.05, 1.2],
                    "parent": "post",
                    "texture": {"asset": "face", "file": "output/asset.png"},
                },
            ],
        },
    })
    style = load_style(project / "styles" / "default.yaml")
    parts = resolved_parts(spec)
    bw, bs, r, m = apply_style_defaults(spec, style)
    script = build_blender_script(
        spec, style, parts, project / ".mason" / "jobs" / "sign",
        bevel_width=bw, bevel_segments=bs, roughness=r, metallic=m,
        part_textures={"board": "/abs/path/face.png"},
    )
    assert "unwrap_stretch(obj)" in script
    assert "unwrap_world" in script


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
    assert "app.setBatchmode(True)" in script
    assert "doc.setBatchmode(True)" in script
    assert "paint_text" in script
    assert "createFileLayer" in script
    assert "background" in script
    assert "#DDD0B4" in script
    assert "#8066A8" in script
    assert "fill_ellipse" in script
    assert "paint_pixels" in script


def test_krita_script_wires_pixels_and_ellipse(project: Path) -> None:
    spec = parse_asset_spec({
        "type": "layered_raster",
        "id": "mark",
        "name": "Mark",
        "dimensions": {"width": 16, "height": 16},
        "layers": [
            {
                "name": "spot",
                "fill": "ink",
                "shape": "ellipse",
                "rect": {"x": 2, "y": 2, "width": 8, "height": 8},
            },
            {
                "name": "glyph",
                "pixels": ["II", ".I"],
                "keys": {"I": "ink"},
            },
        ],
    })
    style = load_style(project / "styles" / "default.yaml")
    script = build_krita_script(spec, style, project / "job", 16, 16)
    assert '"shape": "ellipse"' in script
    assert '"pixels":' in script
    assert spec.layers[1].pixels is not None


def test_krita_script_wires_opacity(project: Path) -> None:
    spec = parse_asset_spec({
        "type": "layered_raster",
        "id": "fade",
        "name": "Fade",
        "dimensions": {"width": 16, "height": 16},
        "layers": [{
            "name": "glow",
            "fill": "ink",
            "shape": "ellipse",
            "opacity": 0.25,
            "rect": {"x": 2, "y": 2, "width": 8, "height": 8},
        }],
    })
    style = load_style(project / "styles" / "default.yaml")
    script = build_krita_script(spec, style, project / "job", 16, 16)
    assert '"opacity": 0.25' in script
    assert "opacity=1.0" in script or "opacity" in script


def test_aseprite_script_draws_pixels(project: Path) -> None:
    spec = parse_asset_spec({
        "type": "sprite_sheet",
        "id": "hero",
        "name": "Hero",
        "canvas": {"width": 8, "height": 8},
        "style": "default",
        "animations": [{
            "name": "idle",
            "loop": True,
            "frames": [{
                "duration_ms": 200,
                "layers": [{
                    "name": "body",
                    "pixels": ["II", ".I"],
                    "keys": {"I": "ink"},
                }],
            }],
        }],
    })
    style = load_style(project / "styles" / "default.yaml")
    job_dir = project / ".mason" / "jobs" / "hero"
    script = build_aseprite_script(spec, style, job_dir)
    assert "local CONFIG =" in script
    assert "Sprite(" in script
    assert "putPixel" in script
    assert "newTag" in script
    assert "saveAs" in script
    assert spec.animations[0].name in script
    layout = sheet_layout(spec)
    assert layout["sheet"] == {"width": 8, "height": 8}
    assert layout["animations"][0]["frames"][0]["duration_ms"] == 200


def test_blender_script_has_garment_pipeline(project: Path) -> None:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "fitted_shirt",
        "name": "Fitted Shirt",
        "dimensions": {"width": 0.5, "depth": 0.4, "height": 0.4},
        "geometry": {
            "garment": {
                "mode": "template",
                "kind": "shirt",
                "archetype": "small_animal",
            },
        },
        "materials": {"primary": "cotton"},
    })
    style = load_style(project / "styles" / "default.yaml")
    parts = resolved_parts(spec)
    assert parts == []
    bw, bs, r, m = apply_style_defaults(spec, style)
    script = build_blender_script(
        spec, style, parts, project / ".mason" / "jobs" / "fitted_shirt",
        bevel_width=bw, bevel_segments=bs, roughness=r, metallic=m,
    )
    assert "def create_small_animal_body" in script
    assert "def analyze_anatomy" in script
    assert "def _refine_stacked_body" in script
    assert "def extract_garment_surface" in script
    assert "def loft_garment" in script
    assert "def add_garment_details" in script
    assert "def render_worn_preview" in script
    assert "def _pale_preview" in script
    assert "worn_front" in script
    assert "def _tighten_sleeves" in script
    assert "def _clip_batwings" in script
    assert "def _bind_sleeve_axes" in script
    assert "def _measure_torso_half" in script
    assert "SLEEVE_TUBE_LOG" in script
    assert "def _append_tube" in script
    assert "def _append_loft" in script
    assert "def _strip_old_sleeves" in script
    assert "def _push_sleeves_off_arm" in script
    assert "def _thicken_sleeves" in script
    assert "def _shirt_radius_at" in script
    assert "def _axis_t" in script
    assert "if method != \"refit\":" in script
    assert "def _push_off_body" in script
    assert "def _sleeve_report" in script
    assert "def _flap_stats" in script
    assert "def _neck_opening" in script
    assert "def _side_face_span" in script
    assert "def _clip_regions" in script
    assert "FIT_METRICS[\"buttons\"]" in script
    assert "def fit_garment" in script
    assert "def _fit_stylized" in script
    assert "def _extract_stylized_shell" in script
    assert "def _bisect_fill" in script
    assert "def _torso_shell_radii" in script
    assert "def _garment_pipeline" in script
    assert "def build_garment" in script
    assert "def silhouette_pass" in script
    assert "_mason_body" in script
    assert "FIT_METRICS" in script
    assert "payload[\"fit\"] = fit" in script
    assert "if CONFIG.get(\"garment\"):" in script
