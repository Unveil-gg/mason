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


def resolve_job_file(root: Path, asset_id: str, rel_file: str) -> Path:
    """Resolve `<root>/.mason/jobs/<asset_id>/<rel_file>`; reject
    escapes outside the project."""
    base = root / ".mason" / "jobs" / asset_id
    return resolve_project_path(root, str(base / rel_file))


def resolve_image_source(source, root: Path) -> Path:
    """Resolve an image reference (literal `path`, or another asset's
    `asset` + `file`) to an absolute path inside the project. Accepts
    any object with `.path`/`.asset`/`.file` attributes."""
    if source.path:
        return resolve_project_path(root, source.path)
    assert source.asset and source.file
    return resolve_job_file(root, source.asset, source.file)
