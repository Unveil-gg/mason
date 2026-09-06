<h1 align="center">
  <img src="docs/images/mason-logo.png" alt="Mason logo" width="176"><br>
  Mason
</h1>

<p align="center">
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.12+-3776AB?logo=python&logoColor=white" alt="Python 3.12+">
  </a>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey" alt="Platforms">
  <img src="https://img.shields.io/badge/version-0.1.0-blue" alt="Version 0.1.0">
</p>

---

<p align="center">
  <img src="docs/images/grand_mansion_contact_sheet.png" alt="Grand Mansion demo preview — front, side, top, and three-quarter views with demo lighting" width="640"><br>
  <sub><em>Grand Mansion — built with Mason + Grok 4.6 Fast (High Effort)</em></sub>
</p>

Mason is a local developer CLI that orchestrates **already installed**
creative tools. It does not bundle [Blender](https://www.blender.org/),
[Krita](https://krita.org/en/), [Aseprite](https://www.aseprite.org/), or
[ImageMagick](https://imagemagick.org/). Coding agents (Cursor, Claude Code,
Codex, and others) write structured asset specs; Mason runs the tools
headlessly, validates outputs, and writes previews the agent can inspect.

Mason itself has no LLM. The agent is the reasoning layer.

## Design philosophy

- Specs and generated scripts are source of truth.
- Binary/editor files are outputs and caches.
- Every build should be reproducible.
- Every asset is technically validated.
- Every visual asset produces previews.
- Every important command supports `--json` (JSON on stdout only).

## Supported OSes

Windows, macOS, and Linux. Tools are discovered via manual config, PATH,
and common install locations. They are **not** assumed to be on PATH.

## Installation

Python 3.12+. Prefer [uv](https://docs.astral.sh/uv/):

```bash
uv sync
uv run mason doctor
```

Editable install with pip:

```bash
pip install -e ".[dev]"
mason doctor
```

## Dependency model

Mason is a thin harness:

| Tool | Mason uses it for | Bundled? |
| --- | --- | --- |
| Blender 4.x | `static_prop` (3D parts → .blend/.glb + 4 previews) | No |
| Krita | `layered_raster` (.kra + PNG) | No |
| ImageMagick | `image_process` (resize, quantize, …) | No |
| Aseprite | `sprite_sheet` (.aseprite + PNG + frames.json) | No |

Install those applications yourself. Point Mason at them if needed:

```bash
mason config set tools.blender.path "C:/Program Files/Blender Foundation/Blender 4.5/blender.exe"
mason tools scan
```

Machine config lives at `%APPDATA%/Mason/config.yaml` on Windows and
`~/.config/mason/config.yaml` on macOS/Linux. Never put machine paths
in asset specs.

## How Mason finds Blender

1. `tools.blender.path` in machine config
2. `blender` on PATH
3. Common locations (`Program Files/Blender Foundation/*`,
   `/Applications/Blender.app/...`, `/usr/bin/blender`, …)

Then `blender --version` confirms the binary. Same pattern for Krita
(`krita` + `kritarunner`), ImageMagick (`magick`, then `convert`), and
Aseprite.

## Quick start

```bash
mason init
mason doctor
mason build examples/assets/simple_crate.yaml
mason inspect simple_crate --json
mason rebuild simple_crate
```

Krita panel + ImageMagick resize (if those tools are installed):

```bash
mason build examples/assets/simple_panel.yaml
mason build examples/assets/simple_panel_512.yaml
```

`simple_panel_512.yaml` reads `examples/ref/swatch.png` so ImageMagick
can be tried without Krita.

## Example asset YAML

```yaml
type: static_prop
id: simple_crate
name: Simple Crate
dimensions: {width: 0.6, depth: 0.6, height: 0.6}
style: default
geometry:
  recipe: crate
  bevel: true
materials:
  primary: wood_dark
export:
  format: glb
  save_blend: true
```

**Recipes** (`crate`, `shelf`, `table`, `hydrant`, `cart`, `house`,
`tree`, `pool`, `estate`) are named clusters, not the path to a
beautiful asset. The source of truth is `parts` plus a style profile.
Add a recipe only after the same cluster appears three times. Beauty
comes from style (palette, families, bevel, tile size), secondary
forms, stamps, and the critic loop — not from a longer recipe list.

3D examples: `simple_crate`, `simple_shelf`, `simple_post`,
`simple_sign`, `simple_fence`, `textured_crate` (tiled material),
`crate_with_label`, `noir_billboard` (a two-post highway billboard with
a decal face), `shopping_cart` (flared wire cart, plus a `black`
palette variant), `grand_mansion` (estate recipe). Raster:
`simple_panel`, `menu_card`, `plank_texture`, `shipping_label`,
`noir_billboard_face`, `rpg_status_frame`. Sprite: `barbarian`
(`sprite_sheet`: idle ×2, walk ×4, attack ×3 on a 4×3 grid) and
`swordsman` (walk ×4, sword-swing attack ×3). Previews include a 2×2
`contact_sheet.png`. EEVEE is preferred; Mason falls back to Cycles
CPU if EEVEE fails.

## Textures on 3D parts

A part can use a 2D asset's PNG as its material instead of a flat
palette color:

```yaml
geometry:
  parts:
    - name: crate
      size: [0.6, 0.6, 0.6]
      location: [0, 0, 0.3]
      texture:
        asset: plank_texture   # another asset id, built beforehand
        file: output/asset.png # or: texture: {path: "textures/x.png"}
```

Build order matters: `plank_texture` (a `layered_raster` job) must be
built before `textured_crate` references it. Two UV modes, chosen
automatically by shape:

- `box`/`cylinder` parts get a deterministic cube projection
  (`bpy.ops.uv.cube_project`), sized by `textures.tile_size` in the
  style profile (world units per tile), so tileable materials (wood,
  stone, fabric) repeat consistently across differently-sized props
  without per-asset tuning.
- A textured `plane` part is treated as a **decal** (a label, sign, or
  billboard face): its single quad gets a stretched 0..1 UV so the
  whole image shows once, undistorted by tile size. `textures.wrap`
  (`repeat`/`clamp`) only affects the tiled case.

Try it: `mason build examples/assets/plank_texture.yaml`, then
`mason build examples/assets/textured_crate.yaml` (tiled material), or
`mason build examples/assets/shipping_label.yaml` then
`mason build examples/assets/crate_with_label.yaml` (decal face).
For the quality-loop example: `mason build examples/assets/fire_hydrant.yaml`,
then inspect the beauty three-quarter render first. Use clay for
geometry and silhouettes only when readability is in doubt.

## Tuning a style

Edit `styles/<name>.yaml`. Specs only name the style; they should not
inline hex or PBR. Useful knobs:

| Knob | What it changes |
| --- | --- |
| `palette.*` | Named colors used by parts and raster layers |
| `materials.families.<name>.roughness` / `metallic` | PBR |
| `materials.families.<name>.variation` | How much solid color mottles |
| `materials.families.<name>.noise_scale` | Grain frequency (higher = finer) |
| `materials.families.<name>.tile_size` | World meters per albedo tile |
| `materials.families.<name>.albedo` | Shared 2D tile (`asset` + `file`) |
| `geometry.bevel_width` / `bevel_segments` | Edge softness |
| `textures.tile_size` / `wrap` | Default UV repeat |
| `lighting.preset` | `neutral_studio` or `high_key` |
| `render.resolution` / `samples` / `engine` | Preview quality |

Organic families (`lawn`, `foliage`) should prefer solid color +
`variation` / `noise_scale` over a coarse tiled albedo. Masonry and
roofing keep bond-stamped tiles.

## Material variants

A `static_prop` spec can fan out into palette-swap siblings from one
`mason build` call, instead of hand-copying the whole spec:

```yaml
materials:
  primary: steel
  palette_overrides:      # optional: tweak this asset's own palette
    steel: "#8A9196"

variants:
  - suffix: black          # -> builds shopping_cart_black as well
    palette_overrides:
      steel: "#2B2E31"
      steel_dark: "#1A1C1E"
  - suffix: brass
    primary: brass          # swap the whole material key instead
```

Each variant becomes its own stored job (`<id>_<suffix>`) with its own
auto-written sibling spec (`<id>_<suffix>.yaml` next to the parent),
so it is independently inspectable and rebuildable. `palette_overrides`
patches specific palette keys for that job only; it never edits
`styles/*.yaml`. See `examples/assets/shopping_cart.yaml`.

## Demo lighting for screenshots

`mason preview <id>` normally uses the same neutral studio rig every
time, so evaluation renders stay comparable across iterations. For a
one-off nicer screenshot (docs, comparisons), pass `--demo-lighting`
to swap in a warmer key light + a subtle rim light:

```bash
mason preview grand_mansion --demo-lighting
```

This only affects that render call; it does not change the stored
spec, style, or `mason build`/`mason rebuild` output. Run
`mason preview <id>` again (no flag) to go back to neutral lighting.

## Raster stamps and sprites

Krita `layered_raster` layers: fill, `shape: rect|ellipse`, text,
image import, `pixels` + `keys`, and stamps (`l_corner`, `gem`,
`rule`, `bond`, `dapple`, `vignette`, `figure`).

Aseprite `sprite_sheet` is the animation path. Prefer `pixels` +
`keys` and a shared style palette so idle / walk / attack stay
cohesive. Mason writes `output/asset.png`, `output/frames.json`, and
an optional `.aseprite` source.

```bash
mason build examples/assets/barbarian.yaml
mason build examples/assets/swordsman.yaml
mason inspect swordsman --json
```

Example agent prompts:

- *32×32 NES hero, side-on, facing right. Style `nes`. Animations:
  idle ×2, walk ×4, attack ×3. One `pixels` map per frame, shared
  `keys`.*
- *16×16 coin sparkle, 4 frames, loop. Style palette only, no new
  hex.*
- *Rebuild `barbarian` walk so the stride reads at 4× preview scale.*

`mason ingest <image> --asset <id>` extracts a **silhouette and
height/width ratio** for the critic loop. It does not write a YAML
spec or a mesh. Image → analysis notes → you write the spec.

## Commands

| Command | Purpose |
| --- | --- |
| `mason doctor` | Detect tools and capabilities |
| `mason init` | Create `mason.yaml`, `.mason/`, `styles/default.yaml` |
| `mason build <spec.yaml>` | Generate, run the tool, preview, validate |
| `mason rebuild <asset-id>` | Rebuild from the stored job / original spec |
| `mason preview <asset-id>` | Re-render previews only |
| `mason inspect <asset-id>` | Job state, art direction, previews, metrics |
| `mason stats [id]` | Triangle / mesh / material counts |
| `mason validate <asset-id>` | Re-read stored validation |
| `mason evaluate <id> <json>` | Store a critic visual evaluation |
| `mason history <asset-id>` | Iteration snapshots and evaluations |
| `mason export <asset-id>` | Copy finished outputs into another project |
| `mason vocab` | Shapes, components, recipes, stamps, families |
| `mason ingest <image>` | Silhouette + ratio from concept art |
| `mason compare <id>` | Write `previews/compare.png` |
| `mason clean [id]` | Delete stored jobs (all, or one id) |
| `mason list` | Jobs in this project |
| `mason tools scan` | Rediscover and store new tool paths |
| `mason config get/set` | Machine config (`tools.blender.path`, …) |

Add `--json` to any of these for agent-friendly output.

## Exporting into another project

`mason build`/`rebuild` only write inside `.mason/jobs/<id>/`. To land the
finished `.glb`/`.png` in a consuming project (e.g. a sibling Godot repo),
use `mason export`. It never copies working files (`.blend`/`.kra`) or
previews.

```bash
mason export simple_crate --to ../my_game/res/models
mason export simple_crate --engine godot   # models/, textures/ subfolders
```

The destination can also be set once instead of passed every time:
`install_dir` in `mason.yaml`, or `export.install_to` in an individual
asset spec (spec setting wins over the project default; `--to` wins over
both).

Each export merges an entry into `mason_manifest.json` at the
destination root, so an agent (or you) can see what Mason has put there
without needing the Mason project itself. Sprite sheets also copy
`{id}_frames.json` (rects, durations, loop flags). 3D exports include
`bounds` on the manifest entry when the last build recorded them.
Mason does **not** write
Godot `.import` sidecars: since Godot 4.0, texture filter/repeat moved
out of the importer into project settings and per-`CanvasItem`
overrides, so a hand-written `.import` file would be silently wrong.
For pixel art, set Project Settings → Rendering → Textures → Canvas
Textures → Default Texture Filter to Nearest instead.

## JSON mode

```bash
mason doctor --json
mason build examples/assets/simple_crate.yaml --json
```

Stdout is valid JSON only. Diagnostics go to stderr. Errors look like:

```json
{"success": false, "error": {"code": "blender_missing", "message": "..."}}
```

## Directory structure

```
mason.yaml
styles/default.yaml
.mason/jobs/<asset-id>/
  asset.yaml
  resolved_style.yaml
  build.py
  stdout.log
  stderr.log
  output/          # .blend .glb .kra .png
  previews/        # front/side/top/three_quarter or full.png
  validation.json
  result.json
```

## How agents should interact

See [AGENTS.md](AGENTS.md). Short version: `doctor --json`, edit a spec,
`build --json`, **open the preview images**, then iterate. Do not treat
a zero exit code as “it looks right.”

## Current limitations (v0.1)

- Raster generation is palette fills, rects/ellipses, text, stamps,
  image import, and per-pixel maps. Not freehand painting.
- `mason ingest` is silhouette + ratio only. There is no image → YAML
  → mesh compiler.
- `mason export` copies files and a manifest only; it does not
  construct Godot scenes/resources or write `.import` sidecars.
- No in-process LLM, no bundled creative apps.

## Roadmap

Design notes: [docs/roadmap.md](docs/roadmap.md).

- In-engine / Godot preview (`preview_roles.context`) — hook only
- Multi-asset kits (one export of a named set)
- Optional richer Krita brushes — only if stamps + pixels stall
- Image-to-spec stays an agent skill, not a Mason command
