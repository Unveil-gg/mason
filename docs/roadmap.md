# Mason roadmap: visual loop + Aseprite pipeline

Design specs for the two items deferred from the texture-contract pass.
Nothing here is implemented yet; this is the plan to implement against.

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

Once 2a-2d land, `examples/assets/barbarian_sheet.yaml` and its nine
`layered_raster` frame files (`barbarian_idle`, `barbarian_idle2`,
`barbarian_walk1-4`, `barbarian_attack`, `barbarian_attack2-3`) get
replaced by one `barbarian.yaml` `sprite_sheet` spec with three
animations, and the old files are deleted (no duplicate implementation
left behind). Not done in this pass — flagged as the concrete
migration once the pipeline above exists.

### 2f. Still on hold: material variants / booleans / kits

- **Material variants** — one `AssetSpec` fans out into several jobs
  with palette overrides (e.g. a crate in `wood_dark` and
  `wood_light`) instead of duplicating the whole spec file. Likely a
  `variants: [{suffix, palette_overrides}]` block on `static_prop`/
  `layered_raster`.
- **Booleans** — Blender boolean modifiers (cut a window into a wall,
  notch a shelf board), via a new `part.op.boolean: {with, mode}`.
  Deferred: it multiplies the geometry-validation surface
  (self-intersection, non-manifold results) and no concrete asset has
  needed it yet.
- **Kits** — a manifest grouping several already-built assets (e.g.
  "cafe furniture set") into one `mason export` call, building on the
  per-asset manifest-merge logic already in `pipelines/export.py`.

All three stay deferred until a concrete asset needs them, per "no new
patterns without exhausting the existing implementation first."
