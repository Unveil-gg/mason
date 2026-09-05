"""Export pipeline: copy finished outputs into another project."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mason.core.assets import parse_asset_spec
from mason.core.config import load_project_config, save_project_config
from mason.core.jobs import AssetJob
from mason.core.results import BuildResult
from mason.errors import MasonError
from mason.pipelines.export import run_export


def _make_job(project: Path, asset_id: str = "box") -> AssetJob:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": asset_id,
        "name": "Box",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {"recipe": "crate"},
    })
    job = AssetJob(project, asset_id)
    job.prepare()
    job.write_spec(spec)
    glb = job.output / "asset.glb"
    glb.write_bytes(b"glb-bytes")
    result = BuildResult(
        success=True,
        asset_id=asset_id,
        asset_type="static_prop",
        outputs={"glb": job.rel(glb)},
    )
    job.write_result(result)
    return job


def test_export_requires_destination(project: Path, monkeypatch) -> None:
    monkeypatch.chdir(project)
    _make_job(project)
    with pytest.raises(MasonError):
        run_export("box")


def test_export_uses_to_override(
    project: Path, monkeypatch, tmp_path: Path,
) -> None:
    monkeypatch.chdir(project)
    _make_job(project)
    dest = tmp_path / "godot_project" / "res"
    result = run_export("box", to=dest)
    assert result.success
    assert (dest / "box.glb").is_file()
    assert result.installed["glb"] == str(dest / "box.glb")


def test_export_uses_project_config(
    project: Path, monkeypatch, tmp_path: Path,
) -> None:
    monkeypatch.chdir(project)
    _make_job(project)
    config = load_project_config(project)
    config.install_dir = str(tmp_path / "install_from_config")
    save_project_config(project, config)
    run_export("box")
    assert (tmp_path / "install_from_config" / "box.glb").is_file()


def test_export_godot_subfolder(
    project: Path, monkeypatch, tmp_path: Path,
) -> None:
    monkeypatch.chdir(project)
    _make_job(project)
    dest = tmp_path / "res"
    result = run_export("box", to=dest, engine="godot")
    assert (dest / "models" / "box.glb").is_file()
    assert result.installed["glb"] == str(dest / "models" / "box.glb")


def test_export_writes_manifest(
    project: Path, monkeypatch, tmp_path: Path,
) -> None:
    monkeypatch.chdir(project)
    _make_job(project, "box")
    _make_job(project, "crate")
    dest = tmp_path / "res"
    run_export("box", to=dest)
    result = run_export("crate", to=dest)
    manifest = json.loads(Path(result.manifest).read_text(encoding="utf-8"))
    assert set(manifest["assets"]) == {"box", "crate"}
    assert manifest["assets"]["crate"]["files"]["glb"] == str(dest / "crate.glb")
