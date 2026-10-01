"""Assemble a standalone Blender build.py for one job."""

from __future__ import annotations

import json
from pathlib import Path

from mason.core.assets import PropPart, StaticPropSpec
from mason.core.styles import StyleProfile
from mason.generators.blender.bodies import CREATE_BODIES_SRC
from mason.generators.blender.curves import CREATE_CURVE_SRC
from mason.generators.blender.export import EXPORT_SRC
from mason.generators.blender.prop_atlas import PROP_ATLAS_SRC
from mason.generators.blender.prop_atlas_pack import (
    PROP_ATLAS_PACK_SRC,
)
from mason.generators.blender.prop_atlas_sample import (
    PROP_ATLAS_SAMPLE_SRC,
)
from mason.generators.blender.prop_pack import PROP_PACK_SRC
from mason.generators.blender.instance import CREATE_INSTANCE_SRC
from mason.generators.blender.garment_anatomy import (
    CREATE_GARMENT_ANATOMY_SRC,
)
from mason.generators.blender.garment_body import CREATE_GARMENT_BODY_SRC
from mason.generators.blender.garment_details import (
    CREATE_GARMENT_DETAILS_SRC,
)
from mason.generators.blender.garment_fit import CREATE_GARMENT_FIT_SRC
from mason.generators.blender.garment_metrics import (
    CREATE_GARMENT_METRICS_SRC,
)
from mason.generators.blender.garment_rig import CREATE_GARMENT_RIG_SRC
from mason.generators.blender.garment_surface import (
    CREATE_GARMENT_SURFACE_SRC,
)
from mason.generators.blender.lathe import CREATE_LATHE_SRC
from mason.generators.blender.materials import CREATE_MATERIAL_SRC
from mason.generators.blender.preview_scene import PREVIEW_SCENE_SRC
from mason.generators.blender.primitives import CREATE_BOX_SRC
from mason.generators.blender.skin import CREATE_SKIN_SRC


def build_blender_script(
    spec: StaticPropSpec,
    style: StyleProfile,
    parts: list[PropPart],
    job_dir: Path,
    *,
    bevel_width: float,
    bevel_segments: int,
    roughness: float,
    metallic: float,
    part_textures: dict[str, str] | None = None,
    part_roughness: dict[str, str] | None = None,
    part_bump: dict[str, str] | None = None,
    part_normal: dict[str, str] | None = None,
    bump_image: str | None = None,
    normal_image: str | None = None,
    bump_strength: float = 0.04,
    shader: str = "principled",
    palette_image: str | None = None,
    swatch_rects: dict[str, list[float]] | None = None,
    atlas_image: str | None = None,
    atlas_rect: list[float] | None = None,
    demo_lighting: bool = False,
    instance_paths: dict[str, str] | None = None,
) -> str:
    """Return a self-contained Blender Python script."""
    palette = {part.material: style.color(part.material) for part in parts}
    # always include primary
    try:
        palette.setdefault("primary", style.color(spec.materials.primary))
    except Exception:
        pass
    if spec.geometry.garment:
        key = spec.materials.primary
        try:
            palette[key] = style.color(key)
            palette.setdefault("primary", palette[key])
        except Exception:
            pass
    payload = {
        "job_dir": str(job_dir.resolve()),
        "save_blend": spec.export.save_blend,
        "bevel": spec.geometry.bevel,
        "bevel_width": bevel_width,
        "bevel_segments": bevel_segments,
        "roughness": roughness,
        "metallic": metallic,
        "resolution": [
            style.render.resolution.width,
            style.render.resolution.height,
        ],
        "samples": style.render.samples,
        "engine": style.render.engine,
        "lighting_preset": style.lighting.preset,
        "demo_lighting": demo_lighting,
        "families": {
            key: fam.model_dump(mode="json")
            for key, fam in style.materials.families.items()
        },
        "palette": palette,
        "part_textures": part_textures or {},
        "part_roughness": part_roughness or {},
        "part_bump": part_bump or {},
        "part_normal": part_normal or {},
        "bump_image": bump_image or "",
        "normal_image": normal_image or "",
        "bump_strength": bump_strength,
        "shader": shader,
        "attachments": [
            item.model_dump(mode="json") for item in spec.attachments
        ],
        "export_profile": spec.export.profile,
        "export_movers": _export_movers(spec),
        "export_atlas_size": spec.export.atlas_size,
        "export_volumes": [
            item.model_dump(mode="json") for item in spec.export.volumes
        ],
        "tile_size": style.textures.tile_size,
        "wrap": style.textures.wrap,
        "surface_strategy": spec.materials.strategy,
        "palette_image": palette_image or "",
        "swatch_rects": swatch_rects or {},
        "atlas_image": atlas_image or "",
        "atlas_rect": atlas_rect or [],
        "decimate": spec.geometry.decimate,
        "bodies": [b.model_dump(mode="json") for b in spec.geometry.bodies],
        "parts": [p.model_dump(mode="json") for p in parts],
        "instance_paths": instance_paths or {},
        "garment": _garment_payload(spec, job_dir),
    }
    return (
        _HEADER
        + json.dumps(payload, indent=2)
        + "\n''')\n"
        + _BODY
    )


