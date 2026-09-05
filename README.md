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
| Aseprite | discovery only in v0.1 | No |

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
`simple_sign`, `simple_fence`. Raster: `simple_panel`, `menu_card`
(text + image import). Previews include a 2×2 `contact_sheet.png`.
EEVEE is preferred; Mason falls back to Cycles CPU if EEVEE fails.

## Commands

| Command | Purpose |
| --- | --- |
| `mason doctor` | Detect tools and capabilities |
| `mason init` | Create `mason.yaml`, `.mason/`, `styles/default.yaml` |
| `mason build <spec.yaml>` | Generate, run the tool, preview, validate |
| `mason rebuild <asset-id>` | Rebuild from the stored job / original spec |
| `mason preview <asset-id>` | Re-render previews only |
| `mason inspect <asset-id>` | Job state, paths, metrics |
| `mason validate <asset-id>` | Re-read stored validation |
| `mason list` | Jobs in this project |
| `mason tools scan` | Rediscover and store new tool paths |
| `mason config get/set` | Machine config (`tools.blender.path`, …) |

Add `--json` to any of these for agent-friendly output.

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

- 3D primitives are boxes only (no cylinders/planes yet).
- Raster generation is palette fills and rectangles, not painting.
- Aseprite is discovery-only.
- Previews use Cycles CPU (reliable headless, slower than EEVEE).
- No Godot export, no in-process LLM, no bundled creative apps.

## Roadmap

- More 3D primitives and richer part ops
- Krita text/import/paint hooks
- Aseprite sprite sheets + animation metadata
- Optional Godot SpriteFrames / in-engine preview
- EEVEE preview path where the GPU context is available
