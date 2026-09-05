"""Optional live-tool integration tests. Skip if tools are missing."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from PIL import Image
from typer.testing import CliRunner

from mason.cli import app
from mason.tools.registry import detect_all

runner = CliRunner()


def _tools():
    return detect_all()


@pytest.mark.integration
def test_blender_crate_build(project: Path, crate_yaml: Path, monkeypatch) -> None:
    tools = _tools()
    if not tools["blender"].available:
        pytest.skip("Blender not installed")
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["build", str(crate_yaml), "--json"])
    assert result.exit_code == 0, result.stdout + result.stderr
    glb = project / ".mason" / "jobs" / "simple_crate" / "output" / "asset.glb"
    preview = (
        project / ".mason" / "jobs" / "simple_crate" / "previews" / "front.png"
    )
    assert glb.is_file() and glb.stat().st_size > 0
    assert preview.is_file()
    data = __import__("json").loads(result.stdout)
    assert data["validation"]["passed"] is True


@pytest.mark.integration
def test_imagemagick_resize(project: Path, monkeypatch) -> None:
    tools = _tools()
    if not tools["imagemagick"].available:
        pytest.skip("ImageMagick not installed")
    src = project / "swatch.png"
    Image.new("RGB", (128, 64), (200, 80, 40)).save(src)
    spec = {
        "type": "image_process",
        "id": "swatch_32",
        "name": "Swatch",
        "source": {"path": "swatch.png"},
        "operations": [{
            "op": "resize",
            "width": 32,
            "height": 32,
            "fit": "stretch",
        }],
    }
    spec_path = project / "swatch.yaml"
    spec_path.write_text(yaml.safe_dump(spec), encoding="utf-8")
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["build", str(spec_path), "--json"])
    assert result.exit_code == 0, result.stdout + result.stderr
    out = project / ".mason" / "jobs" / "swatch_32" / "output" / "asset.png"
    assert out.is_file()
    with Image.open(out) as img:
        assert img.size == (32, 32)
    preview = project / ".mason" / "jobs" / "swatch_32" / "previews" / "full.png"
    assert preview.is_file()


@pytest.mark.integration
def test_krita_panel(project: Path, monkeypatch) -> None:
    tools = _tools()
    info = tools["krita"]
    if not info.available or not (info.extras or {}).get("kritarunner"):
        pytest.skip("Krita/kritarunner not installed")
    spec = {
        "type": "layered_raster",
        "id": "panel",
        "name": "Panel",
        "dimensions": {"width": 64, "height": 64},
        "layers": [
            {"name": "background", "fill": "cream"},
            {"name": "accent", "fill": "accent",
             "rect": {"x": 0, "y": 0, "width": 64, "height": 8}},
        ],
    }
    path = project / "panel.yaml"
    path.write_text(yaml.safe_dump(spec), encoding="utf-8")
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["build", str(path), "--json"])
    assert result.exit_code == 0, result.stdout + result.stderr
    preview = project / ".mason" / "jobs" / "panel" / "previews" / "full.png"
    assert preview.is_file()


@pytest.mark.integration
def test_aseprite_sprite_sheet(project: Path, monkeypatch) -> None:
    tools = _tools()
    if not tools["aseprite"].available:
        pytest.skip("Aseprite not installed")
    spec = {
        "type": "sprite_sheet",
        "id": "hero",
        "name": "Hero",
        "canvas": {"width": 8, "height": 8},
        "animations": [
            {
                "name": "idle",
                "loop": True,
                "frames": [
                    {
                        "duration_ms": 200,
                        "layers": [{
                            "name": "body",
                            "pixels": [
                                "IIII....",
                                "I..I....",
                                "IIII....",
                                "........",
                                "........",
                                "........",
                                "........",
                                "........",
                            ],
                            "keys": {"I": "ink"},
                        }],
                    },
                    {
                        "duration_ms": 200,
                        "layers": [{
                            "name": "body",
                            "pixels": [
                                ".IIII...",
                                ".I..I...",
                                ".IIII...",
                                "........",
                                "........",
                                "........",
                                "........",
                                "........",
                            ],
                            "keys": {"I": "ink"},
                        }],
                    },
                ],
            },
        ],
    }
    path = project / "hero.yaml"
    path.write_text(yaml.safe_dump(spec), encoding="utf-8")
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["build", str(path), "--json"])
    assert result.exit_code == 0, result.stdout + result.stderr
    out = project / ".mason" / "jobs" / "hero" / "output"
    png = out / "asset.png"
    frames = out / "frames.json"
    preview = project / ".mason" / "jobs" / "hero" / "previews" / "full.png"
    assert png.is_file() and png.stat().st_size > 0
    assert frames.is_file()
    assert preview.is_file()
    with Image.open(png) as img:
        assert img.size == (16, 8)
    data = __import__("json").loads(frames.read_text(encoding="utf-8"))
    assert data["animations"][0]["name"] == "idle"
    assert data["animations"][0]["frames"][1]["x"] == 8
