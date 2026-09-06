# Mason roadmap: visual loop + Aseprite pipeline

Item 5 (`frames.json` + richer export manifest) and item 6
(`sprite_sheet` via Aseprite) are implemented. This file is the
design they were built against, plus what stays out of Mason.

## 1. Visual feedback loop (item 5)

Mason's own previews (front/side/top/three_quarter, contact sheet,
`full.png`) already close the loop for a *single asset in isolation*.
The gap is the next link: once an asset is exported into a game
project, does it actually look/behave right there (does the shelf clip
into a wall, does the label read at in-game scale, does the sprite
animate at the right speed)? That loop should stay engine-agnostic in
Mason itself and be closed by a separate, optional bridge — per the
original "keep engine integration separate from asset generation"
constraint.

**What Mason already provides that the bridge needs (no new work):**

- `mason_manifest.json`, written by `mason export` (plain JSON at the
  destination root: asset id → engine → files → timestamp).
- `bounds.min`/`bounds.max` in every `static_prop` job's
  `validation.json`/`result.json`, in world units.

**What Mason should add (cheap now, expensive to retrofit later):**

- `output/frames.json` for sprite sheets: which rect is which named
  animation + frame index + duration, written by Mason at build time
  regardless of whether a Godot/engine bridge exists yet. This is the
  concrete piece of item 6 (`sprite_sheet` type) that item 5 depends
  on — a bridge has nothing to read otherwise.

**What stays out of Mason (a separate project, not a `mason` command):**

- A small bridge that reads `mason_manifest.json` and, per asset:
  - 3D: procedurally builds/updates a scene via a `tool` GDScript
    (never hand-edits `.tscn` — the user's own warning about agents
    scrambling node UUIDs applies doubly to a bridge), using
    `bounds` to flag obvious clipping against known colliders.
  - 2D: builds a `SpriteFrames .tres` from `output/asset.png` +
    `output/frames.json`.
  - Runs the engine headless (`--headless`/`--script`), captures a
    frame, and writes it to
    `<mason job dir>/previews/in_engine.png` — so the same
    "open previews → critique → edit spec → rebuild" loop the agent
    already uses keeps working, just with one more preview image.

No Mason CLI surface changes are required for item 5 itself; it is
unblocked by shipping `frames.json` as part of item 6.

## 2. Aseprite pipeline (item 6)

Aseprite 1.3.18 is installed and already detected correctly by
`mason doctor` (Steam install, `C:\Program Files (x86)\Steam\steamapps\
common\Aseprite\Aseprite.exe`) — the adapter needed no fix. This
unblocks replacing the hand-assembled Krita+ImageMagick sprite sheet
(see `examples/assets/barbarian_sheet.yaml`) with a pipeline that
carries real animation metadata and lets an agent compose frames
precisely.

### 2a. New AssetSpec type: `sprite_sheet`

```yaml
type: sprite_sheet
id: barbarian
name: Barbarian
canvas: {width: 32, height: 32}
style: nes
animations:
  - name: idle
    loop: true
    frames:
      - duration_ms: 500
        layers: [ ... ]   # same fill/rect/text/image primitives as layered_raster
      - duration_ms: 500
        layers: [ ... ]
  - name: walk
    loop: true
    frames: [ ... 4 frames ... ]
  - name: attack
    loop: false
    frames: [ ... 3 frames ... ]
export:
  png: true       # packed sheet
  json: true       # frame/tag metadata
  aseprite: true   # editable .aseprite source
```

`layered_raster` is "one image, N layers"; a sprite sheet is "N frames,
grouped into named+timed animations, exported as one sheet plus
metadata" — different enough at the top level to be its own tagged-
union member (`Literal["static_prop"|"layered_raster"|"image_process"|
"sprite_sheet"]`), while reusing the existing `layers` vocabulary per
frame so authoring stays familiar.

### 2b. Generator: `generators/aseprite/script_builder.py`

