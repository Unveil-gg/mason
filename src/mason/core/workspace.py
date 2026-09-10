"""Project root discovery and mason init."""

from __future__ import annotations

from pathlib import Path

from mason.core.config import ProjectConfig, save_project_config
from mason.core.styles import DEFAULT_STYLE_YAML
from mason.errors import MasonError

MASON_WORKFLOW = """
# Mason Agent Workflow

Separate creator and critic even if you are one model.

1. Run `mason doctor --json`.
2. Confirm the required capabilities are available.
3. Run `mason vocab --json` and read the style profile.
4. If references exist, ingest them with --view and write
   reference_analysis (silhouettes, profile, landmarks).
5. Write `art_direction` (forms, usage, silhouette, materials).
6. Write geometric_plan (masses, silhouette, landmarks+uv,
   critical_views, stage). Intent only. Recognition is not
   ship; style/type must match. Profile first when silhouette
   dominates; no secondary detail until the ortho profile holds.
7. Block out with primitives, then snap + bodies remesh
   (inflate). skin is optional (skeleton pipes / blob spheres).
   Record techniques on construction_plan. Intent only.
8. Create or modify the AssetSpec YAML. Blockout first when
   silhouette dominates recognition.
9. Run `mason build <spec> --json`.
10. Check technical validation. Do not ignore failures.
11. If recognition is silhouette, inspect preview_roles.silhouette
    first. Ignore materials and tiny details.
12. Inspect preview_roles.primary after the silhouette holds
    (worn.png for garments, else three_quarter).
13. Inspect clay_three_quarter.png if geometry needs review.
14. Evaluate vs current_best (view_scores + silhouette_metrics
    + compare verdict). Reject if identity, a critical view,
    or IoU dropped, or represents_object is false.
    Continuity cannot beat a worse silhouette. Newest is
    not best. Revert restores the GLB.
    Restart a failing region; or try best-of-N.
    Do not advance stage while critical issues remain.
15. Move named landmarks, record actions_taken, rebuild.
16. Repeat until validation passes and evaluation `ship` is true.
17. Treat asset.yaml, geometric_plan.yaml, construction_plan.yaml,
    and build.py as reproducible source.

Important rules:

- Mason drives Blender only through generated bpy scripts.
- Do not manually operate Blender, Krita, or Aseprite when Mason can invoke them.
- Prefer editing specs/generator source and rebuilding.
- Do not assume a successful tool exit means the asset looks correct.
- Always inspect previews. Beauty three-quarter first.
- Do not ignore validation failures.
- Use `--json` when operating autonomously.
- When a style palette matters for rasters, follow generation with
  an `image_process` quantize step.
"""


def find_project_root(start: Path | None = None) -> Path:
    """Walk parents for mason.yaml. Returns the project root."""
    cur = (start or Path.cwd()).resolve()
    for path in [cur, *cur.parents]:
        if (path / "mason.yaml").is_file():
            return path
    raise MasonError(
        "Not inside a Mason project (no mason.yaml found).",
        code="not_a_project",
        hint="Run mason init in the project directory.",
    )


def init_project(root: Path, name: str | None = None) -> dict[str, str]:
    """Create mason.yaml, .mason/, and styles/default.yaml."""
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    created: dict[str, str] = {}

    config = ProjectConfig(name=name or root.name)
    mason_yaml = save_project_config(root, config)
    created["mason.yaml"] = str(mason_yaml)

    jobs = root / ".mason" / "jobs"
    jobs.mkdir(parents=True, exist_ok=True)
    created["jobs"] = str(jobs)

    styles = root / "styles"
    styles.mkdir(parents=True, exist_ok=True)
    default_style = styles / "default.yaml"
    if not default_style.is_file():
        default_style.write_text(DEFAULT_STYLE_YAML, encoding="utf-8")
    created["style"] = str(default_style)

    agents = root / "AGENTS.md"
    _ensure_agents_workflow(agents)
    created["agents"] = str(agents)
    return created


def _ensure_agents_workflow(path: Path) -> None:
    """Append Mason workflow to AGENTS.md if it is missing."""
    marker = "# Mason Agent Workflow"
    if path.is_file():
        text = path.read_text(encoding="utf-8")
        if marker in text:
            return
        path.write_text(text.rstrip() + "\n" + MASON_WORKFLOW, encoding="utf-8")
        return
    path.write_text(MASON_WORKFLOW.lstrip(), encoding="utf-8")
