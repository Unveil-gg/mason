# Mason

Mason is a local developer CLI that orchestrates **already installed**
creative tools. It does not bundle Blender, Krita, Aseprite, or
ImageMagick. Coding agents (Cursor, Claude Code, Codex, and others)
write structured asset specs; Mason runs the tools headlessly, validates
outputs, and writes previews the agent can inspect.

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

`crate`, `shelf`, and `table` are optional **recipes**. The source of
truth is a list of `parts` (`box`, `cylinder`, `plane`) with optional
`parent`, `inset`, and linear `array`.

3D examples: `simple_crate`, `simple_shelf`, `simple_post`,
`simple_sign`, `simple_fence`, `textured_crate` (tiled material),
`crate_with_label`, `noir_billboard` (a two-post highway billboard with
a decal face). Raster: `simple_panel`, `menu_card` (text + image
import), `plank_texture` (tileable material), `shipping_label`,
`noir_billboard_face` (black-and-white movie-poster decal),
`barbarian` (`sprite_sheet`: idle ×2, walk ×4, attack ×3 on a 4×3
grid, plus `frames.json`). Previews include a 2×2
`contact_sheet.png`. EEVEE is preferred; Mason falls back to Cycles CPU
if EEVEE fails.

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

- Raster generation is palette fills, rects, text, stamps, image
  import, and per-pixel maps. Not freehand painting.
- `mason export` copies files and a manifest only; it does not
  construct Godot scenes/resources or write `.import` sidecars.
- No in-process LLM, no bundled creative apps.

## Roadmap

Design notes: [docs/roadmap.md](docs/roadmap.md).

- In-engine / Godot preview (`preview_roles.context`) — hook only
- Richer Krita paint tools beyond fill/text/stamp/image layers
- Multi-asset kits (shared atlas families beyond one entry)
