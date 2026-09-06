"""Silhouette ingest extracts a ratio and writes a PNG."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image
from typer.testing import CliRunner

from mason.cli import app
from mason.core.assets import parse_asset_spec
from mason.core.jobs import AssetJob
from mason.pipelines.ingest import extract_silhouette, silhouette_iou

runner = CliRunner()


def _dark_rect(path: Path) -> None:
    img = Image.new("L", (40, 80), 255)
    for x in range(10, 30):
        for y in range(10, 70):
            img.putpixel((x, y), 0)
    img.save(path)


def test_extract_ratio(tmp_path: Path) -> None:
    src = tmp_path / "ref.png"
    _dark_rect(src)
    _image, ratio = extract_silhouette(src)
    assert ratio == 3.0


def test_ingest_cli(tmp_path: Path, monkeypatch, project: Path) -> None:
    src = tmp_path / "ref.png"
    _dark_rect(src)
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["ingest", str(src), "--json"])
    assert result.exit_code == 0, result.stdout
    data = json.loads(result.stdout)
    assert data["height_width_ratio"] == 3.0
    assert Path(data["path"]).is_file()


def test_ingest_asset_updates_analysis(
    project: Path, monkeypatch, tmp_path: Path,
) -> None:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "box",
        "name": "Box",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {"recipe": "crate"},
    })
    job = AssetJob(project, spec.id)
    job.prepare()
    job.write_spec(spec)
    job.write_meta(None)
    src = tmp_path / "ref.png"
    _dark_rect(src)
    monkeypatch.chdir(project)
    result = runner.invoke(
        app, ["ingest", str(src), "--asset", "box", "--json"],
    )
    assert result.exit_code == 0, result.stdout
    loaded = job.load_spec()
    assert loaded.art_analysis is not None
    assert loaded.art_analysis.proportions.height_width_ratio == 3.0
    assert (job.previews / "reference_silhouette.png").is_file()


def test_silhouette_iou_self(tmp_path: Path) -> None:
    src = tmp_path / "a.png"
    _dark_rect(src)
    image, _ratio = extract_silhouette(src)
    dest = tmp_path / "sil.png"
    image.save(dest)
    assert silhouette_iou(dest, dest) == 1.0
