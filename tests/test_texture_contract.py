"""Texture contract: part.texture resolution across jobs."""

from __future__ import annotations

from pathlib import Path

import pytest

from mason.core.jobs import AssetJob
from mason.core.parts import ImageSource, PropPart
from mason.errors import MasonError
from mason.pipelines.static_prop import resolve_part_textures


def _job(project: Path, asset_id: str = "crate") -> AssetJob:
    job = AssetJob(project, asset_id)
    job.prepare()
    return job


def test_resolve_part_textures_literal_path(project: Path) -> None:
    png = project / "textures" / "wood.png"
    png.parent.mkdir(parents=True)
    png.write_bytes(b"fake-png")
    job = _job(project)
    part = PropPart(
        name="crate", size=(1, 1, 1), location=(0, 0, 0.5),
        texture=ImageSource(path="textures/wood.png"),
    )
    textures = resolve_part_textures(job, [part])
    assert textures["crate"] == str(png.resolve())


def test_resolve_part_textures_cross_job(project: Path) -> None:
    other_output = project / ".mason" / "jobs" / "plank_texture" / "output"
    other_output.mkdir(parents=True)
    png = other_output / "asset.png"
    png.write_bytes(b"fake-png")
    job = _job(project)
    part = PropPart(
        name="crate", size=(1, 1, 1), location=(0, 0, 0.5),
        texture=ImageSource(asset="plank_texture", file="output/asset.png"),
    )
    textures = resolve_part_textures(job, [part])
    assert textures["crate"] == str(png.resolve())


def test_resolve_part_textures_missing_raises(project: Path) -> None:
    job = _job(project)
    part = PropPart(
        name="crate", size=(1, 1, 1), location=(0, 0, 0.5),
        texture=ImageSource(asset="missing_asset", file="output/asset.png"),
    )
    with pytest.raises(MasonError) as exc:
        resolve_part_textures(job, [part])
    assert exc.value.code == "texture_missing"


def test_no_texture_returns_empty(project: Path) -> None:
    job = _job(project)
    part = PropPart(name="crate", size=(1, 1, 1), location=(0, 0, 0.5))
    assert resolve_part_textures(job, [part]) == {}
