"""Silhouette ingest extracts a ratio and writes a PNG."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image
from typer.testing import CliRunner

from mason.cli import app
from mason.core.assets import parse_asset_spec
from mason.core.jobs import AssetJob
from mason.core.styles import load_style
from mason.pipelines.ingest import (
    analyze_image,
    extract_silhouette,
    silhouette_iou,
)

runner = CliRunner()


def _dark_rect(path: Path) -> None:
    img = Image.new("L", (40, 80), 255)
    for x in range(10, 30):
        for y in range(10, 70):
            img.putpixel((x, y), 0)
    img.save(path)


def _color_blocks(path: Path) -> None:
    """80x40 RGB image: a red block (subject) plus a smaller blue
    block, on a white background -- two distinct color regions."""
    img = Image.new("RGB", (80, 40), (255, 255, 255))
    for x in range(10, 50):
        for y in range(5, 35):
            img.putpixel((x, y), (200, 30, 30))
    for x in range(55, 75):
        for y in range(10, 30):
            img.putpixel((x, y), (30, 30, 200))
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


def test_analyze_image_measures_palette_and_regions(
    tmp_path: Path,
) -> None:
    src = tmp_path / "ref.png"
    _color_blocks(src)
    analysis = analyze_image(src)
    assert analysis.source_size.width == 80
    assert analysis.source_size.height == 40
    assert analysis.palette.dominant
    assert len(analysis.regions) >= 2
    assert analysis.edges in ("hard", "soft")
    assert analysis.contour


def test_analyze_image_maps_style_palette_keys(
    tmp_path: Path, project: Path,
) -> None:
    src = tmp_path / "ref.png"
    _color_blocks(src)
    style = load_style(project / "styles" / "default.yaml")
    analysis = analyze_image(src, style)
    assert analysis.palette_keys.dominant in style.palette


def test_ingest_scaffolds_static_prop(
    project: Path, monkeypatch, tmp_path: Path,
) -> None:
    src = tmp_path / "ref.png"
    _color_blocks(src)
    monkeypatch.chdir(project)
    result = runner.invoke(
        app,
        [
            "ingest", str(src), "--asset", "newthing",
            "--type", "static_prop", "--json",
        ],
    )
    assert result.exit_code == 0, result.stdout
    data = json.loads(result.stdout)
    assert data["scaffold"]
    job = AssetJob(project, "newthing")
    assert job.exists()
    spec = job.load_spec()
    assert spec.type == "static_prop"
    assert spec.geometry.parts[0].name == "mass"
    assert spec.art_analysis is not None
    assert spec.art_analysis.regions


def test_ingest_scaffolds_layered_raster(
    project: Path, monkeypatch, tmp_path: Path,
) -> None:
    src = tmp_path / "ref.png"
    _color_blocks(src)
    monkeypatch.chdir(project)
    result = runner.invoke(
        app,
        [
            "ingest", str(src), "--asset", "newposter",
            "--type", "layered_raster", "--json",
        ],
    )
    assert result.exit_code == 0, result.stdout
    job = AssetJob(project, "newposter")
    assert job.exists()
    spec = job.load_spec()
    assert spec.type == "layered_raster"
    assert spec.layers[0].role == "background"
    assert spec.layers[1].role == "image"


def test_ingest_preserves_existing_geometry(
    project: Path, monkeypatch, tmp_path: Path,
) -> None:
    """Re-ingesting onto a built job must not touch parts/layers."""
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
    _color_blocks(src)
    monkeypatch.chdir(project)
    result = runner.invoke(
        app, ["ingest", str(src), "--asset", "box", "--json"],
    )
    assert result.exit_code == 0, result.stdout
    loaded = job.load_spec()
    assert loaded.geometry.recipe == "crate"
    assert loaded.art_analysis is not None
    assert loaded.art_analysis.regions


def test_ingest_fetch_caches_ref(
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
    from io import BytesIO
    buf = BytesIO()
    Image.new("RGB", (20, 40), (10, 10, 10)).save(buf, format="PNG")
    payload = buf.getvalue()

    class _Headers:
        def get_content_type(self) -> str:
            return "image/png"

    class _Resp:
        headers = _Headers()

        def read(self, _n: int) -> bytes:
            return payload

        def __enter__(self) -> "_Resp":
            return self

        def __exit__(self, *_args) -> bool:
            return False

    monkeypatch.setattr(
        "mason.pipelines.fetch.urlopen",
        lambda _req, timeout=None: _Resp(),
    )
    monkeypatch.chdir(project)
    result = runner.invoke(
        app,
        [
            "ingest", "--fetch", "https://example.com/ref.png",
            "--asset", "box", "--json",
        ],
    )
    assert result.exit_code == 0, result.stdout
    data = json.loads(result.stdout)
    assert data["source_url"] == "https://example.com/ref.png"
    cached = job.dir / "refs" / "ref.png"
    assert cached.is_file()
    assert (job.dir / "refs" / "ref.source.json").is_file()
    assert job.run_json.is_file()
