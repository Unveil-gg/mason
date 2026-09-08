"""Compact catalog of Mason authoring vocabulary."""

from __future__ import annotations

from typing import Any

from mason.generators.blender.components import COMPONENTS
from mason.generators.krita.stamps import STAMPS

SHAPES = (
    "box", "cylinder", "plane", "cone", "torus",
    "tapered_box", "sphere", "lathe",
    "curve", "skin", "outline",
)
TECHNIQUES = (
    "lathe", "box", "curve", "outline", "skin",
    "modular", "remesh", "refine", "sculpt",
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
        "techniques": list(TECHNIQUES),
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
            "preview_roles.silhouette is the black-on-white "
            "set for silhouette-first critique. "
            "When geometric_plan.recognition is silhouette, "
            "inspect those before beauty. Clay for modeling. "
            "silhouette_regressed is advisory, not a ship blocker. "
            "Newest is never automatically best: inspect "
            "current_best and checkpoint.verdict. "
            "silhouette_metrics (iou, contour_distance, "
            "bbox_ratio, widths, com) are objective; use "
            "them with the art critic, not instead of it. "
            "critics.art is evaluate; critics.technical is "
            "validation. Do not polish UVs/materials while "
            "stage is blockout/silhouette. "
            "Recognition is not ship: also ask whether the "
            "STYLE/TYPE is correct. Rank discrepancies "
            "critical/major/minor; fix critical first. "
            "Score continuity and form_conviction for organic "
            "work. history --summary for iteration diffs. "
            "mason style <name> --json for slim palette. "
            "build/rebuild/preview --json validation is slim by "
            "default (drops bulky arrays like layer_names); pass "
            "--full for the complete metrics."
        ),
        "geometric_plan": (
            "Write geometric_plan BEFORE parts. Intent only. "
            "primary_read, recognition (silhouette|proportion|"
            "detail|material|mixed), must_survive_small, "
            "masses, silhouette, silhouette_vs_similar, "
            "proportions, symmetry, negative_space, "
            "abstraction, landmarks, critical_views "
            "[{view, weight}], stage. Empty critical_views "
            "defaults from recognition (silhouette -> side "
            "profile first). Landmarks bind to part+node so a "
            "critique names a control to move. Landmark.uv "
            "is the matching 0..1 point on a reference. "
            "Do not polish detail while stage is "
            "blockout/silhouette."
        ),
        "reference": (
            "mason ingest <image> --asset id --view side|front|"
            "three_quarter writes reference_analysis.views[] "
            "(contour, z-up profile, widths, com, extrema "
            "landmarks) and reference_silhouette_<view>.png. "
            "Treat refs as geometric constraints. For "
            "silhouette-dominant objects: profile -> coarse "
            "outline/lathe/skin volume -> ortho compare -> "
            "only then secondary forms. Multiple views must "
            "all hold; a better front cannot hide a worse side."
        ),
        "stages": (
            "Coarse-to-fine: blockout -> silhouette -> "
            "secondary -> tertiary -> material -> final. "
            "Do not advance if any critical discrepancy "
            "remains. Silhouette stage ignores materials, "
            "textures, and tiny details."
        ),
        "critique": (
            "evaluate mode beauty|silhouette. Set "
            "represents_object and represents_style "
            "separately. Score view_scores [{view, score}] "
            "and compare {best_iteration, improves, worsens, "
            "verdict: accept|reject|try_again, reason}. "
            "A better front cannot hide a worse critical "
            "view. discrepancies: [{rank: critical|"
            "major|minor, category, description, "
            "geometric_intent, suggested_action, landmark}]. "
            "actions_taken records what the next build "
            "changed. acceptance_reason on ship. Intent "
            "first, Blender op second."
        ),
        "iteration": (
            "current_best is the only promoted snapshot. "
            "Pipeline: generate candidate, render, evaluate "
            "vs current_best, accept only if meaningfully "
            "better with no critical-view drop, else "
            "mason revert and try a different correction. "
            "Best-of-N: branch several edits from the same "
            "checkpoint (candidate A/B/C), evaluate all, "
            "promote at most one. mason checkpoint --iteration "
            "N marks a snapshot; mason revert restores spec, "
            "previews, and output GLB. mason restart --keep "
            "a,b --rebuild c copies successful parts from "
            "current_best and drops a failing region so it "
            "can be rebuilt with a different technique."
        ),
        "modeling": (
            "Before writing parts, pick hybrid techniques from "
            "the object's geometry and record them on "
            "construction_plan.techniques. Rotational symmetry "
            "-> lathe. Hard-surface boxes -> box. Path (pipe, "
            "cable, neck) -> curve. 2D blade/ornament -> "
            "outline. Branching volume (limb, tree, creature) "
            "-> skin. Overlapping volumes that must become one "
            "surface -> geometry.bodies remesh. Modular repeats "
            "-> array/component. Recognition is not ship."
        ),
        "curve": (
            "shape: curve + curve.points [{at, radius, "
            "handle_left, handle_right}] is a Bezier path "
            "local to location. bevel_depth, taper (end scale), "
            "fill full|half|none, bevel_profile [[x, y]]. "
            "Converted to mesh. helper: true keeps the path "
            "for part.follow without exporting it."
        ),
        "skin": (
            "shape: skin + skin.nodes [{id, at, radius}] and "
            "edges [[a, b]] is a sparse skeleton. Skin "
            "modifier, then optional subdivide/smooth. Node "
            "ids become vertex groups. Branching necks, "
            "limbs, handles, trees -- not a subject recipe."
        ),
        "outline": (
            "shape: outline + outline.points [[x, z], ...] "
            "and depth extrudes a closed XZ silhouette along "
            "Y (blades, plaques, ornaments). Not lathe profile."
        ),
        "follow": (
            "part.follow {curve, stretch} deforms this mesh "
            "along a named curve part (hose, ribbon, wrap)."
        ),
        "bodies": (
            "geometry.bodies: [{name, members, method: "
            "union|remesh, remesh: {voxel_size, adaptivity}, "
            "smooth, subdivide}] joins overlapping parts into "
            "one continuous surface and discards members. "
            "Keep hard-surface or other-material parts out."
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
