"""Consumer workflow pasted by mason init."""

MASON_WORKFLOW = """\
# Mason Agent Workflow

## Stop early

A one-mass prop or a raster (layered, sprite, or image
process) stops after `mason build`, `mason inspect --json`,
and one look at the primary preview named on the card.
A material or palette change is a rebuild, not a new
evaluation essay. Open another preview only when the card
disagrees with the spec. Run `mason doctor` once per
machine, not once per asset. `inspect --full` is the long
dump.

Separate **creator** and **critic** even if you are one model.
The creator authors direction, plan, and geometry. The critic scores
previews in a fresh pass and looks for reasons not to ship.

1. Run `mason doctor --json` once per machine when it has
   not already succeeded in this session.
2. Confirm the required capabilities are available.
3. Run `mason route <subject-or-id> --json`, then
   `mason vocab --workflow <kind> --json` (and
   `mason style <name> --json`, or `styles/*.yaml`).
   Write `workflow` on the spec. Clothes default to
   `clothing_fitted` (second-skin extract + painted
   details). `clothing_loose` / `pipeline: drape` is
   later. Do not force buildings, clothes, knights, or
   illustrations through one grammar.
4. Understand the request. If `references` exist, run
   `mason ingest <image> --asset <id> [--style <name>] --json`
   or `mason ingest --fetch <url> --asset <id> --json` (caches
   under `.mason/jobs/<id>/refs/`). Prefer `--view side|front|
   three_quarter` so each image is a geometric constraint.
   OpenCV measures ratio, palette, contour, profile, widths,
   COM, and extrema landmarks into `reference_analysis`.
   If `--asset` has no spec yet, ingest writes a minimal
   buildable scaffold -- edit `art_analysis`, `parts`, or
   `layers` from there. Ingest does not compile a mesh.
   For a complex reference (car, character, multi-mass
   sculpture with reusable parts), do not model a monolith.
   Write `decomposition` (`mason decompose <id> <graph>`):
   `parts` mode stays in one spec; `assets` mode gives each
   unique component its own job. Produce isolated 2D refs
   (component only, blank background, prefer 3/4, reconstruct
   hidden sides) and `mason ingest <isolate> --asset <id>
   --component <name> --view three_quarter`. Model and
   evaluate each unique component against its isolate. Then
   `mason assemble <parent>` instances accepted
   `current_best` GLBs. Parent evaluate uses whole-object
   refs only; a better component does not auto-replace the
   assembled best. Skip this loop when
   `geometric_plan.masses` has 1–2 primary masses, no
   repetition, and the silhouette is one blob.
5. Write `art_direction`: subject, usage, silhouette, focal_point,
   value_hierarchy, gameplay read, recognition_details, forms,
   materials. Run `mason plan <id> --json` before parts.
   A barista is posture, weight, and read — not head + torso.
6. Write `geometric_plan` (intent): primary read, recognition
   driver, masses, silhouette vs similar objects, proportions,
   symmetry, negative space, abstraction, landmarks bound to
   `part`+`node`, `critical_views` (which cameras matter most),
   and `stage` (blockout / silhouette / secondary / tertiary /
   material / final). Do not assume anatomical realism.
7. Choose hybrid modeling techniques from the object's geometry
   (lathe, box, curve, outline, skin, remesh, modular). Record them
   on `construction_plan.techniques`. ConstructionPlan is intent,
   not compiled into meshes.
8. Create or modify the AssetSpec (`geometry.parts`, `recipe`, or
   `component`). For silhouette-dominated objects, solve the 2D
   profile first (`outline` / `lathe` / `skin` from
   `reference_analysis` profile), then a coarse volume. Do not
   add eyes, ears, grooves, or materials while the primary
   silhouette fails. At `stage: blockout` only primary masses.
9. Run `mason build <spec> --json`. Each run writes `run.json`
   (timings, prompt, triangles). `model`/`tokens` stay null unless
   `mason note <id> --model --tokens` records a measured count.
10. Check technical validation. Do not ignore failures.
    Success is not “Blender exited” or “the GLB exists.”
11. If `geometric_plan.recognition` is silhouette, inspect
    `preview_roles.silhouette` first (black-on-white). Ignore
    materials, textures, and tiny details. Ask: is the STYLE/TYPE
    correct, not merely recognizable?
12. Inspect `previews/three_quarter.png` (beauty) after the
    silhouette is acceptable, or when recognition is mixed.
    Ask whether the form is convincing, not merely recognizable.
13. Inspect `clay_three_quarter.png` if geometry needs review
    (proportions, continuity, shape language). Required for
    organic / semi-organic assets.
14. Inspect `front` / `side` / `top` for structure.
    `silhouette_regressed` is advisory.
15. Record the critique: `mason evaluate <id> <evaluation.json>`.
    Set `mode` (beauty|silhouette), `represents_object`,
    `represents_style`, `stage`, `view_scores`, and `compare`
    versus `current_best` (`improves` / `worsens` / verdict
    accept|reject|try_again).     Ranked `discrepancies`
    (critical / major / minor) with `geometric_intent` and a
    landmark. Failed reviews need `primary_failure` and one
    `correction_targets` list. Inspect `previews/gameplay.png`.
    Recognition alone is not success. Do not advance
    `stage` while any critical discrepancy remains.
    Newest is never automatically best: accept only if the
    candidate is meaningfully better and no critical view
    or identity score dropped. `represents_object: false`
    is a reject. Continuity cannot beat a worse silhouette.
    Otherwise `mason revert`
    (restores spec, previews, and the GLB) and try another edit.
    If one region keeps failing, `mason restart --keep ...
    --rebuild ...` and try a different technique. For hard
    corrections, branch best-of-N from the same checkpoint.
    Art critic = evaluate. Technical critic = validation.
    Do not chase triangle/UV polish while the design is wrong.
16. Translate intent to a landmark/control-point edit, record
    `actions_taken` on the next evaluate, rebuild. Use
    `mason history <id> --json --summary`.
17. Repeat until validation passes, no critical discrepancies,
    beauty looks production-ready, and `ship` is true.
18. Treat `asset.yaml`, `art_direction.yaml`,
    `construction_plan.yaml`, `geometric_plan.yaml`,
    `decomposition.yaml`, and `build.py` as reproducible
    source.
19. Export with `mason export <id> --to <dir>` when needed. Only
    finished glb/png (and sprite `frames.json`) are copied. For a
    multi-asset pack, write `kits/<id>.yaml` ({id, name, members})
    and run `mason export --kit <id> --to <dir>` once every member
    has a successful build.

When `geometric_plan.recognition` is silhouette, inspect
`preview_roles.silhouette` before beauty. Beauty three-quarter
is the primary artistic image once the profile holds. Do not
treat silhouette success as proof the asset is visually
complete. Use clay for modeling quality. When
`preview_roles.context` is set, prefer that in-engine preview
as the last look.

Important rules:

- Mason drives Blender only through generated `bpy` scripts
  (`blender --background --python build.py`). Do not operate
  the GUI.
- Do not manually operate Blender, Krita, or Aseprite when Mason can
  invoke them.
- Prefer editing specs/generator source and rebuilding.
- Do not assume a successful tool exit means the asset looks correct.
- Always inspect previews. Beauty three-quarter first.
  Open only `preview_roles.primary` unless clay or silhouette
  is needed. `build --json` and `inspect --json` include
  `preview_roles`. Skip contact_sheet unless comparing views.
- `mason stats [id]` reports triangle counts. Use it instead
  of opening the GLB.
- Do not ignore validation failures.
- Use `--json` when operating autonomously.
- When a style palette matters for rasters, follow generation with
  an `image_process` quantize step.
- Prefer `materials.strategy: palette`, then `atlas`, then
  bespoke `part.texture` / family albedo.
- ConstructionPlan is intent. Generation stays `parts` / `recipe` /
  `component`.

Asset types:

- `static_prop` — Blender parts (`box`, `cylinder`, `plane`, `cone`,
  `torus`, `tapered_box`, `sphere`, `lathe`, `curve`, `skin`,
  `outline`, `instance`) with optional `parent`, `snap` (`{to, on, embed}`),
  `flush` (second-axis snap for a wall after a pad),
  `inset`, `array` (linear or `radial`), `mirror`, `component`,
  `family`, `texture` (`{asset, file}`), `profile` (`[[radius, z],
  ...]` on `lathe`, spun about +Z), `curve` (Bezier path + bevel),
  `skin` (optional; `mode: skeleton` pipes or `blob` spheres),
  `outline` (XZ silhouette + depth),
  `follow` (`{curve, stretch}`), `helper` (deform path, not
  exported), `bend` (`{axis, angle, origin: center|base}`),
  and `instance` (`source: {asset, file}` of another job's
  `current_best` GLB). Do not auto-join instanced children
  into `geometry.bodies`.
  Prefer primitives + `snap` + `geometry.bodies` remesh
  (`inflate` closes gaps). Bodies fail validation on enclosed
  silhouette holes.
  Components: bolt, hinge, handle, caster, bracket, trim, x_brace,
  rail, wire_wall, rivet_strip, cornice. Recipes: crate, shelf,
  table, hydrant, cart, house, tree, pool, estate. `cutout:
  {target}` subtracts this part from another, then discards the
  cutter. Textured planes are decals (stretch UV). `decals:` also
  expand to planes. Family `albedo` is used when that PNG already
  exists. `materials.strategy`: `family` (default), `palette` (one
  shared swatch sheet), or `atlas` (`atlas` + `entry`).
- `layered_raster` — Krita layers: fill, text (`font`, `align`),
  `stamp` (`l_corner`, `gem`, `rule`, `bond`, `dapple`, `vignette`,
  `figure`, `speckle`, `courses`, `pavers`), `shape` (`rect` /
  `ellipse`), `opacity`
  (0–1), `stamp_seed`, `pixels` + `keys`, imported image, or
  `expression` (`formula`, `mode`, `to`, `seed`). Text shrinks to
  fit its rect. Source is `.kra`.
- `sprite_sheet` — Aseprite animations of timed frames. Prefer
  `pixels` + `keys`. Source is `.aseprite`; outputs PNG + `frames.json`.
- `image_process` — ImageMagick resize/crop/trim/composite/quantize/convert

3D previews: beauty `front`/`side`/`top`/`three_quarter` (primary
is three-quarter), diagnostic `clay_three_quarter` and silhouettes,
`detail.png`, `contact_sheet.png`, and `compare.png`. Raster:
`previews/full.png` and `compare.png`. Sprite-sheet previews are a
4× nearest-neighbor scale of the packed PNG. Compare previews to
the spec, then `mason rebuild <id> --json`.

# End Mason Agent Workflow
"""
