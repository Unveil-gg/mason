"""Compact catalog of Mason authoring vocabulary."""

from __future__ import annotations

from typing import Any

from mason.generators.blender.components import COMPONENTS
from mason.generators.krita.stamps import STAMPS

SHAPES = (
    "box", "cylinder", "plane", "cone", "torus",
    "tapered_box", "sphere", "lathe",
    "curve", "skin", "outline", "instance",
)
TECHNIQUES = (
    "lathe", "box", "curve", "outline", "skin",
    "modular", "remesh", "refine", "sculpt", "fit",
)
RECIPES = (
    "crate", "shelf", "table", "hydrant", "cart",
    "house", "tree", "pool", "estate",
)
LAYER_ROLES = (
    "background", "fill", "text", "image", "overlay",
    "underlay", "paint", "mask", "lettering",
)
FAMILIES = (
    "painted_metal", "bare_metal", "varnished_wood",
    "rubber", "plastic", "cardboard", "fabric",
    "masonry", "brownstone", "roofing", "foliage", "lawn",
    "water", "pavement", "clapboard",
)


def vocab_payload(workflow: str | None = None) -> dict[str, Any]:
    """Return the agent vocabulary card, optionally scoped."""
    payload = _full_vocab()
    if not workflow:
        return payload
    from mason.core.workflow import scope_vocab
    return scope_vocab(payload, workflow)