def _export_movers(spec: StaticPropSpec) -> list[str]:
    """Roots that stay unmerged. Attachment parents if unset."""
    if spec.export.movers:
        return list(spec.export.movers)
    if spec.export.profile != "prop":
        return []
    found: list[str] = []
    for sock in spec.attachments:
        parent = sock.parent
        if parent and parent not in found:
            found.append(parent)
    return found


def _garment_payload(spec: StaticPropSpec, job_dir: Path) -> dict | None:
    """Dump garment config with resolved GLB paths."""
    garment = spec.geometry.garment
    if garment is None:
        return None
    data = garment.model_dump(mode="json")
    from mason.core.paths import resolve_image_source
    from mason.core.workspace import find_project_root

    try:
        root = find_project_root(job_dir)
    except Exception:
        root = None
    if root is not None and garment.body:
        data["body_path"] = str(resolve_image_source(garment.body, root))
    if root is not None and garment.source:
        data["source_path"] = str(
            resolve_image_source(garment.source, root),
        )
    return data


_HEADER = '''# Generated by Mason. Standalone Blender 4.x script.
import json
import os
import sys

import bpy
from mathutils import Vector

CONFIG = json.loads(r\'\'\'
'''

_BODY = (
    CREATE_INSTANCE_SRC
    + CREATE_BOX_SRC
    + CREATE_LATHE_SRC
    + CREATE_CURVE_SRC
    + CREATE_SKIN_SRC
    + CREATE_BODIES_SRC
    + CREATE_MATERIAL_SRC
    + PROP_PACK_SRC
    + PROP_ATLAS_SAMPLE_SRC
    + PROP_ATLAS_PACK_SRC
    + PROP_ATLAS_SRC
    + CREATE_GARMENT_BODY_SRC
    + CREATE_GARMENT_ANATOMY_SRC
    + CREATE_GARMENT_SURFACE_SRC
    + CREATE_GARMENT_DETAILS_SRC
    + CREATE_GARMENT_FIT_SRC
    + CREATE_GARMENT_METRICS_SRC
    + CREATE_GARMENT_RIG_SRC
    + EXPORT_SRC
    + PREVIEW_SCENE_SRC
    + r'''
def reset_scene():
    """Delete all objects so the build is deterministic."""
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat)
    for cam in list(bpy.data.cameras):
        bpy.data.cameras.remove(cam)
    for light in list(bpy.data.lights):
        bpy.data.lights.remove(light)
    for curve in list(bpy.data.curves):
        bpy.data.curves.remove(curve)


def family_settings(part):
    """Resolve roughness/metallic/variation for one part."""
    families = CONFIG.get("families") or {}
    name = part.get("family")
    if name and name in families:
        return families[name]
    return {
        "roughness": CONFIG["roughness"],
        "metallic": CONFIG["metallic"],
        "variation": 0.0,
    }


def build_geometry():
    """Create parts, materials, bevels, and UVs."""
    mats = {}
    strategy = CONFIG.get("surface_strategy") or "family"

    def solid_material(part, key):
        settings = family_settings(part)
        wear = float(part.get("wear") or 0.0)
        cache = (key, part.get("family"), wear)
        if cache not in mats:
            hex_color = CONFIG["palette"].get(key) or CONFIG["palette"].get(
                "primary",
            )
            mats[cache] = create_material(
                f"{key}_{len(mats)}",
                hex_color,
                settings["roughness"],
                settings["metallic"],
                settings.get("variation") or 0.0,
                wear,
                settings.get("noise_scale") or 0.0,
            )
            shader = (
                settings.get("shader")
                or CONFIG.get("shader")
                or "principled"
            )
            apply_shader(mats[cache], shader, settings.get("shader_params"))
            apply_bump_and_normal(
                mats[cache],
                CONFIG["wrap"],
                (CONFIG.get("part_bump") or {}).get(part["name"])
                or CONFIG.get("bump_image") or None,
                (CONFIG.get("part_normal") or {}).get(part["name"])
                or CONFIG.get("normal_image") or None,
                settings.get("bump_strength")
                or CONFIG.get("bump_strength")
                or 0.04,
            )
        return mats[cache]

    tex_mats = {}

    def texture_material(image_path, part):
        """Cache one material per distinct texture path."""
        settings = family_settings(part)
        rough_path = (CONFIG.get("part_roughness") or {}).get(
            part["name"],
        )
        bump_path = (CONFIG.get("part_bump") or {}).get(part["name"]) or (
            CONFIG.get("bump_image") or None
        )
        normal_path = (CONFIG.get("part_normal") or {}).get(
            part["name"],
        ) or (CONFIG.get("normal_image") or None)
        cache = (image_path, rough_path, bump_path, normal_path)
        if cache not in tex_mats:
            shader = (
                settings.get("shader")
                or CONFIG.get("shader")
                or "principled"
            )
            tex_mats[cache] = create_textured_material(
                f"tex_{len(tex_mats)}",
                image_path,
                settings["roughness"],
                settings["metallic"],
                CONFIG["wrap"],
                rough_path,
                bump_path,
                normal_path,
                settings.get("bump_strength")
                or CONFIG.get("bump_strength")
                or 0.04,
                shader,
                settings.get("shader_params"),
            )
        return tex_mats[cache]

    shared = None
    if strategy == "palette" and CONFIG.get("palette_image"):
        shared = create_textured_material(
            "mason_palette",
            CONFIG["palette_image"],
            CONFIG["roughness"],
            CONFIG["metallic"],
            "clamp",
            None,
            CONFIG.get("bump_image") or None,
            CONFIG.get("normal_image") or None,
            CONFIG.get("bump_strength") or 0.04,
            CONFIG.get("shader") or "principled",
        )
    elif strategy == "atlas" and CONFIG.get("atlas_image"):
        shared = create_textured_material(
            "mason_atlas",
            CONFIG["atlas_image"],
            CONFIG["roughness"],
            CONFIG["metallic"],
            "clamp",
            None,
            CONFIG.get("bump_image") or None,
            CONFIG.get("normal_image") or None,
            CONFIG.get("bump_strength") or 0.04,
            CONFIG.get("shader") or "principled",
        )

    created = {}
    organic = ("sphere", "lathe", "curve", "skin", "outline")
    for part in CONFIG["parts"]:
        obj = create_primitive(part)
        if part.get("bend") and obj.type == "MESH":
            apply_bend(obj, part["bend"])
        if part.get("drape") and obj.type == "MESH":
            apply_drape(obj, part["drape"])
        created[part["name"]] = obj
        if obj.type != "MESH":
            continue
        is_plane = (part.get("shape") or "box") == "plane"
        tex_path = CONFIG["part_textures"].get(part["name"])
        if shared is not None:
            assign_material(obj, shared)
        elif tex_path:
            assign_material(obj, texture_material(tex_path, part))
        else:
            key = part.get("material") or "primary"
            if key in CONFIG["palette"] or "primary" in CONFIG["palette"]:
                assign_material(obj, solid_material(part, key))
        use_bevel = part.get("bevel")
        if use_bevel is None:
            use_bevel = CONFIG["bevel"]
        if part.get("cutout") or part.get("family") == "lawn":
            use_bevel = False
        if (part.get("shape") or "box") in organic:
            use_bevel = False
        if use_bevel and not is_plane:
            apply_bevel(obj, CONFIG["bevel_width"], CONFIG["bevel_segments"])
        settings = family_settings(part)
        tile = settings.get("tile_size") or CONFIG["tile_size"]
        if strategy == "palette":
            key = part.get("material") or "primary"
            rect = (CONFIG.get("swatch_rects") or {}).get(key)
            if rect:
                unwrap_swatch(obj, rect)
            else:
                unwrap_cube(obj, tile)
        elif strategy == "atlas":
            rect = CONFIG.get("atlas_rect")
            if rect:
                unwrap_swatch(obj, rect)
            else:
                unwrap_cube(obj, tile)
        elif tex_path and is_plane:
            unwrap_stretch(obj)
        elif tex_path:
            unwrap_world(obj, tile)
        else:
            unwrap_cube(obj, tile)
    finish_geometry(created)


def parse_mode():
    argv = sys.argv
    if "--" in argv:
        extra = argv[argv.index("--") + 1:]
    else:
        extra = []
    if "--mode" in extra:
        return extra[extra.index("--mode") + 1]
    return "all"


def main():
    mode = parse_mode()
    job_dir = CONFIG["job_dir"]
    output = os.path.join(job_dir, "output")
    previews = os.path.join(job_dir, "previews")
    os.makedirs(output, exist_ok=True)
    os.makedirs(previews, exist_ok=True)
    blend = os.path.join(output, "asset.blend")
    if mode in ("all", "build"):
        reset_scene()
        if CONFIG.get("garment"):
            build_garment()
        else:
            build_geometry()
        create_attachments()
        if CONFIG["save_blend"]:
            save_blend(blend)
        export_glb(os.path.join(output, "asset.glb"))
        export_uv_layout(os.path.join(output, "uv_layout.png"))
        write_metadata(os.path.join(output, "metadata.json"))
    if mode in ("all", "preview"):
        if mode == "preview" and os.path.isfile(blend):
            bpy.ops.wm.open_mainfile(filepath=blend)
        render_previews(
            previews,
            CONFIG["resolution"],
            CONFIG["samples"],
            CONFIG.get("engine") or "eevee",
            demo_lighting=bool(CONFIG.get("demo_lighting")),
        )


if __name__ == "__main__":
    main()
'''
)
