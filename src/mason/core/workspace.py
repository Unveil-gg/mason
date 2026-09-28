"""Project root discovery and mason init."""

from __future__ import annotations

from pathlib import Path

from mason.core.agent_workflow import MASON_WORKFLOW
from mason.core.config import ProjectConfig, save_project_config
from mason.core.styles import DEFAULT_STYLE_YAML
from mason.errors import MasonError

START_MARKER = "# Mason Agent Workflow"
END_MARKER = "# End Mason Agent Workflow"


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
    """Create mason.yaml, .mason/, styles/default.yaml, and agent files."""
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
    claude = root / "CLAUDE.md"
    _write_workflow(agents)
    _write_workflow(claude)
    created["agents"] = str(agents)
    created["claude"] = str(claude)
    return created


def _write_workflow(path: Path) -> None:
    """Insert or replace the marked workflow block in path."""
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    path.write_text(_splice_workflow(text), encoding="utf-8")


def _splice_workflow(text: str) -> str:
    """Return text with one current Mason workflow block."""
    block = MASON_WORKFLOW.strip() + "\n"
    start = text.find(START_MARKER)
    if start < 0:
        body = text.rstrip()
        return (body + "\n\n" + block) if body else block
    end_at = text.find(END_MARKER, start)
    if end_at < 0:
        head = text[:start].rstrip()
        return (head + "\n\n" + block) if head else block
    after = end_at + len(END_MARKER)
    if text[after:after + 1] == "\n":
        after += 1
    head = text[:start].rstrip()
    tail = text[after:].strip()
    parts: list[str] = []
    if head:
        parts.append(head)
    parts.append(block.rstrip("\n"))
    if tail:
        parts.append(tail)
    return "\n\n".join(parts) + "\n"