def _full_vocab() -> dict[str, Any]:
    """Unscoped catalog."""
    from mason.core.workflow import WORKFLOWS
    return {
        "workflows": list(WORKFLOWS),
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
            "exists. family.bump_map / part.bump_map is a "
            "height PNG; family.normal_map / part.normal_map "
            "is tangent RGB. materials.shader principled|"
            "fabric. family.noise_scale tunes solid grain. "
            "Do not put masonry albedo on sidewalks or "
            "stoops; pavement is ground, brownstone/masonry "
            "are brick walls, clapboard is siding. Ornate "
            "subjects need openings on side and back, not "
            "only the beauty camera. Build family albedo "
            "tiles before the 3D job or solids win."
        ),
        "raster": (
            "layered_raster: fill, text, image, stamp, "
            "pixels+keys, expression. shape rect|ellipse. "
            "opacity 0-1. stamps: l_corner gem rule bond "
            "dapple vignette figure speckle courses pavers. "
            "courses=clapboard, pavers=sidewalk slabs. "
            "stamp_seed for "
            "reproducible dapple/speckle. expression: "
            "{formula, mode: alpha|color|height|normal, to, "
            "seed} over x y u v w h; Mason bakes a PNG (no "
            "raw Krita code). height is grayscale; normal is "
            "a Sobel map. image_process op height_to_normal "
            "converts a height PNG. Text shrinks to fit its "
            "rect. "
            "Mixed 2D: AI image for atmosphere, Mason text/"
            "icons/chrome on top. Never AI the type."
        ),
        "sprites": (
            "sprite_sheet via Aseprite. Approve ONE still "
            "(master_frame) before animation. Later frames "
            "inherit palette, canvas, and anchors. Prefer "
            "pixels+keys. Example: examples/assets/"
            "barbarian.yaml."
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
            "three times. Prefer a specification plus an "
            "approved master over a new make_* recipe."
        ),
        "workflow": (
            "mason route <subject-or-id> chooses prop|building|"
            "turned|sculptural|clothing_fitted|clothing_loose|"
            "character|illustrated|texture|pixel|import. "
            "Write spec.workflow. mason vocab --workflow "
            "turned returns only that card. Clothes default "
            "to clothing_fitted (second-skin). "
            "clothing_loose / pipeline: drape is later. "
            "Do not force buildings, clothes, or knights "
            "through one shape grammar. Painterly work goes "
            "to Krita "
            "(illustrated/texture/paint); geometry stays "
            "on the 3D spec. import is a valid success."
        ),
        "plan": (
            "mason plan <id> checks art_direction completeness "
            "for the workflow. Include focal_point, "
            "value_hierarchy, asymmetry, gameplay.must_read, "
            "and recognition_details. Design the object; do "
            "not list body parts. Route then ingest then plan "
            "before writing geometry."
        ),
        "paint": (
            "Krita is the painting desk, not mesh repair. "
            "mason paint <id> --from render|uv|raster writes "
            "a locked underlay plus paint/mask/lettering. "
            "UV: export uv_layout.png, paint, rebind "
            "part.texture. Paintover: ingest --purpose "
            "correction. Do not open Krita to fix a neck."
        ),
        "taste": (
            "Ground is pavement or lawn, never a wall albedo. "
            "NYC walls are brownstone; stoop and cornice are "
            "cast stone (plastic). Queen Anne walls are "
            "clapboard with openings on left, right, and back. "
            "Do not paint every part with one family."
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
            "all hold; a better front cannot hide a worse side. "
            "mason ingest --component name writes a scoped "
            "isolate (reference_silhouette_<component>_<view>.png) "
            "and does not overwrite whole-object refs."
        ),
        "decompose": (
            "Complex refs: decompose before modeling a monolith. "
            "Skip when geometric_plan.masses has 1-2 primary "
            "masses, no repetition, one blob. mode parts = "
            "named parts in one spec + restart --keep/--rebuild. "
            "mode assets = one job per unique component; parent "
            "instances current_best GLBs. Isolate: component "
            "only, blank bg, prefer 3/4, reconstruct hidden "
            "sides, no extra props. instance_of reuses one "
            "asset (wheels). mason decompose <id> <graph> "
            "stores the graph. mason assemble compiles joints "
            "to shape:instance. Parent current_best is "
            "independent: a better wheel that worsens the car "
            "reverts the parent, keeps the wheel."
        ),
        "stages": (
            "Coarse-to-fine: blockout -> silhouette -> "
            "secondary -> tertiary -> material -> final. "
            "Do not advance if any critical discrepancy "
            "remains. Silhouette stage ignores materials, "
            "textures, and tiny details."
        ),
        "critique": (
            "evaluate mode beauty|silhouette. Ask only: "
            "silhouette match, gameplay-size read, major "
            "proportions, focal point, material family, "
            "pose weight, and the SINGLE highest-impact "
            "correction (primary_failure + "
            "correction_targets). Do not list ten changes. "
            "Inspect previews/gameplay.png. "
            "represents_object is false if it does not read "
            "as the subject. that forces reject. Identity "
            "outranks continuity. A drop in target_identity "
            "or primary_silhouette rejects. ship is false "
            "while any critical discrepancy remains. "
            "Failed evaluate needs primary_failure. "
            "Score view_scores and compare "
            "{verdict: accept|reject|try_again}."
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
            "Before writing parts, record techniques on "
            "construction_plan.techniques. Keep named "
            "primitive masses (skull, jaw, snout) until the "
            "silhouette holds. Remesh/inflate is polish on a "
            "subset, never a full-head regenerate. snap seats "
            "parts. skin is optional. Recognition is not ship."
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
            "Optional. skin.nodes [{id, at, radius}]. "
            "mode skeleton (default) needs edges and uses "
            "the Skin modifier (pipes). mode blob is spheres "
            "at nodes, optional edge capsules -- no Skin "
            "modifier. Prefer primitives + bodies remesh "
            "when that is enough."
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
            "inflate, smooth, subdivide}] joins overlapping "
            "primitives into one surface. inflate (solidify) "
            "closes small gaps before remesh. Keep other-"
            "material parts out. Joined bodies must have no "
            "enclosed silhouette holes."
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
        "drape": (
            "part.drape {axis, amount radians, origin: "
            "top|base|center} flares the free end. origin=top "
            "plants max-Z so the hem moves. First cloth step, "
            "not a sim."
        ),
        "attachments": (
            "static_prop.attachments: [{name, location, "
            "rotation, parent}]. Empties named attach_<name> "
            "export in the GLB and metadata.json / manifest."
        ),
        "garment": (
            "geometry.garment.pipeline is stylized (default) "
            "or drape. Stylized is Animal Crossing-style: "
            "extract covered body faces including the sleeve "
            "band, offset, solidify, transfer weights. "
            "Hem/hat/pack stay mesh. Buttons, placket, "
            "prints stay surface_details. Do not loft sleeve "
            "tubes or run cloth. drape is a later path "
            "(silhouette pass + optional cloth_frames). "
            "Inspect worn.png first. Read fit.penetration, "
            "fit.clearance_min, and fit.buttons before "
            "guessing from PNGs. Pose tests gate validation "
            "when pose_scores exist."
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
            "embed} meets a named face. Skin/curve/outline snap "
            "against their local AABB (location is the origin, "
            "not the box center). embed pushes into the target. "
            "part.flush is a second-axis snap after the first, "
            "for a portico that sits on a plinth and meets a "
            "wall. facade_fit fails if a flush decoration does "
            "not overlap the host face."
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
