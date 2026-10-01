# Directed Mason loop

Use this when `mason route` sets `decompose` or returns any
`required_refs`. Also use it for buildings, characters, sculpture,
turned profiles, and clothing.

Separate creator and critic, even in one model. The creator writes
direction, plan, and geometry. The critic scores previews and looks
for reasons not to ship.

## Author

1. If the user supplied references, run
   `mason ingest <image> --asset <id> --view side|front|three_quarter --json`.
   Ingest measures the image. It does not build a mesh.
   Skip decomposition when the subject is one or two masses and
   one silhouette. Otherwise `mason decompose`, model each part,
   then `mason assemble`.
2. Write `art_direction` (subject, usage, silhouette, focal point,
   gameplay read, materials). Run `mason plan <id> --json` before
   parts.
3. Write `geometric_plan`: masses, proportions, landmarks bound to
   a part and a node, `critical_views`, and `stage`
   (`blockout`, `silhouette`, `secondary`, `tertiary`, `material`,
   `final`). Record techniques on `construction_plan.techniques`.
4. At `stage: blockout`, build primary masses only. Solve the 2D
   profile before grooves, eyes, or materials when recognition is
   silhouette.
5. Run `mason build <spec> --json`.

## Critique

1. If recognition is silhouette, open `preview_roles.silhouette`
   first. Ignore materials.
2. Then open `preview_roles.primary`. Use `clay_three_quarter.png`
   for organic form. Open `front`, `side`, and `top` for structure.
3. Write an evaluation with
   [evaluate.md](evaluate.md) and run
   `mason evaluate <id> <evaluation.json>`.
4. Do not advance `stage` while a critical discrepancy remains.
   `represents_object: false` is a reject. Accept only when the
   candidate is better and no critical view or identity score
   dropped. Otherwise `mason revert`.
5. Record `actions_taken` on the next evaluation. Use
   `mason history <id> --json --summary`.
6. Stop when validation passes, no critical discrepancy remains,
   the beauty preview looks ready, and `ship` is true.
7. Export only when the user wants the files in the game.
   `mason export <id> --to <dir> --engine godot|unreal`.
   `--optimize` shrinks the copy, not the job.

`asset.yaml`, `art_direction.yaml`, `construction_plan.yaml`,
`geometric_plan.yaml`, `decomposition.yaml`, and `build.py` in the
job directory are reproducible source. Jobs live under `.mason/`
and stay out of git.
