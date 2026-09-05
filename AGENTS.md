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

Before generating assets:

1. Run `mason doctor --json`.
2. Confirm the required capabilities are available.
3. Read the project's Mason style profile.
4. Create or modify an AssetSpec YAML.
5. Run `mason build <spec> --json`.
6. Check validation results.
7. Open and inspect generated preview images.
8. If the asset does not visually satisfy the request, modify the spec
   and rebuild.
9. Continue until technical validation passes and the visual result
   is acceptable.
10. Treat asset.yaml and build.py as reproducible source artifacts.

Important rules:

- Do not manually operate Blender or Krita when Mason can invoke them.
- Prefer editing specs/generator source and rebuilding.
- Do not assume a successful tool exit means the asset looks correct.
- Always inspect previews.
- Do not ignore validation failures.
- Use `--json` when operating autonomously.
- When a style palette matters for rasters, follow generation with
  an `image_process` quantize step.

Asset types:

- `static_prop` — Blender parts (`box`, `cylinder`, `plane`) with
  optional `parent`, `inset`, and linear `array`. Recipes
  (crate/shelf/table) expand into parts.
- `layered_raster` — Krita layers: fill, text, or imported image,
  plus optional `role`. Source is `.kra`.
- `image_process` — ImageMagick resize/crop/trim/composite/quantize/convert

3D previews: front, side, top, three_quarter, plus `contact_sheet.png`.
Raster previews: previews/full.png.
Compare previews to the spec, then edit the spec or generated script
and `mason rebuild <id> --json`.
