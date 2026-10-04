---
name: mason
description: >-
  Builds game assets with the Mason CLI: 3D props and 2D art
  (sprites, pixel art, tilesets, UI, icons, posters, labels,
  textures, palettes). Use when the user asks for a crate, kit,
  Krita or Aseprite work, a reference image, or to export into
  Godot or Unreal. Installs the Mason CLI when it is missing.
compatibility: >-
  Python 3.12+. Blender 4+ is required for 3D. Krita, Aseprite,
  and ImageMagick are optional for 2D.
metadata:
  mason_version: "0.1.0"
---

# Mason

The user describes the object. You write the YAML spec and run
the CLI. Do not open Blender, Krita, or Aseprite. The spec is
the source. A GUI edit is not a reproducible job.

## Setup

Skip this block when `mason --version` works and the repo has
`mason.yaml`. Then only `mason doctor --json` once per session.

Otherwise:

1. If `mason` is missing:

   ```bash
   uv tool install "git+https://github.com/Unveil-gg/mason.git"
   ```

2. Compare `mason --version` to `mason_version` in this file's
   frontmatter. If the CLI is older, stop and tell the user to
   upgrade Mason.
3. If there is no `mason.yaml`, run `mason init` at the git
   root, or in the current directory when there is no git root.
4. Run `mason doctor --json` once per machine per session.
   3D needs Blender. 2D needs Krita or Aseprite as routed.

## Build

1. Run `mason route "<subject>" --json` and copy `workflow` onto
   the spec.
2. **Quick** when `decompose` is false and `required_refs` is
   empty (simple prop, texture, pixel, poster, import): write
   the spec, run `mason build <spec> --json`, and open only the
   preview named by `preview_roles.primary`. A palette or
   material change is another build. Do not write an evaluation.
3. **Directed** otherwise: run
   `mason vocab --workflow <kind> --json` and
   `mason style <name> --json`, then follow
   [references/workflow.md](references/workflow.md). Score with
   [references/evaluate.md](references/evaluate.md).
4. Specs name a style (`style: default`). Do not inline hex.
   `default` is built into the CLI. `styles/<name>.yaml` in the
   project overrides it.
5. Export when the user wants files in the game:
   `mason export <id> --to <dir> --engine godot|unreal`.
   A kit is `mason export --kit <id> --to <dir>`.
   Add `--optimize` to shrink the copy only. Use `--layout
   grouped` for engine folders (`models/` or `Meshes/`).
   Prefer `install_dir` in `mason.yaml` so later exports omit
   `--to`.

## Rules

- Use `--json` on Mason commands.
- Prefer the CLI, validation, project styles, and the iteration
  record. Those get more useful as models improve. Do not add a
  generator whose only job is to spare the model from the tool.
- A clean process exit is not success. Read validation and the
  primary preview.
- A failed review is one `primary_failure` and
  `correction_targets` naming a landmark, part, or layer on the
  job. Read `next` from `mason evaluate` or
  `mason history <id> --json --summary`. Scores are optional.
- Shapes, recipes, and stamps come from `mason vocab --json`,
  not from memory.
- Painter scripts, generated PNGs, and scratch specs go in
  `.mason/jobs/<id>/` (`output/`, `previews/`). Do not leave
  them at the repo root. `styles/<name>.yaml` stays in `styles/`.
- Holes in the 2D path (no brush stroke, headless Krita cannot
  play a preset) and in how a picture is judged are in
  [references/gaps.md](references/gaps.md).
