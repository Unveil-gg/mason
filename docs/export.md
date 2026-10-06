# Export

Builds stay in `.mason/jobs/<id>/`. Export copies the finished
`.glb` or `.png` (and a sprite's `frames.json`) into another project.
It skips `.blend`, `.kra`, and previews.

```bash
mason export simple_crate --to ../my_game/res
mason export simple_crate --layout grouped --engine godot
mason export simple_crate --layout grouped --engine unreal
mason export simple_crate --to ../my_game/res --optimize
```

## Destination precedence

`--to` wins over `export.install_to` on the spec, which wins over
`install_dir` in `mason.yaml`. Set `install_dir` once if this
project always exports to the same game folder.

## Layout and optimization

`--layout grouped` uses `models/` and `textures/` for Godot, or
`Meshes/` and `Textures/` for Unreal. `--optimize` shrinks the copy
only (palette-quantize PNG; `gltfpack` on GLB if that tool is on
PATH). Job files stay untouched.

Each export updates `mason_manifest.json` at the destination.
Mason does not write Godot `.import` or Unreal `.uasset` files.
For pixel art, set the Godot project’s default texture filter to
Nearest.

## Kits

A kit is a list of jobs you have already built. Export does not
build them or merge them into one GLB.

```yaml
# kits/cafe.yaml
id: cafe
name: Cafe furniture
members: [simple_crate, simple_shelf]
```

```bash
mason export --kit cafe --to ../my_game/res/models --engine godot
```