Aseprite scripts are Lua, run via `aseprite -b --script build.lua`
(same "generate a script, run headless" shape as Blender/Krita). Per
frame: create/resize the sprite on frame 1, `addFrame()` after; draw
each layer's `fill`/`rect` via the Lua `Image`/`Cel` pixel API; set
`frame.duration`; tag frame ranges as named animations with
`spr:newTag(name, from, to)` and `tag.aniDir` for loop vs. once. Text
layers reuse the existing Krita/Pillow text-rendering path and get
imported as a PNG (Aseprite's Lua API has no text rendering, and
sprites rarely need in-canvas text). Export: `spr:saveAs(...)` for the
`.aseprite` source (analogous to `.blend`/`.kra`), then
`ExportSpriteSheet` for a packed PNG + JSON data file into
`output/asset.png` + `output/asset.json`.

### 2c. Pipeline: `pipelines/sprite_sheet.py`

Mirrors `pipelines/layered_raster.py`: resolve style, build the Lua
script into the job dir, run the Aseprite adapter's `execute()`
(already implemented; today nothing calls it), validate (frame count
matches spec, every named animation appears as a tag, sheet dimensions
match the expected pack layout), write Mason's own
`output/frames.json` (the plain-JSON contract item 5's bridge reads),
and generate `previews/full.png` from the packed sheet directly (no
render needed, same as `image_process`).

### 2d. Validation additions

`validation.json` gains `animations: [{name, frame_count, loop}]` and
`frame_size` — matching the existing "emit metadata, validate metadata,
don't parse binary" pattern used for Blender's `metadata.json`.

### 2e. Migration for the barbarian example

Done: `examples/assets/barbarian.yaml` is the one `sprite_sheet` spec
(idle / walk / attack). The nine Krita frame files and the
ImageMagick composite job were deleted.

### 2f. Quality loop (shipped)

ArtDirection, ConstructionPlan, silhouette/beauty/detail previews,
`mason evaluate` / `mason history`, material families, components,
and a `hydrant` recipe are in. ConstructionPlan is intent only.

### 2g. Shipped: material variants (`static_prop` only)

`StaticPropSpec.variants: [{suffix, primary, palette_overrides}]`
fans one spec out into sibling jobs at build time
(`pipelines/dispatch.py::_variant_specs` / `_build_variants`). Each
variant is snapshotted from the parent spec *before* recipe
expansion, so its auto-written sibling YAML (`<id>_<suffix>.yaml`)
keeps `recipe:`/`recipe_params:` instead of a frozen part list.
`materials.palette_overrides` (a small dict merged onto the resolved
style's palette, in-memory, never touching `styles/*.yaml`) is what
each variant actually overrides; it also works standalone on a
non-variant spec. `layered_raster` variants are not wired up yet —
same shape would apply if a concrete asset needs it.

### 2h. Shipped: demo lighting toggle

`mason preview <id> --demo-lighting` (default off) swaps the studio
three-point rig for a warmer key + cool rim setup, for one-off
screenshots/comparisons. Threaded as a plain kwarg
(`run_rebuild` → `_run` → `build_static_prop` → `build_blender_script`
→ `CONFIG["demo_lighting"]` → `setup_studio_lights(..., demo=True)`);
it never touches the stored spec/style, so evaluation renders from
plain `mason build`/`mason rebuild` stay comparable across iterations.

### 2i. Still on hold: kits

- **Kits** — a manifest grouping several already-built assets (e.g.
  "cafe furniture set") into one `mason export` call, building on the
  per-asset manifest-merge logic already in `pipelines/export.py`.
- **Booleans** — single `cutout: {target}` shipped. Nested CSG stays
  out until a concrete asset needs it.

Krita stamps now include `bond`, `dapple`, `vignette`, and `figure`,
plus `shape: ellipse` and `pixels` + `keys` on `layered_raster`.
Further paint tools wait until those stall a real poster or UI.

Kits stay deferred until a concrete asset needs them.
