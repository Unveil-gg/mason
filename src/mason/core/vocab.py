"""Compact catalog of Mason authoring vocabulary."""

from __future__ import annotations

from typing import Any

from mason.generators.blender.components import COMPONENTS
from mason.generators.krita.stamps import STAMPS

SHAPES = (
    "box", "cylinder", "plane", "cone", "torus",
    "tapered_box", "sphere", "lathe",
)
RECIPES = (
    "crate", "shelf", "table", "hydrant", "cart",
    "house", "tree", "pool", "estate",
)
LAYER_ROLES = ("background", "fill", "text", "image", "overlay")
FAMILIES = (
    "painted_metal", "bare_metal", "varnished_wood",
    "rubber", "plastic", "cardboard",
    "masonry", "roofing", "foliage", "lawn", "water",
)


def vocab_payload() -> dict[str, Any]:
    """Return the agent vocabulary card."""
    return {
        "shapes": list(SHAPES),
        "components": sorted(COMPONENTS),
        "recipes": list(RECIPES),
        "layer_roles": list(LAYER_ROLES),
        "stamps": list(STAMPS),
        "families": list(FAMILIES),
        "texture": (
            "Prefer materials.strategy palette, then atlas, "
            "then bespoke. part.texture {path|asset+file} is "
            "albedo. Planes stretch UV (decals). Other "
            "textured shapes use world-space UVs. "
            "family.tile_size overrides style tile_size. "
            "Style family.albedo applies when the file "
            "exists. family.noise_scale tunes solid grain."
        ),
        "raster": (
            "layered_raster: fill, text, image, stamp, "
            "pixels+keys, expression. shape rect|ellipse. "
            "opacity 0-1. stamps: l_corner gem rule bond "
            "dapple vignette figure speckle. stamp_seed for "
            "reproducible dapple/speckle. expression: "
            "{formula, mode: alpha|color, to, seed} over "
            "x y u v w h; Mason bakes a PNG (no raw Krita "
            "code). Text shrinks to fit its rect. "
            "Mixed 2D: AI image for atmosphere, Mason text/"
            "icons/chrome on top. Never AI the type."
        ),
        "sprites": (
            "sprite_sheet via Aseprite. One animation per "
            "row. Prefer pixels+keys and a shared style "
            "palette. Example: examples/assets/barbarian.yaml."
        ),
        "style_tune": (
            "styles/<name>.yaml is the project look bible "
            "(not example-only). mason.yaml default_style "
            "plus each spec's style: name. Edit palette, "
            "family roughness/variation/noise_scale/"
            "tile_size/albedo, bevel, lighting, render. "
            "harvest is the Harvest Hollow pack bible."
        ),
        "recipes_note": (
            "Recipes are named clusters, not the path to "
            "beauty. Novel assets use parts + style + stamps. "
            "Add a recipe only after the same cluster appears "
            "three times."
        ),
        "inspect": (
            "build/inspect preview_roles.primary: "
            "three_quarter (3D) or full (2D). "
            "Inspect beauty first, clay for modeling, "
            "silhouette only for readability. "
            "silhouette_regressed is advisory, not a ship blocker. "
            "history --summary for iteration diffs. "
            "mason style <name> --json for slim palette. "
            "build/rebuild/preview --json validation is slim by "
            "default (drops bulky arrays like layer_names); pass "
            "--full for the complete metrics."
        ),
        "lathe": (
            "shape: lathe + profile: [[radius, z], ...] revolves "
            "around +Z (vases, stems, bottles, columns). size is "
            "optional and derived from the profile for snap. "
            "segments 8-64 (default 24). General turned form, "
            "not a subject-specific recipe."
        ),
        "bend": (
            "part.bend {axis: x|y|z, angle radians, "
            "origin: center|base} is a Simple Deform after the "
            "primitive is built. Works on any shape. origin=base "
            "plants min-Z so the top leans (necks, posts, horns)."
        ),
        "run": (
            "Each build writes .mason/jobs/<id>/run.json (copied "
            "into iterations/NNN): started_at, ended_at, "
            "duration_ms, prompt (art_direction.subject or "
            "--prompt), triangles, tool, style. model and tokens "
            "stay null unless mason note <id> --model --tokens "
            "records a measured count. Mason cannot see Cursor's "
            "meter."
        ),
        "snap": (
            "part.snap {to, on: top|bottom|front|back|left|right, "
            "embed} meets a named face. embed pushes into the "
            "target so sloped roofs get a through-joint."
        ),
        "decal_face": (
            "decal.face: top|bottom|front|back|left|right derives "
            "location/rotation/size from the spec's own dimensions "
            "(no hand-rotated Euler triples, no axis-swap risk). "
            "top/front/right read the image unmirrored; back/left "
            "mirror horizontally, bottom mirrors vertically -- "
            "unavoidable once viewed from that side. Omit face to "
            "place a decal manually with location+rotation+size."
        ),
        "decimate": (
            "geometry.decimate is an optional keep-ratio "
            "(0-1) Blender collapse after cutouts. Off by default."
        ),
        "cutout": (
            "part.cutout {target} subtracts this mesh from the "
            "named part, then discards the cutter. One subtract "
            "each. No nested CSG."
        ),
        "variants": (
            "static_prop only: top-level variants: "
            "[{suffix, primary, palette_overrides}] fans one "
            "spec into sibling jobs (<id>_<suffix>) on the same "
            "geometry. materials.palette_overrides on the spec "
            "itself works standalone too, patching style palette "
            "keys for this job only. See "
            "examples/assets/shopping_cart.yaml."
        ),
        "demo_lighting": (
            "mason preview <id> --demo-lighting swaps in a "
            "warmer/rim-lit rig for one-off screenshots. Off by "
            "default; never changes the stored spec/style, so "
            "plain build/rebuild renders stay comparable."
        ),
        "kits": (
            "kits/<id>.yaml {id, name, members: [asset-id, ...]} is a "
            "named list of already-built jobs. mason export --kit <id> "
            "[--to dir] [--engine godot] fans mason export over every "
            "member (fails first if any member has no successful "
            "build) and adds kits.<id> to the same mason_manifest.json. "
            "Export-only: no auto-build, no merged mesh."
        ),
        "ingest": (
            "mason ingest <image> [--asset id] [--style name] "
            "[--type static_prop|layered_raster] [--out path] "
            "or mason ingest --fetch URL --asset id: downloads "
            "into .mason/jobs/<id>/refs/ (source_url sidecar), "
            "then OpenCV measures silhouette ratio, a k-means "
            "palette, color regions, contour, and edge character. "
            "Merges into art_analysis on an existing spec "
            "(parts/layers untouched), or writes a minimal "
            "buildable scaffold for a brand-new --asset id. "
            "Not an image-to-mesh compiler."
        ),
    }
