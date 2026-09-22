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
from mason.core.kits import KitSpec, resolve_kit
from mason.core.results import ExportResult, KitExportResult
from mason.core.workspace import find_project_root
from mason.errors import MasonError

INSTALLABLE_KEYS = {"glb", "png", "frames"}
_OUTPUT_NAMES = {"glb": "asset.glb", "png": "asset.png", "frames": "frames.json"}
GODOT_SUBDIRS = {"glb": "models", "png": "textures", "frames": "textures"}
INSTALL_NAMES = {"frames": "{id}_frames.json"}


def _export_source(
    root: Path,
    job: AssetJob,
    key: str,
    rel_path: str,
    *,
    best: bool = False,
) -> Path | None:
    """Pick the GLB/PNG to install.

    Default: latest live output/ (most recent rebuild). Pass best=True
    to ship the promoted current_best snapshot instead.
    """
    name = _OUTPUT_NAMES.get(key)
    live = root / rel_path
    if not best and live.is_file():
        return live
    meta = job.load_meta()
    if meta and meta.current_best and name:
        snap = (
            job.iterations / f"{meta.current_best:03d}" / "output" / name
        )
        if snap.is_file():
            return snap
    return live if live.is_file() else None


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
    for key in (
        "bounds", "animations", "frame_size", "attachments", "volumes",
    ):
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


def _copy_atlas_sidecars(
    src_glb: Path, dest_glb: Path, asset_id: str,
) -> dict[str, str]:
    """Place baked atlas PNGs beside the installed GLB."""
    names = {
        "atlas_albedo.png": f"{asset_id}_albedo.png",
        "atlas_orm.png": f"{asset_id}_orm.png",
    }
    copied: dict[str, str] = {}
    for src_name, dest_name in names.items():
        src = src_glb.parent / src_name
        if not src.is_file():
            continue
        dest = dest_glb.parent / dest_name
        dest.write_bytes(src.read_bytes())
        copied[dest.stem] = str(dest)
    return copied


def run_export(
    asset_id: str,
    to: Path | None = None,
    engine: str = "generic",
    *,
    best: bool = False,
    layout: str = "flat",
) -> ExportResult:
    """Copy a built asset's finished outputs into a target project.

    Args:
        asset_id: Job/asset id to export.
        to: Optional destination dir, overriding spec/project config.
        engine: "generic" or "godot" (manifest only; layout is
            separate).
        layout: "flat" writes into --to. "grouped" adds models/
            and textures/ subfolders.

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
        src = _export_source(root, job, key, rel_path, best=best)
        if src is None or not src.is_file():
            continue
        sub = GODOT_SUBDIRS.get(key, "") if layout == "grouped" else ""
        target_dir = (dest_dir / sub) if sub else dest_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        name = INSTALL_NAMES.get(key)
        dest = target_dir / (
            name.format(id=asset_id) if name else f"{asset_id}{src.suffix}"
        )
        dest.write_bytes(src.read_bytes())
        installed[key] = str(dest)
        if key == "glb":
            installed.update(_copy_atlas_sidecars(src, dest, asset_id))
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


def _update_kit_manifest(dest_dir: Path, kit: KitSpec) -> Path:
    """Write `kits.<id>` alongside the `assets` block on the same
    manifest members were installed to."""
    manifest_path = dest_dir / "mason_manifest.json"
    data: dict = {"assets": {}}
    if manifest_path.is_file():
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except ValueError:
            data = {"assets": {}}
    data.setdefault("kits", {})[kit.id] = {
        "name": kit.name,
        "members": list(kit.members),
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return manifest_path


def run_export_kit(
    kit: str,
    to: Path | None = None,
    engine: str = "generic",
    *,
    best: bool = False,
    layout: str = "flat",
) -> KitExportResult:
    """Export every member of a kit (an already-built asset pack).

    Reuses `run_export` per member so Godot layout and manifest
    `assets` entries stay identical to a plain single-asset export.
    Fails before copying anything if a member has no successful
    build.

    Args:
        kit: Kit id, or a path to a kit YAML.
        to: Optional destination dir, overriding spec/project config.
        engine: "generic" or "godot".

    Returns:
        KitExportResult with each member's ExportResult.
    """
    root = find_project_root()
    spec = resolve_kit(root, kit)
    for member in spec.members:
        job = require_job(root, member)
        result = job.load_result()
        if result is None or not result.success:
            raise MasonError(
                f"Kit member '{member}' has no successful build.",
                code="kit_member_not_built",
                hint=f"Run mason build for '{member}' first.",
                context={"kit": spec.id, "member": member},
            )
    members: dict[str, ExportResult] = {
        member: run_export(
            member, to, engine, best=best, layout=layout,
        )
        for member in spec.members
    }
    manifest_path = next(
        (Path(m.manifest) for m in members.values() if m.manifest), None,
    )
    if manifest_path:
        manifest_path = _update_kit_manifest(manifest_path.parent, spec)
    return KitExportResult(
        success=all(m.success for m in members.values()),
        kit_id=spec.id,
        engine=engine,
        members=members,
        manifest=str(manifest_path) if manifest_path else None,
    )
