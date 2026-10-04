# 2D harness gaps

Noted while painting a watercolor viaduct in
`.mason/jobs/bridge_troubled_water`. The picture had to be drawn
in a job-local numpy script. The CLI then only files the PNG.

## Krita

`layered_raster` can fill rects and ellipses, set text, stamp, and
evaluate a formula. Stamps are `l_corner`, `gem`, `rule`, `bond`,
`dapple`, `vignette`, `figure`, `speckle`, `courses`, and `pavers`.
`courses` is a bond of rectangles, not a stone wash. Nothing in
that list is a brush stroke.

kritarunner can create a document and call `setPixelData`.
`-s` still imports a module name from `%APPDATA%\kritarunner`.
`_install_krita_script` writes a loader there that `runpy`s
the job's `build.py`, so the script that runs is the one in
the job. A full path passed to `-s` still does not load.
Fills, stamps, text, and baked stroke dabs do not need a view.

A freehand stroke uses the paintop, and the paintop needs a
`KisView`. `kritarunner` never creates one, so `activeWindow()`
is empty. `QT_QPA_PLATFORM=offscreen` does not fix it. The brush
wants a real canvas. That launch is not wired yet. It waits
until a spec sets `metadata.krita_paintop` to `"1"`.
`mason build --allow-window` is that yes. The preset is
still not called: the build stops with `paintop_unwired`
instead of opening a window.

When it is wired, ask before opening a window. Name the app and
the one step. A yes is `--allow-window` on that invocation. No
flag, a no, or a non-interactive run stays headless. If the step
cannot finish headless, stop. Do not hang on a prompt, and do
not open a window. A confirmed Krita run is `krita --nosplash`,
not `kritarunner`. The script waits for `windowCreated`, calls
`addView`, saves, and quits even if it throws.

Blender meshes and renders stay on `blender --background
--python`. Sculpt, grease pencil, and texture paint need a
`VIEW_3D`, which `--background` never creates. Drop
`--background` only after that failure, and only with
`--allow-window`: `blender --python build.py`, then
`bpy.ops.wm.quit_blender()`. The same confirm rule applies.
ImageMagick and `aseprite -b --script` never need a window.

An image layer is one paint layer. `setPixelData` places it
at the rect. It is not also a file layer at the origin.

`mason paint` copies an underlay and adds empty paint, mask, and
lettering layers. It does not put marks on them.

## ImageMagick

Doctor finds ImageMagick, and the image-process pipeline can run
it. Nothing in the illustrated path uses it to granulate, distort,
or lay a paper texture. Those steps still happen outside the CLI.

## Passes

The viaduct needs separate passes: sky in the openings, river
under the arches, foam where the water hits stone, a cast
shadow, a broken reflection, and the masonry. A fill does not
know which of those it is, and it does not know a pier occludes
it. There is no stamp for a cast shadow or a reflection.

kritarunner stacks paint layers and tries to save each one
under `output/layers/`. The build lists those PNGs on the
result as `layer_<name>`. `previews/silhouette.png` is a
black-on-white read of `full.png`. The illustrated workflow
still flattens the beauty preview to one PNG.

Noise is not a style operation. ImageMagick can add grain to a
finished PNG. It cannot granulate one pass and leave the sky
alone.

A crash of white where an arch meets the river is a path of
dabs. A `stroke` layer (`points`, `radius`, `spacing`,
`strength`) bakes those discs to a PNG before Krita. A
Krita preset still needs a view. `mason build --allow-window`
is the confirm, and a spec with `metadata.krita_paintop: "1"`
stops instead of opening a window, because that path is not
wired.

## What this picture needed

A side elevation in one-point perspective: a horizon, one
vanishing point, and orthoginals (`y = mx + b`) for the deck,
the water, and the footings. Arch size is `exp(-k z)`. Stroke
weight and contrast thin out toward that point. The river is
one plane on that water line, not a separate level per arch.
Nothing in `layered_raster` is a horizon, a vanishing point,
or a ground plane. The ragged edge, the reflection, and the
pigment in the paper are numpy. They are not a style key and
not a layer type.

## Understanding

`geometric_plan.landmarks` can name `waterline`,
`opening.background`, `arch.contact_foam`, and
`bridge.silhouette`. `mason evaluate` resolves those ids.
Nothing in the plan compiles a horizon or a water plane
into the raster. The painter still has to honor the notes.

## Evaluation

`mason evaluate` stores the critic JSON and returns `next`.
It does not open the preview. Illustrated scores may include
`layering`, `background_read`, and `contact_read`. A
layered raster writes `previews/silhouette.png`. Silhouette
IoU appears in `next.measured` only when ingest stored
metrics. `represents_style` is still a yes or no.

## Already fine

`mason doctor`, `mason route`, and a kritarunner save of a
finished PNG work on this machine. A style file can name a color.
It cannot name a painting process.
