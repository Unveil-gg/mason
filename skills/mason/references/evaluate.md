# mason evaluate

Write JSON and pass the file to `mason evaluate <id> <file>`.
Set `compare.verdict` to `accept`, `reject`, or `try_again`.
A failed review must set `primary_failure` (one sentence) and
at least one `correction_targets` entry. Each target names a
landmark, part, or layer that already exists on the job.

The default JSON is `next` and `checkpoint`. `next` is that
failure, the targets, any name that did not resolve, the
primary preview, and measured validation plus silhouette IoU
when those files exist. `--full` prints the stored evaluation.
The next edit reads `next`, or
`mason history <id> --json --summary`, and opens only
`primary_preview`.

Scores are optional integers from 1 to 10. Send a verdict
plus only the scores for the workflow. Extra scores are
allowed.

- Prop: `proportions`, `silhouette`, `game_readability`.
- Illustrated and pixel: `game_readability`,
  `style_consistency`. Illustrated may also send
  `layering`, `background_read`, and `contact_read`.
  Silhouette IoU is optional unless ingest wrote
  `silhouette_metrics.json`. A layered raster also
  writes `previews/silhouette.png`.

`mode` is `beauty` or `silhouette`. `stage` is `blockout`,
`silhouette`, `secondary`, `tertiary`, `material`, or `final`.

Prop:

```json
{
  "passed": false,
  "ship": false,
  "primary_failure": "The lid is taller than the box.",
  "correction_targets": [{"part": "lid", "landmark": "top"}],
  "scores": {
    "proportions": 4,
    "silhouette": 4,
    "game_readability": 5
  },
  "compare": {"verdict": "reject"}
}
```

Illustrated. `waterline` is a landmark id. A layer named
`river` is the same kind of target.

```json
{
  "passed": false,
  "ship": false,
  "primary_failure": "The river sits above the waterline.",
  "correction_targets": [{"landmark": "waterline"}],
  "scores": {
    "game_readability": 4,
    "style_consistency": 5
  },
  "compare": {"verdict": "reject"}
}
```
