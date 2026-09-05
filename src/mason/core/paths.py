"""Safe path resolution inside a project tree."""

from __future__ import annotations

from pathlib import Path

from mason.errors import MasonError


def resolve_project_path(root: Path, raw: str) -> Path:
    """Resolve a project-relative path; reject escapes."""
    root = root.resolve()
    path = Path(raw)
    if not path.is_absolute():
        path = root / path
    resolved = path.resolve()
    if resolved != root and root not in resolved.parents:
        raise MasonError(
            f"Path is outside the project: {raw}",
            code="path_escape",
            context={"path": raw},
        )
    return resolved
