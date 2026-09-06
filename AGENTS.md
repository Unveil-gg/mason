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
10. Open `previews/compare.png` before evaluate. Inspect
    **silhouettes first** (`silhouette_front/side/three_quarter.png`).
    If the shape is not immediately recognizable, revise geometry
    before materials. Do not `ship` if inspect reports
    `silhouette_regressed`.
11. Inspect beauty views (`front`, `side`, `top`, `three_quarter`)
    and `detail.png`.
12. Act as a production art director. Ask:
    - Is the silhouette immediately recognizable?
    - Are proportions intentional, not default cubes?
    - Does it look like primitive geometry assembled by a programmer?
    - Are secondary forms present? Tertiary details appropriate?
    - Are edges unnaturally perfect? Materials readable?
    - Does detail density match viewing distance?
    - Would this sit next to professional indie-game props?
13. Record the critique: `mason evaluate <id> <evaluation.json>`.
    Identify specific reasons not to ship. No praise-only reviews.
14. If `ship` is false, modify spec/plan/source and rebuild.
    Compare `iterations/NNN` via `mason history <id> --json`.
15. Repeat until validation passes, silhouette is strong, evaluation
    `ship` is true, and the asset matches style at intended distance.
16. Treat `asset.yaml`, `art_direction.yaml`, `construction_plan.yaml`,
    and `build.py` as reproducible source.
17. Export with `mason export <id> --to <dir>` when needed. Only
    finished glb/png (and sprite `frames.json`) are copied.

Important rules:

- Do not manually operate Blender, Krita, or Aseprite when Mason can
  invoke them.
- Prefer editing specs/generator source and rebuilding.
- Do not assume a successful tool exit means the asset looks correct.
- Always inspect previews. Silhouette before beauty.
- Do not ignore validation failures.
- Use `--json` when operating autonomously.
- When a style palette matters for rasters, follow generation with
  an `image_process` quantize step.
- ConstructionPlan is intent. Generation stays `parts` / `recipe` /
  `component`.

Asset types:

- `static_prop` — Blender parts (`box`, `cylinder`, `plane`, `cone`,
  `torus`, `tapered_box`, `sphere`) with optional `parent`, `snap`
  (`{to, on}`), `inset`, `array` (linear or `radial`), `mirror`,
  `component`, `family`, and `texture` (`{asset, file}`). Components:
  bolt, hinge, handle, caster, bracket, trim, x_brace, rail,
  wire_wall, rivet_strip, cornice. Recipes: crate, shelf, table,
  hydrant, cart. Textured planes are decals (stretch UV). `decals:`
  also expand to planes. Family `albedo` is used when that PNG
  already exists.
- `layered_raster` — Krita layers: fill, text (`font`, `align`),
  `stamp` (`l_corner`, `gem`, `rule`), or imported image. Source is
  `.kra`.
- `sprite_sheet` — Aseprite animations of timed frames. Prefer
  `pixels` + `keys`. Source is `.aseprite`; outputs PNG + `frames.json`.
- `image_process` — ImageMagick resize/crop/trim/composite/quantize/convert

3D previews: beauty `front`/`side`/`top`/`three_quarter`, silhouettes,
`detail.png`, `contact_sheet.png`, and `compare.png`. Raster:
`previews/full.png` and `compare.png`. Sprite-sheet previews are a
4× nearest-neighbor scale of the packed PNG. Compare previews to
the spec, then `mason rebuild <id> --json`.
