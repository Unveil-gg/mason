"""Kits: named lists of already-built jobs, for multi-model packs.

A kit does not build, does not merge meshes, and does not invent a
new asset type. `mason export --kit` fans `run_export` over each
member so layout and manifest entries stay identical to a plain
single-asset export.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from mason.errors import MasonError


class KitSpec(BaseModel):
    """A named list of member asset ids to export together."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    members: list[str] = Field(min_length=1)


def load_kit(path: Path) -> KitSpec:
    """Parse a kit YAML file at an exact path."""
    if not path.is_file():
        raise MasonError(
            f"Kit spec not found: {path}",
            code="kit_missing",
            context={"path": str(path)},
        )
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    try:
        return KitSpec.model_validate(data)
    except ValidationError as exc:
        raise MasonError(
            f"Invalid kit spec: {exc}",
            code="kit_invalid",
            context={"path": str(path)},
        ) from exc


def resolve_kit(root: Path, raw: str) -> KitSpec:
    """Load a kit from a literal path, a project-relative path, or a
    bare id resolved under `kits/<id>.yaml`."""
    candidate = Path(raw)
    if candidate.is_file():
        return load_kit(candidate)
    direct = root / raw
    if direct.is_file():
        return load_kit(direct)
    named = root / "kits" / f"{raw}.yaml"
    if named.is_file():
        return load_kit(named)
    raise MasonError(
        f"Kit not found: {raw}",
        code="kit_missing",
        hint="Use a path to a kit YAML, or a bare id under kits/.",
        context={"kit": raw},
    )
