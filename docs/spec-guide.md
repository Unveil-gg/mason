# Spec guide

Beyond the [README quick start](../README.md#quick-start): recipes,
textures, styles, variants, rasters, and ingest.

## 3D props

Recipes (`crate`, `shelf`, `table`, `hydrant`, `cart`, `house`,
`tree`, `pool`, `estate`) are shortcuts. New shapes are `parts`
plus a style. EEVEE is preferred; Mason falls back to Cycles CPU.

A part can use another job's PNG instead of a flat color. Build
the raster first. Boxes and cylinders tile by `textures.tile_size`.
A textured plane is a decal (one stretched image).

```yaml
geometry:
  parts:
    - name: crate
      size: [0.6, 0.6, 0.6]
      location: [0, 0, 0.3]
      texture:
        asset: plank_texture
        file: output/asset.png
```

Edit `styles/<name>.yaml` for palette, family roughness, bevel,
and tile size. Specs name the style. They do not inline hex.

`variants` on a `static_prop` builds sibling jobs (`<id>_<suffix>`)
from one spec. `palette_overrides` patches that job only.

```bash
mason preview <id> --demo-lighting   # one warmer screenshot
```

That flag does not change the spec or later builds.

## 2D rasters and sprites

Raster layers are fills, shapes, text, stamps, and `pixels` +
`keys`. A sprite sheet is the same pixels, one map per frame, on
the style palette.

## Ingest

`mason ingest <image> --asset <id>` measures a reference and, for
a new id, writes `assets/<id>.yaml`. It does not build a mesh. You
still write `parts` or `layers`.
