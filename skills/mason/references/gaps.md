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

kritarunner can create a document, add a file layer, and call
`setPixelData`. `-s` loads a module from `%APPDATA%\kritarunner`
(see `_install_krita_script`). A full path to a script in the job
does not load, so the layered document is never written. A freehand
stroke uses the paintop, and the paintop needs a view. A headless
script cannot play a watercolor preset along a path.

A layer that carries an image is added twice in
`script_builder.py`: a file layer, which lands at the origin, and
a paint layer at the rect. A wash that is not full-canvas ghosts
into the corner.

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

kritarunner can stack paint layers if the script calls
`setPixelData` itself. The illustrated workflow still flattens
to one preview and does not round-trip that stack. Putting the
same pixels in as image layers ghosts them, because each image
is also placed at the origin.

Noise is not a style operation. ImageMagick can add grain to a
finished PNG. It cannot granulate one pass and leave the sky
alone.

A crash of white where an arch meets the river is a path of
dabs. A fill cannot break that path or leave paper in the
tip. The numpy painter stamps discs along the line because
no layer type is a stroke.

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

The directed loop asks the same model to paint and then
score. Nothing measures the picture. A silhouette can read
as a bridge while the water sits too high, the distance is
only a pale wash, and no white marks the line where stone
meets the river. Those are contact and depth facts. They
are not in the spec. `mason plan` has no slot for a water
plane, a far hill, or a crash line, so the next pass has
nothing to check them against except the last complaint.

## Evaluation

`mason evaluate` stores the JSON the critic wrote. It does
not open the preview. The score names (proportions,
materials, a three-quarter view) describe a 3D prop. This
job has no separate silhouette render, so "open the
silhouette first" has nothing to open. `represents_style`
is a yes or no. It does not test brush handling, bare
paper, or whether a background reads through an opening.
"Water too high" has no landmark: there is no part named
water and no node for the spring line. `compare` can say
the silhouette improved and still accept a flat haze,
because contrast and contact foam are not scores.

## Already fine

`mason doctor`, `mason route`, and a kritarunner save of a
finished PNG work on this machine. A style file can name a color.
It cannot name a painting process.
