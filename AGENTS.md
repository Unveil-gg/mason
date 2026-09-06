# Agent instructions

## Style
Follow the language’s [Google Style Guide](https://google.github.io/styleguide/).
Lua: [Roblox](https://roblox.github.io/lua-style-guide/). OCaml: [Jane Street](https://opensource.janestreet.com/standards/).
- 80 cols (hard cap 100). Simple over clever. No new patterns if existing ones work.
- Brief function comments: usage, params, returns.

## Changes
Surgical only. Min files/lines. No drive-by refactors, extra docs, or unrelated cleanup.

## After code
If this turn generated or edited code, end with a suggested commit message (1–2 sentences, why not what). Do not commit unless asked.

# Mason Agent Workflow

Separate **creator** and **critic** even if you are one model.
The creator authors direction, plan, and geometry. The critic scores
previews in a fresh pass and looks for reasons not to ship.

1. Run `mason doctor --json`.
2. Confirm the required capabilities are available.
3. Run `mason vocab --json` and read the style profile
   (`styles/*.yaml`).
4. Understand the request. If `references` exist, run
   `mason ingest <image> --asset <id> --json`, then write
   `art_analysis` (shape language, proportions, materials).
5. Write `art_direction`: subject, usage, silhouette goal, primary /
   secondary / tertiary forms, material families, detail density.
6. Write `construction_plan` as intent (not compiled into meshes).
7. Create or modify the AssetSpec (`geometry.parts`, `recipe`, or
   `component`).
8. Run `mason build <spec> --json`.
9. Check technical validation. Do not ignore failures.
   Success is not “Blender exited” or “the GLB exists.”
10. Inspect `previews/three_quarter.png` first (beauty). This is
    the primary artistic target. Ask:
    - Does this look like a good game asset?
    - Does it match the intended style?
    - Does it look overly primitive?
    - Are materials convincing?
    - Are secondary forms present?
    - Is the detail level appropriate?
11. Inspect `clay_three_quarter.png` if geometry needs review
    (proportions, bevels, intersections, shape language).
12. Inspect `front` / `side` / `top` for structural problems.
13. Inspect silhouettes only if readability, identity, or
    negative space is questionable. Do not ship or fail
    primarily on silhouette. `silhouette_regressed` is advisory.
14. Record the critique: `mason evaluate <id> <evaluation.json>`.
    Score the beauty render (`overall_visual_quality`). Treat
    `silhouette` as optional. Identify reasons not to ship.
15. If `ship` is false, modify spec/plan/source and rebuild.
    Compare `iterations/NNN` via `mason history <id> --json`.
16. Repeat until validation passes, the beauty render looks
    production-ready, and evaluation `ship` is true.
17. Treat `asset.yaml`, `art_direction.yaml`, `construction_plan.yaml`,
    and `build.py` as reproducible source.
18. Export with `mason export <id> --to <dir>` when needed. Only
    finished glb/png (and sprite `frames.json`) are copied.

The beauty three-quarter render is the primary artistic
evaluation image. Inspect it before diagnostic renders. Do not
treat silhouette success as proof that an asset is visually
complete. Use clay for modeling quality. Use silhouettes for
readability and shape. When `preview_roles.context` is set,
prefer that in-engine preview as the last look.

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
  is needed. Skip contact_sheet unless comparing views.
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
  `torus`, `tapered_box`, `sphere`) with optional `parent`, `snap`
  (`{to, on, embed}`), `inset`, `array` (linear or `radial`), `mirror`,
  `component`, `family`, and `texture` (`{asset, file}`). Components:
  bolt, hinge, handle, caster, bracket, trim, x_brace, rail,
  wire_wall, rivet_strip, cornice. Recipes: crate, shelf, table,
  hydrant, cart, house, tree, pool, estate. `cutout: {target}`
  subtracts this part from another, then discards the cutter.
  Textured planes are decals (stretch UV). `decals:` also expand
  to planes. Family `albedo` is used when that PNG already exists.
  `materials.strategy`: `family` (default), `palette` (one shared
  swatch sheet), or `atlas` (`atlas` + `entry`).
- `layered_raster` — Krita layers: fill, text (`font`, `align`),
  `stamp` (`l_corner`, `gem`, `rule`), or imported image. Source is
  `.kra`.
- `sprite_sheet` — Aseprite animations of timed frames. Prefer
  `pixels` + `keys`. Source is `.aseprite`; outputs PNG + `frames.json`.
- `image_process` — ImageMagick resize/crop/trim/composite/quantize/convert

3D previews: beauty `front`/`side`/`top`/`three_quarter` (primary
is three-quarter), diagnostic `clay_three_quarter` and silhouettes,
`detail.png`, `contact_sheet.png`, and `compare.png`. Raster:
`previews/full.png` and `compare.png`. Sprite-sheet previews are a
4× nearest-neighbor scale of the packed PNG. Compare previews to
the spec, then `mason rebuild <id> --json`.
