---
name: mason
description: >-
  Builds game assets with the Mason CLI: 3D props, buildings,
  sprites, rasters, textures, and kits. Use when the user asks
  for a prop, crate, sprite, pixel art, poster, palette,
  reference image, or to export a model into a game. Installs
  the Mason CLI when it is missing and initializes the project.
compatibility: >-
  Python 3.12+. Blender 4+ is required for 3D. Krita, Aseprite,
  and ImageMagick are optional.
metadata:
  mason_version: "0.1.0"
---

# Mason

The user describes the object. You write the YAML spec and run
the CLI. Do not open Blender, Krita, or Aseprite.

## Setup

1. Run `mason --version`.
   If the command is missing, install it and continue:

   ```bash
   uv tool install "git+https://github.com/Unveil-gg/mason.git"
   ```

2. Compare `mason --version` to `mason_version` in this file's
   frontmatter. If the CLI is older, stop and tell the user to
   upgrade Mason.
3. If the directory has no `mason.yaml`, run `mason init` at the
   git root, or in the current directory when there is no git root.
4. Run `mason doctor --json` once per machine per session.
   3D needs Blender.

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
5. Run `mason export <id> --to <dir>` when the user wants files
   in the game. A kit is `mason export --kit <id> --to <dir>`.

## Rules

- Use `--json` on Mason commands.
- A clean process exit is not success. Read validation and the
  primary preview.
- Shapes, recipes, and stamps come from `mason vocab --json`,
  not from memory.
