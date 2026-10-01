"""Project root discovery and mason init."""

from __future__ import annotations

from pathlib import Path

from mason.core.config import ProjectConfig, save_project_config
from mason.core.skill_install import install_skill
from mason.errors import MasonError

_GITIGNORE_LINE = ".mason/"


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
    """Create mason.yaml, .mason/, a gitignore line, and the skill.

    Leaves an existing mason.yaml and any styles/ files unchanged.
    Does not write AGENTS.md, CLAUDE.md, or styles/default.yaml.
    Returns the paths written or reused.
    """
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    created: dict[str, str] = {}

    mason_yaml = root / "mason.yaml"
    if not mason_yaml.is_file():
        config = ProjectConfig(name=name or root.name)
        save_project_config(root, config)
    created["mason.yaml"] = str(mason_yaml)

    jobs = root / ".mason" / "jobs"
    jobs.mkdir(parents=True, exist_ok=True)
    created["jobs"] = str(jobs)

    ignored = _ensure_gitignore(root)
    if ignored:
        created["gitignore"] = ignored

    skill = root / ".agents" / "skills" / "mason"
    created.update(install_skill(skill))
    return created


def init_global(home: Path | None = None) -> dict[str, str]:
    """Install the skill for one user. No project files.

    home defaults to the user home directory. Returns skill paths.
    """
    base = (home or Path.home()).resolve()
    return install_skill(base / ".agents" / "skills" / "mason")


def _ensure_gitignore(root: Path) -> str | None:
    """Append .mason/ when a gitignore already exists. Returns path."""
    path = root / ".gitignore"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    lines = {line.strip() for line in text.splitlines()}
    if _GITIGNORE_LINE in lines or ".mason" in lines:
        return None
    suffix = "" if text.endswith("\n") or text == "" else "\n"
    path.write_text(text + suffix + _GITIGNORE_LINE + "\n", encoding="utf-8")
    return str(path)
