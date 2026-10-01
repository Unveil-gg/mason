"""Install the Mason skill into a project or the user home."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from mason.errors import MasonError

_LINK_DIRS = (".cursor", ".claude")


def skill_source() -> Path:
    """Return the shipped skill directory (contains SKILL.md)."""
    here = Path(__file__).resolve()
    candidates = (
        here.parents[3] / "skills" / "mason",
        here.parents[1] / "data" / "skill",
    )
    for path in candidates:
        if (path / "SKILL.md").is_file():
            return path
    raise MasonError(
        "Mason skill files are missing from this install.",
        code="skill_missing",
        hint="Reinstall Mason from the git repo.",
    )


def workflow_text() -> str:
    """Return the directed-loop reference shipped with the skill."""
    path = skill_source() / "references" / "workflow.md"
    if not path.is_file():
        raise MasonError(
            "Directed workflow reference is missing.",
            code="skill_missing",
        )
    return path.read_text(encoding="utf-8")


def install_skill(canonical: Path) -> dict[str, str]:
    """Copy the skill to canonical and link Cursor and Claude.

    canonical is `<root>/.agents/skills/mason` or the user
    equivalent. Returns the paths written.
    """
    _replace_tree(skill_source(), canonical)
    created = {"skill": str(canonical)}
    root = canonical.parents[2]
    for agent in _LINK_DIRS:
        link = root / agent / "skills" / "mason"
        _link_or_copy(canonical, link)
        key = agent.removeprefix(".") + "_skill"
        created[key] = str(link)
    return created


def _replace_tree(src: Path, dest: Path) -> None:
    """Replace dest with a copy of src."""
    _remove_path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest)


def _link_or_copy(canonical: Path, link: Path) -> None:
    """Point link at canonical. Copy the tree if symlink fails."""
    link.parent.mkdir(parents=True, exist_ok=True)
    _remove_path(link)
    try:
        try:
            target: str | Path = os.path.relpath(canonical, link.parent)
        except ValueError:
            target = canonical
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        shutil.copytree(canonical, link)


def _remove_path(path: Path) -> None:
    """Delete a file, symlink, or directory. Missing is fine."""
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
