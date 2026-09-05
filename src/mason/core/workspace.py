"""Project root discovery and mason init."""

from __future__ import annotations

from pathlib import Path

from mason.core.config import ProjectConfig, save_project_config
from mason.core.styles import DEFAULT_STYLE_YAML
from mason.errors import MasonError

MASON_WORKFLOW = """
# Mason Agent Workflow

Before generating assets:

1. Run `mason doctor --json`.
2. Confirm the required capabilities are available.
3. Read the project's Mason style profile.
4. Create or modify an AssetSpec YAML.
5. Run `mason build <spec> --json`.
6. Check validation results.
7. Open and inspect generated preview images.
8. If the asset does not visually satisfy the request, modify the spec and rebuild.
9. Continue until technical validation passes and the visual result is acceptable.
10. Treat asset.yaml and build.py as reproducible source artifacts.

Important rules:

- Do not manually operate Blender, Krita, or Aseprite when Mason can invoke them.
- Prefer editing specs/generator source and rebuilding.
- Do not assume a successful tool exit means the asset looks correct.
- Always inspect previews.
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
