"""Copy an asset's finished outputs into another project (e.g. a game
engine workspace). Working files (.blend/.kra/.aseprite) and previews
are not copied; only the final artifacts (glb/png/frames.json) are.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from mason.core.config import load_project_config
from mason.core.jobs import AssetJob, require_job
from mason.core.results import ExportResult
from mason.core.workspace import find_project_root
from mason.errors import MasonError

INSTALLABLE_KEYS = {"glb", "png", "frames"}
GODOT_SUBDIRS = {"glb": "models", "png": "textures", "frames": "textures"}
INSTALL_NAMES = {"frames": "{id}_frames.json"}


def _resolve_dest(root: Path, raw: str | Path) -> Path:
    """Resolve an install dir. Absolute paths pass through; relative
    paths resolve against the project root and may point outside it
    (e.g. a sibling game project) -- that escape is intentional here.
    """
    path = Path(raw)
    return path if path.is_absolute() else (root / path).resolve()


def _install_dir(root: Path, job: AssetJob, override: Path | None) -> Path:
    """Pick the install dir: --to > spec export.install_to > mason.yaml."""
    if override:
        return _resolve_dest(root, override)
    spec = job.load_spec()
    install_to = getattr(spec.export, "install_to", None)
    if install_to:
        return _resolve_dest(root, install_to)
    config = load_project_config(root)
    if config.install_dir:
        return _resolve_dest(root, config.install_dir)
    raise MasonError(
        "No install destination configured.",
        code="no_install_dir",
        hint=(
            "Pass --to <dir>, set export.install_to in the asset spec, "
            "or install_dir in mason.yaml."
        ),
    )


def _manifest_extra(job: AssetJob) -> dict:
    """Pull bounds / animation metadata from the last build result."""
    result = job.load_result()
    if result is None:
        return {}
    extra: dict = {}
    for key in ("bounds", "animations", "frame_size"):
        value = result.validation.get(key)
        if value:
            extra[key] = value
    return extra


def _update_manifest(
    dest_dir: Path,
    asset_id: str,
    engine: str,
    installed: dict[str, str],
    extra: dict | None = None,
) -> Path:
    """Merge this export into `mason_manifest.json` at the destination
    root, so an agent can see what Mason has put here without needing
    the Mason project."""
    manifest_path = dest_dir / "mason_manifest.json"
    data: dict = {"assets": {}}
    if manifest_path.is_file():
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except ValueError:
            data = {"assets": {}}
    entry = {
        "engine": engine,
        "files": installed,
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        entry.update(extra)
    data.setdefault("assets", {})[asset_id] = entry
    manifest_path.write_text(
        json.dumps(data, indent=2), encoding="utf-8",
    )
    return manifest_path


def run_export(
    asset_id: str,
    to: Path | None = None,
    engine: str = "generic",
) -> ExportResult:
    """Copy a built asset's finished outputs into a target project.

    Args:
        asset_id: Job/asset id to export.
        to: Optional destination dir, overriding spec/project config.
        engine: "generic" (flat copy) or "godot" (models/textures
            subfolders, for res:// friendly layout).

    Returns:
        ExportResult with the absolute paths written.
    """
    root = find_project_root()
    job = require_job(root, asset_id)
    result = job.load_result()
    if result is None:
        raise MasonError(
            f"No build result for '{asset_id}'. Run mason build first.",
            code="no_result",
            context={"asset_id": asset_id},
        )
    dest_dir = _install_dir(root, job, to)
    installed: dict[str, str] = {}
    for key, rel_path in result.outputs.items():
        if key not in INSTALLABLE_KEYS:
            continue
        src = root / rel_path
        if not src.is_file():
            continue
        sub = GODOT_SUBDIRS.get(key, "") if engine == "godot" else ""
        target_dir = (dest_dir / sub) if sub else dest_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        name = INSTALL_NAMES.get(key)
        dest = target_dir / (
            name.format(id=asset_id) if name else f"{asset_id}{src.suffix}"
        )
        dest.write_bytes(src.read_bytes())
        installed[key] = str(dest)
    manifest = None
    if installed:
        manifest = str(_update_manifest(
            dest_dir, asset_id, engine, installed, _manifest_extra(job),
        ))
    return ExportResult(
        success=bool(installed),
        asset_id=asset_id,
        engine=engine,
        installed=installed,
        manifest=manifest,
    )
