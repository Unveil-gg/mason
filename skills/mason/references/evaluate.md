# mason evaluate

Write JSON and pass the file to `mason evaluate <id> <file>`.
A failed review must set `primary_failure` and at least one
`correction_targets` entry.

```json
{
  "passed": false,
  "mode": "beauty",
  "represents_object": true,
  "represents_style": true,
  "stage": "blockout",
  "ship": false,
  "primary_failure": "The lid is taller than the box.",
  "correction_targets": [{"part": "lid", "landmark": "top"}],
  "scores": {
    "proportions": 4,
    "secondary_forms": 5,
    "tertiary_detail": 5,
    "materials": 6,
    "visual_hierarchy": 5,
    "style_consistency": 6,
    "game_readability": 5
  },
  "discrepancies": [
    {
      "rank": "critical",
      "category": "proportion",
      "description": "Lid reads as a second crate.",
      "geometric_intent": "Lid is a thin cap on the box.",
      "landmark": "lid.top"
    }
  ],
  "view_scores": [{"view": "three_quarter", "score": 4}],
  "compare": {
    "improves": [],
    "worsens": ["silhouette"],
    "verdict": "reject"
  }
}
```

`mode` is `beauty` or `silhouette`. `stage` is `blockout`,
`silhouette`, `secondary`, `tertiary`, `material`, or `final`.
Discrepancy `rank` is `critical`, `major`, or `minor`.
`compare.verdict` is `accept`, `reject`, or `try_again`.
Scores are integers from 1 to 10.
